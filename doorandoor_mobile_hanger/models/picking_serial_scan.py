from odoo import api, fields, models


class DoorAndDoorPickingSerialScan(models.Model):
    _name = "ddmh.picking.serial.scan"
    _description = "Lectura serializada por operación Hanger"
    _order = "scan_at desc, id desc"

    picking_id = fields.Many2one(
        "stock.picking", required=True, index=True, ondelete="cascade",
    )
    serial_id = fields.Many2one(
        "inventory.unit.serial", required=True, index=True, ondelete="restrict",
    )
    product_id = fields.Many2one(
        related="serial_id.product_id", store=True, index=True,
    )
    user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        index=True,
    )
    scan_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)

    _sql_constraints = [
        (
            "picking_serial_unique",
            "unique(picking_id, serial_id)",
            "Este serial ya fue leído en esta operación.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            picking = self.env["stock.picking"].browse(vals.get("picking_id")).exists()
            picking._ddmh_check_mobile_warehouse_access()
        return super().create(vals_list)
