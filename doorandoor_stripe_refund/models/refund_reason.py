from odoo import fields, models


class DoorAndDoorStripeRefundReason(models.Model):
    _name = "doorandoor.stripe.refund.reason"
    _description = "Causa de devolución Stripe"
    _order = "sequence, name, id"

    name = fields.Char(string="Causa", required=True, translate=True)
    code = fields.Char(required=True, index=True)
    description = fields.Text(string="Orientación")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_details = fields.Boolean(
        string="Exigir detalle adicional",
        help="Obliga al comercial a explicar la causa antes de enviar la solicitud.",
    )
    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "El código de la causa de devolución debe ser único.",
        )
    ]
