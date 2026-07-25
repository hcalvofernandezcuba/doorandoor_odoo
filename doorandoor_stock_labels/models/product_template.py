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
    ddsl_product_label_code = fields.Char(
        string="Product Label Code",
        help="Code printed as barcode in the dedicated product label.",
    )
    ddsl_label_model = fields.Char(string="Label Model")
    ddsl_label_design = fields.Char(string="Label Design")
    ddsl_label_size = fields.Char(string="Label Size")
    ddsl_label_swing = fields.Char(string="Label Swing")
    ddsl_label_hinge = fields.Char(string="Label Hinge")

    def action_open_ddsl_product_label_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Labels de productos",
            "res_model": "ddsl.product.label.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }
