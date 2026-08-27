from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "done":
            delivered = self.filtered(
                lambda move: move.product_id.ddpc_is_custom_variant
                and move.location_dest_id.usage == "customer"
            )
            delivered.mapped("product_id")._ddpc_mark_custom_variant_delivered(
                fields.Date.context_today(self)
            )
        return result
