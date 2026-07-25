from odoo import api, fields, models


class DoorandoorPickupOrder(models.Model):
    _name = "doorandoor.pickup.order"
    _description = "DoorAndDoor Pickup Order"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "doorandoor.document.barcode.mixin"]

    name = fields.Char(
        string="Pickup Order",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="move_id.partner_id",
        store=True,
        readonly=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        related="move_id.sale_order_id",
        store=True,
        readonly=True,
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Picking",
        readonly=True,
        copy=False,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="move_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="move_id.currency_id",
        store=True,
        readonly=True,
    )
    pickup_line_ids = fields.One2many(
        "doorandoor.pickup.order.line",
        "pickup_order_id",
        string="Pickup Lines",
        copy=False,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("pending", "Pending"),
            ("ready", "Ready"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="new",
        required=True,
        tracking=True,
        copy=False,
    )
    note = fields.Text(string="Notes")
    delivered_by_id = fields.Many2one(
        "res.users",
        string="Delivered By",
        readonly=True,
        copy=False,
    )
    delivered_date = fields.Datetime(
        string="Delivered On",
        readonly=True,
        copy=False,
    )
    amount_total = fields.Monetary(
        string="Amount Total",
        compute="_compute_amount_total",
        currency_field="currency_id",
        store=True,
    )
    line_count = fields.Integer(
        string="Line Count",
        compute="_compute_line_count",
        store=True,
    )

    @api.depends("pickup_line_ids.amount_total")
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.pickup_line_ids.mapped("amount_total"))

    @api.depends("pickup_line_ids")
    def _compute_line_count(self):
        for order in self:
            order.line_count = len(order.pickup_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        seq_model = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = seq_model.next_by_code("doorandoor.pickup.order") or "New"
        return super().create(vals_list)

    def action_mark_pending(self):
        self.write({"state": "pending"})
        return True

    def action_mark_ready(self):
        self.write({"state": "ready"})
        return True

    def action_mark_delivered(self):
        for order in self:
            order.pickup_line_ids.write({"qty_delivered": 0.0})
            for line in order.pickup_line_ids:
                line.qty_delivered = line.product_uom_qty
        self.write(
            {
                "state": "delivered",
                "delivered_by_id": self.env.user.id,
                "delivered_date": fields.Datetime.now(),
            }
        )
        return True

    def action_mark_cancelled(self):
        self.write({"state": "cancelled"})
        return True

    def action_reset_new(self):
        self.write(
            {
                "state": "new",
                "delivered_by_id": False,
                "delivered_date": False,
            }
        )
        return True

    def action_print_pickup_order(self):
        self.ensure_one()
        return self.env.ref("doorandoor_sales_new.action_report_pickup_order").report_action(self)

    def _ddsn_compute_operational_state(self):
        self.ensure_one()
        picking = self.picking_id
        if not picking:
            return "new"
        if picking.state in ("assigned", "done"):
            return "ready"
        if picking.state == "cancel":
            return "cancelled"
        return "pending"

    def _ddsn_sync_state_from_operation(self):
        for order in self.filtered(lambda record: record.state not in ("delivered", "cancelled")):
            order.state = order._ddsn_compute_operational_state()


class DoorandoorPickupOrderLine(models.Model):
    _name = "doorandoor.pickup.order.line"
    _description = "DoorAndDoor Pickup Order Line"
    _order = "id"

    pickup_order_id = fields.Many2one(
        "doorandoor.pickup.order",
        string="Pickup Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    fulfillment_line_id = fields.Many2one(
        "doorandoor.fulfillment.line",
        string="Fulfillment Line",
        required=True,
        ondelete="restrict",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        related="fulfillment_line_id.product_id",
        store=True,
        readonly=True,
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Sale Order Line",
        related="fulfillment_line_id.sale_line_id",
        store=True,
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Authorized Qty",
        digits="Product Unit of Measure",
        readonly=True,
    )
    qty_delivered = fields.Float(
        string="Delivered Qty",
        digits="Product Unit of Measure",
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="pickup_order_id.currency_id",
        store=True,
        readonly=True,
    )
