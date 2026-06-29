from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    ddpc_variant_extra_price = fields.Float(
        string="Variant Extra Price",
        digits="Product Price",
        help="Additional amount to add over the product template sales price when this variant is invoiced.",
    )
