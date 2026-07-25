from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_apply_inventory(self):
        self._ddsn_check_locked_qty_before_inventory_adjustment()
        return super().action_apply_inventory()

    def _apply_inventory(self):
        self._ddsn_check_locked_qty_before_inventory_adjustment()
        return super()._apply_inventory()

    def _ddsn_check_locked_qty_before_inventory_adjustment(self):
        inventory_quants = self.filtered(
            lambda quant: quant.location_id.usage in ("internal", "transit")
            and quant.product_id
            and float_compare(
                quant.inventory_diff_quantity,
                0.0,
                precision_rounding=quant.product_uom_id.rounding,
            ) < 0
        )
        if not inventory_quants:
            return

        locked_qty_by_product = inventory_quants._ddsn_get_locked_qty_by_product()
        for quant in inventory_quants:
            locked_qty = locked_qty_by_product.get((quant.company_id.id, quant.product_id.id), 0.0)
            if float_is_zero(locked_qty, precision_rounding=quant.product_uom_id.rounding):
                continue

            target_qty = quant.inventory_quantity
            if float_compare(
                target_qty,
                locked_qty,
                precision_rounding=quant.product_uom_id.rounding,
            ) < 0:
                raise UserError(
                    _(
                        "No puedes ajustar manualmente el stock de %(product)s por debajo de %(locked_qty)s %(uom)s. "
                        "Esa cantidad ya esta comprometida por facturas confirmadas y debe conciliarse "
                        "mediante el flujo logistico, no con un ajuste manual."
                    )
                    % {
                        "product": quant.product_id.display_name,
                        "locked_qty": locked_qty,
                        "uom": quant.product_uom_id.display_name or quant.product_uom_id.name,
                    }
                )

    def _ddsn_get_locked_qty_by_product(self):
        locked_qty_by_product = {}
        fulfillment_lines = self.env["doorandoor.fulfillment.line"].search(
            [
                ("move_id.state", "=", "posted"),
                ("qty_released", ">", 0.0),
                ("product_id", "in", self.product_id.ids),
                ("move_id.company_id", "in", self.company_id.ids),
            ]
        )
        for line in fulfillment_lines:
            pending_locked_qty = max(line.qty_invoiced - line.qty_delivered, 0.0)
            if pending_locked_qty <= 0:
                continue
            key = (line.move_id.company_id.id, line.product_id.id)
            locked_qty_by_product[key] = locked_qty_by_product.get(key, 0.0) + pending_locked_qty
        return locked_qty_by_product
