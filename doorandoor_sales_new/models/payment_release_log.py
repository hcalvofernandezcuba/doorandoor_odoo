from odoo import fields, models


class DoorandoorPaymentReleaseLog(models.Model):
    _name = "doorandoor.payment.release.log"
    _description = "DoorAndDoor Payment Release Log"
    _order = "write_date desc, id desc"

    move_id = fields.Many2one(
        "account.move",
        string="Invoice",
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
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="move_id.currency_id",
        store=True,
        readonly=True,
    )
    amount_applied = fields.Monetary(
        string="Applied Amount",
        currency_field="currency_id",
        default=0.0,
        readonly=True,
    )
    policy_used = fields.Selection(
        selection=[
            ("prorated", "Prorated"),
            ("sequential_line", "Sequential by Line"),
            ("priority", "Sequential by Priority"),
            ("manual", "Manual"),
        ],
        string="Policy Used",
        readonly=True,
    )
    notes = fields.Text(string="Notes", readonly=True)
