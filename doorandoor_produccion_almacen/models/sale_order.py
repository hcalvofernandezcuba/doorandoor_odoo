from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddpa_delivery_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse Delivery",
        domain="[('company_id', '=', company_id)]",
        copy=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_warehouse_id = vals.get("warehouse_id")
            if not vals.get("ddpa_delivery_warehouse_id"):
                vals["ddpa_delivery_warehouse_id"] = order_warehouse_id
        orders = super().create(vals_list)
        default_warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        for order in orders:
            updates = {}
            if not order.ddpa_delivery_warehouse_id and (order.warehouse_id or default_warehouse):
                updates["ddpa_delivery_warehouse_id"] = (order.warehouse_id or default_warehouse).id
            if updates:
                order.write(updates)
        return orders

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id_set_ddpa_delivery(self):
        for order in self.filtered("warehouse_id"):
            if not order.ddpa_delivery_warehouse_id:
                order.ddpa_delivery_warehouse_id = order.warehouse_id
