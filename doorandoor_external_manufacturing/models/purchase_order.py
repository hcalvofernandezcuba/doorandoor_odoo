from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    ddem_external_order_id = fields.Many2one(
        "ddem.external.order",
        string="Pedido externo",
        copy=False,
        readonly=True,
        index=True,
    )
    ddem_sale_order_id = fields.Many2one(
        related="ddem_external_order_id.sale_order_id",
        string="Venta de origen",
        store=True,
        readonly=True,
    )
    ddem_logistic_route = fields.Selection(
        related="ddem_external_order_id.logistic_route",
        string="Modalidad logística",
        store=True,
        readonly=True,
    )
