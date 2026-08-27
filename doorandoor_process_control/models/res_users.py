from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    ddpc_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "ddpc_user_warehouse_rel",
        "user_id",
        "warehouse_id",
        string="Almacenes operativos",
        help="Almacenes cuyas recepciones, entregas y traslados puede operar el usuario.",
    )
    ddpc_default_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacen operativo predeterminado",
        domain="[('id', 'in', ddpc_warehouse_ids)]",
    )

    @api.constrains("ddpc_default_warehouse_id", "ddpc_warehouse_ids")
    def _check_ddpc_default_warehouse(self):
        for user in self:
            if user.ddpc_default_warehouse_id and user.ddpc_default_warehouse_id not in user.ddpc_warehouse_ids:
                raise ValidationError(
                    "El almacen predeterminado debe pertenecer a los almacenes operativos del usuario."
                )


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    ddpc_operator_user_ids = fields.Many2many(
        "res.users",
        "ddpc_user_warehouse_rel",
        "warehouse_id",
        "user_id",
        string="Operadores DoorAndDoor",
    )
