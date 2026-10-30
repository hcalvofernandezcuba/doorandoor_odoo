from odoo import _, models
from odoo.exceptions import UserError


class DoorandoorPickupOrder(models.Model):
    _inherit = "doorandoor.pickup.order"

    def action_ddmh_count_delivery(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("Este Pickup Order todavía no tiene una entrega asociada."))
        return self.picking_id.action_open_ddsl_receipt_scan_wizard()
