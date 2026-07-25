from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ddsn_payment_release_policy = fields.Selection(
        selection=[
            ("prorated", "Prorated"),
            ("sequential_line", "Sequential by Line"),
            ("priority", "Sequential by Priority"),
            ("manual", "Manual"),
        ],
        string="Default Payment Release Policy",
        config_parameter="doorandoor_sales_new.payment_release_policy",
        default="sequential_line",
    )

    ddsn_fulfillment_route_policy = fields.Selection(
        selection=[
            ("by_stock", "By Stock Availability"),
            ("by_product_route", "By Product Route"),
            ("by_product_type", "By Product Type"),
            ("force_mrp", "Force Manufacturing"),
            ("force_stock", "Force Stock"),
            ("manual", "Manual"),
        ],
        string="Default Fulfillment Route Policy",
        config_parameter="doorandoor_sales_new.fulfillment_route_policy",
        default="by_stock",
    )

    ddsn_partial_stock_policy = fields.Selection(
        selection=[
            ("split_stock_mrp", "Deliver Stock and Manufacture Rest"),
            ("all_mrp", "Manufacture All"),
            ("wait_full_stock", "Wait Full Stock"),
            ("reserve_partial", "Reserve Partial"),
            ("manual", "Manual"),
        ],
        string="Default Partial Stock Policy",
        config_parameter="doorandoor_sales_new.partial_stock_policy",
        default="split_stock_mrp",
    )

    ddsn_picking_creation_policy = fields.Selection(
        selection=[
            ("per_payment", "One Picking per Payment"),
            ("group_by_invoice", "Grouped by Invoice"),
            ("manual_release", "Manual Release"),
        ],
        string="Default Picking Creation Policy",
        config_parameter="doorandoor_sales_new.picking_creation_policy",
        default="per_payment",
    )

    ddsn_mrp_creation_policy = fields.Selection(
        selection=[
            ("per_line", "One MO per Released Line"),
            ("group_by_product", "Group by Product"),
            ("manual_release", "Manual Release"),
        ],
        string="Default Manufacturing Creation Policy",
        config_parameter="doorandoor_sales_new.mrp_creation_policy",
        default="per_line",
    )

    ddsn_preinvoice_reservation_hours = fields.Integer(
        string="Preinvoice Reservation Hours",
        config_parameter="doorandoor_sales_new.preinvoice_reservation_hours",
        default=24,
    )
