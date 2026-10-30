from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_ddsp_special_from_master(self):
        self.ensure_one()
        if (
            self.state != "draft"
            or self.move_type != "out_invoice"
            or (self.ddsn_is_preinvoice and self.ddsn_preinvoice_state == "confirmed")
        ):
            raise UserError(_("La prefactura o factura debe permanecer en borrador para agregar un producto especial."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Agregar producto especial"),
            "res_model": "ddsp.special.from.master.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def action_post(self):
        special_lines = self.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "draft"
        ).invoice_line_ids.filtered(lambda line: line.product_id.product_tmpl_id.ddsp_is_special)
        for line in special_lines:
            product = line.product_id.product_tmpl_id
            bom = product._ddsp_get_special_bom()
            if not bom or not bom.bom_line_ids:
                raise UserError(
                    _("El producto personalizado %s no tiene una LDM con componentes.") % product.display_name
                )
            if product.ddsp_bom_state != "validated":
                raise UserError(
                    _("La LDM del producto personalizado %s debe ser validada por Produccion antes de facturar.")
                    % product.display_name
                )
        result = super().action_post()
        today = fields.Date.context_today(self)
        special_lines.mapped("product_id.product_tmpl_id")._ddsp_mark_sold(today)
        return result

    def _ddsn_get_line_route(self, line, qty_released):
        if qty_released > 0 and line.product_id.product_tmpl_id.ddsp_is_special:
            return "ready_mrp"
        return super()._ddsn_get_line_route(line, qty_released)

    def _ddsn_get_bom_for_product(self, product):
        if product.product_tmpl_id.ddsp_is_special:
            return product.product_tmpl_id._ddsp_get_special_bom()
        return super()._ddsn_get_bom_for_product(product)

    def _ddsn_get_or_create_mrp_production(self, line, qty_to_manufacture):
        if line.product_id.product_tmpl_id.ddsp_is_special:
            existing = line.mrp_production_id.filtered(
                lambda production: production.state not in ("done", "cancel")
            )[:1]
            if existing:
                existing.write(
                    {
                        "product_qty": existing.product_qty + qty_to_manufacture,
                        "origin": self._ddsn_get_mrp_origin_label(line),
                    }
                )
                if existing.state == "draft":
                    existing.action_confirm()
                return existing
        return super()._ddsn_get_or_create_mrp_production(line, qty_to_manufacture)
