from odoo import fields, models


class DoorandoorFulfillmentLine(models.Model):
    _name = "doorandoor.fulfillment.line"
    _description = "DoorAndDoor Fulfillment Line"
    _order = "id"

    move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Invoice Line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        readonly=True,
        copy=False,
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Sale Order Line",
        readonly=True,
        copy=False,
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Picking",
        readonly=True,
        copy=False,
    )
    mrp_production_id = fields.Many2one(
        "mrp.production",
        string="Manufacturing Order",
        readonly=True,
        copy=False,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        related="move_line_id.product_id",
        store=True,
        readonly=True,
    )
    qty_invoiced = fields.Float(string="Qty Invoiced", readonly=True)
    qty_released = fields.Float(string="Qty Released", default=0.0)
    qty_sent_stock = fields.Float(string="Qty Sent to Stock", default=0.0)
    qty_sent_mrp = fields.Float(string="Qty Sent to MRP", default=0.0)
    qty_delivered = fields.Float(string="Qty Delivered", default=0.0)
    qty_pending_payment = fields.Float(string="Qty Pending Payment", default=0.0)
    qty_pending_delivery = fields.Float(string="Qty Pending Delivery", default=0.0)
    amount_total = fields.Monetary(string="Line Amount", currency_field="currency_id", readonly=True)
    amount_released = fields.Monetary(string="Released Amount", currency_field="currency_id", default=0.0)
    pickup_order_line_ids = fields.One2many(
        "doorandoor.pickup.order.line",
        "fulfillment_line_id",
        string="Pickup Order Lines",
        copy=False,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="move_id.currency_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("pending_payment", "Pending Payment"),
            ("ready_stock", "Ready for Stock"),
            ("ready_mrp", "Ready for Manufacturing"),
            ("in_process", "In Process"),
            ("delivered", "Delivered"),
        ],
        string="State",
        default="pending_payment",
        required=True,
    )

    def _ddsn_get_qty_ready_for_pickup(self):
        self.ensure_one()
        return max(self.qty_released - self.qty_delivered, 0.0)
