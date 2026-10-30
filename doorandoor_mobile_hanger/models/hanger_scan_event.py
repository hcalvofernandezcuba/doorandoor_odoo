from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare


class DoorAndDoorHangerScanEvent(models.Model):
    _name = "ddmh.hanger.scan.event"
    _description = "Evento de monitoreo Hanger"
    _order = "event_at desc, id desc"

    picking_id = fields.Many2one(
        "stock.picking", index=True, ondelete="cascade",
    )
    count_session_id = fields.Many2one(
        "inventory.count.session", string="Sesión IC", index=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user, index=True,
    )
    event_at = fields.Datetime(
        string="Fecha y hora", required=True, default=fields.Datetime.now, index=True,
    )
    code = fields.Char(string="Código leído", index=True)
    product_id = fields.Many2one("product.product", string="Producto", index=True)
    serial_id = fields.Many2one("inventory.unit.serial", string="Ítem físico", index=True)
    status = fields.Selection(
        [
            ("opened", "Conteo abierto"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
            ("duplicate", "Duplicado"),
            ("no_input", "Sin código recibido"),
            ("corrected", "Lectura anulada"),
        ],
        required=True,
        default="opened",
        index=True,
    )
    message = fields.Char(string="Resultado")
    corrected_by_id = fields.Many2one(
        "res.users", string="Anulada por", readonly=True, copy=False,
    )
    corrected_at = fields.Datetime(
        string="Anulada el", readonly=True, copy=False,
    )
    counted_batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote contado",
        compute="_compute_replacement_preview",
    )
    expected_serial_id = fields.Many2one(
        "inventory.unit.serial", string="Label esperado a liberar",
        compute="_compute_replacement_preview",
    )
    expected_product_id = fields.Many2one(
        "product.product", string="Producto esperado",
        compute="_compute_replacement_preview",
    )
    expected_batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote esperado",
        compute="_compute_replacement_preview",
    )

    _sql_constraints = [
        (
            "ddmh_event_single_source",
            "CHECK ((picking_id IS NOT NULL)::integer + "
            "(count_session_id IS NOT NULL)::integer = 1)",
            "Cada evento Hanger debe pertenecer a una operación o a una sesión IC.",
        ),
    ]

    def _ddmh_source_label(self):
        self.ensure_one()
        return (self.picking_id or self.count_session_id).display_name

    def _ddmh_source_warehouse(self):
        self.ensure_one()
        if self.picking_id:
            return (
                self.picking_id.ddpc_source_warehouse_id
                or self.picking_id.ddpc_dest_warehouse_id
                or self.picking_id.picking_type_id.warehouse_id
            )
        return self.count_session_id.location_id.warehouse_id

    def _ddmh_notify_live_scan(self):
        """Push every persisted shot to opted-in users and live monitors."""
        internal_users = self.env["res.users"].sudo().search([
            ("active", "=", True), ("share", "=", False),
        ])
        subscribers = internal_users.filtered("ddmh_live_scan_notifications")
        monitor_users = internal_users.filtered(
            lambda user: (
                user.has_group("base.group_system")
                or user.has_group("stock.group_stock_manager")
            )
        )
        status_titles = {
            "opened": _("Conteo abierto"),
            "accepted": _("Lectura aceptada"),
            "rejected": _("Lectura rechazada"),
            "duplicate": _("Lectura duplicada"),
            "no_input": _("Lectura sin código"),
            "corrected": _("Lectura corregida"),
        }
        for event in self:
            warehouse = event._ddmh_source_warehouse()
            payload = {
                "event_id": event.id,
                "picking_id": event.picking_id.id or False,
                "count_session_id": event.count_session_id.id or False,
                "source_model": (
                    "stock.picking" if event.picking_id
                    else "inventory.count.session"
                ),
                "source_res_id": event.picking_id.id or event.count_session_id.id,
                "source_name": event._ddmh_source_label(),
                "warehouse": warehouse.display_name if warehouse else "-",
                "operator": event.user_id.display_name,
                "code": event.code or "-",
                "status": event.status,
                "message": event.message or status_titles.get(event.status, ""),
                "event_at": fields.Datetime.to_string(event.event_at),
            }
            for user in monitor_users | subscribers:
                self.env["bus.bus"]._sendone(
                    user.partner_id, "ddmh_hanger_event", payload,
                )
            notification_type = (
                "success" if event.status == "accepted"
                else "warning" if event.status == "opened"
                else "danger"
            )
            title = _("Hanger - %s") % status_titles.get(event.status, event.status)
            message = _(
                "%(operator)s · %(source)s · %(code)s\n%(warehouse)s · %(result)s"
            ) % {
                "operator": event.user_id.display_name,
                "source": event._ddmh_source_label(),
                "code": event.code or "-",
                "warehouse": warehouse.display_name if warehouse else "-",
                "result": event.message or status_titles.get(event.status, ""),
            }
            for user in subscribers:
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "simple_notification",
                    {
                        "title": title,
                        "message": message,
                        "type": notification_type,
                        "sticky": event.status not in ("accepted", "opened"),
                    },
                )

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        events._ddmh_notify_live_scan()
        return events

    def _ddmh_replacement_serial(self):
        self.ensure_one()
        if not self.picking_id or not self.serial_id or not self.product_id:
            return self.env["inventory.unit.serial"]
        scanned = self.picking_id.ddmh_serial_scan_ids.mapped("serial_id")
        candidates = self.picking_id.ddmh_reserved_serial_ids.filtered(
            lambda item: (
                item.product_id == self.product_id
                and item != self.serial_id
            )
        )
        # Accepted/scanned labels are final and never qualify as replacements.
        return (candidates - scanned)[:1]

    @api.depends(
        "serial_id", "serial_id.batch_id", "product_id", "status",
        "picking_id.ddmh_reserved_serial_ids",
        "picking_id.ddmh_serial_scan_ids",
    )
    def _compute_replacement_preview(self):
        for event in self:
            replacement = (
                event._ddmh_replacement_serial()
                if event.status in ("rejected", "duplicate")
                else self.env["inventory.unit.serial"]
            )
            expected_products = event.picking_id.move_ids.filtered(
                lambda move: move.state != "cancel"
            ).product_id
            expected_product = (
                replacement.product_id
                or (event.product_id if event.product_id in expected_products else False)
            )
            reserved_same_product = event.picking_id.ddmh_reserved_serial_ids.filtered(
                lambda item: item.product_id == expected_product
            )[:1]
            event.counted_batch_id = event.serial_id.batch_id
            event.expected_serial_id = replacement
            event.expected_product_id = expected_product
            event.expected_batch_id = (
                replacement.batch_id or reserved_same_product.batch_id
            )

    def _ddmh_check_correction_manager(self):
        if not (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("stock.group_stock_manager")
        ):
            raise AccessError(_(
                "Solo un responsable de Inventario puede corregir eventos Hanger."
            ))

    def action_ddmh_accept_failed_label(self):
        """Promote a rejected physical label after full server validation."""
        self._ddmh_check_correction_manager()
        self.ensure_one()
        self.env.cr.execute(
            "SELECT id FROM ddmh_hanger_scan_event WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset()
        if self.status not in ("rejected", "duplicate"):
            raise UserError(_("Este evento no contiene un label fallido aceptable."))
        picking = self.picking_id
        serial = self.serial_id
        product = self.product_id
        if not serial or not product or serial.product_id != product:
            raise UserError(_("El evento no identifica un label físico válido."))
        if picking.state in ("done", "cancel") or picking.ddmh_validation_state != "counting":
            raise UserError(_("Solo se aceptan labels mientras la operación está En conteo."))
        if picking.picking_type_code not in ("outgoing", "internal"):
            raise UserError(_(
                "Aceptar label se usa únicamente para sustituir una unidad esperada "
                "en una entrega o traslado."
            ))
        expected_products = picking.move_ids.filtered(
            lambda move: move.state != "cancel"
        ).product_id
        if product not in expected_products:
            raise UserError(_("El producto del label no pertenece a esta operación."))
        source_warehouse = (
            picking.ddpc_source_warehouse_id or picking.picking_type_id.warehouse_id
        )
        if picking.picking_type_code in ("outgoing", "internal"):
            if not serial.inventory_loaded:
                raise UserError(_("El label todavía no está aplicado al inventario."))
            if source_warehouse and serial.current_warehouse_id != source_warehouse:
                raise UserError(_(
                    "El label está en %(actual)s y la operación sale de %(expected)s."
                ) % {
                    "actual": serial.current_warehouse_id.display_name,
                    "expected": source_warehouse.display_name,
                })
            if (
                serial.reserved_picking_id
                and serial.reserved_picking_id != picking
                and serial.reserved_picking_id.state != "cancel"
            ):
                raise UserError(_(
                    "El label está reservado para %(operation)s."
                ) % {"operation": serial.reserved_picking_id.display_name})
            if serial.reserved_picking_id == picking:
                raise UserError(_(
                    "Este label ya pertenece a la operación; no hay un label esperado que sustituir."
                ))

        shared_serial = product.product_tmpl_id.ddic_shared_lot_serial
        existing_scan = self.env["ddmh.picking.serial.scan"].search([
            ("picking_id", "=", picking.id),
            ("serial_id", "=", serial.id),
        ], limit=1)
        if existing_scan and not shared_serial:
            raise UserError(_(
                "Este serial único ya fue aceptado. No puede contarse dos veces."
            ))

        count_line = self.env["ddsl.stock.receipt.count"].search([
            ("picking_id", "=", picking.id),
            ("product_id", "=", product.id),
        ], limit=1)
        if not count_line:
            expected_qty = sum(picking.move_ids.filtered(
                lambda move: move.state != "cancel" and move.product_id == product
            ).mapped("product_uom_qty"))
            count_line = self.env["ddsl.stock.receipt.count"].create({
                "picking_id": picking.id,
                "product_id": product.id,
                "expected_qty": expected_qty,
            })
        self.env.cr.execute(
            "SELECT id FROM ddsl_stock_receipt_count WHERE id = %s FOR UPDATE",
            [count_line.id],
        )
        # Use the exact expected label shown to the manager in the monitoring
        # row, so the preview and the server-side replacement cannot diverge.
        replaced_serial = self._ddmh_replacement_serial()
        if not replaced_serial:
            raise UserError(_(
                "No existe un label esperado pendiente del mismo ITEM "
                "para sustituir por %(serial)s."
            ) % {"serial": serial.code})
        replaced_scan = self.env["ddmh.picking.serial.scan"].sudo().search([
            ("picking_id", "=", picking.id),
            ("serial_id", "=", replaced_serial.id),
        ], limit=1)
        if replaced_scan:
            raise UserError(_(
                "El label esperado %(serial)s ya fue aceptado y no puede sustituirse."
            ) % {"serial": replaced_serial.code})
        count_line.invalidate_recordset(["counted_qty", "expected_qty"])
        new_qty = count_line.counted_qty + 1.0
        if count_line.expected_qty and float_compare(
            new_qty, count_line.expected_qty,
            precision_rounding=product.uom_id.rounding,
        ) > 0:
            raise UserError(_(
                "Aceptar este label excedería el documento: esperado %(expected)s, contado %(counted)s."
            ) % {"expected": count_line.expected_qty, "counted": count_line.counted_qty})

        replaced_serial.sudo().write({
            "reserved_picking_id": False,
            "reserved_invoice_id": False,
            "reserved_by_id": False,
            "reserved_at": False,
        })
        invoice = self.env["account.move"].sudo().search([
            ("fulfillment_line_ids.picking_id", "=", picking.id),
            ("move_type", "=", "out_invoice"),
        ], order="id desc", limit=1)
        serial.sudo().write({
            "reserved_picking_id": picking.id,
            "reserved_invoice_id": invoice.id or False,
            "reserved_by_id": self.env.user.id,
            "reserved_at": fields.Datetime.now(),
        })

        count_line.write({
            "counted_qty": new_qty,
            "is_counted": True,
            "last_scan_date": fields.Datetime.now(),
            "last_scan_user_id": self.env.user.id,
        })
        wizard_lines = self.env["ddsl.stock.receipt.scan.wizard.line"].sudo().search([
            ("count_id", "=", count_line.id),
        ])
        for line in wizard_lines:
            self.env.cr.execute(
                """UPDATE ddsl_stock_receipt_scan_wizard_line
                      SET counted_qty = %s, is_counted = TRUE, difference_qty = %s
                    WHERE id = %s""",
                [new_qty, new_qty - line.expected_qty, line.id],
            )
        wizard_lines.invalidate_recordset([
            "counted_qty", "is_counted", "difference_qty",
        ])
        if not existing_scan:
            self.env["ddmh.picking.serial.scan"].sudo().create({
                "picking_id": picking.id,
                "serial_id": serial.id,
                "user_id": self.env.user.id,
            })
        prior_message = self.message or _("Label rechazado.")
        self.sudo().write({
            "status": "accepted",
            "corrected_by_id": self.env.user.id,
            "corrected_at": fields.Datetime.now(),
            "message": _(
                "Label aceptado por %(user)s en sustitución de %(replaced)s; "
                "acumulado %(counted)s/%(expected)s. Antes: %(message)s"
            ) % {
                "user": self.env.user.display_name,
                "replaced": replaced_serial.code,
                "counted": new_qty,
                "expected": count_line.expected_qty,
                "message": prior_message,
            },
        })
        picking.message_post(
            body=Markup(
                "<p><strong>Label fallido aceptado por Inventario.</strong> "
                "Código entregado: %(code)s. Producto: %(product)s. Conteo: %(counted)s/%(expected)s. "
                "Label esperado liberado: %(replaced)s. Responsable: %(user)s.</p>"
            ) % {
                "code": escape(serial.code),
                "product": escape(product.display_name),
                "counted": new_qty,
                "expected": count_line.expected_qty,
                "replaced": escape(replaced_serial.code if replaced_serial else "Ninguno"),
                "user": escape(self.env.user.display_name),
            },
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ddmh_void_failed_event(self):
        """Dismiss a failed attempt without changing the physical count."""
        self._ddmh_check_correction_manager()
        self.ensure_one()
        self.env.cr.execute(
            "SELECT id FROM ddmh_hanger_scan_event WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset()
        failed_statuses = ("rejected", "duplicate", "no_input")
        if self.status not in failed_statuses:
            raise UserError(_(
                "Solo se pueden anular eventos fallidos. Las lecturas aceptadas "
                "forman parte del conteo y deben conservarse."
            ))
        source = self.picking_id or self.count_session_id
        previous_message = self.message or _("Evento fallido.")
        self.sudo().write({
            "status": "corrected",
            "corrected_by_id": self.env.user.id,
            "corrected_at": fields.Datetime.now(),
            "message": _("Evento fallido anulado por %(user)s. Antes: %(message)s") % {
                "user": self.env.user.display_name,
                "message": previous_message,
            },
        })
        source.message_post(
            body=Markup(
                "<p><strong>Evento fallido Hanger anulado.</strong> "
                "Código: %(code)s. Producto: %(product)s. "
                "El conteo físico no fue modificado. Responsable: %(user)s.</p>"
            ) % {
                "code": escape(self.code or "-"),
                "product": escape(self.product_id.display_name or "-"),
                "user": escape(self.env.user.display_name),
            },
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    def log_client_attempt(self, picking_id, code, status="rejected", message=None):
        """Persist a failed browser scan after the original RPC rolled back."""
        picking = self.env["stock.picking"].browse(int(picking_id or 0)).exists()
        if not picking:
            return False
        picking._ddmh_check_mobile_warehouse_access()
        code = (code or "").strip()
        serial = self.env["inventory.unit.serial"].search([
            ("code", "=", code), ("active", "=", True),
        ], limit=1)
        vals = {
            "picking_id": picking.id,
            "user_id": self.env.user.id,
            "code": code or False,
            "serial_id": serial.id or False,
            "product_id": serial.product_id.id or False,
            "status": status if status in dict(self._fields["status"].selection) else "rejected",
            "message": (message or "")[:500],
        }
        return self.sudo().create(vals).id

    @api.model
    def log_count_session_attempt(
        self, session_id, code, status="rejected", message=None,
    ):
        """Persist a failed IC shot after the business RPC rolled back."""
        session = self.env["inventory.count.session"].browse(
            int(session_id or 0)
        ).exists()
        if not session:
            return False
        session._ddic_check_location_access(session.location_id)
        code = (code or "").strip()
        serial = self.env["inventory.unit.serial"].search([
            ("code", "=", code), ("active", "=", True),
        ], limit=1)
        product = serial.product_id or self.env["product.product"].search([
            ("barcode", "=", code), ("active", "=", True),
        ], limit=1)
        vals = {
            "count_session_id": session.id,
            "user_id": self.env.user.id,
            "code": code or False,
            "serial_id": serial.id or False,
            "product_id": product.id or False,
            "status": status if status in dict(self._fields["status"].selection) else "rejected",
            "message": (message or "")[:500],
        }
        return self.sudo().create(vals).id
