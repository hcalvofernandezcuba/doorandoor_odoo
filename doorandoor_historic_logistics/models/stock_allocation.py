from collections import defaultdict

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class DoorAndDoorHistoricalDelivery(models.Model):
    _inherit = "doorandoor.historical.delivery"

    ddhl_inventory_treatment = fields.Selection(
        [
            ("existing_stock", "Consumir stock existente de Odoo"),
            ("excluded_legacy", "Excluida: inventario controlado en sistema anterior"),
            ("exceptional_regularization", "Regularización excepcional"),
        ],
        string="Tratamiento de inventario",
        default="existing_stock",
        required=True,
        tracking=True,
        copy=False,
    )
    ddhl_exclusion_reason = fields.Text(string="Motivo de exclusión", tracking=True)
    ddhl_stock_allocation_ids = fields.One2many(
        "doorandoor.historical.stock.allocation",
        "historical_delivery_id",
        string="Labels tomados del inventario",
        copy=False,
    )
    ddhl_stock_allocation_count = fields.Integer(
        compute="_compute_ddhl_stock_allocation",
        string="Labels asignados",
    )
    ddhl_stock_allocation_ready = fields.Boolean(
        compute="_compute_ddhl_stock_allocation",
        string="Stock completamente asignado",
    )

    @api.depends(
        "line_ids.quantity",
        "ddhl_stock_allocation_ids.quantity",
        "ddhl_stock_allocation_ids.state",
    )
    def _compute_ddhl_stock_allocation(self):
        for history in self:
            active = history.ddhl_stock_allocation_ids.filtered(
                lambda allocation: allocation.state != "cancel"
            )
            history.ddhl_stock_allocation_count = int(sum(active.mapped("quantity")))
            requested = sum(history.line_ids.mapped("quantity"))
            allocated = sum(active.mapped("quantity"))
            rounding = history.line_ids[:1].product_uom_id.rounding or 1.0
            history.ddhl_stock_allocation_ready = bool(
                requested
                and float_compare(allocated, requested, precision_rounding=rounding) == 0
            )

    def _ddhl_assert_existing_stock_mode(self):
        self.ensure_one()
        if self.ddhl_inventory_treatment != "existing_stock":
            raise UserError(_(
                "Esta acción solo corresponde a históricos que consumirán stock "
                "existente de Odoo."
            ))
        if self.state != "draft":
            raise UserError(_("La asignación debe prepararse antes de liberar operaciones."))
        if not self.line_ids:
            raise UserError(_("Defina primero los ITEM y cantidades del histórico."))

    def action_ddhl_start_predispatch_cycle(self):
        for history in self:
            if history.ddhl_inventory_treatment != "exceptional_regularization":
                raise UserError(_(
                    "La recepción con labels nuevos está reservada para una "
                    "regularización excepcional documentada. En el flujo normal use "
                    "Proponer labels existentes."
                ))
        return super().action_ddhl_start_predispatch_cycle()

    def action_create_operation(self):
        for history in self:
            if history.ddhl_inventory_treatment == "existing_stock":
                raise UserError(_(
                    "Primero revise y confirme la propuesta de labels existentes. "
                    "La salida histórica no puede reservar stock genérico ni crear "
                    "movimientos sin trazabilidad por label."
                ))
            if history.ddhl_inventory_treatment == "excluded_legacy":
                raise UserError(_(
                    "Una factura excluida no puede crear operaciones de inventario."
                ))
        return super().action_create_operation()

    def _ddhl_available_serial_domain(self, line):
        domain = [
            ("product_id", "=", line.product_id.id),
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("inventory_loaded", "=", True),
            ("current_warehouse_id", "!=", False),
            ("current_location_id.usage", "=", "internal"),
            ("reserved_picking_id", "=", False),
        ]
        if "ddhl_reserved_history_id" in self.env["inventory.unit.serial"]._fields:
            domain.append(("ddhl_reserved_history_id", "=", False))
        return domain

    def _ddhl_linked_operations(self):
        operations = super()._ddhl_linked_operations()
        allocations = self.mapped("ddhl_stock_allocation_ids")
        operations |= allocations.mapped("picking_id")
        operations |= allocations.mapped("receipt_picking_id")
        operations |= allocations.mapped("delivery_picking_id")
        return operations._ddhl_expand_explicit_chain()

    def action_ddhl_prepare_existing_stock(self):
        """Allocate existing unit labels without creating stock or new labels."""
        self.ensure_one()
        self._ddhl_assert_existing_stock_mode()
        if self.ddhl_stock_allocation_ids.filtered(lambda item: item.state != "cancel"):
            raise UserError(_(
                "Ya existe una propuesta de labels. Libérela expresamente antes de recalcular."
            ))

        Serial = self.env["inventory.unit.serial"].sudo()
        # Serialize competing historical allocations.  The serial reservation
        # itself is still made only when the linked stock operation is created.
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", (88413, self.id))
        commands = []
        shortages = []
        for line in self.line_ids:
            rounded = int(round(line.quantity))
            if float_compare(
                line.quantity,
                rounded,
                precision_rounding=line.product_uom_id.rounding,
            ) != 0:
                raise ValidationError(_(
                    "El ITEM %s requiere una cantidad entera para utilizar labels unitarios."
                ) % line.product_id.display_name)

            serials = Serial.search(self._ddhl_available_serial_domain(line))
            priority = {
                self.supply_warehouse_id.id: 0,
                self.warehouse_id.id: 1,
            }
            serials = serials.sorted(
                key=lambda serial: (
                    priority.get(serial.current_warehouse_id.id, 2),
                    serial.current_warehouse_id.id,
                    serial.current_batch_id.id,
                    serial.id,
                )
            )[:rounded]
            if len(serials) < rounded:
                shortages.append(_("%(product)s: requiere %(required)s, disponibles %(available)s") % {
                    "product": line.product_id.display_name,
                    "required": rounded,
                    "available": len(serials),
                })
                continue
            grouped = defaultdict(lambda: Serial.browse())
            for serial in serials:
                grouped[serial.current_warehouse_id] |= serial
            for warehouse, warehouse_serials in grouped.items():
                commands.append((0, 0, {
                    "historical_line_id": line.id,
                    "source_warehouse_id": warehouse.id,
                    "serial_ids": [(6, 0, warehouse_serials.ids)],
                    "quantity": len(warehouse_serials),
                }))

        if shortages:
            raise UserError(_(
                "No hay labels disponibles suficientes para cubrir el histórico:\n%s\n\n"
                "No se creó inventario, recepción ni label nuevo. Revise el almacén "
                "origen o clasifique el caso como regularización excepcional."
            ) % "\n".join(shortages))

        self.write({"ddhl_stock_allocation_ids": commands})
        labels = self.ddhl_stock_allocation_ids.mapped("serial_ids")
        warehouses = self.ddhl_stock_allocation_ids.mapped("source_warehouse_id")
        self.message_post(body=Markup(
            "<p><strong>Propuesta de stock existente preparada.</strong> "
            "No se creó recepción, existencia ni label nuevo.</p>"
            "<p>Unidades: %(quantity)s<br/>Almacenes origen: %(warehouses)s<br/>"
            "Labels: %(labels)s</p>"
        ) % {
            "quantity": len(labels),
            "warehouses": escape(", ".join(warehouses.mapped("display_name"))),
            "labels": escape(", ".join(labels.mapped("code"))),
        })
        return self.get_formview_action()

    def _ddhl_existing_stock_quantities(self, allocations=None):
        self.ensure_one()
        allocations = allocations or self.ddhl_stock_allocation_ids.filtered(
            lambda allocation: allocation.state != "cancel"
        )
        quantities = defaultdict(float)
        for allocation in allocations:
            quantities[allocation.product_id.id] += allocation.quantity
        return quantities

    def _ddhl_reserve_allocation_serials(self, allocations, picking=False):
        self.ensure_one()
        serials = allocations.mapped("serial_ids").sudo()
        if serials:
            self.env.cr.execute(
                "SELECT id FROM inventory_unit_serial WHERE id IN %s FOR UPDATE",
                [tuple(serials.ids)],
            )
        for allocation in allocations:
            final_delivery = bool(
                picking
                and picking == allocation.delivery_picking_id
                and picking.picking_type_id.code == "outgoing"
            )
            expected_warehouse = (
                self.warehouse_id if final_delivery else allocation.source_warehouse_id
            )
            for serial in allocation.serial_ids:
                if (
                    not serial.active
                    or not serial.inventory_loaded
                    or serial.current_warehouse_id != expected_warehouse
                    or serial.current_location_id.usage != "internal"
                ):
                    raise UserError(_(
                        "El label %(label)s cambió de almacén, ubicación o estado desde "
                        "que se preparó la propuesta. Libere la propuesta y calcúlela nuevamente."
                    ) % {"label": serial.code})
                if serial.reserved_picking_id and serial.reserved_picking_id != picking:
                    raise UserError(_(
                        "El label %(label)s ya está reservado para %(operation)s. "
                        "Libere la propuesta y revísela nuevamente."
                    ) % {
                        "label": serial.code,
                        "operation": serial.reserved_picking_id.display_name,
                    })
                if (
                    serial.ddhl_reserved_history_id
                    and serial.ddhl_reserved_history_id != self
                ):
                    raise UserError(_(
                        "El label %(label)s ya está reservado por %(history)s."
                    ) % {
                        "label": serial.code,
                        "history": serial.ddhl_reserved_history_id.display_name,
                    })
        values = {
            "ddhl_reserved_history_id": self.id,
            "reserved_by_id": self.env.user.id,
            "reserved_at": fields.Datetime.now(),
        }
        if picking:
            values["reserved_picking_id"] = picking.id
        serials.write(values)
        return serials

    def _ddhl_create_existing_stock_dispatch(self, source_warehouse, allocations):
        self.ensure_one()
        target = self.warehouse_id.lot_stock_id
        picking_type = source_warehouse.int_type_id
        if not picking_type or not source_warehouse.lot_stock_id or not target:
            raise UserError(_(
                "Los almacenes %(source)s y %(destination)s no tienen configurado "
                "el traslado interno."
            ) % {
                "source": source_warehouse.display_name,
                "destination": self.warehouse_id.display_name,
            })
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source_warehouse.lot_stock_id.id,
            "location_dest_id": target.id,
            "origin": _("Stock existente de %(history)s / %(reference)s") % {
                "history": self.display_name,
                "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
            "ddpc_transfer_target_location_id": target.id,
            "ddpc_transfer_origin_warehouse_id": source_warehouse.id,
        })
        for product_id, quantity in self._ddhl_existing_stock_quantities(
            allocations
        ).items():
            product = self.env["product.product"].browse(product_id)
            self.env["stock.move"].create({
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_id.id,
            })
        picking.action_confirm()
        picking.action_assign()
        allocations.write({"picking_id": picking.id, "state": "reserved"})
        self._ddhl_reserve_allocation_serials(allocations, picking=picking)
        return picking

    def _ddhl_try_create_existing_stock_delivery(self):
        self.ensure_one()
        allocations = self.ddhl_stock_allocation_ids.filtered(
            lambda allocation: allocation.state != "cancel"
        )
        if not allocations or self.picking_id:
            return self.picking_id
        serials = allocations.mapped("serial_ids").filtered("active")
        ready = serials and all(
            serial.inventory_loaded
            and serial.current_warehouse_id == self.warehouse_id
            and serial.current_location_id.usage == "internal"
            for serial in serials
        )
        if not ready:
            return self.env["stock.picking"]
        delivery = self._ddhl_create_delivery_shell(
            self.warehouse_id.lot_stock_id,
            quantities=self._ddhl_existing_stock_quantities(allocations),
        )
        allocations.write({
            "delivery_picking_id": delivery.id,
            "state": "reserved",
        })
        self._ddhl_reserve_allocation_serials(allocations, picking=delivery)
        self.write({"picking_id": delivery.id, "state": "ready"})
        delivery.message_post(body=Markup(
            "<p><strong>Entrega histórica preparada con stock existente.</strong></p>"
            "<p>Histórico: %(history)s<br/>Labels: %(labels)s</p>"
        ) % {
            "history": escape(self.display_name),
            "labels": escape(", ".join(serials.mapped("code"))),
        })
        self.message_post(body=Markup(
            "<p><strong>Todos los labels llegaron al almacén de entrega.</strong> "
            "Se creó %(delivery)s sin generar existencias ni códigos nuevos.</p>"
        ) % {"delivery": escape(delivery.display_name)})
        if not self.env.context.get("ddhl_skip_pdf"):
            self._ddhl_attach_operation_pdfs(delivery, serials, _("entrega"))
        return delivery

    def action_ddhl_approve_existing_stock(self):
        self.ensure_one()
        self._ddhl_assert_existing_stock_mode()
        allocations = self.ddhl_stock_allocation_ids.filtered(
            lambda allocation: allocation.state != "cancel"
        )
        if not allocations or not self.ddhl_stock_allocation_ready:
            raise UserError(_(
                "La propuesta no cubre toda la histórica. Recálculela antes de aprobar."
            ))
        if allocations.filtered(lambda allocation: allocation.state != "proposed"):
            raise UserError(_("La propuesta ya fue aprobada o procesada."))

        # Reserve the historical claim before creating any operation.  The
        # transaction is atomic: any later error restores every serial.
        self._ddhl_reserve_allocation_serials(allocations)
        remote = allocations.filtered(
            lambda allocation: allocation.source_warehouse_id != self.warehouse_id
        )
        operations = self.env["stock.picking"]
        for warehouse in remote.mapped("source_warehouse_id"):
            source_allocations = remote.filtered(
                lambda allocation: allocation.source_warehouse_id == warehouse
            )
            operations |= self._ddhl_create_existing_stock_dispatch(
                warehouse, source_allocations,
            )
        local = allocations - remote
        if local:
            local.write({"state": "reserved"})

        if operations:
            primary = operations.sorted("id")[:1]
            values = {
                "transfer_dispatch_id": primary.id,
                "state": "transfer_pending",
            }
            if len(operations) == 1:
                values["supply_warehouse_id"] = primary.ddpc_source_warehouse_id.id
            self.write(values)
            for operation in operations:
                operation.message_post(body=Markup(
                    "<p><strong>Traslado creado desde stock histórico existente.</strong></p>"
                    "<p>Histórico: %(history)s<br/>Labels: %(labels)s</p>"
                ) % {
                    "history": escape(self.display_name),
                    "labels": escape(", ".join(
                        allocations.filtered(
                            lambda allocation: allocation.picking_id == operation
                        ).mapped("serial_ids.code")
                    )),
                })
                if not self.env.context.get("ddhl_skip_pdf"):
                    self._ddhl_attach_operation_pdfs(
                        operation,
                        allocations.filtered(
                            lambda allocation: allocation.picking_id == operation
                        ).mapped("serial_ids"),
                        _("despacho de traslado"),
                    )
            self.message_post(body=Markup(
                "<p><strong>Propuesta aprobada.</strong> Se crearon %(count)s "
                "traslado(s) desde los almacenes reales. La entrega continuará "
                "bloqueada hasta validar todos los destinos con Hanger.</p>"
            ) % {"count": len(operations)})
            return primary.get_formview_action()

        delivery = self._ddhl_try_create_existing_stock_delivery()
        return delivery.get_formview_action()

    def _release_after_transfer_receipt(self, receipt):
        existing = self.filtered(
            lambda history: history.ddhl_inventory_treatment == "existing_stock"
        )
        regular = self - existing
        result = True
        if regular:
            result = super(
                DoorAndDoorHistoricalDelivery, regular
            )._release_after_transfer_receipt(receipt)
        for history in existing:
            if (
                history.transfer_dispatch_id
                == receipt.ddpc_transfer_source_picking_id
            ):
                history.transfer_receipt_id = receipt
            history._ddhl_try_create_existing_stock_delivery()
        return result

    def action_ddhl_clear_stock_proposal(self):
        self.ensure_one()
        self._ddhl_assert_existing_stock_mode()
        allocations = self.ddhl_stock_allocation_ids.filtered(
            lambda allocation: allocation.state == "proposed"
        )
        if len(allocations) != len(self.ddhl_stock_allocation_ids):
            raise UserError(_("No puede liberar una propuesta que ya creó operaciones."))
        allocations.unlink()
        self.message_post(body=_("Propuesta de stock liberada para una nueva revisión."))
        return self.get_formview_action()

    def action_ddhl_mark_excluded(self):
        self.ensure_one()
        if self.ddhl_inventory_treatment != "excluded_legacy":
            raise UserError(_("Seleccione primero el tratamiento de exclusión."))
        if not (self.ddhl_exclusion_reason or "").strip():
            raise UserError(_("Documente por qué esta factura no debe mover inventario en Odoo."))
        if self.ddhl_regularization_ids or self.picking_id or self.transfer_dispatch_id:
            raise UserError(_("El histórico ya tiene operaciones; no puede excluirse automáticamente."))
        self.write({"state": "cancel"})
        self.message_post(body=Markup(
            "<p><strong>Histórico excluido del control logístico de Odoo.</strong></p>"
            "<p>Motivo: %(reason)s</p><p>Se conserva documento, PDF y huella para auditoría; "
            "no se creó ni movió inventario.</p>"
        ) % {"reason": escape(self.ddhl_exclusion_reason)})
        return self.get_formview_action()


class DoorAndDoorHistoricalStockAllocation(models.Model):
    _name = "doorandoor.historical.stock.allocation"
    _description = "Asignación de stock existente a histórico"
    _order = "historical_line_id, source_warehouse_id, id"

    historical_delivery_id = fields.Many2one(
        "doorandoor.historical.delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )
    historical_line_id = fields.Many2one(
        "doorandoor.historical.delivery.line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        related="historical_line_id.product_id", store=True, readonly=True,
    )
    source_warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, ondelete="restrict", index=True,
    )
    serial_ids = fields.Many2many(
        "inventory.unit.serial",
        "ddhl_stock_allocation_serial_rel",
        "allocation_id",
        "serial_id",
        string="Labels existentes",
        readonly=True,
    )
    serial_codes = fields.Char(
        string="Labels existentes",
        compute="_compute_serial_codes",
        readonly=True,
    )
    quantity = fields.Float(
        required=True, digits="Product Unit of Measure", readonly=True,
    )
    state = fields.Selection(
        [("proposed", "Propuesta"), ("reserved", "Reservada"),
         ("done", "Procesada"), ("cancel", "Cancelada")],
        default="proposed", required=True, readonly=True, index=True,
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Operación", readonly=True, copy=False,
        ondelete="restrict",
    )
    receipt_picking_id = fields.Many2one(
        related="picking_id.ddpc_transfer_receipt_picking_id",
        string="Recepción destino",
        readonly=True,
    )
    delivery_picking_id = fields.Many2one(
        "stock.picking", string="Entrega final", readonly=True, copy=False,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        related="historical_delivery_id.company_id", store=True, readonly=True,
    )

    @api.depends("serial_ids.code")
    def _compute_serial_codes(self):
        for allocation in self:
            allocation.serial_codes = ", ".join(allocation.serial_ids.mapped("code"))

    @api.constrains("historical_delivery_id", "historical_line_id")
    def _check_line_history(self):
        for allocation in self:
            if allocation.historical_line_id.delivery_id != allocation.historical_delivery_id:
                raise ValidationError(_("La línea asignada no pertenece al histórico."))

    @api.constrains("quantity", "serial_ids")
    def _check_quantity_serials(self):
        for allocation in self:
            if allocation.quantity <= 0 or int(round(allocation.quantity)) != len(allocation.serial_ids):
                raise ValidationError(_("La cantidad debe coincidir con los labels asignados."))

    @api.constrains("serial_ids")
    def _check_unique_serial(self):
        for allocation in self:
            duplicate = self.search([
                ("id", "!=", allocation.id),
                ("state", "!=", "cancel"),
                ("serial_ids", "in", allocation.serial_ids.ids),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Un label no puede cubrir dos históricos activos: %s."
                ) % ", ".join((allocation.serial_ids & duplicate.serial_ids).mapped("code")))


class InventoryUnitSerial(models.Model):
    _inherit = "inventory.unit.serial"

    ddhl_reserved_history_id = fields.Many2one(
        "doorandoor.historical.delivery",
        string="Histórico reservado",
        readonly=True,
        copy=False,
        index=True,
        ondelete="restrict",
    )

    def write(self, vals):
        picking = self.env["stock.picking"].browse(
            vals.get("reserved_picking_id")
        ).exists()
        if picking:
            for serial in self.filtered("ddhl_reserved_history_id"):
                history = serial.ddhl_reserved_history_id
                allowed = history._ddhl_linked_operations()
                allowed |= history.ddhl_stock_allocation_ids.mapped("picking_id")
                allowed |= history.ddhl_stock_allocation_ids.mapped(
                    "delivery_picking_id"
                )
                if picking not in allowed:
                    raise UserError(_(
                        "El label %(label)s está reservado por %(history)s y no "
                        "puede asignarse a %(operation)s."
                    ) % {
                        "label": serial.code,
                        "history": history.display_name,
                        "operation": picking.display_name,
                    })
        return super().write(vals)


class DoorAndDoorHistoricalStockPicking(models.Model):
    _inherit = "stock.picking"

    def _ddhl_existing_stock_allocations(self):
        self.ensure_one()
        operation = self
        if operation.ddpc_transfer_source_picking_id:
            operation = operation.ddpc_transfer_source_picking_id
        while operation.backorder_id:
            operation = operation.backorder_id
        return self.env["doorandoor.historical.stock.allocation"].sudo().search([
            "|",
            ("picking_id", "=", operation.id),
            ("delivery_picking_id", "=", operation.id),
        ])

    def _action_done(self):
        reserved_before = {
            picking.id: picking.ddmh_reserved_serial_ids.filtered(
                "ddhl_reserved_history_id"
            )
            for picking in self
        }
        result = super()._action_done()
        for picking in self.filtered(lambda operation: operation.state == "done"):
            allocations = picking._ddhl_existing_stock_allocations()
            if not allocations:
                continue

            scanned = picking.ddmh_serial_scan_ids.mapped("serial_id")
            unscanned = reserved_before.get(
                picking.id, self.env["inventory.unit.serial"]
            ) - scanned
            open_backorders = picking.backorder_ids.filtered(
                lambda operation: operation.state not in ("done", "cancel")
            )
            for serial in unscanned:
                target = open_backorders.filtered(
                    lambda operation: serial.product_id in operation.move_ids.product_id
                )[:1]
                if target:
                    serial.sudo().write({"reserved_picking_id": target.id})

            histories = allocations.mapped("historical_delivery_id")
            for history in histories:
                history._ddhl_try_create_existing_stock_delivery()

            root_delivery = allocations.mapped("delivery_picking_id")
            if root_delivery and picking in root_delivery._ddhl_expand_explicit_chain():
                pending = root_delivery._ddhl_expand_explicit_chain().filtered(
                    lambda operation: operation.state not in ("done", "cancel")
                )
                if not pending:
                    allocations.write({"state": "done"})
                    allocations.mapped("serial_ids").sudo().write({
                        "ddhl_reserved_history_id": False,
                    })
                    histories.filtered(lambda history: history.picking_id).write({
                        "state": "done",
                    })
        return result
