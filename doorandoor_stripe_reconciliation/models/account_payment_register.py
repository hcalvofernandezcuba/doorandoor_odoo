from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ddsr_stripe_checkout_mode = fields.Boolean(
        compute="_compute_ddsr_stripe_checkout_mode"
    )

    @api.depends("journal_id")
    def _compute_ddsr_stripe_checkout_mode(self):
        providers = self.env["payment.provider"].sudo().search([
            ("code", "=", "stripe"),
            ("state", "in", ("test", "enabled")),
        ])
        stripe_journals = providers.journal_id
        for wizard in self:
            wizard.ddsr_stripe_checkout_mode = wizard.journal_id in stripe_journals

    def action_create_payments(self):
        self.ensure_one()
        if not self.ddsr_stripe_checkout_mode:
            return super().action_create_payments()
        return self._ddsr_open_stripe_checkout()

    def _ddsr_open_stripe_checkout(self):
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            raise ValidationError(
                _("Stripe requiere seleccionar una sola factura publicada por operación.")
            )
        invoice = invoices.ensure_one()
        providers = self.env["payment.provider"].sudo().search([
            ("code", "=", "stripe"),
            ("state", "in", ("test", "enabled")),
            ("company_id", "=", invoice.company_id.id),
        ])
        provider = providers.filtered(
            lambda item: item.journal_id == self.journal_id
        )[:1]
        if not provider:
            raise ValidationError(_("El diario seleccionado no tiene Stripe activo."))
        if self.currency_id.compare_amounts(self.amount, invoice.amount_residual) != 0:
            raise ValidationError(
                _("Para esta prueba Stripe debe cobrar el saldo pendiente completo de la factura.")
            )

        card = provider.payment_method_ids.filtered(lambda method: method.code == "card")[:1]
        if not card:
            raise ValidationError(_("Stripe no tiene habilitado el método Tarjeta."))

        transaction = self.env["payment.transaction"].sudo().create({
            "provider_id": provider.id,
            "payment_method_id": card.id,
            "reference": self.env["payment.transaction"]._compute_reference(
                "stripe", prefix=invoice.name
            ),
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "partner_id": invoice.commercial_partner_id.id,
            "operation": "online_direct",
            "invoice_ids": [(6, 0, invoice.ids)],
            "landing_route": f"/web#id={invoice.id}&model=account.move&view_type=form",
        })
        base_url = provider.get_base_url().rstrip("/") + "/"
        invoice_url = urljoin(
            base_url,
            f"web#id={invoice.id}&model=account.move&view_type=form",
        )
        payload = {
            "mode": "payment",
            "success_url": invoice_url,
            "cancel_url": invoice_url,
            "line_items[0][price_data][currency]": self.currency_id.name.lower(),
            "line_items[0][price_data][unit_amount]": int(round(self.amount * 100)),
            "line_items[0][price_data][product_data][name]": invoice.name,
            "line_items[0][quantity]": 1,
            "payment_intent_data[description]": transaction.reference,
            "metadata[odoo_reference]": transaction.reference,
            "payment_intent_data[metadata][odoo_reference]": transaction.reference,
        }
        if invoice.partner_id.email:
            payload["customer_email"] = invoice.partner_id.email
        session = provider._stripe_make_request("checkout/sessions", payload=payload)
        checkout_url = session.get("url")
        if not checkout_url:
            raise ValidationError(_("Stripe no devolvió la URL del formulario de pago."))
        transaction._set_pending(
            state_message=_("Esperando que el cliente complete Stripe Checkout.")
        )
        transaction._log_sent_message()
        return {
            "type": "ir.actions.act_url",
            "url": checkout_url,
            "target": "self",
        }
