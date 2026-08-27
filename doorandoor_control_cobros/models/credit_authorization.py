import hashlib
import hmac
import secrets
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCreditAuthorization(models.Model):
    _name = "doorandoor.credit.authorization"
    _description = "Autorizacion de pago con credito DoorAndDoor"
    _order = "create_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(default=lambda self: _("Nueva autorizacion"), readonly=True)
    partner_id = fields.Many2one("res.partner", required=True, readonly=True, index=True)
    invoice_id = fields.Many2one(
        "account.move", required=True, readonly=True, index=True, check_company=True
    )
    journal_id = fields.Many2one(
        "account.journal", required=True, readonly=True, check_company=True
    )
    company_id = fields.Many2one("res.company", required=True, readonly=True, index=True)
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    amount = fields.Monetary(required=True, readonly=True, currency_field="currency_id")
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", string="Moneda de la compania", readonly=True
    )
    amount_company_currency = fields.Monetary(
        required=True, readonly=True, currency_field="company_currency_id"
    )
    credit_available_before = fields.Monetary(
        string="Credito disponible antes",
        readonly=True,
        currency_field="company_currency_id",
    )
    credit_available_after = fields.Monetary(
        string="Credito disponible despues",
        readonly=True,
        currency_field="company_currency_id",
    )
    code_salt = fields.Char(readonly=True, groups="base.group_system")
    code_hash = fields.Char(readonly=True, groups="base.group_system")
    expires_at = fields.Datetime(required=True, readonly=True, index=True)
    requested_by_id = fields.Many2one(
        "res.users", required=True, readonly=True, default=lambda self: self.env.user
    )
    used_by_id = fields.Many2one("res.users", readonly=True)
    payment_id = fields.Many2one("account.payment", readonly=True, check_company=True)
    financing_move_id = fields.Many2one(
        "account.move",
        string="Asiento de credito",
        readonly=True,
        check_company=True,
    )
    financing_line_id = fields.Many2one(
        "account.move.line",
        string="Saldo financiado",
        readonly=True,
        check_company=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pendiente de codigo"),
            ("used", "Utilizada"),
            ("cancelled", "Cancelada"),
            ("expired", "Vencida"),
        ],
        default="pending",
        required=True,
        readonly=True,
        index=True,
    )
    used_at = fields.Datetime(readonly=True)
    amount_repaid = fields.Monetary(
        string="Pagado realmente",
        currency_field="company_currency_id",
        compute="_compute_accounting_status",
        store=True,
    )
    amount_due = fields.Monetary(
        string="Saldo que debe",
        currency_field="company_currency_id",
        compute="_compute_accounting_status",
        store=True,
    )
    accounting_state = fields.Selection(
        [
            ("pending", "Pendiente de autorizacion"),
            ("active", "Credito utilizado"),
            ("partial", "Pagado parcialmente"),
            ("paid", "Liquidado"),
            ("expired", "Vencido"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado contable",
        compute="_compute_accounting_status",
        store=True,
    )
    telegram_delivery_state = fields.Selection(
        [("sent", "Enviado"), ("failed", "Fallido")],
        string="Entrega por Telegram",
        readonly=True,
    )
    telegram_sent_at = fields.Datetime(string="Enviado a Telegram", readonly=True)
    telegram_message_id = fields.Char(string="ID mensaje Telegram", readonly=True)

    @api.depends(
        "state",
        "amount_company_currency",
        "financing_line_id.amount_residual",
        "financing_line_id.reconciled",
    )
    def _compute_accounting_status(self):
        for authorization in self:
            authorization.amount_repaid = 0.0
            authorization.amount_due = 0.0
            if authorization.state == "pending":
                authorization.accounting_state = "pending"
                continue
            if authorization.state == "expired":
                authorization.accounting_state = "expired"
                continue
            if authorization.state == "cancelled":
                authorization.accounting_state = "cancelled"
                continue
            due = (
                abs(authorization.financing_line_id.amount_residual)
                if authorization.financing_line_id
                else authorization.amount_company_currency
            )
            repaid = max(authorization.amount_company_currency - due, 0.0)
            authorization.amount_due = due
            authorization.amount_repaid = repaid
            currency = authorization.company_currency_id
            if currency.is_zero(due):
                authorization.accounting_state = "paid"
            elif not currency.is_zero(repaid):
                authorization.accounting_state = "partial"
            else:
                authorization.accounting_state = "active"

    @api.model
    def _expire_pending(self, partner=None, company=None):
        domain = [("state", "=", "pending"), ("expires_at", "<=", fields.Datetime.now())]
        if partner:
            domain.append(("partner_id", "=", partner.commercial_partner_id.id))
        if company:
            domain.append(("company_id", "=", company.id))
        expired = self.sudo().search(domain)
        if expired:
            expired.write({"state": "expired"})

    @api.model
    def credit_totals(self, partner, company, exclude_authorization=None):
        partner = partner.commercial_partner_id
        self._expire_pending(partner=partner, company=company)
        domain = [
            ("partner_id", "=", partner.id),
            ("company_id", "=", company.id),
            ("state", "in", ["pending", "used"]),
        ]
        if exclude_authorization:
            domain.append(("id", "!=", exclude_authorization.id))
        authorizations = self.sudo().search(domain)
        used = sum(
            abs(auth.financing_line_id.amount_residual)
            if auth.financing_line_id
            else auth.amount_company_currency
            for auth in authorizations.filtered(lambda auth: auth.state == "used")
        )
        reserved = sum(
            authorizations.filtered(lambda auth: auth.state == "pending").mapped(
                "amount_company_currency"
            )
        )
        return used, reserved

    @api.model
    def create_for_wizard(self, wizard):
        invoice = wizard._ddc_credit_invoice()
        partner = invoice.commercial_partner_id
        company = invoice.company_id
        amount_company = wizard.currency_id._convert(
            wizard.amount,
            company.currency_id,
            company,
            wizard.payment_date or fields.Date.context_today(wizard),
        )
        limit_amount = partner.with_company(company).ddc_authorized_credit_limit
        used, reserved = self.credit_totals(partner, company)
        available = limit_amount - used - reserved
        if company.currency_id.compare_amounts(amount_company, available) > 0:
            raise ValidationError(
                _(
                    "El cliente solo dispone de %(available)s de credito autorizado; "
                    "la solicitud requiere %(requested)s."
                )
                % {
                    "available": company.currency_id.format(available),
                    "requested": company.currency_id.format(amount_company),
                }
            )
        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        expiration = fields.Datetime.now() + timedelta(minutes=10)
        authorization = self.sudo().create(
            {
                "name": self.env["ir.sequence"].next_by_code(
                    "doorandoor.credit.authorization"
                )
                or _("Autorizacion de credito"),
                "partner_id": partner.id,
                "invoice_id": invoice.id,
                "journal_id": wizard.journal_id.id,
                "company_id": company.id,
                "currency_id": wizard.currency_id.id,
                "amount": wizard.amount,
                "amount_company_currency": amount_company,
                "credit_available_before": available,
                "credit_available_after": available - amount_company,
                "code_salt": salt,
                "code_hash": self._hash_code(salt, code),
                "expires_at": expiration,
                "requested_by_id": self.env.user.id,
            }
        )
        try:
            authorization._send_telegram_code(code)
        except Exception as error:
            authorization.write({"state": "cancelled"})
            raise ValidationError(
                _("No se pudo enviar el codigo de autorizacion al canal de pruebas: %s")
                % error
            ) from error
        invoice.message_post(
            body=_(
                "Se solicito autorizacion del cliente para aplicar %(amount)s "
                "mediante credito. El codigo vence a las %(expiration)s."
            )
            % {
                "amount": wizard.currency_id.format(wizard.amount),
                "expiration": fields.Datetime.to_string(expiration),
            },
            subtype_xmlid="mail.mt_note",
        )
        return authorization

    @staticmethod
    def _hash_code(salt, code):
        return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()

    def _send_telegram_code(self, code):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_param("doorandoor_credit.telegram_bot_token")
        chat_id = params.get_param("doorandoor_credit.telegram_chat_id")
        if not token or not chat_id:
            raise ValidationError(
                _("Configure el bot y chat de pruebas para autorizaciones de credito.")
            )
        text = self._build_telegram_message(code)
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            self.sudo().write({"telegram_delivery_state": "failed"})
            raise ValidationError(_("Telegram rechazo el envio del codigo."))
        self.sudo().write(
            {
                "telegram_delivery_state": "sent",
                "telegram_sent_at": fields.Datetime.now(),
                "telegram_message_id": str(payload.get("result", {}).get("message_id") or ""),
            }
        )

    def _build_telegram_message(self, code):
        self.ensure_one()
        invoice = self.invoice_id
        product_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type not in ("line_section", "line_note")
        )
        product_texts = []
        for line in product_lines[:15]:
            description = line.product_id.display_name if line.product_id else line.name
            product_texts.append(
                _("• %(quantity)s × %(product)s")
                % {"quantity": line.quantity, "product": description}
            )
        if len(product_lines) > 15:
            product_texts.append(_("• ... y %s linea(s) adicional(es)") % (len(product_lines) - 15))
        products = "\n".join(product_texts) or _("• Sin lineas de producto")
        # Telegram limits a message to 4096 characters. Preserve the financial
        # summary and OTP even if product descriptions are exceptionally long.
        products = products[:1800]
        remaining_invoice = max(invoice.amount_residual - self.amount, 0.0)
        expiration = fields.Datetime.context_timestamp(self, self.expires_at)
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        invoice_url = (
            f"{base_url.rstrip('/')}/web#id={invoice.id}&model=account.move&view_type=form"
            if base_url
            else "-"
        )
        return _(
            "DOORANDDOOR — AUTORIZACION DE VENTA A CREDITO\n\n"
            "Codigo: %(code)s\n"
            "Valido hasta: %(expiration)s\n\n"
            "Cliente: %(partner)s\n"
            "Factura: %(invoice)s\n"
            "Fecha: %(date)s\n"
            "Vendedor: %(salesperson)s\n\n"
            "Instancia: %(base_url)s\n"
            "Abrir factura: %(invoice_url)s\n\n"
            "PRODUCTOS\n%(products)s\n\n"
            "Total de la factura: %(invoice_total)s\n"
            "Credito solicitado: %(requested)s\n"
            "Saldo restante de factura: %(invoice_remaining)s\n"
            "Credito disponible antes: %(before)s\n"
            "Credito disponible despues: %(after)s\n\n"
            "Al compartir este codigo usted autoriza esta venta y el uso del "
            "credito indicado. El codigo vence en 10 minutos y es de un solo uso."
        ) % {
            "code": code,
            "expiration": fields.Datetime.to_string(expiration),
            "partner": self.partner_id.display_name,
            "invoice": invoice.name,
            "date": invoice.invoice_date or fields.Date.context_today(self),
            "salesperson": invoice.invoice_user_id.name or self.requested_by_id.name,
            "base_url": base_url or "-",
            "invoice_url": invoice_url,
            "products": products,
            "invoice_total": invoice.currency_id.format(invoice.amount_total),
            "requested": self.currency_id.format(self.amount),
            "invoice_remaining": invoice.currency_id.format(remaining_invoice),
            "before": self.company_currency_id.format(self.credit_available_before),
            "after": self.company_currency_id.format(self.credit_available_after),
        }

    def validate_for_wizard(self, wizard, code):
        self.ensure_one()
        self.env.cr.execute(
            "SELECT id FROM doorandoor_credit_authorization WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset()
        invoice = wizard._ddc_credit_invoice()
        if self.state != "pending":
            raise ValidationError(_("La autorizacion ya fue utilizada, cancelada o vencio."))
        if self.expires_at <= fields.Datetime.now():
            self.write({"state": "expired"})
            raise ValidationError(_("El codigo de autorizacion vencio. Solicite uno nuevo."))
        bound_values = (
            self.partner_id == invoice.commercial_partner_id
            and self.invoice_id == invoice
            and self.journal_id == wizard.journal_id
            and self.currency_id == wizard.currency_id
            and self.currency_id.compare_amounts(self.amount, wizard.amount) == 0
        )
        if not bound_values:
            raise ValidationError(
                _("La autorizacion no corresponde al cliente, factura, diario o importe actual.")
            )
        candidate = self._hash_code(self.code_salt, (code or "").strip())
        if not hmac.compare_digest(candidate, self.code_hash):
            raise ValidationError(_("El codigo de autorizacion no es correcto."))
        limit_amount = self.partner_id.with_company(self.company_id).ddc_authorized_credit_limit
        used, reserved = self.credit_totals(
            self.partner_id, self.company_id, exclude_authorization=self
        )
        available = limit_amount - used - reserved
        if self.company_currency_id.compare_amounts(
            self.amount_company_currency, available
        ) > 0:
            raise ValidationError(_("El credito disponible cambio y ya no cubre este pago."))
        return self

    def _get_or_create_financing_account(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        if partner.ddc_credit_financing_account_id:
            return partner.ddc_credit_financing_account_id
        parent = self.journal_id.ddc_credit_parent_account_id
        if not parent:
            raise ValidationError(
                _(
                    "El diario %s no tiene configurada la cuenta madre de "
                    "creditos autorizados."
                )
                % self.journal_id.display_name
            )
        lock_key = int(parent.code) if (parent.code or "").isdigit() else 122000
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)", (lock_key, self.company_id.id)
        )
        partner.invalidate_recordset(["ddc_credit_financing_account_id"])
        if partner.ddc_credit_financing_account_id:
            return partner.ddc_credit_financing_account_id
        account_model = self.env["account.account"].sudo().with_company(self.company_id)
        prefix = (parent.code or "122000")[:4]
        accounts = account_model.search(
            [
                ("code", "=like", f"{prefix}__"),
                ("company_ids", "in", self.company_id.id),
            ]
        )
        used_codes = {
            account.code for account in accounts if (account.code or "").isdigit()
        }
        base_number = int(f"{prefix}00") if prefix.isdigit() else 122000
        next_number = max([int(code) for code in used_codes] + [base_number]) + 1
        while str(next_number) in used_codes:
            next_number += 1
        account = account_model.create(
            {
                "name": _("Credito Autorizado - %s") % partner.display_name,
                "code": str(next_number),
                "account_type": "asset_receivable",
                "reconcile": True,
                "company_ids": [fields.Command.set(self.company_id.ids)],
            }
        )
        partner.sudo().ddc_credit_financing_account_id = account
        return account

    def settle_invoice(self):
        self.ensure_one()
        invoice = self.invoice_id
        company = self.company_id
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        if not receivable_lines:
            raise ValidationError(_("La factura ya no tiene una deuda abierta que financiar."))
        receivable_account = receivable_lines[:1].account_id
        financing_account = self._get_or_create_financing_account()
        amount_company = self.amount_company_currency
        line_common = {"partner_id": self.partner_id.id}
        debit_vals = {
            **line_common,
            "account_id": financing_account.id,
            "name": _("Credito autorizado %(authorization)s") % {"authorization": self.name},
            "debit": amount_company,
            "credit": 0.0,
        }
        credit_vals = {
            **line_common,
            "account_id": receivable_account.id,
            "name": _("Aplicacion a %(invoice)s") % {"invoice": invoice.name},
            "debit": 0.0,
            "credit": amount_company,
        }
        if self.currency_id != company.currency_id:
            debit_vals.update(
                {"currency_id": self.currency_id.id, "amount_currency": self.amount}
            )
            credit_vals.update(
                {"currency_id": self.currency_id.id, "amount_currency": -self.amount}
            )
        move = self.env["account.move"].sudo().create(
            {
                "move_type": "entry",
                "journal_id": self.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": _("Credito %(authorization)s - %(invoice)s")
                % {"authorization": self.name, "invoice": invoice.name},
                "line_ids": [
                    fields.Command.create(debit_vals),
                    fields.Command.create(credit_vals),
                ],
            }
        )
        move.action_post()
        financing_line = move.line_ids.filtered(lambda line: line.debit > 0)[:1]
        settlement_line = move.line_ids.filtered(lambda line: line.credit > 0)[:1]
        # Reconcile only the original invoice debt with the settlement credit.
        # The debit line remains open and becomes the customer's financed debt;
        # future real payments reduce it through normal receivable reconciliation.
        (receivable_lines | settlement_line).reconcile()
        self.write(
            {
                "state": "used",
                "used_at": fields.Datetime.now(),
                "used_by_id": self.env.user.id,
                "financing_move_id": move.id,
                "financing_line_id": financing_line.id,
                "code_hash": False,
                "code_salt": False,
            }
        )
        self.invoice_id.message_post(
            body=_(
                "El cliente autorizo el credito por %s. La factura fue liquidada y "
                "el importe permanece como cuenta por cobrar financiada en %s."
            )
            % (self.currency_id.format(self.amount), self.name),
            subtype_xmlid="mail.mt_note",
        )
        return move
