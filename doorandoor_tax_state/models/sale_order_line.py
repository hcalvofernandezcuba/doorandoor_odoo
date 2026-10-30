# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        "product_id",
        "company_id",
        "order_id.ddts_tax_rule_id",
        "order_id.ddts_tax_city_rule_id",
        "order_id.ddts_partner_tax_exempt",
    )
    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self:
            if line.order_id.ddts_partner_tax_exempt:
                line.tax_id = False
                continue
            rule = line.order_id.ddts_tax_city_rule_id.sale_tax_id or line.company_id._ddts_get_default_sale_tax()
            if (
                line.display_type
                or line.product_type == "combo"
                or not rule
                or not line.company_id
            ):
                continue
            taxes = rule._filter_taxes_by_company(line.company_id)
            if taxes and line.order_id.fiscal_position_id:
                taxes = line.order_id.fiscal_position_id.map_tax(taxes)
            line.tax_id = taxes
