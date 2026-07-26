from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ddpc_color_overdue = fields.Char(string="DDPC Overdue Color", default="#dc2626")
    ddpc_color_in_progress = fields.Char(string="DDPC In Progress Color", default="#ea580c")
    ddpc_color_done = fields.Char(string="DDPC Done Color", default="#16a34a")
