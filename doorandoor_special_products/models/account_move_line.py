from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddsp_is_special_product = fields.Boolean(
        related="product_id.product_tmpl_id.ddsp_is_special",
        string="Producto personalizado",
        readonly=True,
    )
    ddsp_special_bom_state = fields.Selection(
        related="product_id.product_tmpl_id.ddsp_bom_state",
        string="Estado LDM transformada",
        readonly=True,
    )

    def _ddsp_get_production_report_status(self):
        self.ensure_one()
        if not self.ddsp_is_special_product:
            return False
        fulfillment = self.move_id.fulfillment_line_ids.filtered(
            lambda item: item.move_line_id == self
        )[:1]
        production = fulfillment.mrp_production_id
        if production:
            state_label = dict(
                production._fields["state"]._description_selection(self.env)
            ).get(production.state, production.state)
            return _("Salida a Produccion: %s (%s)") % (
                production.name,
                state_label,
            )
        return _("Preparado para Produccion. La MO se liberara al cumplir las reglas de pago.")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        lines._ddsp_link_special_origin()
        return lines

    def write(self, vals):
        products_before = self.mapped("product_id.product_tmpl_id")
        result = super().write(vals)
        if {"product_id", "quantity", "price_unit", "move_id"}.intersection(vals):
            (products_before | self.mapped("product_id.product_tmpl_id"))._ddsp_touch_activity()
            self._ddsp_link_special_origin()
        return result

    def _ddsp_link_special_origin(self):
        for line in self.filtered(
            lambda item: item.move_id
            and item.move_id.move_type in ("out_invoice", "out_refund")
            and item.product_id
        ):
            template = line.product_id.product_tmpl_id
            if template.ddsp_is_special and not template.ddsp_origin_invoice_line_id:
                template.sudo().write(
                    {
                        "ddsp_origin_invoice_id": line.move_id.id,
                        "ddsp_origin_invoice_line_id": line.id,
                    }
                )

    def action_open_ddsp_special_product_wizard(self):
        self.ensure_one()
        if self.move_id.state != "draft" or self.move_id.move_type != "out_invoice":
            raise UserError(_("El producto transformado solo puede crearse desde una factura o prefactura de cliente en borrador."))
        if not self.product_id:
            raise UserError(_("Selecciona primero el producto que servira como base."))
        if self.product_id.product_tmpl_id.ddsp_is_special:
            raise UserError(_("Esta linea ya contiene un producto transformado. Abre su ficha para revisar sus medidas y LDM."))
        if not self.product_id.product_tmpl_id.ddsp_allow_special:
            raise UserError(_("El producto seleccionado no permite crear productos transformados."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear producto transformado"),
            "res_model": "ddsp.special.product.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_invoice_line_id": self.id},
        }
