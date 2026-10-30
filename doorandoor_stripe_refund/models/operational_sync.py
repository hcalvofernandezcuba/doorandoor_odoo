from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddsr_refunded_quantity = fields.Float(
        string="Cantidad devuelta", compute="_compute_ddsr_refund_quantities",
        digits="Product Unit of Measure",
    )
    ddsr_net_quantity = fields.Float(
        string="Cantidad neta", compute="_compute_ddsr_refund_quantities",
        digits="Product Unit of Measure",
    )

    def _compute_ddsr_refund_quantities(self):
        request_line_model = self.env["doorandoor.stripe.refund.request.line"]
        grouped = request_line_model._read_group(
            [("invoice_line_id", "in", self.ids), ("request_id.state", "=", "done")],
            ["invoice_line_id"], ["quantity:sum"],
        ) if self.ids else []
        refunded_by_line = {line.id: quantity for line, quantity in grouped}
        for line in self:
            refunded = refunded_by_line.get(line.id, 0.0)
            line.ddsr_refunded_quantity = refunded
            line.ddsr_net_quantity = max(line.quantity - refunded, 0.0)


class DoorandoorFulfillmentLine(models.Model):
    _inherit = "doorandoor.fulfillment.line"

    ddsr_qty_refunded = fields.Float(
        string="Qty Refunded", default=0.0, readonly=True,
        digits="Product Unit of Measure", copy=False,
    )
    ddsr_qty_net = fields.Float(
        string="Qty Net", compute="_compute_ddsr_qty_net",
        digits="Product Unit of Measure",
    )

    @api.depends("qty_invoiced", "ddsr_qty_refunded")
    def _compute_ddsr_qty_net(self):
        for line in self:
            line.ddsr_qty_net = max(line.qty_invoiced - line.ddsr_qty_refunded, 0.0)


class StripeRefundRequest(models.Model):
    _inherit = "doorandoor.stripe.refund.request"

    operational_sync_state = fields.Selection(
        [("pending", "Pendiente"), ("done", "Sincronizada"), ("error", "Error")],
        default="pending", readonly=True, copy=False, tracking=True,
    )
    operational_sync_error = fields.Text(readonly=True, copy=False)

    def _sync_from_transaction(self):
        result = super()._sync_from_transaction()
        for request in self.filtered(lambda item: item.state == "done" and item.operational_sync_state != "done"):
            try:
                request._apply_operational_refund()
            except Exception as error:
                request.sudo().with_context(ddsr_state_transition=True).write({
                    "operational_sync_state": "error", "operational_sync_error": str(error),
                })
                request.invoice_id.message_post(body=_(
                    "ALERTA: Stripe confirmó %(request)s, pero falló la actualización de las cantidades "
                    "operativas. Las entregas permanecen bloqueadas hasta corregir el error: %(error)s"
                ) % {"request": request.name, "error": str(error)})
        return result

    def _apply_operational_refund(self):
        self.ensure_one()
        affected = self.env["doorandoor.fulfillment.line"]
        for request_line in self.line_ids.filtered(lambda line: line.quantity > 0):
            fulfillment = request_line.invoice_line_id.fulfillment_line_id
            if not fulfillment:
                continue
            refunded = sum(self.env["doorandoor.stripe.refund.request.line"].search([
                ("invoice_line_id", "=", request_line.invoice_line_id.id),
                ("request_id.state", "=", "done"),
            ]).mapped("quantity"))
            net = max(fulfillment.qty_invoiced - refunded, 0.0)
            if fulfillment.qty_delivered > net:
                raise ValidationError(_(
                    "No puede reducirse %(product)s a %(net)s: ya se entregaron %(delivered)s."
                ) % {"product": fulfillment.product_id.display_name, "net": net, "delivered": fulfillment.qty_delivered})
            fulfillment.ddsr_qty_refunded = refunded
            affected |= fulfillment
        self._rebuild_open_operations(affected)
        completed_requests = self.search([
            ("invoice_id", "=", self.invoice_id.id),
            ("state", "=", "done"),
            ("operational_sync_state", "!=", "done"),
        ])
        completed_requests.sudo().with_context(ddsr_state_transition=True).write({
            "operational_sync_state": "done", "operational_sync_error": False,
        })
        self.invoice_id.message_post(body=_(
            "Cantidades operativas sincronizadas después de %(request)s. Se conservaron las cantidades originales de la factura y se recalcularon los saldos netos entregables."
        ) % {"request": self.name})
        return True

    def _rebuild_open_operations(self, affected):
        if not affected:
            return True
        linked_pickings = affected.mapped("picking_id").filtered(lambda p: p.state != "done")
        rebuild_lines = affected
        if linked_pickings:
            rebuild_lines |= self.env["doorandoor.fulfillment.line"].search([
                ("picking_id", "in", linked_pickings.ids)
            ])
            self.env["doorandoor.pickup.order"].search([
                ("picking_id", "in", linked_pickings.ids),
            ]).filtered(
                lambda order: order.state not in ("delivered", "cancelled")
            ).action_mark_cancelled()
            linked_pickings.filtered(lambda picking: picking.state != "cancel").action_cancel()
        open_productions = rebuild_lines.mapped("mrp_production_id").filtered(
            lambda production: production.state not in ("done", "cancel")
        )
        if open_productions:
            open_productions.action_cancel()
        invoices = rebuild_lines.mapped("move_id")
        for line in rebuild_lines:
            net = max(line.qty_invoiced - line.ddsr_qty_refunded, line.qty_delivered)
            released = min(line.qty_released, net)
            route = line.move_id._ddsn_get_line_route(line, released)
            line.write({
                "qty_released": released,
                "qty_pending_payment": max(net - released, 0.0),
                "qty_pending_delivery": max(net - line.qty_delivered, 0.0),
                "qty_sent_stock": line.qty_delivered,
                "qty_sent_mrp": 0.0,
                "picking_id": False,
                "mrp_production_id": False,
                "state": "delivered" if line.qty_delivered >= net else route,
            })
        for invoice in invoices:
            invoice._ddsn_sync_stock_fulfillment_documents()
            invoice._ddsn_sync_mrp_fulfillment_documents()
            invoice._ddsn_ensure_pickup_orders()
            invoice._ddsn_set_release_state()
        return True


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ddsr_check_refund_hold(self):
        for picking in self.filtered(lambda item: item.picking_type_code == "outgoing"):
            invoices = self.env["doorandoor.fulfillment.line"].search([
                ("picking_id", "=", picking.id)
            ]).mapped("move_id")
            pending = invoices.mapped("ddsr_refund_request_ids").filtered(
                lambda request: request.state in ("pending", "processing")
                or (request.state == "done" and request.operational_sync_state != "done")
            )
            if pending:
                raise ValidationError(_(
                    "No puede validarse esta entrega: las devoluciones %(requests)s están pendientes "
                    "de resolución o de sincronización operativa y bloquean temporalmente el despacho."
                ) % {"requests": ", ".join(pending.mapped("name"))})

    def button_validate(self):
        self._ddsr_check_refund_hold()
        return super().button_validate()
