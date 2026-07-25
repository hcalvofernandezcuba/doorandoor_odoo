from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddsl_print_label_on_receipt = fields.Boolean(
        string="Print Label On Receipt",
        help="If enabled, this product is included by default when printing receipt labels.",
    )
    ddsl_label_use_barcode = fields.Boolean(
        string="Use Product Barcode On Label",
        default=True,
        help="If enabled, label barcode uses the product barcode. Otherwise it uses the internal reference.",
    )
