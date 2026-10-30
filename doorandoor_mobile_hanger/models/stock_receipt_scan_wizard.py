from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class StockReceiptScanWizard(models.TransientModel):
    _inherit = "ddsl.stock.receipt.scan.wizard"

    picking_type_code = fields.Selection(
        related="picking_id.picking_type_code",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for wizard in records.filtered("picking_id"):
            self.env["ddmh.hanger.scan.event"].sudo().create({
                "picking_id": wizard.picking_id.id,
                "user_id": self.env.user.id,
                "status": "opened",
                "message": _("Pantalla de conteo abierta y esperando un disparo."),
            })
        return records

    @api.model
    def _ddsl_can_count_picking(self, picking):
        return bool(
            super()._ddsl_can_count_picking(picking)
            or picking.picking_type_code in ("outgoing", "internal")
        )

    def _ddsl_find_product(self, code):
        product = super()._ddsl_find_product(code)
        if product:
            return product
        serial = self.env["inventory.unit.serial"].search([
            ("code", "=", (code or "").strip()),
            ("active", "=", True),
        ], limit=1)
        return serial.product_id

    def _ddmh_reserve_scanned_serial(self, serial):
        """Claim an available physical item while legacy documents are migrated."""
        self.ensure_one()
        picking = self.picking_id
        if picking.picking_type_code not in ("outgoing", "internal"):
            return
        self.env.cr.execute(
            "SELECT id FROM inventory_unit_serial WHERE id = %s FOR UPDATE",
            [serial.id],
        )
        serial.invalidate_recordset([
            "reserved_picking_id", "reserved_invoice_id", "reserved_by_id",
            "reserved_at", "inventory_loaded", "current_warehouse_id",
        ])
        if not serial.inventory_loaded:
            raise UserError(_(
                "El ítem %(serial)s todavía no está aplicado al inventario."
            ) % {"serial": serial.code})
        source_warehouse = (
            picking.ddpc_source_warehouse_id
            or picking.picking_type_id.warehouse_id
        )
        if source_warehouse and serial.current_warehouse_id != source_warehouse:
            raise UserError(_(
                "El ítem %(serial)s está en %(actual)s y la operación sale de %(expected)s."
            ) % {
                "serial": serial.code,
                "actual": serial.current_warehouse_id.display_name,
                "expected": source_warehouse.display_name,
            })
        expected_products = picking.move_ids.filtered(
            lambda move: move.state != "cancel"
        ).product_id
        if serial.product_id not in expected_products:
            raise UserError(_(
                "El ítem %(serial)s corresponde a %(product)s, que no pertenece "
                "a la operación %(operation)s."
            ) % {
                "serial": serial.code,
                "product": serial.product_id.display_name,
                "operation": picking.display_name,
            })
        reserved_for_other = (
            serial.reserved_picking_id
            and serial.reserved_picking_id != picking
            and serial.reserved_picking_id.state != "cancel"
        )
        if reserved_for_other:
            raise UserError(_(
                "El ítem %(serial)s está reservado para la operación %(operation)s."
            ) % {
                "serial": serial.code,
                "operation": serial.reserved_picking_id.display_name,
            })
        if serial.reserved_picking_id == picking:
            return
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
        picking.message_post(
            body=Markup(
                "<p><strong>Ítem reservado al escanear con Hanger.</strong> "
                "Serial: %(serial)s. Producto: %(product)s. Usuario: %(user)s.</p>"
            ) % {
                "serial": escape(serial.code),
                "product": escape(serial.product_id.display_name),
                "user": escape(self.env.user.display_name),
            },
            subtype_xmlid="mail.mt_note",
        )

    def _ddmh_same_batch_replacement(self, serial, expected_serials):
        """Return an uncounted reserved label that the physical label may replace."""
        self.ensure_one()
        scanned = self.picking_id.ddmh_serial_scan_ids.mapped("serial_id")
        physical_batch = serial.current_batch_id or serial.batch_id
        if not physical_batch:
            return self.env["inventory.unit.serial"]
        return (expected_serials - scanned).filtered(
            lambda expected: (
                expected != serial
                and expected.product_id == serial.product_id
                and (expected.current_batch_id or expected.batch_id) == physical_batch
            )
        )[:1]

    def action_register_scan(self, scanned_code=None):
        self.ensure_one()
        code = (scanned_code or self.scan_code or "").strip()
        document_scanner = self.env["doorandoor.hanger.document.scan"]
        if document_scanner.ddmh_is_document_code(code):
            # A document shot always changes operational context; it must
            # never be recorded as a rejected product on the current picking.
            # The resolver repeats normal record rules and warehouse checks,
            # so switching does not broaden the operator's access.
            action = document_scanner.ddmh_open_scanned_operation(code)
            self.unlink()
            return action
        quantity = 1
        serial = self.env["inventory.unit.serial"].search([
            ("code", "=", code),
            ("active", "=", True),
        ], limit=1)
        replaced_serial = self.env["inventory.unit.serial"]
        if not serial:
            if self.picking_id.picking_type_code in ("outgoing", "internal"):
                raise UserError(_(
                    "El código %s no identifica un ítem serializado del almacén. "
                    "Escanee el label único de la unidad física, no el código genérico del producto."
                ) % code)
            return super().action_register_scan(scanned_code)
        if self.picking_id.picking_type_code in ("outgoing", "internal"):
            # Compare against the labels already reserved by the commercial
            # dispatch before claiming a new physical unit. Reserving first
            # made an unexpected serial appear valid in the following check.
            expected_serials = self.picking_id.ddmh_reserved_serial_ids.filtered("active")
            expected_product_serials = expected_serials.filtered(
                lambda item: item.product_id == serial.product_id
            )
            if expected_product_serials and serial not in expected_product_serials:
                expected_qty = sum(self.picking_id.move_ids.filtered(
                    lambda move: (
                        move.state != "cancel"
                        and move.product_id == serial.product_id
                    )
                ).mapped("product_uom_qty"))
                reservation_is_partial = float_compare(
                    len(expected_product_serials),
                    expected_qty,
                    precision_rounding=serial.product_id.uom_id.rounding,
                ) < 0
                if not reservation_is_partial:
                    replaced_serial = self._ddmh_same_batch_replacement(
                        serial, expected_product_serials,
                    )
                    if not replaced_serial:
                        raise UserError(_(
                            "El serial %(serial)s pertenece al ITEM esperado, pero "
                            "la operación ya tiene %(reserved)s/%(expected)s labels "
                            "reservados en otro lote. Use un label del mismo lote "
                            "reservado o realice la sustitución desde Monitoreo Hanger."
                        ) % {
                            "serial": serial.code,
                            "reserved": len(expected_product_serials),
                            "expected": expected_qty,
                        })
                    self.env.cr.execute(
                        "SELECT id FROM inventory_unit_serial WHERE id = %s FOR UPDATE",
                        [replaced_serial.id],
                    )
                    replaced_serial.sudo().write({
                        "reserved_picking_id": False,
                        "reserved_invoice_id": False,
                        "reserved_by_id": False,
                        "reserved_at": False,
                    })
            self._ddmh_reserve_scanned_serial(serial)
        existing = self.env["ddmh.picking.serial.scan"].search([
            ("picking_id", "=", self.picking_id.id),
            ("serial_id", "=", serial.id),
        ], limit=1)
        shared_serial = serial.product_id.product_tmpl_id.ddic_shared_lot_serial
        if existing and not shared_serial:
            raise UserError(_(
                "El serial %s ya fue leído en la operación %s."
            ) % (serial.code, self.picking_id.display_name))
        line = self._ddsl_get_or_create_wizard_line(serial.product_id)
        if line.expected_qty and line.counted_qty + quantity > line.expected_qty:
            raise UserError(_(
                "La lectura excede la cantidad del documento para %(product)s. "
                "Esperado: %(expected)s; contado: %(counted)s; intento: +%(quantity)s."
            ) % {
                "product": serial.product_id.display_name,
                "expected": line.expected_qty,
                "counted": line.counted_qty,
                "quantity": quantity,
            })
        result = False
        for __index in range(quantity):
            result = super().action_register_scan(code)
        if not existing:
            self.env["ddmh.picking.serial.scan"].create({
                "picking_id": self.picking_id.id,
                "serial_id": serial.id,
            })
        event_message = (
            _(
                "Lectura aceptada. El label %(scanned)s sustituyó automáticamente "
                "al reservado %(replaced)s porque ambos pertenecen al mismo lote e ITEM."
            ) % {
                "scanned": serial.code,
                "replaced": replaced_serial.code,
            }
            if replaced_serial
            else (
                _(
                    "Lectura compartida aceptada: +%(quantity)s. "
                    "Acumulado: %(counted)s/%(expected)s."
                ) % {
                    "quantity": quantity,
                    "counted": result["counted_qty"],
                    "expected": result["expected_qty"],
                }
                if shared_serial
                else _("Lectura aceptada y sumada al conteo.")
            )
        )
        self.env["ddmh.hanger.scan.event"].sudo().create({
            "picking_id": self.picking_id.id,
            "user_id": self.env.user.id,
            "code": code,
            "serial_id": serial.id,
            "product_id": serial.product_id.id,
            "status": "accepted",
            "message": event_message,
        })
        if replaced_serial:
            self.picking_id.message_post(
                body=Markup(
                    "<p><strong>Sustitución automática Hanger.</strong> "
                    "Label físico: %(scanned)s. Label reservado liberado: %(replaced)s. "
                    "ITEM: %(product)s. Lote: %(batch)s. Operador: %(user)s.</p>"
                ) % {
                    "scanned": escape(serial.code),
                    "replaced": escape(replaced_serial.code),
                    "product": escape(serial.product_id.display_name),
                    "batch": escape((serial.current_batch_id or serial.batch_id).display_name),
                    "user": escape(self.env.user.display_name),
                },
                subtype_xmlid="mail.mt_note",
            )
        result["unit_serial"] = serial.code
        result["scanned_quantity"] = quantity
        return result

    def action_apply_and_send_to_review(self):
        """Finish the operator workflow without leaving the Hanger UI."""
        self.ensure_one()
        picking = self.picking_id
        self.action_apply_count()
        # ``quantity`` is stored on move lines by action_apply_count. Force a
        # fresh read before evaluating the computed completion flag in the
        # same RPC transaction.
        picking.invalidate_recordset([
            "ddmh_count_complete",
            "ddmh_validation_state",
        ])
        return picking.action_ddmh_send_to_review()

    def action_apply_and_validate_operation(self):
        """Apply the exact Hanger count and close the warehouse operation."""
        self.ensure_one()
        picking = self.picking_id
        # Native reservations may already have populated every move line with
        # the full requested quantity.  The Hanger is the physical evidence:
        # clear those proposed quantities first so the inherited count writer
        # applies only what the operator actually scanned.  Odoo will place the
        # remaining demand in a backorder during controlled validation.
        open_lines = picking.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
        ).mapped("move_line_ids")
        if open_lines:
            open_lines.write({"quantity": 0.0})
        self.action_apply_count()
        picking.invalidate_recordset([
            "ddmh_count_complete",
            "ddmh_validation_state",
        ])
        result = picking.action_ddmh_validate_operation_from_hanger()
        picking.invalidate_recordset(["state", "ddmh_validation_state"])
        if picking.state != "done":
            # Preserve legitimate native workflows such as an immediate
            # transfer or backorder wizard. The counting screen must only be
            # discarded after Odoo really closed the stock operation.
            return result

        # A validated operation must not leave its transient receiver alive
        # on Zebra/Android. Keeping that record on screen made the next
        # document shot look like a product label for the operation that had
        # already finished. Build a fresh document launcher first, then remove
        # this wizard and clear the previous mobile navigation stack.
        launcher = self.env.ref(
            "doorandoor_mobile_hanger.action_ddmh_document_scan"
        ).sudo().read()[0]
        launcher_view = self.env.ref(
            "doorandoor_mobile_hanger.view_ddmh_document_scan_form"
        )
        launcher.update({
            "res_id": False,
            "view_mode": "form",
            "views": [(launcher_view.id, "form")],
            "target": "main",
            "context": {},
        })
        self.unlink()
        return launcher
