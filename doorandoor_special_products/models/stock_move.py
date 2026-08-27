from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        return moves

    def write(self, vals):
        result = super().write(vals)
        if {"state", "quantity", "product_uom_qty", "location_id", "location_dest_id"}.intersection(vals):
            self.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        return result
