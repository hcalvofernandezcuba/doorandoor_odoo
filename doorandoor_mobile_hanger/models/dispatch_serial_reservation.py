from collections import defaultdict

from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class InventoryUnitSerial(models.Model):
    _inherit = "inventory.unit.serial"

    reserved_picking_id = fields.Many2one(
        "stock.picking", string="Despacho reservado", readonly=True,
        copy=False, index=True, ondelete="restrict",
    )
    reserved_invoice_id = fields.Many2one(
        "account.move", string="Factura reservada", readonly=True,
        copy=False, index=True, ondelete="restrict",
    )
    reserved_by_id = fields.Many2one(
        "res.users", string="Reservado por", readonly=True, copy=False,
    )
    reserved_at = fields.Datetime(
        string="Reservado el", readonly=True, copy=False,
    )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddmh_reserved_serial_ids = fields.One2many(
        "inventory.unit.serial", "reserved_picking_id",
        string="Seriales reservados para el despacho", readonly=True,
    )

    def _ddmh_release_open_serial_reservations(self):
        for picking in self:
            picking.ddmh_reserved_serial_ids.filtered("active").write({
                "reserved_picking_id": False,
                "reserved_invoice_id": False,
                "reserved_by_id": False,
                "reserved_at": False,
            })

    def action_cancel(self):
        self._ddmh_release_open_serial_reservations()
        return super().action_cancel()


class AccountMove(models.Model):
    _inherit = "account.move"

    ddmh_label_print_count = fields.Integer(
        string="Impresiones de labels de despacho", readonly=True, copy=False,
    )
    ddmh_label_last_printed_at = fields.Datetime(
        string="Última impresión de labels", readonly=True, copy=False,
    )
    ddmh_label_last_printed_by_id = fields.Many2one(
        "res.users", string="Última impresión por", readonly=True, copy=False,
    )

    def _ddmh_dispatch_pickings_for_labels(self):
        self.ensure_one()
        return self.fulfillment_line_ids.mapped("picking_id").filtered(
            lambda picking: picking.state != "cancel"
            and picking.picking_type_code == "outgoing"
        )

    def _ddmh_reserved_serials_for_labels(self, pickings):
        """Read only the serials already linked to the selected dispatches.

        Sales users are allowed to prepare and print customer delivery labels,
        but intentionally have no direct access to the inventory serial model.
        Keep that separation: elevate this narrow technical lookup instead of
        granting inventory-count permissions to the salesperson.
        """
        self.ensure_one()
        return self.env["inventory.unit.serial"].sudo().search([
            ("reserved_picking_id", "in", pickings.ids),
            ("reserved_invoice_id", "=", self.id),
            ("active", "=", True),
        ])

    def _ddmh_prepare_dispatch_serials(self):
        """Use the paid fulfillment channel and reserve existing unit labels."""
        self.ensure_one()
        if self.move_type != "out_invoice" or self.state != "posted":
            raise UserError(_(
                "La factura debe estar publicada antes de preparar el despacho."
            ))
        # Reuse the exact commercial guard already approved for invoice output
        # (full payment or the configured validated partial-payment threshold).
        self._ddsn_check_printable_invoice()

        # This method is the existing payment/fulfillment gate.  It may create
        # the native delivery only when the configured release policy permits it.
        self._ddsn_sync_release_from_payments()
        pickings = self._ddmh_dispatch_pickings_for_labels()
        if not pickings:
            raise UserError(_(
                "Todavía no existe un despacho liberado para esta factura. "
                "Revise las políticas firmadas, el control de pago y cualquier "
                "traslado pendiente. No se generaron códigos nuevos."
            ))

        Serial = self.env["inventory.unit.serial"].sudo()
        newly_reserved = Serial.browse()
        for picking in pickings:
            self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", (88412, picking.id))
            warehouse = picking.picking_type_id.warehouse_id
            if not warehouse:
                raise UserError(_(
                    "La operación %s no tiene un almacén de salida configurado."
                ) % picking.display_name)

            required_by_product = defaultdict(float)
            for move in picking.move_ids.filtered(lambda item: item.state != "cancel"):
                required_by_product[move.product_id] += move.product_uom_qty

            for product, required_qty in required_by_product.items():
                rounded_qty = int(round(required_qty))
                if float_compare(
                    required_qty, rounded_qty,
                    precision_rounding=product.uom_id.rounding,
                ) != 0:
                    raise ValidationError(_(
                        "El producto %s requiere una cantidad entera para reservar labels unitarios."
                    ) % product.display_name)

                current = Serial.search([
                    ("reserved_picking_id", "=", picking.id),
                    ("reserved_invoice_id", "=", self.id),
                    ("product_id", "=", product.id),
                    ("active", "=", True),
                ])
                missing = max(rounded_qty - len(current), 0)
                if not missing:
                    continue
                available = Serial.search([
                    ("product_id", "=", product.id),
                    ("active", "=", True),
                    ("inventory_loaded", "=", True),
                    ("current_warehouse_id", "=", warehouse.id),
                    ("reserved_picking_id", "=", False),
                ], order="current_batch_id, id", limit=missing)
                if len(available) < missing:
                    raise UserError(_(
                        "Stock serializado insuficiente para %(product)s en %(warehouse)s. "
                        "Se requieren %(required)s unidades y solo hay %(available)s labels "
                        "disponibles. Se debe completar Inventario o solicitar el traslado; "
                        "no se crearán seriales duplicados."
                    ) % {
                        "product": product.display_name,
                        "warehouse": warehouse.display_name,
                        "required": rounded_qty,
                        "available": len(current) + len(available),
                    })
                available.write({
                    "reserved_picking_id": picking.id,
                    "reserved_invoice_id": self.id,
                    "reserved_by_id": self.env.user.id,
                    "reserved_at": fields.Datetime.now(),
                })
                newly_reserved |= available

            picking.action_assign()
            if newly_reserved.filtered(lambda serial: serial.reserved_picking_id == picking):
                picking.message_post(
                    body=Markup(
                        "<p><strong>Seriales reservados desde la factura %(invoice)s.</strong> "
                        "Usuario: %(user)s.</p><p>Labels: %(codes)s</p>"
                    ) % {
                        "invoice": escape(self.display_name),
                        "user": escape(self.env.user.display_name),
                        "codes": escape(", ".join(
                            newly_reserved.filtered(
                                lambda serial: serial.reserved_picking_id == picking
                            ).mapped("code")
                        )),
                    },
                    subtype_xmlid="mail.mt_note",
                )

        if newly_reserved:
            self.message_post(
                body=Markup(
                    "<p><strong>Despacho preparado con seriales existentes.</strong> "
                    "No se generaron códigos nuevos.</p><p>Operaciones: %(pickings)s</p>"
                    "<p>Labels reservados: %(codes)s</p>"
                ) % {
                    "pickings": escape(", ".join(pickings.mapped("name"))),
                    "codes": escape(", ".join(newly_reserved.mapped("code"))),
                },
                subtype_xmlid="mail.mt_note",
            )
        return pickings

    def action_open_ddsl_document_label_wizard(self):
        self.ensure_one()
        if self.move_type == "out_invoice":
            self._ddmh_prepare_dispatch_serials()
        return super().action_open_ddsl_document_label_wizard()


class DocumentLabelWizard(models.TransientModel):
    _inherit = "ddsl.document.label.wizard"

    def _ddmh_serial_payload(self, serial, picking):
        product = serial.product_id
        tmpl = product.product_tmpl_id
        line = self.move_id.invoice_line_ids.filtered(
            lambda candidate: candidate.product_id == product
            and candidate.display_type in (False, "product")
        )[:1]
        return {
            "document_name": self.move_id.name or self.move_id.ref or "INV",
            "dispatch_name": picking.name or "",
            "customer_name": self.move_id.partner_id.display_name or "",
            "product_name": product.display_name or "",
            "variant_attributes": line._ddpc_get_configuration_attributes() if line else [],
            "label_model": tmpl.ddsl_label_model or "",
            "label_design": tmpl.ddsl_label_design or "",
            "label_size": tmpl.ddsl_label_size or "",
            "label_swing": tmpl.ddsl_label_swing or "",
            "label_hinge": tmpl.ddsl_label_hinge or "",
            "product_code": serial.code,
            "barcode_src": product.ddsl_get_label_barcode_src(serial.code),
            "prepared_by": (self.move_id.invoice_user_id or self.move_id.create_uid).name or "",
            "printed_by": self.env.user.name or "",
        }

    def _prepare_label_payloads(self):
        self.ensure_one()
        if not self.move_id or self.move_id.move_type != "out_invoice":
            return super()._prepare_label_payloads()
        pickings = self.move_id._ddmh_dispatch_pickings_for_labels()
        serials = self.move_id._ddmh_reserved_serials_for_labels(pickings)
        if not serials:
            raise UserError(_(
                "La factura no tiene labels unitarios reservados. Use primero "
                "Preparar despacho e imprimir labels."
            ))
        payloads = []
        for picking in pickings:
            for serial in serials.filtered(
                lambda item: item.reserved_picking_id == picking
            ).sorted("id"):
                payloads.append(self._ddmh_serial_payload(serial, picking))
        return payloads

    def action_print_labels(self):
        action = super().action_print_labels()
        if self.move_id and self.move_id.move_type == "out_invoice":
            move = self.move_id
            move.write({
                "ddmh_label_print_count": move.ddmh_label_print_count + 1,
                "ddmh_label_last_printed_at": fields.Datetime.now(),
                "ddmh_label_last_printed_by_id": self.env.user.id,
            })
            move.message_post(
                body=_(
                    "Labels del despacho impresos/reimpresos por %(user)s. "
                    "Impresión número %(count)s. Los códigos reservados se conservaron sin cambios."
                ) % {
                    "user": self.env.user.display_name,
                    "count": move.ddmh_label_print_count,
                },
                subtype_xmlid="mail.mt_note",
            )
        return action
