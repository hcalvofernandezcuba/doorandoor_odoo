from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    ddivc_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Moneda",
        readonly=True,
    )
    ddivc_unit_cost = fields.Monetary(
        string="Costo unitario",
        currency_field="ddivc_currency_id",
        compute="_compute_ddivc_prices",
        readonly=True,
        groups="base.group_system",
    )
    ddivc_sale_price = fields.Monetary(
        string="Precio de venta final",
        currency_field="ddivc_currency_id",
        compute="_compute_ddivc_prices",
        readonly=True,
        groups="base.group_system",
    )

    @api.depends(
        "product_id",
        "product_id.standard_price",
        "product_id.product_tmpl_id.list_price",
        "product_id.ddpc_variant_extra_price",
        "company_id",
    )
    def _compute_ddivc_prices(self):
        for quant in self:
            product = quant.product_id.with_company(quant.company_id)
            quant.ddivc_unit_cost = product.standard_price
            quant.ddivc_sale_price = (
                product.product_tmpl_id.list_price
                + product.ddpc_variant_extra_price
            )
