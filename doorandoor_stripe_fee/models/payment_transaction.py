import re
import unicodedata

from odoo import _, api, fields, models
from odoo.tools import html_escape


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    ddtp_cardholder_name = fields.Char(string="Titular declarado por Stripe", copy=False, readonly=True)
    ddtp_cardholder_check = fields.Selection([
        ("pending", "Pendiente de validar"),
        ("matched", "Titular coincide"),
        ("review", "Revisión requerida"),
    ], string="Control de titular", default="pending", copy=False, readonly=True)

    ddtp_origin_invoice_id = fields.Many2one(
        "account.move", string="Factura de origen", copy=False, readonly=True
    )
    ddtp_fee_invoice_id = fields.Many2one(
        "account.move", string="Factura de cargo por tarjeta", copy=False, readonly=True
    )
    ddtp_collection_base_amount = fields.Monetary(
        string="Base del cobro con tarjeta", currency_field="currency_id", copy=False, readonly=True
    )
    ddtp_collection_fee_amount = fields.Monetary(
        string="Cargo de esta operación", currency_field="currency_id", copy=False, readonly=True
    )
    ddtp_collection_fee_account_id = fields.Many2one(
        "account.account", string="Cuenta del cargo", copy=False, readonly=True
    )
    ddtp_notification_sent = fields.Boolean(string="Aviso de pago enviado", copy=False, readonly=True)

    @api.model
    def _ddtp_normalize_holder_name(self, value):
        value = unicodedata.normalize("NFKD", (value or ""))
        value = "".join(char for char in value if not unicodedata.combining(char)).upper()
        return re.sub(r"[^A-Z0-9]", "", value)

    def _ddtp_get_stripe_cardholder_name(self, notification_data):
        intent = notification_data.get("payment_intent") or {}
        charges = intent.get("charges", {}).get("data", [])
        if charges:
            name = charges[0].get("billing_details", {}).get("name")
            if name:
                return name
        method = notification_data.get("payment_method") or {}
        return method.get("billing_details", {}).get("name") if isinstance(method, dict) else False

    def _process_notification_data(self, notification_data):
        """Hold a successful card payment if its declared holder differs.

        Stripe's billing name is not identity proof, but it is a useful
        server-side fraud-control signal.  A mismatch never creates a payment
        or releases the invoice automatically; an administrator must review it.
        """
        self.ensure_one()
        intent = notification_data.get("payment_intent") or {}
        status = intent.get("status")
        if self.provider_code == "stripe" and status == "succeeded" and self.invoice_ids:
            holder = self._ddtp_get_stripe_cardholder_name(notification_data)
            expected = self.invoice_ids[:1].commercial_partner_id.name
            if not holder or self._ddtp_normalize_holder_name(holder) != self._ddtp_normalize_holder_name(expected):
                self.write({
                    "ddtp_cardholder_name": holder or _("No informado por Stripe"),
                    "ddtp_cardholder_check": "review",
                    "provider_reference": intent.get("id") or self.provider_reference,
                })
                self._set_pending(state_message=_(
                    "Pago retenido para revisión: el titular declarado por Stripe no coincide con el cliente de la factura."
                ), extra_allowed_states=("pending",))
                self.invoice_ids.message_post(body=_(
                    "Pago con tarjeta retenido para revisión de titular. Cliente: %(customer)s. Titular Stripe: %(holder)s."
                ) % {"customer": expected, "holder": holder or _("No informado")})
                return
            self.write({"ddtp_cardholder_name": holder, "ddtp_cardholder_check": "matched"})
        return super()._process_notification_data(notification_data)

    def _ddtp_get_notification_recipients(self):
        self.ensure_one()
        system_group = self.env.ref("base.group_system")
        control_group = self.env.ref("doorandoor_control_cobros.group_ddc_manager")
        users = self.env["res.users"].sudo().search([
            ("active", "=", True),
            ("groups_id", "in", (system_group | control_group).ids),
        ])
        return (users.partner_id | self.provider_id.ddtp_payment_notification_partner_ids).filtered("email")

    def _ddtp_send_payment_notification(self):
        for transaction in self.filtered(
            lambda tx: tx.state == "done" and tx.payment_id and not tx.ddtp_notification_sent
        ):
            recipients = transaction._ddtp_get_notification_recipients()
            if not recipients:
                transaction.ddtp_notification_sent = True
                continue
            currency = transaction.currency_id
            fee_amount = transaction.ddtp_fee_invoice_id.amount_total or transaction.ddtp_origin_invoice_id.ddtp_card_fee_amount
            base_amount = transaction.amount - fee_amount
            rows = [
                (_("Factura"), transaction.ddtp_origin_invoice_id.name),
                (_("Cliente"), transaction.partner_id.display_name),
                (_("Pago base"), currency.format(base_amount)),
                (_("Cargo por procesamiento"), currency.format(fee_amount)),
                (_("Total cobrado"), currency.format(transaction.amount)),
                (_("Referencia"), transaction.provider_reference or transaction.reference),
            ]
            body = "".join(
                "<tr><td><strong>%s</strong></td><td>%s</td></tr>" % (html_escape(label), html_escape(value or ""))
                for label, value in rows
            )
            mail = self.env["mail.mail"].sudo().create({
                "subject": _("Pago con tarjeta confirmado - %(invoice)s") % {
                    "invoice": transaction.ddtp_origin_invoice_id.name,
                },
                "email_to": ",".join(recipients.mapped("email")),
                "body_html": "<p>%s</p><table>%s</table>" % (
                    html_escape(_("Se confirmó un pago con tarjeta.")), body,
                ),
                "auto_delete": False,
            })
            mail.send()
            transaction.ddtp_notification_sent = True
            for invoice in transaction.invoice_ids:
                invoice.message_post(
                    body=_("Se envió el aviso de pago con tarjeta confirmado a los administradores configurados.")
                )

    def _create_payment(self, **extra_create_values):
        """Allocate card payments to their fee document before the sale invoice.

        The standard implementation reconciles all linked invoices in one pass.
        For a partial card payment that could consume the base invoice first and
        leave the processing-fee document open.  This controlled allocation
        preserves the exact accounting meaning of the checkout total.
        """
        self.ensure_one()
        if self.ddtp_collection_fee_amount:
            fee = self.ddtp_collection_fee_amount
            balance = self.currency_id._convert(
                fee, self.company_id.currency_id, self.company_id,
                fields.Date.context_today(self),
            )
            # Inbound payment: a negative write-off credits fee income and
            # reduces the receivable counterpart to the commercial balance.
            # The customer therefore never receives a credit for the fee.
            extra_create_values = {
                **extra_create_values,
                "write_off_line_vals": [{
                    "name": _("Cargo por pago con tarjeta"),
                    "account_id": self.ddtp_collection_fee_account_id.id,
                    "partner_id": self.partner_id.commercial_partner_id.id,
                    "currency_id": self.currency_id.id,
                    "amount_currency": -fee,
                    "balance": -balance,
                }],
            }
            return super()._create_payment(**extra_create_values)
        if not self.ddtp_fee_invoice_id:
            return super()._create_payment(**extra_create_values)

        payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_provider_id == self.provider_id
        )[:1]
        if not payment_method_line:
            return super()._create_payment(**extra_create_values)

        payment = self.env["account.payment"].create({
            "amount": abs(self.amount),
            "payment_type": "inbound" if self.amount > 0 else "outbound",
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.commercial_partner_id.id,
            "partner_type": "customer",
            "journal_id": self.provider_id.journal_id.id,
            "company_id": self.provider_id.company_id.id,
            "payment_method_line_id": payment_method_line.id,
            "payment_transaction_id": self.id,
            "memo": _("Pago con tarjeta - %(reference)s") % {"reference": self.reference},
            "write_off_line_vals": [],
            **extra_create_values,
        })
        payment.action_post()
        self.payment_id = payment

        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == payment.destination_account_id and not line.reconciled
        )
        for invoice in (self.ddtp_fee_invoice_id | self.ddtp_origin_invoice_id).filtered(
            lambda item: item.state == "posted" and item.state != "cancel"
        ):
            invoice_lines = invoice.line_ids.filtered(
                lambda line: line.display_type == "payment_term"
                and line.account_id == payment.destination_account_id
                and not line.reconciled
            )
            if payment_lines and invoice_lines:
                (payment_lines + invoice_lines).reconcile()
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda line: line.account_id == payment.destination_account_id and not line.reconciled
                )
        return payment

    def _ddtp_cancel_fee_invoice(self, reason):
        for transaction in self.filtered("ddtp_fee_invoice_id"):
            fee_invoice = transaction.ddtp_fee_invoice_id
            if fee_invoice.state == "posted" and fee_invoice.payment_state not in ("paid", "in_payment"):
                fee_invoice.button_cancel()
                fee_invoice.message_post(
                    body=_("Cancelada automáticamente: el pago con tarjeta %(reference)s no se completó (%(reason)s).")
                    % {"reference": transaction.reference, "reason": reason}
                )

    def _set_canceled(self, state_message=None, extra_allowed_states=()):
        transactions = super()._set_canceled(state_message, extra_allowed_states)
        transactions._ddtp_cancel_fee_invoice(_("operación cancelada"))
        return transactions

    def _set_error(self, state_message, extra_allowed_states=()):
        transactions = super()._set_error(state_message, extra_allowed_states)
        transactions._ddtp_cancel_fee_invoice(_("pago rechazado"))
        return transactions

    def _post_process(self):
        result = super()._post_process()
        self._ddtp_send_payment_notification()
        return result
