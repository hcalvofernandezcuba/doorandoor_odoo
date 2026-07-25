from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ddsn_prepare_mrp_production_vals(self, line, qty_to_manufacture, bom):
        vals = super()._ddsn_prepare_mrp_production_vals(line, qty_to_manufacture, bom)
        sale_order = self.sale_order_id
        origin_warehouse = sale_order.warehouse_id
        delivery_warehouse = sale_order.ddpa_delivery_warehouse_id or origin_warehouse
        vals.update(
            {
                "ddpa_origin_warehouse_id": origin_warehouse.id if origin_warehouse else False,
                "ddpa_delivery_warehouse_id": delivery_warehouse.id if delivery_warehouse else False,
            }
        )
        return vals

    def _ddsn_get_outgoing_picking_type(self):
        self.ensure_one()
        production = self.fulfillment_line_ids.mapped("mrp_production_id").filtered(
            lambda prod: prod.state not in ("done", "cancel") or prod.ddpa_delivery_warehouse_id
        )[:1]
        if production and production.ddpa_delivery_warehouse_id:
            warehouse = production.ddpa_delivery_warehouse_id
            if warehouse.out_type_id:
                return warehouse.out_type_id
        return super()._ddsn_get_outgoing_picking_type()
