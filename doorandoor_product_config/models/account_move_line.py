from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddpc_base_price = fields.Float(
        string="Base Price",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )
    ddpc_variant_extra_price = fields.Float(
        string="Variant Extra",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )
    ddpc_configured_price_unit = fields.Float(
        string="Configured Price",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )

    @api.depends("product_id", "product_id.product_tmpl_id.list_price", "product_id.ddpc_variant_extra_price")
    def _compute_ddpc_pricing(self):
        for line in self:
            if not line.product_id:
                line.ddpc_base_price = 0.0
                line.ddpc_variant_extra_price = 0.0
                line.ddpc_configured_price_unit = 0.0
                continue

            base_price = line._ddpc_get_base_price()
            extra_price = line.product_id.ddpc_variant_extra_price
            line.ddpc_base_price = base_price
            line.ddpc_variant_extra_price = extra_price
            line.ddpc_configured_price_unit = base_price + extra_price

    def _ddpc_is_customer_invoice_line(self):
        self.ensure_one()
        return (
            self.move_id
            and self.move_id.move_type in ("out_invoice", "out_refund")
            and self.display_type in (False, "product")
            and self.product_id
        )

    def _ddpc_get_base_price(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return 0.0
        return product.product_tmpl_id.list_price

    def _ddpc_apply_variant_price(self):
        for line in self:
            if not line._ddpc_is_customer_invoice_line():
                continue
            line.price_unit = line._ddpc_get_base_price() + line.product_id.ddpc_variant_extra_price

    @api.onchange("product_id")
    def _onchange_product_id_ddpc_variant_price(self):
        self._ddpc_apply_variant_price()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ddpc_apply_variant_price()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if "product_id" in vals:
            self._ddpc_apply_variant_price()
        return result
