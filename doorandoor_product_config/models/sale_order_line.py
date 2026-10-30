from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ddpc_item_variant = fields.Char(
        string="ITEM / Variante",
        related="product_id.ddpc_item_group",
        readonly=True,
    )

    def _reset_price_unit(self):
        """Use the selected item's final price as the commercial source price."""
        super()._reset_price_unit()
        for line in self.filtered(lambda item: item.product_id and not item.display_type):
            product = line.product_id.with_company(line.company_id)
            price = product.ddpc_variant_final_price
            if line.product_uom and product.uom_id != line.product_uom:
                price = product.uom_id._compute_price(price, line.product_uom)
            if product.currency_id != line.currency_id:
                price = product.currency_id._convert(
                    price,
                    line.currency_id,
                    line.company_id,
                    line._get_order_date(),
                )
            product_taxes = product.taxes_id._filter_taxes_by_company(line.company_id)
            price = product._get_tax_included_unit_price_from_price(
                price,
                product_taxes=product_taxes,
                fiscal_position=line.order_id.fiscal_position_id,
            )
            line.update({"price_unit": price, "technical_price_unit": price})
