import base64

from markupsafe import Markup, escape

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class DoorAndDoorHistoricalDelivery(models.Model):
    _inherit = "doorandoor.historical.delivery"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ddhl_invalidate_linked_operation_cache()
        return records

    def write(self, vals):
        linked_before = self._ddhl_linked_operations()
        result = super().write(vals)
        if {"picking_id", "transfer_dispatch_id", "transfer_receipt_id"}.intersection(vals):
            self._ddhl_invalidate_linked_operation_cache(extra=linked_before)
        return result

    def _ddhl_linked_operations(self):
        operations = self.env["stock.picking"].sudo()
        for history in self.sudo():
            operations |= history.picking_id
            operations |= history.transfer_dispatch_id
            operations |= history.transfer_receipt_id
            operations |= history.ddhl_regularization_ids.mapped("picking_id")
        return operations._ddhl_expand_explicit_chain()

    def _ddhl_invalidate_linked_operation_cache(self, extra=None):
        operations = self._ddhl_linked_operations() | (
            extra or self.env["stock.picking"].sudo()
        )
        if operations:
            operations.invalidate_recordset([
                "ddhl_related_operation_ids",
                "ddhl_related_operation_count",
            ])

    ddhl_regularization_ids = fields.One2many(
        "doorandoor.historic.regularization", "historical_delivery_id",
        string="Recepciones históricas", readonly=True,
    )
    ddhl_regularization_count = fields.Integer(
        string="Recepciones históricas", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_requested_qty = fields.Float(
        string="Solicitado", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_regularized_qty = fields.Float(
        string="Localizado", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_reserved_qty = fields.Float(
        string="Reservado", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_pending_qty = fields.Float(
        string="Pendiente físico", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_readiness_state = fields.Selection(
        [("review", "Revisar histórico"),
         ("missing", "Falta localizar mercancía"),
         ("partial", "Localización parcial"),
         ("ready_dispatch", "Lista para despachar"),
         ("in_transit", "En tránsito"),
         ("awaiting_receipt", "Pendiente de recepción"),
         ("ready_delivery", "Lista para entregar"),
         ("delivered", "Entregada"),
         ("incident", "Incidencia")],
        string="Preparación física", compute="_compute_ddhl_readiness", store=True,
    )
    ddhl_cycle_operation_ids = fields.Many2many(
        "stock.picking",
        compute="_compute_ddhl_cycle_operations",
        string="Operaciones del ciclo",
    )
    ddhl_cycle_operation_count = fields.Integer(
        compute="_compute_ddhl_cycle_operations",
        string="Operaciones del ciclo",
    )
    ddhl_can_create_next_operation = fields.Boolean(
        compute="_compute_ddhl_cycle_operations",
        string="Puede crear la siguiente operación",
    )

    @api.depends(
        "picking_id",
        "transfer_dispatch_id",
        "transfer_receipt_id",
        "ddhl_regularization_ids.state",
        "ddhl_regularization_ids.destination_mode",
        "ddhl_regularization_ids.picking_id",
        "ddhl_regularization_ids.picking_id.state",
    )
    def _compute_ddhl_cycle_operations(self):
        for history in self:
            operations = history._ddhl_linked_operations().exists()
            history.ddhl_cycle_operation_ids = operations
            history.ddhl_cycle_operation_count = len(operations)
            ready_receipt = history.ddhl_regularization_ids.filtered(
                lambda record: (
                    record.state == "done"
                    and record.destination_mode == "predispatch"
                    and record.picking_id.state == "done"
                )
            )
            history.ddhl_can_create_next_operation = bool(
                ready_receipt
                and not history.picking_id
                and not history.transfer_dispatch_id
                and history.state == "draft"
            )

    @api.depends(
        "state", "line_ids.quantity",
        "ddhl_regularization_ids.state",
        "ddhl_regularization_ids.line_ids.physical_quantity",
        "picking_id.state", "picking_id.move_ids.product_uom_qty",
        "picking_id.move_ids.quantity",
        "transfer_dispatch_id.state",
        "transfer_dispatch_id.move_ids.product_uom_qty",
        "transfer_dispatch_id.move_ids.quantity",
        "transfer_receipt_id.state",
    )
    def _compute_ddhl_readiness(self):
        for history in self:
            requested = sum(history.line_ids.mapped("quantity"))
            completed = history.ddhl_regularization_ids.filtered(
                lambda record: record.state == "done"
            )
            regularized = sum(completed.line_ids.mapped("physical_quantity"))
            operation = history.transfer_dispatch_id or history.picking_id
            demand = sum(operation.move_ids.filtered(
                lambda move: move.state != "cancel"
            ).mapped("product_uom_qty"))
            reserved = sum(operation.move_ids.filtered(
                lambda move: move.state != "cancel"
            ).mapped("quantity"))
            history.ddhl_regularization_count = len(history.ddhl_regularization_ids)
            history.ddhl_requested_qty = requested
            history.ddhl_regularized_qty = regularized
            history.ddhl_reserved_qty = reserved
            history.ddhl_pending_qty = max(requested - max(regularized, reserved), 0.0)

            if history.state == "done" or history.picking_id.state == "done":
                readiness = "delivered"
            elif history.state == "cancel":
                readiness = "incident"
            elif history.transfer_dispatch_id:
                receipt = history.transfer_receipt_id or (
                    history.transfer_dispatch_id.ddpc_transfer_receipt_picking_id
                )
                if receipt.state == "done":
                    readiness = "ready_delivery" if history.picking_id else "awaiting_receipt"
                elif history.transfer_dispatch_id.state == "done":
                    readiness = "awaiting_receipt"
                elif demand and float_compare(
                    reserved, demand,
                    precision_rounding=history.line_ids[:1].product_uom_id.rounding or 1.0,
                ) >= 0:
                    readiness = "ready_dispatch"
                elif regularized or reserved:
                    readiness = "partial"
                else:
                    readiness = "missing"
            elif history.picking_id:
                if demand and float_compare(
                    reserved, demand,
                    precision_rounding=history.line_ids[:1].product_uom_id.rounding or 1.0,
                ) >= 0:
                    readiness = "ready_delivery"
                elif regularized or reserved:
                    readiness = "partial"
                else:
                    readiness = "missing"
            elif not history.line_ids:
                readiness = "review"
            elif regularized >= requested:
                readiness = "ready_dispatch"
            elif regularized:
                readiness = "partial"
            else:
                readiness = "missing"
            history.ddhl_readiness_state = readiness

    def action_ddhl_create_regularization(self):
        self.ensure_one()
        self._ddhl_assert_regularization_needed()
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar mercancía histórica"),
            "res_model": "doorandoor.historic.regularization",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_historical_delivery_id": self.id,
                # A regularization records where the merchandise will be
                # received, not the warehouse that currently supplies it.
                "default_warehouse_id": self.warehouse_id.id,
                "default_destination_location_id": self.warehouse_id.lot_stock_id.id,
                "default_evidence_attachment_ids": [
                    (6, 0, self.evidence_attachment_ids.ids)
                ],
            },
        }

    def action_ddhl_start_predispatch_cycle(self):
        """Prepare only the physical origin receipt and its printable evidence."""
        self.ensure_one()
        self._ddhl_assert_regularization_needed()
        if self.state != "draft":
            raise UserError(_(
                "El ciclo debe iniciarse antes de liberar la venta histórica."
            ))
        if not self.line_ids:
            raise UserError(_("Defina primero los ITEM de la factura histórica."))
        direct_attachments = self.env["ir.attachment"].sudo().search([
            ("res_model", "=", self._name), ("res_id", "=", self.id),
        ])
        evidence = self.evidence_attachment_ids | direct_attachments
        if not evidence:
            raise UserError(_(
                "Adjunte primero la factura o documento del sistema anterior."
            ))

        RegularizationLine = self.env[
            "doorandoor.historic.regularization.line"
        ].sudo()
        commands = []
        for historical_line in self.line_ids:
            completed = RegularizationLine.search([
                ("historical_line_id", "=", historical_line.id),
                ("regularization_id.state", "=", "done"),
            ])
            pending = historical_line.quantity - sum(
                completed.mapped("physical_quantity")
            )
            if pending <= 0:
                continue
            rounded = int(round(pending))
            if abs(pending - rounded) > (
                historical_line.product_uom_id.rounding or 1.0
            ) / 2:
                raise UserError(_(
                    "El ITEM %(product)s tiene %(quantity)s unidades pendientes; "
                    "los labels físicos requieren cantidades enteras."
                ) % {
                    "product": historical_line.product_id.display_name,
                    "quantity": pending,
                })
            commands.append((0, 0, {
                "historical_line_id": historical_line.id,
                "physical_quantity": rounded,
            }))
        if not commands:
            raise UserError(_("La factura histórica no tiene cantidades pendientes."))

        regularization = self.env["doorandoor.historic.regularization"].create({
            "historical_delivery_id": self.id,
            "warehouse_id": self.supply_warehouse_id.id,
            "destination_mode": "predispatch",
            # Safe temporary destination. The receipt replaces it immediately
            # with a document-specific predispatch area.
            "destination_location_id": self.supply_warehouse_id.lot_stock_id.id,
            "evidence_attachment_ids": [(6, 0, evidence.ids)],
            "physical_note": _(
                "Recepción iniciada desde %(history)s / %(reference)s. "
                "El operador debe confirmar físicamente cantidades y labels."
            ) % {
                "history": self.display_name,
                "reference": self.external_reference,
            },
            "line_ids": commands,
        })
        regularization.action_prepare_reception()
        regularization.action_prepare_labels()
        self._ddhl_attach_operation_pdfs(
            regularization.picking_id,
            regularization.line_ids.mapped("serial_ids").filtered("active"),
            _("recepcion inicial"),
        )
        body = Markup(
            "<p><strong>Ciclo histórico iniciado desde la factura anterior.</strong></p>"
            "<p>Recepción: %(receipt)s<br/>Almacén: %(warehouse)s<br/>"
            "Unidades propuestas: %(quantity)s.</p>"
            "<p>El operador debe comprobar las cantidades, preparar e imprimir "
            "los labels y validar la recepción con Hanger. Solo esa validación "
            "creará el traslado o la entrega siguiente.</p>"
        ) % {
            "receipt": escape(regularization.picking_id.display_name),
            "warehouse": escape(self.supply_warehouse_id.display_name),
            "quantity": regularization.total_physical,
        }
        self.message_post(body=body, attachment_ids=evidence.ids)
        regularization.message_post(body=body, attachment_ids=evidence.ids)
        return regularization.get_formview_action()

    def _ddhl_attach_operation_pdfs(self, picking, serials, phase):
        """Attach the operation slip and its exact DoorAndDoor labels."""
        self.ensure_one()
        if not picking:
            raise UserError(_("No existe una operación para preparar sus PDF."))
        Attachment = self.env["ir.attachment"].sudo()
        created = Attachment
        slip_name = "%s_albaran_%s.pdf" % (
            picking.name.replace("/", "-"), phase.replace(" ", "-"),
        )
        if not Attachment.search_count([
            ("res_model", "=", picking._name), ("res_id", "=", picking.id),
            ("name", "=", slip_name),
        ]):
            report = self.env.ref("stock.action_report_picking").sudo()
            pdf, __content_type = report._render_qweb_pdf(
                report.report_name, res_ids=picking.ids,
            )
            created |= Attachment.create({
                "name": slip_name, "type": "binary",
                "datas": base64.b64encode(pdf), "mimetype": "application/pdf",
                "res_model": picking._name, "res_id": picking.id,
            })

        serials = serials.filtered("active")
        label_name = "%s_labels_%s.pdf" % (
            picking.name.replace("/", "-"), phase.replace(" ", "-"),
        )
        if serials and not Attachment.search_count([
            ("res_model", "=", picking._name), ("res_id", "=", picking.id),
            ("name", "=", label_name),
        ]):
            payloads = []
            for batch in serials.mapped("batch_id"):
                payloads.extend(batch._label_payloads(
                    serials=serials.filtered(lambda item: item.batch_id == batch)
                ))
            report = self.env.ref(
                "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
            ).sudo()
            pdf, __content_type = report._render_qweb_pdf(
                report.report_name,
                res_ids=serials[:1].batch_id.ids,
                data={"labels": payloads},
            )
            created |= Attachment.create({
                "name": label_name, "type": "binary",
                "datas": base64.b64encode(pdf), "mimetype": "application/pdf",
                "res_model": picking._name, "res_id": picking.id,
            })
        if created:
            body = Markup(
                "<p><strong>Documentos listos para %(phase)s.</strong></p>"
                "<p>Albarán: %(operation)s<br/>Labels: %(labels)s.</p>"
            ) % {
                "phase": escape(phase),
                "operation": escape(picking.display_name),
                "labels": escape(", ".join(serials.mapped("code")) or _("No aplica")),
            }
            picking.message_post(body=body, attachment_ids=created.ids)
            self.message_post(body=body, attachment_ids=created.ids)
        return created

    def _ddhl_create_delivery_shell(self, source_location, quantities=None):
        self.ensure_one()
        picking = self.env["stock.picking"].create({
            "partner_id": self.partner_id.id,
            "picking_type_id": self.warehouse_id.out_type_id.id,
            "location_id": source_location.id,
            "location_dest_id": self.partner_id.property_stock_customer.id,
            "origin": _("Factura histórica %(history)s / %(reference)s") % {
                "history": self.display_name,
                "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
        })
        for line in self.line_ids:
            quantity = (
                quantities.get(line.product_id.id, 0.0)
                if quantities is not None else line.quantity
            )
            if quantity <= 0:
                continue
            self.env["stock.move"].create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": quantity,
                "product_uom": line.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": source_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_id.id,
            })
        picking.action_confirm()
        return picking

    def _ddhl_create_next_after_initial_receipt(self, regularization):
        """Create only the phase unlocked by the validated origin receipt."""
        self.ensure_one()
        if self.picking_id or self.transfer_dispatch_id or self.transfer_receipt_id:
            operation = self.transfer_dispatch_id or self.picking_id
            regularization._ddhl_reserve_received_labels(operation)
            return operation
        source_predispatch = regularization.destination_location_id
        serials = regularization.picking_id.ddmh_serial_scan_ids.mapped(
            "serial_id"
        ).filtered("active")
        received_lines = regularization.line_ids.filtered(
            lambda line: line.physical_quantity > 0
        )
        received_quantities = {
            line.product_id.id: line.physical_quantity
            for line in received_lines
        }
        if self.supply_warehouse_id == self.warehouse_id:
            delivery = self._ddhl_create_delivery_shell(
                source_predispatch, quantities=received_quantities,
            )
            self.write({"picking_id": delivery.id, "state": "ready"})
            regularization._ddhl_reserve_received_labels(delivery)
            self._ddhl_attach_operation_pdfs(delivery, serials, _("entrega"))
            return delivery

        # The destination predispatch belongs to the transfer receipt. The
        # customer delivery does not exist until that receipt is validated.
        Location = self.env["stock.location"].sudo()
        root = Location.search([
            ("location_id", "=", self.warehouse_id.view_location_id.id),
            ("ddic_is_predispatch_root", "=", True),
        ], limit=1)
        if not root:
            root = Location.create({
                "name": "PRE-DESPACHO",
                "location_id": self.warehouse_id.view_location_id.id,
                "usage": "view",
                "ddic_is_predispatch_root": True,
            })
        destination_predispatch = Location.create({
            "name": "HDEL-%s" % self.name.replace("/", "-"),
            "location_id": root.id,
            "usage": "internal",
            "ddic_is_predispatch": True,
        })

        transit = self.env["stock.picking"]._ddpc_get_transfer_transit_location(
            self.company_id
        )
        dispatch = self.env["stock.picking"].create({
            "picking_type_id": self.supply_warehouse_id.int_type_id.id,
            "location_id": source_predispatch.id,
            "location_dest_id": transit.id,
            "origin": _("Factura histórica %(history)s / %(reference)s") % {
                "history": self.display_name,
                "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
            "ddpc_transfer_stage": "dispatch",
            "ddpc_transfer_target_location_id": destination_predispatch.id,
            "ddpc_transfer_origin_warehouse_id": self.supply_warehouse_id.id,
            "ddhl_source_operation_id": regularization.picking_id.id,
        })
        for line in received_lines:
            self.env["stock.move"].create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.physical_quantity,
                "product_uom": line.product_id.uom_id.id,
                "picking_id": dispatch.id,
                "location_id": source_predispatch.id,
                "location_dest_id": transit.id,
                "company_id": self.company_id.id,
            })
        dispatch.action_confirm()

        receipt = self.env["stock.picking"].create({
            "picking_type_id": self.warehouse_id.in_type_id.id,
            "location_id": transit.id,
            "location_dest_id": destination_predispatch.id,
            "origin": _("Recepción de %s") % dispatch.display_name,
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
            "ddpc_transfer_stage": "receipt",
            "ddpc_transfer_source_picking_id": dispatch.id,
            "ddpc_transfer_target_location_id": destination_predispatch.id,
            "ddpc_transfer_origin_warehouse_id": self.supply_warehouse_id.id,
            "ddhl_source_operation_id": dispatch.id,
        })
        for dispatch_move in dispatch.move_ids:
            self.env["stock.move"].create({
                "name": dispatch_move.name,
                "product_id": dispatch_move.product_id.id,
                "product_uom_qty": dispatch_move.product_uom_qty,
                "product_uom": dispatch_move.product_uom.id,
                "picking_id": receipt.id,
                "location_id": transit.id,
                "location_dest_id": destination_predispatch.id,
                "company_id": self.company_id.id,
                "origin": dispatch.name,
                "move_orig_ids": [(4, dispatch_move.id)],
            })
        receipt.action_confirm()
        dispatch.write({"ddpc_transfer_receipt_picking_id": receipt.id})

        for line in received_lines:
            # The origin Hanger operator must not receive general access to the
            # destination warehouse.  Create only this linked destination
            # control with technical elevation; chatter and Hanger validation
            # continue recording the real operators at each stage.
            self.env["inventory.serial.receipt"].with_user(SUPERUSER_ID).create({
                "operation_type": "internal",
                "label_mode": "existing",
                "destination_purpose": "delivery",
                "picking_id": receipt.id,
                "warehouse_id": self.warehouse_id.id,
                "predispatch_location_id": destination_predispatch.id,
                "product_id": line.product_id.id,
                "quantity": int(round(line.physical_quantity)),
            })
        self.write({
            "transfer_dispatch_id": dispatch.id,
            "transfer_receipt_id": receipt.id,
            "state": "transfer_pending",
        })
        regularization._ddhl_reserve_received_labels(dispatch)
        self._ddhl_attach_operation_pdfs(dispatch, serials, _("despacho de traslado"))
        self._ddhl_attach_operation_pdfs(receipt, serials, _("recepcion destino"))
        return dispatch | receipt

    def _ddhl_create_delivery_after_transfer_receipt(self, serials):
        """Create the customer delivery only after Hanger validates destination."""
        self.ensure_one()
        if self.picking_id:
            return self.picking_id
        receipt = self.transfer_receipt_id
        if not receipt or receipt.state != "done":
            raise UserError(_("Valide primero la recepción destino con Hanger."))
        received_quantities = {}
        for move in receipt.move_ids.filtered(lambda move: move.state == "done"):
            received_quantities[move.product_id.id] = (
                received_quantities.get(move.product_id.id, 0.0) + move.quantity
            )
        delivery = self._ddhl_create_delivery_shell(
            receipt.location_dest_id, quantities=received_quantities,
        )
        delivery.write({
            "ddhl_source_operation_id": receipt.id,
            "ddic_predispatch_location_id": receipt.location_dest_id.id,
        })
        self.write({"picking_id": delivery.id, "state": "ready"})
        serials.sudo().write({
            "reserved_picking_id": delivery.id,
            "reserved_by_id": self.env.user.id,
            "reserved_at": fields.Datetime.now(),
        })
        delivery.action_assign()
        self._ddhl_attach_operation_pdfs(delivery, serials, _("entrega"))
        return delivery

    def _ddhl_predispatch_source_location(self):
        self.ensure_one()
        regularizations = self.ddhl_regularization_ids.filtered(
            lambda record: (
                record.state == "done"
                and record.destination_mode == "predispatch"
                and record.destination_location_id
                and record.warehouse_id == self.warehouse_id
            )
        )
        locations = regularizations.mapped("destination_location_id")
        if len(locations) > 1:
            raise UserError(_(
                "La mercancía de esta factura quedó distribuida en varios "
                "predespachos. Consolídela antes de crear una sola salida."
            ))
        return locations

    def _create_customer_delivery(self):
        """Dispatch the received goods from their document predispatch area."""
        self.ensure_one()
        source = self._ddhl_predispatch_source_location()
        if not source:
            return super()._create_customer_delivery()

        picking_type = self.warehouse_id.out_type_id
        destination = self.partner_id.property_stock_customer
        if not picking_type or not destination:
            raise UserError(_(
                "El almacén o el cliente no tiene configurada la operación de entrega."
            ))
        picking = self.env["stock.picking"].create({
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "origin": _("Factura histórica %(reference)s") % {
                "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
        })
        for line in self.line_ids:
            self.env["stock.move"].create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.quantity,
                "product_uom": line.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "company_id": self.company_id.id,
            })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _release_after_transfer_receipt(self, receipt):
        """Complete the historical chain after the official transfer receipt.

        The base flow creates and links the customer delivery.  Historical
        predispatch labels also need to follow that delivery; otherwise the
        operation exists but Hanger cannot identify the units assigned to it.
        """
        pending = self.filtered(
            lambda history: history.state == "transfer_pending" and not history.picking_id
        )
        result = super()._release_after_transfer_receipt(receipt)
        for history in pending.filtered("picking_id"):
            history.transfer_receipt_id = receipt
            regularizations = history.ddhl_regularization_ids.filtered(
                lambda record: (
                    record.state == "done"
                    and record.destination_mode == "predispatch"
                    and record.destination_location_id == receipt.location_dest_id
                )
            )
            if len(regularizations) == 1:
                regularizations._ddhl_reserve_received_labels(history.picking_id)
        return result

    def _ddhl_assert_regularization_needed(self):
        """Never duplicate inventory already assigned to the historical operation."""
        for history in self:
            operation = history.transfer_dispatch_id or history.picking_id
            moves = operation.move_ids.filtered(
                lambda move: move.state not in ("done", "cancel")
            ) if operation else self.env["stock.move"]
            if not moves:
                continue
            fully_reserved = all(
                float_compare(
                    move.quantity,
                    move.product_uom_qty,
                    precision_rounding=move.product_uom.rounding or 1.0,
                ) >= 0
                for move in moves
            )
            if fully_reserved:
                raise UserError(_(
                    "%(history)s ya tiene %(operation)s reservado al 100%%. "
                    "No cree inventario adicional: continúe con el conteo Hanger y la validación de esa operación."
                ) % {
                    "history": history.display_name,
                    "operation": operation.display_name,
                })
        return True

    def action_ddhl_open_regularizations(self):
        self.ensure_one()
        action = self.env.ref(
            "doorandoor_historic_logistics.action_historic_regularizations"
        ).sudo().read()[0]
        action["domain"] = [("historical_delivery_id", "=", self.id)]
        action["context"] = {"default_historical_delivery_id": self.id}
        return action

    def action_ddhl_open_cycle_operations(self):
        self.ensure_one()
        operations = self.ddhl_cycle_operation_ids
        if not operations:
            raise UserError(_(
                "El ciclo todavía no tiene operaciones. Inicie primero la recepción."
            ))
        if len(operations) == 1:
            return operations.get_formview_action()
        # Reading the technical window action requires Settings in standard
        # Odoo.  Elevate only that metadata read; ``operations`` was already
        # computed under the real user's stock rules and remains the domain.
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        action.update({
            "name": _("Operaciones de %s") % self.display_name,
            "domain": [("id", "in", operations.ids)],
            "context": {"create": False},
        })
        return action

    def action_ddhl_select_next_operation(self, source_operation=None):
        self.ensure_one()
        if not self.ddhl_can_create_next_operation:
            raise UserError(_(
                "Confirme primero la recepción y sus labels, o abra la operación "
                "que ya está enlazada al ciclo."
            ))
        completed = self.ddhl_regularization_ids.filtered(
            lambda record: (
                record.state == "done"
                and record.destination_mode == "predispatch"
                and record.picking_id.state == "done"
            )
        )
        source = source_operation or completed[:1].picking_id
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear siguiente operación"),
            "res_model": "doorandoor.historic.next.operation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_historical_delivery_id": self.id,
                "default_source_operation_id": source.id,
                "default_destination_warehouse_id": self.warehouse_id.id,
            },
        }


class DoorAndDoorHistoricalDeliveryLine(models.Model):
    _inherit = "doorandoor.historical.delivery.line"

    ddhl_regularized_qty = fields.Float(
        string="Localizado físicamente", compute="_compute_ddhl_regularized_qty",
    )

    def _compute_ddhl_regularized_qty(self):
        RegularizationLine = self.env["doorandoor.historic.regularization.line"]
        for line in self:
            registered = RegularizationLine.search([
                ("historical_line_id", "=", line.id),
                ("regularization_id.state", "=", "done"),
            ])
            line.ddhl_regularized_qty = sum(registered.mapped("physical_quantity"))


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ddhl_expand_explicit_chain(self):
        """Include every explicitly linked partial/backorder operation."""
        operations = self.sudo().exists()
        pending = operations
        while pending:
            linked = (
                pending.mapped("backorder_id")
                | pending.mapped("backorder_ids")
                | pending.mapped("ddpc_transfer_source_picking_id")
                | pending.mapped("ddpc_transfer_receipt_picking_id")
                | pending.mapped("ddhl_source_operation_id")
                | pending.mapped("ddhl_created_operation_ids")
            ).exists()
            new_operations = linked - operations
            if not new_operations:
                break
            operations |= new_operations
            pending = new_operations
        return operations

    def button_validate(self):
        if not self.env.context.get("ddhl_historical_validation"):
            pending = self.env["doorandoor.historic.regularization"].sudo().search([
                ("picking_id", "in", self.ids),
                ("state", "in", ("draft", "labels_ready")),
            ], limit=1)
            if pending:
                raise UserError(_(
                    "La recepción %(receipt)s pertenece a %(regularization)s. "
                    "Confirme los labels desde la regularización histórica; no use la validación estándar."
                ) % {
                    "receipt": pending.picking_id.display_name,
                    "regularization": pending.display_name,
                })
        return super().button_validate()

    ddhl_related_operation_ids = fields.Many2many(
        "stock.picking",
        compute="_compute_ddhl_related_operations",
        string="Operaciones enlazadas",
    )
    ddhl_related_operation_count = fields.Integer(
        compute="_compute_ddhl_related_operations",
        string="Operaciones enlazadas",
    )
    ddhl_source_operation_id = fields.Many2one(
        "stock.picking",
        string="Operación precedente",
        readonly=True,
        copy=False,
        index=True,
    )
    ddhl_created_operation_ids = fields.One2many(
        "stock.picking",
        "ddhl_source_operation_id",
        string="Operaciones siguientes",
        readonly=True,
    )

    def _ddhl_linked_histories(self):
        self.ensure_one()
        History = self.env["doorandoor.historical.delivery"].sudo()
        Regularization = self.env["doorandoor.historic.regularization"].sudo()
        histories = History.search([
            "|", "|",
            ("picking_id", "=", self.id),
            ("transfer_dispatch_id", "=", self.id),
            ("transfer_receipt_id", "=", self.id),
        ])
        histories |= Regularization.search([
            ("picking_id", "=", self.id)
        ]).mapped("historical_delivery_id")
        return histories

    def _ddhl_operation_chain_candidates(self):
        """Return explicit picking links only; never infer chains from free text."""
        self.ensure_one()
        Regularization = self.env["doorandoor.historic.regularization"].sudo()
        histories = self._ddhl_linked_histories()
        regularizations = Regularization.search([("picking_id", "=", self.id)])
        histories |= regularizations.mapped("historical_delivery_id")

        candidates = self.env["stock.picking"].sudo()
        if histories:
            candidates |= histories.mapped("picking_id")
            candidates |= histories.mapped("transfer_dispatch_id")
            candidates |= histories.mapped("transfer_receipt_id")
            candidates |= Regularization.search([
                ("historical_delivery_id", "in", histories.ids),
                ("picking_id", "!=", False),
            ]).mapped("picking_id")

        candidates |= self.ddpc_transfer_source_picking_id.sudo()
        candidates |= self.ddpc_transfer_receipt_picking_id.sudo()
        candidates |= self.ddhl_source_operation_id.sudo()
        candidates |= self.ddhl_created_operation_ids.sudo()
        if self.ddpc_transfer_source_picking_id:
            candidates |= self.ddpc_transfer_source_picking_id.sudo().ddpc_transfer_receipt_picking_id
        if self.ddpc_transfer_receipt_picking_id:
            candidates |= self.ddpc_transfer_receipt_picking_id.sudo().ddpc_transfer_source_picking_id

        candidates = candidates._ddhl_expand_explicit_chain()
        return candidates - self.sudo()

    @api.depends(
        "ddpc_transfer_source_picking_id",
        "ddpc_transfer_receipt_picking_id",
        "ddhl_source_operation_id",
        "ddhl_created_operation_ids",
    )
    def _compute_ddhl_related_operations(self):
        Picking = self.env["stock.picking"]
        for picking in self:
            candidate_ids = picking._ddhl_operation_chain_candidates().ids
            # Apply the current operator's stock rules before exposing links.
            visible = Picking.search([("id", "in", candidate_ids)]) if candidate_ids else Picking
            picking.ddhl_related_operation_ids = visible
            picking.ddhl_related_operation_count = len(visible)

    def action_ddhl_open_related_operations(self):
        self.ensure_one()
        operations = self.ddhl_related_operation_ids
        if not operations:
            histories = self._ddhl_linked_histories()
            if len(histories) == 1:
                return histories.action_ddhl_select_next_operation(
                    source_operation=self
                )
            return {
                "type": "ir.actions.act_window",
                "name": _("Crear siguiente operación"),
                "res_model": "doorandoor.historic.next.operation.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_source_operation_id": self.id,
                    "default_partner_id": self.partner_id.id,
                    "default_destination_warehouse_id": (
                        self.location_dest_id.warehouse_id
                        or self.picking_type_id.warehouse_id
                    ).id,
                },
            }
        if len(operations) == 1:
            return operations.get_formview_action()
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        action.update({
            "name": _("Operaciones enlazadas de %s") % self.display_name,
            "domain": [("id", "in", operations.ids)],
            "context": {"create": False},
        })
        return action
