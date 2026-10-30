from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashMovement(models.Model):
    _name = "doorandoor.cash.movement"
    _description = "Movimiento de billetes de caja"
    _order = "create_date, id"
    _rec_name = "name"

    name = fields.Char(required=True, readonly=True, copy=False)
    session_id = fields.Many2one("doorandoor.cash.session", required=True, readonly=True, ondelete="restrict", index=True)
    payment_id = fields.Many2one("account.payment", required=True, readonly=True, ondelete="restrict", index=True)
    move_id = fields.Many2one("account.move", readonly=True, ondelete="restrict", string="Factura")
    user_id = fields.Many2one("res.users", required=True, readonly=True, default=lambda self: self.env.user)
    currency_id = fields.Many2one(related="session_id.currency_id", store=True)
    tender_amount = fields.Monetary(string="Efectivo recibido", required=True, readonly=True, currency_field="currency_id")
    payment_amount = fields.Monetary(string="Cobro aplicado", required=True, readonly=True, currency_field="currency_id")
    change_amount = fields.Monetary(string="Vuelto entregado", required=True, readonly=True, currency_field="currency_id")
    line_ids = fields.One2many("doorandoor.cash.movement.line", "movement_id", readonly=True)

    _sql_constraints = [
        ("ddcc_one_movement_per_payment", "unique(payment_id)", "El pago ya tiene un movimiento de efectivo."),
    ]


class DoorAndDoorCashMovementLine(models.Model):
    _name = "doorandoor.cash.movement.line"
    _description = "Detalle de billetes recibidos y vuelto"
    _order = "denomination_id desc, id"

    movement_id = fields.Many2one("doorandoor.cash.movement", required=True, ondelete="cascade", index=True)
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True, readonly=True)
    received_quantity = fields.Integer(string="Recibidos", required=True, readonly=True, default=0)
    change_quantity = fields.Integer(string="Vuelto", required=True, readonly=True, default=0)
    net_quantity = fields.Integer(compute="_compute_net_quantity", store=True)
    currency_id = fields.Many2one(related="movement_id.currency_id", store=True)
    received_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    change_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")

    _sql_constraints = [
        ("ddcc_one_denomination_per_movement", "unique(movement_id, denomination_id)", "La denominación solo puede aparecer una vez por movimiento."),
        ("ddcc_non_negative_received", "CHECK(received_quantity >= 0)", "La cantidad recibida no puede ser negativa."),
        ("ddcc_non_negative_change", "CHECK(change_quantity >= 0)", "La cantidad de vuelto no puede ser negativa."),
    ]

    @api.depends("received_quantity", "change_quantity")
    def _compute_net_quantity(self):
        for line in self:
            line.net_quantity = line.received_quantity - line.change_quantity

    @api.depends("denomination_id.value", "received_quantity", "change_quantity")
    def _compute_amounts(self):
        for line in self:
            line.received_amount = line.denomination_id.value * line.received_quantity
            line.change_amount = line.denomination_id.value * line.change_quantity
