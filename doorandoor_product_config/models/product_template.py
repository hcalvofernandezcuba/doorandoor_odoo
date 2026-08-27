from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_add_mode = fields.Selection(default="configurator")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["product_add_mode"] = "configurator"
        return super().create(vals_list)

    def get_single_product_variant(self):
        """Mantener el configurador estandar como selector unico en Ventas."""
        result = super().get_single_product_variant()
        if self.has_configurable_attributes:
            result["mode"] = "configurator"
        return result

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
