from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_ddsp_special_from_master(self):
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError(_("La cotizacion debe permanecer abierta para agregar un producto especial."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Agregar producto especial"),
            "res_model": "ddsp.special.from.master.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sale_order_id": self.id},
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ddsp_is_special_product = fields.Boolean(
        related="product_id.product_tmpl_id.ddsp_is_special",
        string="Producto personalizado",
        readonly=True,
    )

    def _ddsp_get_production_report_status(self):
        self.ensure_one()
        if not self.ddsp_is_special_product:
            return False
        return _("Configurado para Produccion. La MO se liberara al cumplir las reglas de pago.")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped("product_id.product_tmpl_id")._ddsp_touch_activity()
        lines._ddsp_link_special_origin()
        return lines

    def write(self, vals):
        products_before = self.mapped("product_id.product_tmpl_id")
        result = super().write(vals)
        if {"product_id", "product_uom_qty", "price_unit", "order_id"}.intersection(vals):
            (products_before | self.mapped("product_id.product_tmpl_id"))._ddsp_touch_activity()
            self._ddsp_link_special_origin()
        return result

    def _ddsp_link_special_origin(self):
        for line in self.filtered(lambda item: item.order_id and item.product_id):
            template = line.product_id.product_tmpl_id
            if template.ddsp_is_special and not template.ddsp_origin_sale_order_line_id:
                template.sudo().write(
                    {
                        "ddsp_origin_sale_order_id": line.order_id.id,
                        "ddsp_origin_sale_order_line_id": line.id,
                    }
                )

    def action_open_ddsp_special_product_wizard(self):
        self.ensure_one()
        if self.order_id.state not in ("draft", "sent"):
            raise UserError(_("El producto transformado solo puede crearse desde una cotizacion abierta."))
        if not self.product_id:
            raise UserError(_("Selecciona primero el producto que servira como base."))
        if self.product_id.product_tmpl_id.ddsp_is_special:
            raise UserError(_("Esta linea ya contiene un producto transformado."))
        if not self.product_id.product_tmpl_id.ddsp_allow_special:
            raise UserError(_("El producto seleccionado no permite crear productos transformados."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear producto transformado"),
            "res_model": "ddsp.special.product.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sale_order_line_id": self.id},
        }
