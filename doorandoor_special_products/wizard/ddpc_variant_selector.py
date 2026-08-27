from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DdpcVariantSelector(models.TransientModel):
    _inherit = "ddpc.variant.selector"

    ddsp_can_create_special = fields.Boolean(
        compute="_compute_ddsp_can_create_special"
    )
    ddsp_declare_special = fields.Boolean(string="Declarar como producto transformado")
    ddsp_width = fields.Float(string="Ancho transformado")
    ddsp_height = fields.Float(string="Alto transformado")
    ddsp_special_notes = fields.Text(string="Especificaciones de transformacion")
    ddsp_production_instructions = fields.Text(string="Instrucciones de fabricacion")

    @api.depends(
        "move_line_id.move_id.state",
        "move_line_id.move_id.move_type",
        "move_line_id.product_id",
        "move_line_id.product_id.product_tmpl_id.ddsp_is_special",
        "move_line_id.product_id.product_tmpl_id.ddsp_allow_special",
    )
    def _compute_ddsp_can_create_special(self):
        for wizard in self:
            line = wizard.move_line_id
            wizard.ddsp_can_create_special = bool(
                line
                and line.move_id.state == "draft"
                and line.move_id.move_type == "out_invoice"
                and line.product_id
                and not line.product_id.product_tmpl_id.ddsp_is_special
                and line.product_id.product_tmpl_id.ddsp_allow_special
            )

    def action_open_ddsp_special_product_wizard(self):
        self.ensure_one()
        return self.move_line_id.action_open_ddsp_special_product_wizard()

    def action_apply_variant(self):
        self.ensure_one()
        if not self.ddsp_declare_special:
            return super().action_apply_variant()
        if not self.ddsp_can_create_special:
            raise UserError(_("Esta linea no permite crear un producto transformado."))
        if self.ddsp_width <= 0 or self.ddsp_height <= 0:
            raise UserError(_("Complete Ancho y Alto transformado con valores mayores que cero."))
        if not self.ddsp_special_notes or not self.ddsp_production_instructions:
            raise UserError(_("Complete las especificaciones y las instrucciones de fabricacion."))

        variant = self._ddpc_get_guided_variant()
        line = self._ddpc_apply_variant_to_line(variant)
        special_wizard = self.env["ddsp.special.product.wizard"].with_context(
            default_invoice_line_id=line.id
        ).create(
            {
                "invoice_line_id": line.id,
                "base_product_id": variant.id,
                "width": self.ddsp_width,
                "height": self.ddsp_height,
                "special_notes": self.ddsp_special_notes,
                "production_instructions": self.ddsp_production_instructions,
                "price_unit": line.price_unit,
            }
        )
        special_wizard._onchange_special_dimensions_name()
        return {
            "type": "ir.actions.act_window",
            "name": _("Completar producto transformado y LDM"),
            "res_model": "ddsp.special.product.wizard",
            "res_id": special_wizard.id,
            "view_mode": "form",
            "target": "new",
        }
