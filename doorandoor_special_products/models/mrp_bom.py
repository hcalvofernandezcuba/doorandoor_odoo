from odoo import api, fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    ddsp_is_special = fields.Boolean(related="product_tmpl_id.ddsp_is_special")
    ddsp_product_kind = fields.Selection(
        related="product_tmpl_id.ddsp_product_kind",
        string="Tipo de producto personalizado",
    )
    ddsp_manufacturing_family = fields.Selection(
        related="product_tmpl_id.ddsp_manufacturing_family",
        string="Familia de fabricacion",
    )
    ddsp_source_bom_template_id = fields.Many2one(
        related="product_tmpl_id.ddsp_source_bom_template_id",
        string="LDM maestra utilizada",
    )
    ddsp_base_product_tmpl_id = fields.Many2one(
        related="product_tmpl_id.ddsp_base_product_tmpl_id", string="Producto base"
    )
    ddsp_dimensions_display = fields.Char(
        related="product_tmpl_id.ddsp_dimensions_display", string="Cambios de fabricacion"
    )
    ddsp_origin_invoice_id = fields.Many2one(
        related="product_tmpl_id.ddsp_origin_invoice_id", string="Factura de origen"
    )
    ddsp_special_notes = fields.Text(
        related="product_tmpl_id.ddsp_special_notes", string="Especificaciones de transformacion"
    )
    ddsp_production_instructions = fields.Text(
        related="product_tmpl_id.ddsp_production_instructions",
        string="Instrucciones de fabricacion",
    )
    ddsp_bom_state = fields.Selection(
        related="product_tmpl_id.ddsp_bom_state", string="Estado de LDM transformada"
    )

    def write(self, vals):
        products = self.mapped("product_tmpl_id").filtered("ddsp_is_special")
        result = super().write(vals)
        if products and not self.env.context.get("ddsp_keep_bom_validation"):
            products.filtered(lambda product: product.ddsp_bom_state == "validated").write(
                {"ddsp_bom_state": "draft"}
            )
        return result


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ddsp_reset_special_bom_validation()
        return lines

    def write(self, vals):
        products_before = self.mapped("bom_id.product_tmpl_id")
        result = super().write(vals)
        (products_before | self.mapped("bom_id.product_tmpl_id")).filtered(
            lambda product: product.ddsp_is_special and product.ddsp_bom_state == "validated"
        ).write({"ddsp_bom_state": "draft"})
        return result

    def unlink(self):
        products = self.mapped("bom_id.product_tmpl_id").filtered("ddsp_is_special")
        result = super().unlink()
        products.filtered(lambda product: product.ddsp_bom_state == "validated").write(
            {"ddsp_bom_state": "draft"}
        )
        return result

    def _ddsp_reset_special_bom_validation(self):
        self.mapped("bom_id.product_tmpl_id").filtered(
            lambda product: product.ddsp_is_special and product.ddsp_bom_state == "validated"
        ).write({"ddsp_bom_state": "draft"})
