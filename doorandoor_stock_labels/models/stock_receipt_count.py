from odoo import api, fields, models


class StockReceiptCount(models.Model):
    _name = "ddsl.stock.receipt.count"
    _description = "DoorAndDoor Physical Receipt Count"
    _order = "product_id, id"
    _rec_name = "product_id"

    picking_id = fields.Many2one(
        "stock.picking",
        required=True,
        index=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
        index=True,
        ondelete="restrict",
    )
    expected_qty = fields.Float(string="Esperado", readonly=True)
    counted_qty = fields.Float(string="Contado", default=0.0)
    is_counted = fields.Boolean(string="Contado fisicamente", default=False)
    difference_qty = fields.Float(
        string="Diferencia",
        compute="_compute_difference_qty",
        store=True,
    )
    last_scan_date = fields.Datetime(string="Ultima lectura", readonly=True)
    last_scan_user_id = fields.Many2one(
        "res.users",
        string="Ultimo usuario",
        readonly=True,
    )

    _sql_constraints = [
        (
            "picking_product_unique",
            "unique(picking_id, product_id)",
            "Solo puede existir un conteo fisico por producto y recepcion.",
        ),
    ]

    @api.depends("expected_qty", "counted_qty", "is_counted")
    def _compute_difference_qty(self):
        for line in self:
            line.difference_qty = (
                line.counted_qty - line.expected_qty if line.is_counted else 0.0
            )
