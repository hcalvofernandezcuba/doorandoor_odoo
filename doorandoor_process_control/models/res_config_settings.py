from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ddpc_color_overdue = fields.Char(related="company_id.ddpc_color_overdue", readonly=False)
    ddpc_color_in_progress = fields.Char(related="company_id.ddpc_color_in_progress", readonly=False)
    ddpc_color_done = fields.Char(related="company_id.ddpc_color_done", readonly=False)
    ddpc_transfer_alert_interval_hours = fields.Integer(
        related="company_id.ddpc_transfer_alert_interval_hours", readonly=False
    )
    ddpc_transfer_overdue_hours = fields.Integer(
        related="company_id.ddpc_transfer_overdue_hours", readonly=False
    )
    ddpc_transfer_transit_location_id = fields.Many2one(
        related="company_id.ddpc_transfer_transit_location_id", readonly=False
    )
