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
        string="Codigo de producto para label",
        help="Codigo que se imprimira como texto y codigo de barras en el label del producto.",
    )
    ddsl_label_model = fields.Char(string="Label Model")
    ddsl_label_design = fields.Char(string="Label Design")
    ddsl_label_size = fields.Char(string="Label Size")
    ddsl_label_swing = fields.Char(string="Label Swing")
    ddsl_label_hinge = fields.Char(string="Label Hinge")

    def ddsl_get_product_label_code(self):
        self.ensure_one()
        configured_code = self.ddsl_product_label_code or self.default_code or self.barcode
        if configured_code:
            return configured_code
        active_variants = self.product_variant_ids.filtered("active")
        if len(active_variants) == 1:
            variant = active_variants[0]
            variant_code = variant.barcode or variant.default_code
            if variant_code:
                return variant_code
        return f"DDSL-P{self.id}"

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
