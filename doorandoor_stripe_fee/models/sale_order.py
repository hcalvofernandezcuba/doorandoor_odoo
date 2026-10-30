from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddtp_payment_plan = fields.Selection([
        ("full", "Pago total"),
        ("partial", "Pago parcial: 50% + impuestos"),
    ], string="Tipo de pago", default="full", copy=False)
    ddtp_payment_due_amount = fields.Monetary(
        string="Importe a cobrar", compute="_compute_ddtp_payment_due_amount",
        currency_field="currency_id", readonly=True,
    )
    ddtp_payment_pending_amount = fields.Monetary(
        string="Saldo pendiente después del primer pago",
        compute="_compute_ddtp_payment_pending_amount",
        currency_field="currency_id",
        readonly=True,
    )

    ddtp_card_payment_enabled = fields.Boolean(
        string="Pago con tarjeta", copy=False,
        help="Incluye el cargo de procesamiento al generar la factura.",
    )
    ddtp_card_payment_amount = fields.Monetary(
        string="Importe a cobrar con tarjeta", copy=False, currency_field="currency_id",
        help="Importe del primer cobro con tarjeta, sin su cargo de procesamiento.",
    )

    ddtp_card_fee_preview = fields.Monetary(
        string="Cargo por procesamiento", compute="_compute_ddtp_card_payment_preview",
        currency_field="currency_id", readonly=True,
    )
    ddtp_card_fee_rate = fields.Float(
        string="Porcentaje de cargo por tarjeta", compute="_compute_ddtp_card_payment_preview",
        readonly=True,
    )
    ddtp_card_total_preview = fields.Monetary(
        string="Total con tarjeta", compute="_compute_ddtp_card_payment_preview",
        currency_field="currency_id", readonly=True,
    )

    @api.depends("ddtp_payment_plan", "amount_untaxed", "amount_tax")
    def _compute_ddtp_payment_due_amount(self):
        for order in self:
            if order.ddtp_payment_plan == "partial":
                order.ddtp_payment_due_amount = order.currency_id.round(
                    order.amount_untaxed * 0.5 + order.amount_tax
                )
            else:
                order.ddtp_payment_due_amount = order.amount_total

    @api.depends("ddtp_payment_plan", "ddtp_payment_due_amount", "amount_total")
    def _compute_ddtp_payment_pending_amount(self):
        for order in self:
            order.ddtp_payment_pending_amount = order.currency_id.round(
                max(order.amount_total - order.ddtp_payment_due_amount, 0.0)
            ) if order.ddtp_payment_plan == "partial" else 0.0

    @api.depends("ddtp_card_payment_enabled", "ddtp_card_payment_amount", "amount_total", "company_id")
    def _compute_ddtp_card_payment_preview(self):
        for order in self:
            provider = self.env["payment.provider"]._ddtp_get_active_card_provider(order.company_id)
            base_amount = order._ddtp_get_planned_card_amount()
            fee_amount = order.currency_id.round(
                base_amount * provider.ddtp_card_fee_rate / 100.0
            ) if order.ddtp_card_payment_enabled and provider else 0.0
            order.ddtp_card_fee_rate = provider.ddtp_card_fee_rate if provider else 0.0
            order.ddtp_card_fee_preview = fee_amount
            order.ddtp_card_total_preview = base_amount + fee_amount if order.ddtp_card_payment_enabled else 0.0

    @api.onchange("ddtp_card_payment_enabled")
    def _onchange_ddtp_card_payment_enabled(self):
        for order in self:
            if order.ddtp_card_payment_enabled:
                order.ddtp_card_payment_amount = order._ddtp_get_planned_card_amount()

    @api.onchange("ddtp_payment_plan", "amount_untaxed", "amount_tax")
    def _onchange_ddtp_payment_plan(self):
        for order in self:
            if order.ddtp_card_payment_enabled:
                order.ddtp_card_payment_amount = order._ddtp_get_planned_card_amount()

    def _ddtp_get_planned_card_amount(self):
        """Compute the card principal from final server-side totals."""
        self.ensure_one()
        if self.ddtp_payment_plan == "partial":
            return self.ddtp_payment_due_amount
        return self.amount_total

    def _ddsn_create_preinvoice(self):
        """Preserve the card choice when a quote creates its prefactura."""
        preinvoice = super()._ddsn_create_preinvoice()
        if self.ddtp_card_payment_enabled:
            preinvoice.write({
                "ddtp_card_payment_enabled": True,
                "ddtp_card_payment_amount": self._ddtp_get_planned_card_amount(),
                "ddtp_payment_plan": self.ddtp_payment_plan,
            })
        return preinvoice

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        self.ensure_one()
        if self.ddtp_card_payment_enabled:
            values.update({
                "ddtp_card_payment_enabled": True,
                "ddtp_card_payment_amount": self._ddtp_get_planned_card_amount(),
            })
        return values
