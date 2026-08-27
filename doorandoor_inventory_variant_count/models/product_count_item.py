from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductCountItem(models.Model):
    _name = "product.count.item"
    _description = "Product Count Item"
    _order = "product_id, sequence, name"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)
    product_id = fields.Many2one(
        "product.product", required=True, ondelete="cascade", index=True,
        domain="[('is_storable', '=', True)]",
    )
    item_type = fields.Selection(
        [("component", "Component"), ("attribute", "Custom Attribute")],
        required=True, default="component",
    )
    code = fields.Char(index=True, help="Internal identifier used during imports.")
    barcode = fields.Char(index=True, help="Barcode accepted by counting sessions.")
    qty_per_product = fields.Float(
        string="Quantity per Product", required=True, default=1.0,
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        "uom.uom", required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
    )
    note = fields.Char()

    _sql_constraints = [
        ("product_code_unique", "unique(product_id, code)",
         "The item code must be unique for each product variant."),
        ("barcode_unique", "unique(barcode)", "The item barcode must be unique."),
        ("qty_positive", "check(qty_per_product > 0)",
         "Quantity per product must be greater than zero."),
    ]

    @api.constrains("barcode")
    def _check_barcode(self):
        for rec in self:
            if rec.barcode and not rec.barcode.strip():
                raise ValidationError("The barcode cannot contain only spaces.")


class ProductProduct(models.Model):
    _inherit = "product.product"

    count_item_ids = fields.One2many(
        "product.count.item", "product_id", string="Count Items"
    )
    count_item_count = fields.Integer(compute="_compute_count_item_count")

    def _compute_count_item_count(self):
        grouped = self.env["product.count.item"]._read_group(
            [("product_id", "in", self.ids)], ["product_id"], ["__count"]
        )
        counts = {product.id: count for product, count in grouped}
        for product in self:
            product.count_item_count = counts.get(product.id, 0)

    def action_open_count_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "doorandoor_inventory_variant_count.action_product_count_item"
        )
        action["domain"] = [("product_id", "=", self.id)]
        action["context"] = {"default_product_id": self.id}
        return action
