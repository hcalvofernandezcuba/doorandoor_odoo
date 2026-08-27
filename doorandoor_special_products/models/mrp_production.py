from odoo import _, api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    ddsp_is_special = fields.Boolean(related="product_id.product_tmpl_id.ddsp_is_special")
    ddsp_product_kind = fields.Selection(
        related="product_id.product_tmpl_id.ddsp_product_kind",
        string="Tipo de producto personalizado",
    )
    ddsp_manufacturing_family = fields.Selection(
        related="product_id.product_tmpl_id.ddsp_manufacturing_family",
        string="Familia de fabricacion",
    )
    ddsp_source_bom_template_id = fields.Many2one(
        related="product_id.product_tmpl_id.ddsp_source_bom_template_id",
        string="LDM maestra utilizada",
    )
    ddsp_base_product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id.ddsp_base_product_tmpl_id", string="Producto base"
    )
    ddsp_dimensions_display = fields.Char(
        related="product_id.product_tmpl_id.ddsp_dimensions_display", string="Cambios de fabricacion"
    )
    ddsp_origin_invoice_id = fields.Many2one(
        related="product_id.product_tmpl_id.ddsp_origin_invoice_id", string="Factura de origen"
    )
    ddsp_special_notes = fields.Text(
        related="product_id.product_tmpl_id.ddsp_special_notes", string="Especificaciones de transformacion"
    )
    ddsp_production_instructions = fields.Text(
        related="product_id.product_tmpl_id.ddsp_production_instructions",
        string="Instrucciones de fabricacion",
    )

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        productions.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        for production in productions.filtered("ddsp_is_special"):
            product_type = dict(
                production._fields["ddsp_product_kind"]._description_selection(self.env)
            ).get(production.ddsp_product_kind, _("Personalizado"))
            production.message_post(
                body=_("Orden de producto %s: medidas %s. Revise especificaciones e instrucciones de fabricacion.")
                % (product_type, production.ddsp_dimensions_display or _("sin medidas registradas"))
            )
        return productions

    def write(self, vals):
        result = super().write(vals)
        if {"state", "product_qty", "qty_producing", "date_start", "date_finished"}.intersection(vals):
            self.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        return result
