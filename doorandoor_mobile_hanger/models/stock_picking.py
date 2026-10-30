from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_ddmh_print_delivery_slip(self):
        """Open the native delivery slip directly from the Hanger workflow."""
        self.ensure_one()
        return self.env.ref("stock.action_report_delivery").report_action(self)

    def _ddmh_use_physical_partial_delivery_report(self):
        """Use Hanger evidence when a completed picking was only partly scanned.

        A supervisor may historically have validated the native picking before
        creating its backorder.  Native Odoo then prints every completed move as
        delivered, even though Hanger proves that only some labels left the
        warehouse.  Keep the stock correction auditable and make the delivery
        slip reflect the physical scan evidence.
        """
        self.ensure_one()
        expected = sum(
            self.move_ids.filtered(lambda move: move.state != "cancel").mapped(
                "product_uom_qty"
            )
        )
        scanned = len(self.ddmh_serial_scan_ids)
        pending_backorder = self.backorder_ids.filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        return bool(
            self.state == "done"
            and pending_backorder
            and scanned
            and float_compare(
                scanned, expected, precision_rounding=1.0
            ) < 0
        )

    def _ddmh_physical_delivery_report_rows(self):
        """Return product quantities and labels accepted by Hanger."""
        self.ensure_one()
        rows = {}
        for scan in self.ddmh_serial_scan_ids.sorted(lambda item: (item.product_id.id, item.id)):
            product = scan.product_id
            row = rows.setdefault(
                product.id,
                {
                    "product": product,
                    "quantity": 0.0,
                    "uom": product.uom_id,
                    "labels": [],
                },
            )
            row["quantity"] += 1.0
            row["labels"].append(scan.serial_id.code)
        return list(rows.values())

    ddmh_is_pickup_delivery = fields.Boolean(
        string="Entrega de Pickup Order",
        compute="_compute_ddmh_is_pickup_delivery",
    )
    ddmh_pickup_order_ids = fields.One2many(
        "doorandoor.pickup.order", "picking_id",
        string="Pickup Orders", readonly=True,
    )
    ddmh_serial_scan_ids = fields.One2many(
        "ddmh.picking.serial.scan", "picking_id",
        string="Seriales leídos con Hanger", readonly=True,
    )
    ddmh_scan_event_ids = fields.One2many(
        "ddmh.hanger.scan.event", "picking_id",
        string="Monitoreo Hanger", readonly=True,
    )
    ddmh_monitor_progress = fields.Char(
        string="Progreso Hanger", compute="_compute_ddmh_monitor",
    )
    ddmh_last_scan_user_id = fields.Many2one(
        "res.users", string="Último operador", compute="_compute_ddmh_monitor",
    )
    ddmh_last_scan_at = fields.Datetime(
        string="Última actividad", compute="_compute_ddmh_monitor",
    )
    ddmh_last_scan_status = fields.Char(
        string="Último resultado", compute="_compute_ddmh_monitor",
    )
    ddmh_product_summary = fields.Char(
        string="Productos", compute="_compute_ddmh_product_summary",
    )
    ddmh_total_units = fields.Float(
        string="Unidades", compute="_compute_ddmh_product_summary",
    )
    ddmh_work_stage = fields.Selection(
        [
            ("dispatch", "Por despachar"),
            ("receipt", "Por recibir"),
            ("delivery", "Listo para entregar"),
            ("completed", "Completada"),
            ("other", "Revisar"),
        ],
        string="Paso actual",
        compute="_compute_ddmh_work_stage",
        store=True,
        index=True,
        group_expand="_group_expand_ddmh_work_stage",
    )
    ddmh_validation_state = fields.Selection(
        [
            ("counting", "En conteo"),
            ("review", "Pendiente de validación"),
            ("validated", "Validada y cerrada"),
        ],
        string="Validación Hanger",
        default="counting",
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    ddmh_count_complete = fields.Boolean(
        string="Conteo completo",
        compute="_compute_ddmh_count_complete",
    )
    ddmh_review_requested_by_id = fields.Many2one(
        "res.users", string="Enviada a validar por", readonly=True, copy=False,
    )
    ddmh_review_requested_at = fields.Datetime(
        string="Enviada a validar el", readonly=True, copy=False,
    )
    ddmh_validated_by_id = fields.Many2one(
        "res.users", string="Validada por", readonly=True, copy=False,
    )
    ddmh_validated_at = fields.Datetime(
        string="Validada el", readonly=True, copy=False,
    )

    @api.depends(
        "move_ids.product_uom_qty",
        "ddsl_receipt_count_ids.counted_qty",
        "ddmh_scan_event_ids.event_at",
        "ddmh_scan_event_ids.status",
        "ddmh_scan_event_ids.message",
        "ddmh_scan_event_ids.user_id",
    )
    def _compute_ddmh_monitor(self):
        status_labels = dict(self.env["ddmh.hanger.scan.event"]._fields["status"].selection)
        for picking in self:
            expected = sum(picking.move_ids.filtered(lambda m: m.state != "cancel").mapped("product_uom_qty"))
            counted = len(picking.ddmh_serial_scan_ids) or sum(
                picking.ddsl_receipt_count_ids.mapped("counted_qty")
            )
            picking.ddmh_monitor_progress = "%s / %s" % (
                format(counted, ".2f"), format(expected, ".2f"),
            )
            latest = picking.ddmh_scan_event_ids[:1]
            picking.ddmh_last_scan_user_id = latest.user_id
            picking.ddmh_last_scan_at = latest.event_at
            picking.ddmh_last_scan_status = (
                "%s%s" % (
                    status_labels.get(latest.status, latest.status or ""),
                    (": %s" % latest.message) if latest.message else "",
                ) if latest else "Sin actividad registrada"
            )

    @api.depends(
        "state",
        "move_ids.state",
        "move_ids.product_id",
        "move_ids.product_uom_qty",
        "ddsl_receipt_count_ids.product_id",
        "ddsl_receipt_count_ids.expected_qty",
        "ddsl_receipt_count_ids.counted_qty",
        "ddsl_receipt_count_ids.is_counted",
    )
    def _compute_ddmh_count_complete(self):
        for picking in self:
            expected = {}
            for move in picking.move_ids.filtered(lambda item: item.state != "cancel"):
                expected[move.product_id] = (
                    expected.get(move.product_id, 0.0) + move.product_uom_qty
                )
            counts = {
                line.product_id: line
                for line in picking.ddsl_receipt_count_ids
            }
            complete = bool(expected) and picking.state not in ("done", "cancel")
            for product, quantity in expected.items():
                line = counts.get(product)
                rounding = product.uom_id.rounding
                if (
                    not line
                    or not line.is_counted
                    or float_compare(
                        line.counted_qty, quantity, precision_rounding=rounding
                    ) != 0
                ):
                    complete = False
                    break
            picking.ddmh_count_complete = complete

    @api.depends(
        "state",
        "ddpc_transfer_stage",
        "ddpc_operation_category",
        "picking_type_code",
    )
    def _compute_ddmh_work_stage(self):
        for picking in self:
            if picking.state == "done":
                stage = "completed"
            elif picking.ddpc_transfer_stage == "dispatch":
                stage = "dispatch"
            elif picking.ddpc_transfer_stage == "receipt":
                stage = "receipt"
            elif picking.ddpc_operation_category in ("receipt", "factory_entry"):
                stage = "receipt"
            elif picking.ddpc_operation_category == "delivery":
                stage = "delivery"
            elif picking.ddpc_operation_category == "transfer":
                stage = "dispatch"
            else:
                stage = "other"
            picking.ddmh_work_stage = stage

    @api.model
    def _group_expand_ddmh_work_stage(self, stages, domain):
        return ["dispatch", "receipt", "delivery", "completed", "other"]

    def _compute_ddmh_product_summary(self):
        for picking in self:
            moves = picking.move_ids.filtered(lambda move: move.state != "cancel")
            names = moves.mapped("product_id.display_name")
            picking.ddmh_product_summary = ", ".join(names[:3]) + (
                _(" y %s más") % (len(names) - 3) if len(names) > 3 else ""
            )
            picking.ddmh_total_units = sum(moves.mapped("product_uom_qty"))

    def _compute_ddmh_is_pickup_delivery(self):
        linked_ids = set(self.env["doorandoor.pickup.order"].sudo().search([
            ("picking_id", "in", self.ids),
        ]).mapped("picking_id").ids)
        for picking in self:
            picking.ddmh_is_pickup_delivery = picking.id in linked_ids

    def action_open_ddsl_receipt_scan_wizard(self):
        self.ensure_one()
        self._ddmh_check_mobile_warehouse_access()
        action = super().action_open_ddsl_receipt_scan_wizard()
        # This action is also returned by a direct ORM call from the camera
        # widget. Unlike a standard button response, that path does not run
        # through Odoo's action normalizer, so the web client requires the
        # explicit ``views`` list before calling ``preprocessAction``.
        action["views"] = [(False, "form")]
        # Zebra/Android must remain on the counting screen. A modal target can
        # be dismissed when the keyboard-wedge finishes the document shot,
        # leaving the operator back on the launcher before the item scan.
        action["target"] = "current"
        if self.picking_type_code == "incoming":
            action["name"] = _("Contar recepción con hanger")
        elif self.picking_type_code == "internal":
            action["name"] = _("Contar traslado con hanger")
        elif self.ddmh_is_pickup_delivery:
            action["name"] = _("Contar entrega con hanger")
        else:
            action["name"] = _("Contar operación con hanger")
        return action

    def _ddmh_check_mobile_warehouse_access(self):
        """Apply a clear warehouse check in addition to the native record rules."""
        system = self.env.user.has_group("base.group_system")
        inventory_manager = self.env.user.has_group("stock.group_stock_manager")
        operator = self.env.user.has_group(
            "doorandoor_process_control.group_ddpc_warehouse_operator"
        )
        if system or inventory_manager or not operator:
            return True

        allowed = self.env.user.ddpc_warehouse_ids
        if not allowed:
            raise AccessError(
                _("Su usuario no tiene almacenes operativos asignados.")
            )
        for picking in self:
            warehouses = picking.ddpc_source_warehouse_id | picking.ddpc_dest_warehouse_id
            if not (warehouses & allowed):
                raise AccessError(
                    _("La operación %(operation)s no pertenece a uno de sus almacenes.")
                    % {"operation": picking.display_name}
                )
        return True

    def action_ddmh_open_mobile(self):
        self.ensure_one()
        self.check_access_rights("read")
        self.check_access_rule("read")
        self._ddmh_check_mobile_warehouse_access()
        pending_recovery = self.serial_receipt_ids.filtered(
            lambda receipt: (
                receipt.state not in ("done", "cancel")
                and "ddhl_historical_regularization_id" in receipt._fields
                and receipt.ddhl_historical_regularization_id
            )
        )
        if self.state == "done" and pending_recovery:
            self.env["ddmh.hanger.scan.event"].sudo().create({
                "picking_id": self.id,
                "user_id": self.env.user.id,
                "status": "opened",
                "message": _("Conteo físico histórico abierto y esperando labels."),
            })
            return self.action_open_ddsl_receipt_scan_wizard()
        # The operator workflow must always land on the barcode receiver.
        # Opening the intermediate picking form left no focused input, so the
        # Zebra beep could be mistaken for a successful Odoo count and the
        # native stock state "waiting" for Hanger's review state.
        if (
            self.picking_type_code in ("incoming", "outgoing", "internal")
            and self.state not in ("done", "cancel")
        ):
            return self.action_open_ddsl_receipt_scan_wizard()
        # The action definition is technical metadata and regular warehouse
        # operators cannot read ir.actions.act_window directly. The picking
        # and warehouse permissions were already checked above with the real
        # user; sudo is limited strictly to reading this UI definition.
        action = self.env.ref(
            "doorandoor_mobile_hanger.action_ddmh_mobile_picking"
        ).sudo().read()[0]
        action.update({"res_id": self.id, "target": "current"})
        return action

    def action_ddmh_open_full_operation(self):
        self.ensure_one()
        self._ddmh_check_mobile_warehouse_access()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "stock.picking",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_ddmh_reload_mobile(self):
        self.ensure_one()
        self._ddmh_check_mobile_warehouse_access()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ddmh_reload_monitor(self):
        """Refresh data while preserving the dedicated support monitor view."""
        self.ensure_one()
        self._ddmh_check_mobile_warehouse_access()
        action = self.env.ref(
            "doorandoor_mobile_hanger.action_ddmh_picking_monitor_form"
        ).sudo().read()[0]
        action.update({"name": self.display_name, "res_id": self.id})
        return action

    def _ddmh_review_partners(self):
        groups = (
            self.env.ref("stock.group_stock_manager", raise_if_not_found=False)
            | self.env.ref("base.group_system", raise_if_not_found=False)
        )
        return groups.sudo().users.filtered("active").partner_id

    def action_ddmh_send_to_review(self):
        for picking in self:
            picking._ddmh_check_mobile_warehouse_access()
            if picking.state in ("done", "cancel"):
                raise UserError(_("La operación ya está terminada o cancelada."))
            if picking.ddmh_validation_state == "review":
                continue
            if not picking.ddmh_count_complete:
                raise UserError(_(
                    "Complete el conteo físico sin diferencias antes de enviarlo a validar."
                ))
            picking.write({
                "ddmh_validation_state": "review",
                "ddmh_review_requested_by_id": self.env.user.id,
                "ddmh_review_requested_at": fields.Datetime.now(),
            })
            operation_labels = dict(
                picking._fields["ddpc_operation_category"].selection
            )
            operation_type = operation_labels.get(
                picking.ddpc_operation_category, _("Operación de almacén")
            )
            picking.message_post(
                body=_(
                    "%(operation_type)s %(operation)s fue enviada a validación por "
                    "%(user)s. Conteo físico completo: %(units)s unidades. "
                    "Está pendiente de Validar y cerrar."
                ) % {
                    "operation_type": operation_type,
                    "operation": picking.display_name,
                    "user": self.env.user.display_name,
                    "units": picking.ddmh_total_units,
                },
                partner_ids=picking._ddmh_review_partners().ids,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ddmh_validate_and_close(self):
        allowed = (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("stock.group_stock_manager")
            or self.env.user.has_group("doorandoor_mobile_hanger.group_ddmh_supervisor")
        )
        if not allowed:
            raise AccessError(_(
                "Solo un supervisor o administrador de inventarios puede validar la operación."
            ))
        for picking in self:
            if picking.ddmh_validation_state != "review":
                raise UserError(_("La operación debe enviarse primero a validación."))
            if not picking.ddmh_count_complete:
                raise UserError(_("El conteo dejó de estar completo; devuélvalo al operador."))
        result = self.button_validate()
        # A validation that finishes immediately must return to a freshly
        # queried daily-work board.  If Odoo needs a legitimate backorder or
        # immediate-transfer wizard, preserve that action and refresh after
        # the wizard is completed instead of bypassing it.
        if all(picking.state == "done" for picking in self):
            action = self.env.ref(
                "doorandoor_mobile_hanger.action_ddmh_daily_work"
            ).sudo().read()[0]
            action.update({"target": "current"})
            return action
        return result

    def action_ddmh_validate_operation_from_hanger(self):
        """Close the physically counted quantity from the controlled Hanger flow.

        This is intentionally separate from ``button_validate`` so warehouse
        operators do not gain general validation rights in standard Odoo
        views.  The server repeats every operational check; hiding a button is
        never considered an authorization boundary.
        """
        operator_roles = {"counter", "delivery", "warehouse"}
        privileged = (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("stock.group_stock_manager")
            or self.env.user.has_group(
                "doorandoor_mobile_hanger.group_ddmh_supervisor"
            )
        )
        counted_by_picking = {}
        requested_by_picking = {}
        for picking in self:
            picking._ddmh_check_mobile_warehouse_access()
            if (
                self.env.user.ddmh_operational_role not in operator_roles
                and not privileged
            ):
                raise AccessError(_(
                    "Esta acción directa está reservada a operadores Hanger, "
                    "supervisores o administradores de Inventario/Ajustes."
                ))
            if picking.picking_type_code not in ("incoming", "outgoing", "internal"):
                raise UserError(_(
                    "Este tipo de operación no puede validarse desde el Hanger."
                ))
            if picking.state in ("done", "cancel"):
                raise UserError(_("La operación ya está terminada o cancelada."))
            if picking.ddmh_validation_state != "counting":
                raise UserError(_(
                    "La operación no está en estado de conteo Hanger. Actualice la "
                    "pantalla antes de continuar."
                ))
            counted = sum(
                picking.ddsl_receipt_count_ids.filtered(
                    lambda line: line.counted_qty > 0
                ).mapped("counted_qty")
            )
            requested = sum(
                picking.move_ids.filtered(
                    lambda move: move.state != "cancel"
                ).mapped("product_uom_qty")
            )
            if not counted:
                raise UserError(_(
                    "Cuente al menos una unidad física antes de validar la operación."
                ))
            counted_by_picking[picking.id] = counted
            requested_by_picking[picking.id] = requested

        # Deliberately bypass this module's general operator guard only after
        # the Hanger-specific checks above have succeeded.
        operator = self.env.user
        # Cost and valuation fields remain restricted to Administrador/Ajustes.
        # Native stock validation still needs those fields internally, so
        # elevate only after all Hanger and warehouse checks above succeeded.
        # Preserve the real operator explicitly for the operational audit.
        direct_pickings = self.with_context(
            ddmh_direct_hanger_validation=True,
            ddmh_operator_user_id=operator.id,
            # Create the pending reception automatically when the Hanger count
            # is partial; never discard the uncounted demand.
            skip_backorder=True,
        ).sudo()
        result = super(StockPicking, direct_pickings).button_validate()
        self.invalidate_recordset(["state", "ddmh_validation_state"])
        if all(picking.state == "done" for picking in self):
            for picking in self:
                picking.sudo().message_post(
                    body=_(
                        "Operación %(operation)s validada y cerrada directamente "
                        "desde el Hanger por %(user)s. Cantidad solicitada: "
                        "%(requested)s; recibida físicamente: %(counted)s; "
                        "pendiente en recepción posterior: %(pending)s."
                    ) % {
                        "operation": picking.display_name,
                        "user": self.env.user.display_name,
                        "requested": requested_by_picking.get(picking.id, 0.0),
                        "counted": counted_by_picking.get(picking.id, 0.0),
                        "pending": max(
                            requested_by_picking.get(picking.id, 0.0)
                            - counted_by_picking.get(picking.id, 0.0),
                            0.0,
                        ),
                    },
                    author_id=operator.partner_id.id,
                    subtype_xmlid="mail.mt_note",
                )
            action = self.env.ref(
                "doorandoor_mobile_hanger.action_ddmh_daily_work"
            ).sudo().read()[0]
            action.update({"target": "current"})
            return action
        return result

    def button_validate(self):
        """Operators validate only through the controlled Hanger workflow."""
        operator_roles = {"counter", "delivery", "warehouse"}
        if self.env.user.ddmh_operational_role in operator_roles:
            raise AccessError(_(
                "Como operador Hanger no puede validar ni cerrar operaciones. "
                "Complete el conteo y use 'Validar operación' dentro del Hanger."
            ))
        return super().button_validate()

    def _action_done(self):
        hanger_completed = self.filtered(
            lambda picking: (
                self.env.context.get("ddmh_direct_hanger_validation")
                or
                picking.ddmh_validation_state == "review"
                or (
                    picking.ddmh_validation_state == "counting"
                    and picking.ddmh_serial_scan_ids
                    and picking.ddmh_count_complete
                )
            )
        )
        scanned_serials = {
            picking.id: picking.ddmh_serial_scan_ids.mapped("serial_id").filtered("active")
            for picking in hanger_completed
        }
        validation_user = self.env["res.users"].browse(
            self.env.context.get("ddmh_operator_user_id")
        ).exists() or self.env.user
        result = super()._action_done()
        completed = hanger_completed.filtered(lambda picking: picking.state == "done")
        if completed:
            now = fields.Datetime.now()
            completed.write({
                "ddmh_validation_state": "validated",
                "ddmh_validated_by_id": validation_user.id,
                "ddmh_validated_at": now,
            })
            for picking in completed:
                serials = scanned_serials.get(
                    picking.id, self.env["inventory.unit.serial"]
                )
                if serials and picking.picking_type_code in ("incoming", "outgoing", "internal"):
                    shared_serials = serials.filtered(
                        lambda serial: serial.product_id.product_tmpl_id.ddic_shared_lot_serial
                    )
                    unique_serials = serials - shared_serials
                    # A shared label represents the remaining bulk stock in
                    # its physical lot. A partial customer delivery reduces
                    # the native quant but must not retire that master label.
                    if shared_serials and picking.picking_type_code == "outgoing":
                        shared_serials.sudo().write({
                            "reserved_picking_id": False,
                            "reserved_invoice_id": False,
                            "reserved_by_id": False,
                            "reserved_at": False,
                        })
                        serials = unique_serials
                    serial_values = {
                        "current_batch_id": False,
                        "current_location_id": picking.location_dest_id.id,
                        "reserved_picking_id": False,
                        "reserved_invoice_id": False,
                        "reserved_by_id": False,
                        "reserved_at": False,
                    }
                    if picking.picking_type_code == "outgoing":
                        serial_values.update({
                            "current_warehouse_id": False,
                            "inventory_loaded": False,
                        })
                    else:
                        location = picking.location_dest_id
                        parents = self.env["stock.location"]
                        while location:
                            parents |= location
                            location = location.location_id
                        destination_warehouse = self.env["stock.warehouse"].search([
                            ("view_location_id", "in", parents.ids),
                        ], limit=1)
                        serial_values.update({
                            "current_warehouse_id": destination_warehouse.id or False,
                            "inventory_loaded": True,
                        })
                    if serials:
                        serials.sudo().write(serial_values)
                picking.message_post(
                    body=_(
                        "Operación validada y cerrada por %(user)s después del "
                        "conteo Hanger. Ítems actualizados en movimientos y mapa: %(serials)s."
                    ) % {
                        "user": validation_user.display_name,
                        "serials": ", ".join(serials.mapped("code")) or _("ninguno"),
                    },
                    author_id=validation_user.partner_id.id,
                    partner_ids=picking.ddmh_review_requested_by_id.partner_id.ids,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
        return result

    def _ddsn_get_barcode_backend_url(self):
        """Make picking QR codes open the dedicated mobile operation view."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        action = self.env.ref(
            "doorandoor_mobile_hanger.action_ddmh_mobile_picking",
            raise_if_not_found=False,
        )
        action_part = f"action={action.id}&" if action else ""
        return (
            f"{base_url}/web#{action_part}id={self.id}"
            "&model=stock.picking&view_type=form"
        )
