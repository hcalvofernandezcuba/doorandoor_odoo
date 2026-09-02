from odoo import fields, models


class DoorAndDoorFulfillmentLine(models.Model):
    _inherit = "doorandoor.fulfillment.line"

    qty_sent_planning = fields.Float(string="Cantidad enviada a planificación", default=0.0, copy=False)
    production_need_ids = fields.One2many(
        "ddfc.production.need", "fulfillment_line_id", string="Necesidades de producción", copy=False
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ddsn_sync_mrp_fulfillment_documents(self):
        for move in self:
            mrp_lines = move.fulfillment_line_ids.filtered(
                lambda line: line.state == "ready_mrp" and line.qty_released > line.qty_sent_planning
            )
            for line in mrp_lines:
                quantity = max(line.qty_released - line.qty_sent_planning, 0.0)
                if quantity <= 0:
                    continue
                sale = move.sale_order_id
                warehouse = sale.ddpa_delivery_warehouse_id or sale.warehouse_id
                if not warehouse:
                    continue
                self.env["ddfc.production.need"].create({
                    "warehouse_id": warehouse.id, "product_id": line.product_id.id,
                    "requested_qty": quantity, "required_date": fields.Date.context_today(move),
                    "eligible_at": fields.Datetime.now(), "source_type": "sale",
                    "origin": "%s | %s" % (move.name, line.product_id.display_name),
                    "source_invoice_id": move.id,
                    "fulfillment_line_id": line.id,
                })
                line.qty_sent_planning += quantity
