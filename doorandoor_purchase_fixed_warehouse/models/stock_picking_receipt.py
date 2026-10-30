from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ddpfw_delivery_picking(self, allocation):
        picking = allocation.fulfillment_line_id.picking_id
        if picking and picking.state != "cancel":
            return picking
        sale = allocation.sale_order_id
        if not sale and allocation.invoice_id:
            sale = allocation.invoice_id.invoice_line_ids.sale_line_ids.order_id[:1]
        return sale.picking_ids.filtered(
            lambda item: item.picking_type_code == "outgoing" and item.state != "cancel"
        )[:1]

    def _ddic_receipt_groups(self):
        self.ensure_one()
        if self.location_id.usage != "supplier" or not self.move_ids.purchase_line_id:
            return super()._ddic_receipt_groups()

        groups = []
        for move in self.move_ids.filtered(
            lambda item: item.state != "cancel" and item.product_uom_qty > 0
        ):
            remaining = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id
            )
            allocations = move.purchase_line_id.ddpfw_supply_allocation_ids.sorted("id")
            for allocation in allocations:
                if remaining <= 1e-6:
                    break
                allocated = allocation.product_uom_id._compute_quantity(
                    allocation.quantity, move.product_id.uom_id
                )
                quantity = min(remaining, allocated)
                if quantity <= 1e-6:
                    continue
                delivery = allocation.origin_type == "sale"
                destination_picking = (
                    self._ddpfw_delivery_picking(allocation)
                    if delivery else self.env["stock.picking"]
                )
                reference = allocation.origin_document if delivery else False
                groups.append({
                    "key": "move:%s:allocation:%s" % (move.id, allocation.id),
                    "product": move.product_id,
                    "quantity": quantity,
                    "destination_purpose": "delivery" if delivery else "storage",
                    "destination_reference": reference,
                    "destination_picking": destination_picking,
                    "operation_type": "supplier",
                    "label_mode": "generate",
                })
                remaining -= quantity
            if remaining > 1e-6:
                groups.append({
                    "key": "move:%s:unallocated-storage" % move.id,
                    "product": move.product_id,
                    "quantity": remaining,
                    "destination_purpose": "storage",
                    "destination_reference": False,
                    "destination_picking": self.env["stock.picking"],
                    "operation_type": "supplier",
                    "label_mode": "generate",
                })
        return groups
