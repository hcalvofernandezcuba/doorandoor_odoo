from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ddpc_color_overdue = fields.Char(string="DDPC Overdue Color", default="#dc2626")
    ddpc_color_in_progress = fields.Char(string="DDPC In Progress Color", default="#ea580c")
    ddpc_color_done = fields.Char(string="DDPC Done Color", default="#16a34a")
    ddpc_transfer_alert_interval_hours = fields.Integer(
        string="Intervalo de alertas de traslado (horas)", default=4
    )
    ddpc_transfer_overdue_hours = fields.Integer(
        string="Escalamiento de traslado (horas)", default=24
    )
    ddpc_transfer_transit_location_id = fields.Many2one(
        "stock.location",
        string="Ubicacion de mercancia en transito",
        domain="[('usage', '=', 'transit'), '|', ('company_id', '=', False), ('company_id', '=', id)]",
        help=(
            "Ubicacion temporal usada entre el despacho del almacen origen y "
            "la recepcion fisica del almacen destino."
        ),
    )
