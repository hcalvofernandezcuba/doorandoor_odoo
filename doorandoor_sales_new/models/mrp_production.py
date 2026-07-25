from odoo import models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def button_mark_done(self):
        productions = self.filtered(lambda production: production.state != "done")
        result = super().button_mark_done()
        productions._ddsn_sync_invoice_fulfillment_after_done()
        return result

    def _ddsn_sync_invoice_fulfillment_after_done(self):
        for production in self:
            fulfillment_lines = self.env["doorandoor.fulfillment.line"].search(
                [("mrp_production_id", "=", production.id)]
            )
            for fulfillment_line in fulfillment_lines:
                fulfillment_line.move_id._ddsn_sync_finished_mrp_to_outgoing_picking(fulfillment_line)
