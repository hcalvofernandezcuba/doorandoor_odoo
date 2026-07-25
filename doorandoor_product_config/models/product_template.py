from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_ddpc_variant_pricing(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Variant Pricing",
            "res_model": "product.product",
            "view_mode": "list,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "search_default_product_tmpl_id": self.id,
            },
            "target": "current",
        }
