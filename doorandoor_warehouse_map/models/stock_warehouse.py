from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    ddwm_vertical_level_count = fields.Integer(
        string="Niveles verticales del mapa",
        default=0,
        help=(
            "Altura física mínima que debe dibujar el mapa en cada posición "
            "horizontal. Los niveles sin mercancía se muestran como Vacío. "
            "El valor 0 mantiene el cálculo automático."
        ),
    )
