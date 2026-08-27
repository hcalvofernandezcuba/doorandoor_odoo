from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "doorandoor.document.barcode.mixin"]

    ddsn_supply_invoice_id = fields.Many2one(
        "account.move",
        string="Factura solicitante",
        copy=False,
        readonly=True,
        index=True,
    )
    ddsn_supply_preinvoice_id = fields.Many2one(
        "account.move",
        string="Prefactura de origen",
        copy=False,
        readonly=True,
        index=True,
    )
    ddsn_supply_source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén proveedor",
        copy=False,
        readonly=True,
        index=True,
    )
    ddsn_supply_destination_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén solicitante",
        copy=False,
        readonly=True,
        index=True,
    )

    _sql_constraints = [
        (
            "ddsn_supply_unique",
            "UNIQUE(ddsn_supply_invoice_id, ddsn_supply_source_warehouse_id, ddsn_supply_destination_warehouse_id)",
            "Ya existe un traslado de abastecimiento para esta factura y estos almacenes.",
        )
    ]

    def _action_done(self):
        """Synchronize fulfillment after the native move is really completed.

        This hook also covers the second step of the partial-delivery wizard;
        relying only on ``button_validate`` misses that path in Odoo.
        """
        result = super()._action_done()
        done_outgoing = self.filtered(
            lambda picking: picking.state == "done" and picking.picking_type_code == "outgoing"
        )
        if done_outgoing:
            done_outgoing._ddsn_sync_invoice_delivery_status()
            done_outgoing._ddsn_sync_pickup_order_state()
        self.filtered(
            lambda picking: picking.state == "done" and picking.ddsn_supply_invoice_id
        ).mapped("ddsn_supply_invoice_id")._ddsn_sync_release_from_payments()
        return result

    def button_validate(self):
        self._ddsn_check_fully_paid_before_delivery()
        pending_pickings = self.filtered(lambda picking: picking.state not in ("done", "cancel"))
        result = super().button_validate()
        done_pickings = pending_pickings.filtered(lambda picking: picking.state == "done")
        done_pickings._ddsn_sync_invoice_delivery_status()
        self._ddsn_sync_pickup_order_state()
        return result

    def _ddsn_check_fully_paid_before_delivery(self):
        """Never complete a customer delivery before its invoice is fully paid."""
        for picking in self.filtered(lambda record: record.picking_type_code == "outgoing"):
            sale_orders = picking.sale_id | picking.move_ids.sale_line_id.order_id
            if not sale_orders:
                continue

            invoices = sale_orders.invoice_ids
            if "ddsn_invoice_move_id" in sale_orders._fields:
                invoices |= sale_orders.mapped("ddsn_invoice_move_id")
            invoices = invoices.filtered(
                lambda move: move.move_type == "out_invoice"
                and move.state != "cancel"
                and not move.ddsn_is_preinvoice
            )
            if invoices and all(
                move.state == "posted" and move._ddsn_is_fully_paid()
                for move in invoices
            ):
                continue

            raise ValidationError(
                _(
                    "No se puede validar la entrega %(delivery)s. La cotizacion "
                    "%(sale)s debe tener una factura publicada y totalmente pagada."
                )
                % {
                    "delivery": picking.display_name,
                    "sale": ", ".join(sale_orders.mapped("name")),
                }
            )

    def _ddsn_sync_invoice_delivery_status(self):
        for picking in self:
            fulfillment_lines = self.env["doorandoor.fulfillment.line"].search([("picking_id", "=", picking.id)])
            for fulfillment_line in fulfillment_lines:
                # ``qty_sent_stock`` is the planned/released quantity.  It must
                # never be treated as delivered during a partial validation.
                # The sale line is Odoo's official delivered quantity and also
                # follows split moves/backorders and returns.
                sale_line = fulfillment_line.sale_line_id
                delivered_qty = fulfillment_line.qty_delivered
                if sale_line:
                    delivered_qty = min(
                        max(sale_line.qty_delivered, 0.0),
                        fulfillment_line.qty_invoiced,
                    )

                pending_qty = max(fulfillment_line.qty_invoiced - delivered_qty, 0.0)
                values = {
                    "qty_delivered": delivered_qty,
                    "qty_pending_delivery": pending_qty,
                }
                values["state"] = "delivered" if pending_qty <= 0 else "in_process"

                # A partial validation completes the original picking and
                # creates a native backorder.  Keep the operational line linked
                # to that open document so the warehouse can finish the saldo.
                if pending_qty > 0:
                    open_backorder = picking.backorder_ids.filtered(
                        lambda backorder: backorder.state not in ("done", "cancel")
                        and backorder.move_ids.filtered(
                            lambda move: move.product_id == fulfillment_line.product_id
                            and (not sale_line or move.sale_line_id == sale_line)
                        )
                    )[:1]
                    if open_backorder:
                        values["picking_id"] = open_backorder.id
                fulfillment_line.write(values)
                fulfillment_line.move_id._ddsn_set_release_state()

    def _ddsn_sync_pickup_order_state(self):
        pickup_orders = self.env["doorandoor.pickup.order"].search([("picking_id", "in", self.ids)])
        pickup_orders._ddsn_sync_state_from_operation()
