import hashlib
import logging
import secrets
import unicodedata
import uuid
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class CloverOperation(models.Model):
    _name = "doorandoor.clover.operation"
    _description = "Operación Clover Ecommerce"
    _order = "create_date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, readonly=True, copy=False, index=True)
    invoice_id = fields.Many2one("account.move", required=True, readonly=True, ondelete="restrict")
    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True, readonly=True)
    provider_id = fields.Many2one("payment.provider", required=True, readonly=True, ondelete="restrict")
    currency_id = fields.Many2one(related="invoice_id.currency_id", store=True, readonly=True)
    amount = fields.Monetary(required=True, readonly=True, currency_field="currency_id")
    collection_base_amount = fields.Monetary(
        string="Saldo aplicado a factura", readonly=True, currency_field="currency_id"
    )
    collection_fee_amount = fields.Monetary(
        string="Cargo de procesamiento", readonly=True, currency_field="currency_id"
    )
    state = fields.Selection([
        ("draft", "Borrador"), ("pending", "Esperando Clover"),
        ("approved", "Aprobada"), ("declined", "Rechazada"), ("cancelled", "Cancelada"),
        ("unknown", "En revisión"),
    ], default="pending", required=True, readonly=True, copy=False)
    provider_reference = fields.Char(string="Referencia Clover", readonly=True, copy=False)
    idempotency_key = fields.Char(required=True, readonly=True, copy=False, index=True)
    payment_register_id = fields.Integer(
        string="Identificador temporal del registro de pago", readonly=True, copy=False,
        help="Identificador técnico del wizard usado para crear el pago tras la aprobación."
    )
    payment_id = fields.Many2one("account.payment", string="Pago Odoo", readonly=True, copy=False)
    is_mock = fields.Boolean(string="Simulación local", readonly=True, copy=False)
    state_message = fields.Text(string="Detalle", readonly=True, copy=False)
    otp_hash = fields.Char(string="Huella OTP", readonly=True, copy=False)
    otp_sent_at = fields.Datetime(string="OTP enviado", readonly=True, copy=False)
    otp_expires_at = fields.Datetime(string="OTP vence", readonly=True, copy=False)
    otp_attempts = fields.Integer(string="Intentos OTP", readonly=True, default=0, copy=False)
    otp_verified_at = fields.Datetime(string="OTP validado", readonly=True, copy=False)
    otp_email = fields.Char(string="Email de autorización", readonly=True, copy=False)
    otp_delivery = fields.Selection([
        ("email", "Correo electrónico"), ("telegram", "Telegram de pruebas"),
    ], string="Canal OTP", readonly=True, copy=False)
    otp_destination = fields.Char(string="Destino OTP", readonly=True, copy=False)
    otp_mail_id = fields.Many2one(
        "mail.mail", string="Correo OTP", readonly=True, copy=False,
        help="Mensaje de salida conservado para la auditoría de esta autorización.",
    )
    cardholder_name = fields.Char(string="Titular declarado de la tarjeta", readonly=True, copy=False)
    cardholder_match = fields.Selection([
        ("pending", "Pendiente"), ("matched", "Coincide con cliente autorizado"),
        ("rejected", "No coincide"),
    ], string="Control de titular", default="pending", readonly=True, copy=False)
    portal_token = fields.Char(string="Token de acceso portal", readonly=True, copy=False, index=True)
    payment_channel = fields.Selection([
        ("backend", "Backoffice"), ("portal", "Portal cliente"),
    ], default="backend", required=True, readonly=True, copy=False)

    _sql_constraints = [
        ("doorandoor_clover_operation_idempotency_unique", "unique(idempotency_key)", "La clave de idempotencia Clover debe ser única."),
    ]

    @classmethod
    def _ddcl_new_idempotency_key(cls):
        return str(uuid.uuid4())

    @api.model_create_multi
    def create(self, vals_list):
        """Guarantee safe defaults for every entry point into Clover operations.

        Payment wizards can be extended by several DoorAndDoor modules.  This
        normalizes operations created through an older or external override so
        the database never receives an operation without its idempotency key.
        """
        normalized_vals_list = []
        for vals in vals_list:
            values = dict(vals)
            values.setdefault("idempotency_key", self._ddcl_new_idempotency_key())
            values.setdefault("state", "pending")
            normalized_vals_list.append(values)
        return super().create(normalized_vals_list)

    def action_mark_declined(self):
        self.write({"state": "declined", "state_message": _("Pago rechazado en el simulador Clover.")})
        return {"type": "ir.actions.act_window_close"}

    def _ddcl_register_approved_payment(self):
        """Register exactly what Clover collected without crediting the fee.

        For a later liquidation Clover collects residual plus fee.  The bank
        receives the total, the invoice is reconciled only for its residual,
        and the difference is credited to the configured fee-income account.
        """
        self.ensure_one()
        payment_register = self.env["account.payment.register"].browse(
            self.payment_register_id
        ).exists()
        if not payment_register:
            raise ValidationError(_("El registro temporal de pago expiró antes de la confirmación Clover."))
        if not self.collection_fee_amount:
            payment_register.with_context(ddcl_bypass_checkout=True).action_create_payments()
            payment = self.env["account.payment"].search([
                ("partner_id", "=", self.partner_id.id),
                ("amount", "=", self.collection_base_amount or self.amount),
                ("journal_id", "=", self.provider_id.journal_id.id),
            ], order="id desc", limit=1)
            return payment

        product = self.provider_id.ddtp_card_fee_product_id
        fee_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not fee_account:
            raise ValidationError(_("Configure una cuenta de ingresos para el cargo por pago con tarjeta."))
        card = self.provider_id.payment_method_ids.filtered(
            lambda method: method.code == "card"
        )[:1]
        if not card:
            raise ValidationError(_("Clover no tiene habilitado el método Tarjeta."))
        transaction = self.env["payment.transaction"].sudo().create({
            "provider_id": self.provider_id.id,
            "payment_method_id": card.id,
            "reference": self.env["payment.transaction"]._compute_reference(
                "clover", prefix=self.invoice_id.name
            ),
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.commercial_partner_id.id,
            "operation": "online_direct",
            "invoice_ids": [(6, 0, self.invoice_id.ids)],
            "ddtp_origin_invoice_id": self.invoice_id.id,
            "ddtp_collection_base_amount": self.collection_base_amount,
            "ddtp_collection_fee_amount": self.collection_fee_amount,
            "ddtp_collection_fee_account_id": fee_account.id,
        })
        # Control de Cobros normally validates linked payments as soon as
        # they are posted.  During a card checkout that is too early: it can
        # consume the receivable counterpart against Clover's internal
        # clearing entry before the payment transaction reconciles the sale
        # invoice.  Let the transaction finish its invoice allocation first.
        payment = transaction.with_context(
            ddc_skip_automatic_policy=True,
        )._create_payment()
        transaction.write({
            "provider_reference": self.provider_reference or self.reference,
        })
        transaction._set_done()
        self.invoice_id.message_post(body=_(
            "Clover liquidó %(base)s y cobró %(fee)s de cargo de procesamiento; total %(total)s."
        ) % {
            "base": self.currency_id.format(self.collection_base_amount),
            "fee": self.currency_id.format(self.collection_fee_amount),
            "total": self.currency_id.format(self.amount),
        })
        return payment


    def _ddcl_send_otp(self, delivery=None):
        self.ensure_one()
        if self.cardholder_match != "matched":
            raise ValidationError(_("Valide primero el titular autorizado de la tarjeta."))
        email = self.invoice_id.partner_id.email
        params = self.env["ir.config_parameter"].sudo()
        # The portal always delivers the authorization to the customer email.
        # Internal Telegram distribution remains exclusive to backoffice tests.
        delivery = delivery or params.get_param("doorandoor_clover.otp_delivery", "email")
        if delivery not in ("email", "telegram"):
            delivery = "email"
        if delivery == "email" and not email:
            raise ValidationError(_("La factura no tiene un correo de cliente para autorizar el pago con tarjeta."))
        code = "%06d" % secrets.randbelow(1000000)
        now = fields.Datetime.now()
        self.write({
            "otp_hash": hashlib.sha256((self.idempotency_key + code).encode()).hexdigest(),
            "otp_sent_at": now,
            "otp_expires_at": now + timedelta(minutes=10),
            "otp_attempts": 0,
            "otp_verified_at": False,
            "otp_email": email if delivery == "email" else False,
            "otp_delivery": delivery,
            "otp_destination": email if delivery == "email" else False,
            "state_message": _("Código de autorización preparado para entrega."),
        })
        if delivery == "telegram":
            self._ddcl_send_telegram_otp(code)
            return True
        mail = self.env["mail.mail"].sudo().create({
            "subject": _("Código de autorización para pago con tarjeta %(invoice)s") % {"invoice": self.invoice_id.name},
            "email_to": email,
            "body_html": "<p>Door &amp; Door solicita confirmar un pago con tarjeta de <strong>%s %s</strong> para la factura <strong>%s</strong>.</p><p>Su código de autorización es: <strong style=\"font-size:22px;letter-spacing:3px\">%s</strong></p><p>Vence en 10 minutos. No comparta este código si no autorizó el pago.</p>" % (self.amount, self.currency_id.name, self.invoice_id.name, code),
            # OTPs are evidence of a real authorization attempt.  Preserve
            # the outgoing message in Odoo's email queue instead of deleting
            # it after SMTP accepts delivery.
            "auto_delete": False,
            "model": self._name,
            "res_id": self.id,
        })
        try:
            mail.send()
        except Exception:
            # SMTP may be unavailable in a local environment.  Do not let the
            # transport exception roll back the previously validated holder or
            # turn an expected operational condition into an HTTP 500 page.
            _logger.exception("Clover OTP email delivery failed for operation %s", self.id)
            self.write({
                "otp_hash": False, "otp_sent_at": False, "otp_expires_at": False,
                "otp_attempts": 0, "otp_email": False, "otp_delivery": False, "otp_destination": False,
                "state_message": _("No fue posible entregar el código de autorización por correo."),
            })
            raise ValidationError(_(
                "No se pudo enviar el código al correo del cliente porque el SMTP local no está disponible. "
                "No se realizó ningún cargo; configure SMTP y solicite un código nuevo."
            ))
        mail.invalidate_recordset(["state", "failure_reason"])
        if mail.state == "exception":
            self.write({
                "otp_hash": False, "otp_sent_at": False, "otp_expires_at": False,
                "otp_attempts": 0, "otp_email": False, "otp_delivery": False, "otp_destination": False,
                "state_message": _("No fue posible entregar el código de autorización por correo."),
            })
            raise ValidationError(_(
                "No se pudo enviar el código al correo del cliente porque el SMTP local no está disponible. "
                "No se realizó ningún cargo; configure SMTP y solicite un código nuevo."
            ))
        self.write({
            "otp_mail_id": mail.id,
            "state_message": _("Código de autorización enviado por correo al cliente."),
        })
        return True

    def _ddcl_send_telegram_otp(self, code):
        """Deliver a Clover test OTP to the explicitly configured test chats."""
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_param("doorandoor_credit.telegram_bot_token")
        configured_chat_ids = params.get_param("doorandoor_clover.telegram_chat_ids", "")
        # Keep local development backwards compatible with the pre-existing
        # single test-chat configuration.  Pruebas may explicitly opt into
        # several internal validators through the Clover-specific parameter.
        chat_ids = [chat_id.strip() for chat_id in configured_chat_ids.split(",") if chat_id.strip()]
        if not chat_ids:
            fallback_chat_id = params.get_param("doorandoor_credit.telegram_chat_id")
            chat_ids = [fallback_chat_id] if fallback_chat_id else []
        chat_ids = list(dict.fromkeys(chat_ids))
        if not token or not chat_ids:
            self._ddcl_clear_otp_delivery()
            raise ValidationError(_(
                "Telegram de pruebas no está configurado. No se realizó ningún cargo; "
                "configure el canal o solicite entrega por correo."
            ))
        text = _(
            "DOORANDDOOR — AUTORIZACIÓN DE TARJETA CLOVER (PRUEBAS)\n\n"
            "Código: %(code)s\n"
            "Factura: %(invoice)s\n"
            "Cliente: %(partner)s\n"
            "Titular validado: %(holder)s\n"
            "Importe: %(amount)s\n\n"
            "Vence en 10 minutos y es de un solo uso. No comparta este código."
        ) % {
            "code": code,
            "invoice": self.invoice_id.name,
            "partner": self.invoice_id.partner_id.display_name,
            "holder": self.cardholder_name,
            "amount": self.currency_id.format(self.amount),
        }
        try:
            for chat_id in chat_ids:
                response = requests.post(
                    "https://api.telegram.org/bot%s/sendMessage" % token,
                    data={"chat_id": chat_id, "text": text}, timeout=10,
                )
                response.raise_for_status()
                if not response.json().get("ok"):
                    raise requests.RequestException("Telegram rechazó el envío del código.")
        except (requests.RequestException, ValueError) as error:
            _logger.exception("Clover OTP Telegram delivery failed for operation %s", self.id)
            self._ddcl_clear_otp_delivery()
            raise ValidationError(_(
                "No se pudo enviar el código por Telegram. No se realizó ningún cargo; "
                "revise el canal de pruebas y solicite un código nuevo."
            )) from error
        self.write({
            "otp_destination": ", ".join(chat_ids),
            "state_message": _("Código de autorización enviado por Telegram a los validadores de Pruebas."),
        })

    def _ddcl_clear_otp_delivery(self):
        self.ensure_one()
        self.write({
            "otp_hash": False, "otp_sent_at": False, "otp_expires_at": False,
            "otp_attempts": 0, "otp_email": False, "otp_delivery": False, "otp_destination": False,
            "state_message": _("No fue posible entregar el código de autorización."),
        })

    @staticmethod
    def _ddcl_normalize_name(value):
        value = unicodedata.normalize("NFKD", value or "")
        return " ".join("".join(char for char in value if not unicodedata.combining(char)).upper().split())

    def _ddcl_validate_cardholder(self, cardholder_name):
        self.ensure_one()
        declared = self._ddcl_normalize_name(cardholder_name)
        if not declared:
            raise ValidationError(_("Indique el nombre del titular de la tarjeta."))
        partner = self.invoice_id.partner_id
        authorized = partner | partner.commercial_partner_id | partner.parent_id | partner.commercial_partner_id.child_ids
        names = {self._ddcl_normalize_name(item.name) for item in authorized if item.name}
        if declared not in names:
            self.write({"cardholder_name": cardholder_name, "cardholder_match": "rejected", "state_message": _("El titular declarado no coincide con el cliente ni con un contacto empresarial autorizado.")})
            raise ValidationError(_("Titular no autorizado. El pago quedó bloqueado; registre primero la persona o empresa autorizada en el cliente."))
        self.write({"cardholder_name": cardholder_name, "cardholder_match": "matched", "state_message": _("Titular de tarjeta validado contra el cliente autorizado.")})
        return True

    def _ddcl_verify_otp(self, code):
        self.ensure_one()
        now = fields.Datetime.now()
        if self.otp_verified_at:
            return True
        if not self.otp_hash or not self.otp_expires_at or now > self.otp_expires_at:
            raise ValidationError(_("El código de autorización venció. Solicite uno nuevo."))
        if self.otp_attempts >= 3:
            raise ValidationError(_("Se agotaron los intentos del código. Solicite uno nuevo."))
        valid = secrets.compare_digest(
            self.otp_hash, hashlib.sha256((self.idempotency_key + (code or "")).encode()).hexdigest()
        )
        self.otp_attempts += 1
        if not valid:
            raise ValidationError(_("Código de autorización incorrecto."))
        self.write({"otp_verified_at": now, "state_message": _("Cliente autorizó el pago por código de un solo uso.")})
        return True
