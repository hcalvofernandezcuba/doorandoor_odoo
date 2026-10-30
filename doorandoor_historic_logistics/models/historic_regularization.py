from markupsafe import Markup, escape

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


class DoorAndDoorHistoricRegularization(models.Model):
    _name = "doorandoor.historic.regularization"
    _description = "Recepción histórica de arrancada"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Regularización", required=True, readonly=True, copy=False,
        default=lambda self: _("Nuevo"), tracking=True,
    )
    historical_delivery_id = fields.Many2one(
        "doorandoor.historical.delivery", string="Venta histórica",
        required=True, tracking=True, ondelete="restrict",
        domain="[('state', 'not in', ('done', 'cancel'))]",
    )
    external_reference = fields.Char(
        related="historical_delivery_id.external_reference", store=True,
        readonly=True, string="Factura anterior",
    )
    partner_id = fields.Many2one(
        related="historical_delivery_id.partner_id", store=True,
        readonly=True, string="Cliente",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén físico", required=True,
        tracking=True, context={"ddic_authorized_warehouse_search": True},
    )
    destination_mode = fields.Selection(
        [("storage", "Almacenar en inventario"),
         ("predispatch", "Enviar directamente a predespacho")],
        string="Destino después de recibir", default="storage",
        required=True, tracking=True,
    )
    destination_location_id = fields.Many2one(
        "stock.location", string="Ubicación física de destino", required=True,
        tracking=True,
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=', warehouse_id)]",
    )
    source_location_id = fields.Many2one(
        "stock.location", string="Origen técnico de inventario",
        readonly=True, copy=False,
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Entrada de regularización", readonly=True,
        copy=False, tracking=True,
    )
    line_ids = fields.One2many(
        "doorandoor.historic.regularization.line", "regularization_id",
        string="Mercancía localizada", copy=True,
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment", "ddhl_regularization_attachment_rel",
        "regularization_id", "attachment_id", string="Evidencias físicas",
        copy=False,
    )
    physical_note = fields.Text(
        string="Ubicación y comprobación física",
        help="Explique dónde se encontró la mercancía, quién la contó y contra qué documento se comprobó.",
    )
    responsible_id = fields.Many2one(
        "res.users", string="Responsable", required=True,
        default=lambda self: self.env.user, tracking=True,
    )
    validated_by_id = fields.Many2one(
        "res.users", string="Validada por", readonly=True, copy=False,
    )
    validated_at = fields.Datetime(
        string="Validada el", readonly=True, copy=False,
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("receipt_ready", "Recepción preparada"),
         ("labels_ready", "Labels preparados"),
         ("done", "Existencia confirmada"), ("incident", "Incidencia"),
         ("cancel", "Cancelada")],
        default="draft", required=True, tracking=True, copy=False, index=True,
    )
    total_expected = fields.Float(
        string="Pendiente del histórico", compute="_compute_totals",
    )
    total_physical = fields.Integer(
        string="Cantidad física declarada", compute="_compute_totals",
    )
    total_labels = fields.Integer(
        string="Labels preparados", compute="_compute_totals",
    )
    company_id = fields.Many2one(
        related="historical_delivery_id.company_id", store=True, readonly=True,
    )

    _sql_constraints = [
        ("name_company_unique", "unique(name, company_id)",
         "La referencia de regularización debe ser única por compañía."),
    ]

    @api.depends(
        "line_ids.pending_before", "line_ids.physical_quantity",
        "line_ids.serial_ids",
    )
    def _compute_totals(self):
        for record in self:
            record.total_expected = sum(record.line_ids.mapped("pending_before"))
            record.total_physical = sum(record.line_ids.mapped("physical_quantity"))
            record.total_labels = sum(
                line.physical_quantity if line.batch_id.shared_serial and line.serial_ids
                else len(line.serial_ids)
                for line in record.line_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code(
                    "doorandoor.historic.regularization"
                ) or _("Nuevo")
        records = super().create(vals_list)
        records._ddhl_check_warehouse_access()
        for record in records:
            record.historical_delivery_id._ddhl_assert_regularization_needed()
            if not record.evidence_attachment_ids:
                direct_attachments = self.env["ir.attachment"].sudo().search([
                    ("res_model", "=", record.historical_delivery_id._name),
                    ("res_id", "=", record.historical_delivery_id.id),
                ])
                evidence = (
                    record.historical_delivery_id.evidence_attachment_ids
                    | direct_attachments
                )
            else:
                evidence = self.env["ir.attachment"]
            if evidence:
                record.evidence_attachment_ids = [
                    (6, 0, evidence.ids)
                ]
        records.mapped("historical_delivery_id")._ddhl_invalidate_linked_operation_cache()
        return records

    def write(self, vals):
        histories = self.mapped("historical_delivery_id")
        linked_before = histories._ddhl_linked_operations()
        protected = {
            "historical_delivery_id", "warehouse_id", "destination_mode",
            "destination_location_id", "line_ids",
        }
        if protected.intersection(vals) and any(record.state != "draft" for record in self):
            raise UserError(_(
                "No puede cambiar venta, almacén, ubicación o productos después de preparar los labels."
            ))
        result = super().write(vals)
        if protected.intersection(vals):
            self._ddhl_check_warehouse_access()
        if "picking_id" in vals:
            histories._ddhl_invalidate_linked_operation_cache(extra=linked_before)
        return result

    def _ddhl_check_warehouse_access(self):
        if self.env.user.has_group("base.group_system"):
            return True
        for record in self:
            if not record.warehouse_id:
                continue
            allowed = self.env.user.ddpc_warehouse_ids
            if not allowed or record.warehouse_id not in allowed:
                raise AccessError(_(
                    "El usuario %(user)s no tiene asignado el almacén %(warehouse)s."
                ) % {
                    "user": self.env.user.display_name,
                    "warehouse": record.warehouse_id.display_name,
                })
            if (
                record.destination_location_id
                and record.destination_location_id.warehouse_id != record.warehouse_id
            ):
                raise ValidationError(_(
                    "La ubicación física debe pertenecer al almacén seleccionado."
                ))
        return True

    @api.onchange("historical_delivery_id")
    def _onchange_historical_delivery_id(self):
        self.line_ids = [(5, 0, 0)]
        if not self.historical_delivery_id:
            return
        # The physical destination is always the delivery warehouse.  The
        # supplier warehouse remains the origin of the historical transfer.
        self.warehouse_id = self.historical_delivery_id.warehouse_id
        self.evidence_attachment_ids = self.historical_delivery_id.evidence_attachment_ids
        self._ddhl_fill_lines()

    @api.onchange("warehouse_id", "destination_mode")
    def _onchange_destination(self):
        if not self.warehouse_id:
            self.destination_location_id = False
            return
        if self.destination_mode == "storage":
            self.destination_location_id = self.warehouse_id.lot_stock_id
        elif (
            self.historical_delivery_id.picking_id
            and self.historical_delivery_id.picking_id.ddic_predispatch_location_id
        ):
            self.destination_location_id = (
                self.historical_delivery_id.picking_id.ddic_predispatch_location_id
            )
        else:
            self.destination_location_id = False

    def _ddhl_fill_lines(self):
        self.ensure_one()
        commands = []
        for historical_line in self.historical_delivery_id.line_ids:
            done_qty = sum(self.env["doorandoor.historic.regularization.line"].search([
                ("historical_line_id", "=", historical_line.id),
                ("regularization_id.state", "=", "done"),
            ]).mapped("physical_quantity"))
            pending = max(historical_line.quantity - done_qty, 0.0)
            if pending:
                commands.append((0, 0, {
                    "historical_line_id": historical_line.id,
                    "physical_quantity": 0,
                }))
        self.line_ids = commands

    def action_load_pending_products(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Solo puede recargar productos en borrador."))
            record.line_ids = [(5, 0, 0)]
            record._ddhl_fill_lines()
        return True

    def _ddhl_campaign(self):
        self.ensure_one()
        name = _("Regularización histórica %(year)s") % {
            "year": fields.Date.context_today(self).year,
        }
        campaign = self.env["inventory.serial.campaign"].search([
            ("name", "=", name),
            ("company_id", "=", self.company_id.id),
            ("state", "=", "open"),
        ], limit=1)
        return campaign or self.env["inventory.serial.campaign"].create({
            "name": name,
            "company_id": self.company_id.id,
        })

    def action_prepare_labels(self):
        for record in self:
            record._ddhl_check_warehouse_access()
            if record.state == "draft":
                record.action_prepare_reception()
            if record.state != "receipt_ready":
                continue
            if not record.evidence_attachment_ids:
                raise UserError(_(
                    "Adjunte la factura histórica, foto del producto o evidencia física antes de generar labels."
                ))
            is_predispatch = bool(
                "ddic_is_predispatch" in record.destination_location_id._fields
                and record.destination_location_id.ddic_is_predispatch
            )
            if record.destination_mode == "predispatch" and not is_predispatch:
                raise UserError(_(
                    "La ubicación %(location)s no es un área de predespacho DoorAndDoor. "
                    "Seleccione el predespacho propio del documento; no use Stock general."
                ) % {"location": record.destination_location_id.display_name})
            if record.destination_mode == "storage" and is_predispatch:
                raise UserError(_(
                    "La ubicación de predespacho no puede usarse para almacenar inventario general."
                ))
            active_lines = record.line_ids.filtered(lambda line: line.physical_quantity > 0)
            if not active_lines:
                raise UserError(_("Indique al menos una cantidad física recibida."))
            for line in active_lines:
                line._ddhl_check_quantity()
                line._ddhl_prepare_labels(record._ddhl_campaign())
            record.state = "labels_ready"
            record.message_post(body=Markup(
                "<strong>Labels históricos preparados</strong>"
                "<p>Responsable: %(user)s<br/>Almacén: %(warehouse)s<br/>"
                "Unidades físicas: %(qty)s. Todavía no se modificó el inventario.</p>"
            ) % {
                "user": escape(self.env.user.display_name),
                "warehouse": escape(record.warehouse_id.display_name),
                "qty": record.total_physical,
            })
        return True

    def _ddhl_active_lines_for_reception(self):
        self.ensure_one()
        active_lines = self.line_ids.filtered(
            lambda line: line.physical_quantity > 0
        )
        if not active_lines:
            raise UserError(_("Indique al menos una cantidad física recibida."))
        for line in active_lines:
            rounding = line.product_id.uom_id.rounding or 1.0
            if float_compare(
                line.physical_quantity,
                line.pending_before,
                precision_rounding=rounding,
            ) > 0:
                raise ValidationError(_(
                    "La cantidad física de %(product)s (%(physical)s) supera "
                    "lo pendiente (%(pending)s)."
                ) % {
                    "product": line.product_id.display_name,
                    "physical": line.physical_quantity,
                    "pending": line.pending_before,
                })
        return active_lines

    def action_prepare_reception(self):
        """Create the auditable incoming document without changing stock."""
        for record in self:
            record._ddhl_check_warehouse_access()
            if record.state != "draft":
                continue
            if not record.evidence_attachment_ids:
                raise UserError(_(
                    "Adjunte la factura histórica o documento de respaldo."
                ))
            record._ddhl_active_lines_for_reception()
            picking = record._ddhl_create_stock_entry()
            record.state = "receipt_ready"
            body = Markup(
                "<p><strong>Recepción histórica preparada.</strong></p>"
                "<p>Documento: %(picking)s<br/>Factura anterior: %(reference)s<br/>"
                "Destino físico: %(location)s<br/>Unidades: %(quantity)s.</p>"
                "<p>Todavía no se modificó el inventario. Continúe preparando "
                "e imprimiendo los labels.</p>"
            ) % {
                "picking": escape(picking.display_name),
                "reference": escape(record.external_reference),
                "location": escape(record.destination_location_id.display_name),
                "quantity": record.total_physical,
            }
            record.message_post(body=body)
            record.historical_delivery_id.message_post(body=body)
            picking.message_post(body=body)
        return True

    def action_print_labels(self):
        self.ensure_one()
        if self.state not in ("labels_ready", "done"):
            raise UserError(_("Prepare primero los labels de esta recepción."))
        payloads = []
        for line in self.line_ids.filtered("serial_ids"):
            labels = line.batch_id._label_payloads(serials=line.serial_ids)
            if line.batch_id.shared_serial and labels:
                labels = labels[:1] * line.physical_quantity
            payloads.extend(labels)
        if not payloads:
            raise UserError(_("Esta recepción no tiene labels para imprimir."))
        return self.env.ref(
            "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
        ).report_action(self.line_ids[:1].batch_id, data={"labels": payloads})

    def _ddhl_create_stock_entry(self):
        self.ensure_one()
        if self.picking_id:
            return self.picking_id
        source = self.env.ref("stock.location_inventory", raise_if_not_found=False)
        if not source:
            source = self.env["stock.location"].search([
                ("usage", "=", "inventory"),
                ("company_id", "in", (False, self.company_id.id)),
            ], limit=1)
        if not source:
            raise UserError(_("No existe una ubicación virtual de ajuste de inventario."))
        picking_type = self.warehouse_id.in_type_id
        if not picking_type:
            raise UserError(_("El almacén no tiene configurada una operación de recepción."))
        initial_destination = (
            self.warehouse_id.lot_stock_id
            if self.destination_mode == "predispatch"
            else self.destination_location_id
        )
        if not initial_destination:
            raise UserError(_("Seleccione la ubicación física de destino."))
        picking = self.env["stock.picking"].sudo().create({
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": initial_destination.id,
            "origin": _("Regularización %(regularization)s / %(reference)s") % {
                "regularization": self.name,
                "reference": self.external_reference,
            },
            "company_id": self.company_id.id,
            "move_type": "direct",
        })
        for line in self._ddhl_active_lines_for_reception():
            if line.product_id.tracking != "none":
                raise UserError(_(
                    "El producto %(product)s usa seguimiento nativo %(tracking)s. "
                    "Revise su lote/serie nativo antes de continuar."
                ) % {
                    "product": line.product_id.display_name,
                    "tracking": line.product_id.tracking,
                })
            self.env["stock.move"].sudo().create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.physical_quantity,
                "product_uom": line.product_id.uom_id.id,
                "picking_id": picking.id,
                "location_id": source.id,
                "location_dest_id": initial_destination.id,
                "company_id": self.company_id.id,
            })
        picking.action_confirm()
        if self.destination_mode == "predispatch":
            destination = picking._ddic_get_or_create_predispatch_location()
            picking.sudo().write({"location_dest_id": destination.id})
            picking.move_ids.sudo().write({"location_dest_id": destination.id})
            self.sudo().write({"destination_location_id": destination.id})
        else:
            destination = initial_destination
        for move in picking.move_ids:
            # Odoo can prepare the detailed line during action_confirm().
            # Reuse it instead of adding a second counted quantity.
            if move.move_line_ids:
                move.move_line_ids.sudo().write({
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                })
            else:
                self.env["stock.move.line"].sudo().create({
                    "picking_id": picking.id,
                    "move_id": move.id,
                    "product_id": move.product_id.id,
                    "product_uom_id": move.product_uom.id,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                    "quantity": move.product_uom_qty,
                })
        self.sudo().write({
            "source_location_id": source.id,
            "picking_id": picking.id,
        })
        return picking

    def action_validate_inventory(self):
        raise UserError(_(
            "La recepción histórica debe validarse físicamente con Hanger. "
            "Imprima el albarán y los labels desde el chatter, escanee el "
            "albarán una vez y luego todos los labels recibidos."
        ))

    def _ddhl_advance_after_hanger_receipt(self):
        """Unlock exactly one next phase after the physical origin receipt."""
        for record in self:
            history = record.historical_delivery_id
            operation = history._ddhl_create_next_after_initial_receipt(record)
            body = Markup(
                "<p><strong>Recepción inicial validada con Hanger.</strong></p>"
                "<p>Recepción: %(receipt)s<br/>Siguiente fase: %(operation)s.</p>"
            ) % {
                "receipt": escape(record.picking_id.display_name),
                "operation": escape(operation.mapped("display_name") and ", ".join(
                    operation.mapped("display_name")
                ) or _("Pendiente")),
            }
            record.message_post(body=body)
            history.message_post(body=body)
        return True

    def action_release_logistics(self):
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Confirme primero la existencia física."))
        history = self.historical_delivery_id
        pending = history.line_ids.filtered(
            lambda line: line.ddhl_regularized_qty + 1e-6 < line.quantity
        )
        if pending:
            raise UserError(_(
                "Todavía faltan unidades por localizar: %s"
            ) % ", ".join(
                "%s (%.2f)" % (
                    line.product_id.display_name,
                    line.quantity - line.ddhl_regularized_qty,
                ) for line in pending
            ))
        if history.state == "draft":
            action = history.action_create_operation()
            history.invalidate_recordset(["picking_id", "state"])
            self._ddhl_reserve_received_labels(history.picking_id)
            return action
        if history.transfer_dispatch_id:
            return history.action_open_transfer_dispatch()
        if history.picking_id:
            self._ddhl_align_existing_customer_delivery(history.picking_id)
            self._ddhl_reserve_received_labels(history.picking_id)
            return history.action_open_operation()
        raise UserError(_("La venta histórica no tiene operación logística disponible."))

    def _ddhl_align_existing_customer_delivery(self, picking):
        """Move an early-created delivery to the confirmed predispatch source.

        Some historic deliveries may already exist when the physical receipt is
        completed.  Keeping their original warehouse-stock source would reserve
        unrelated inventory and disconnect the receipt from its dispatch.
        """
        self.ensure_one()
        source = self.destination_location_id
        if (
            self.destination_mode != "predispatch"
            or not source
            or not picking
            or picking.picking_type_code != "outgoing"
            or picking.state in ("done", "cancel")
            or picking.location_id == source
        ):
            return
        if not source.ddic_is_predispatch:
            raise UserError(_(
                "La ubicación %(location)s no es un predespacho válido."
            ) % {"location": source.display_name})

        picking.do_unreserve()
        picking.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
        ).write({"location_id": source.id})
        picking.write({"location_id": source.id})
        picking.action_assign()
        body = Markup(
            "<p><strong>Origen de entrega sincronizado con la recepción "
            "histórica.</strong></p><p>Recepción: %(receipt)s<br/>"
            "Entrega: %(delivery)s<br/>Predespacho: %(location)s.</p>"
        ) % {
            "receipt": escape(self.picking_id.display_name),
            "delivery": escape(picking.display_name),
            "location": escape(source.display_name),
        }
        self.message_post(body=body)
        self.historical_delivery_id.message_post(body=body)
        picking.message_post(body=body)

    def _ddhl_reserve_received_labels(self, picking):
        self.ensure_one()
        if not picking or picking.picking_type_code not in ("outgoing", "internal"):
            return
        serials = self.line_ids.mapped("serial_ids").filtered(
            lambda serial: (
                serial.active
                and serial.inventory_loaded
                and serial.current_location_id == self.destination_location_id
            )
        )
        for serial in serials:
            other = serial.reserved_picking_id
            if other and other != picking and other.state != "cancel":
                raise UserError(_(
                    "El label %(label)s ya está reservado para %(operation)s."
                ) % {
                    "label": serial.code,
                    "operation": other.display_name,
                })
        serials.sudo().write({
            "reserved_picking_id": picking.id,
            "reserved_by_id": self.env.user.id,
            "reserved_at": fields.Datetime.now(),
        })
        body = Markup(
            "<p><strong>Operación preparada desde la recepción histórica.</strong></p>"
            "<p>Recepción: %(receipt)s<br/>Salida: %(dispatch)s<br/>"
            "Labels reservados: %(labels)s.</p>"
        ) % {
            "receipt": escape(self.picking_id.display_name),
            "dispatch": escape(picking.display_name),
            "labels": escape(", ".join(serials.mapped("code"))),
        }
        self.message_post(body=body)
        self.historical_delivery_id.message_post(body=body)
        picking.message_post(body=body)

    def action_open_stock_entry(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("La entrada todavía no fue creada."))
        return self.picking_id.get_formview_action()

    def action_open_historical_delivery(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.historical_delivery_id.display_name,
            "res_model": "doorandoor.historical.delivery",
            "res_id": self.historical_delivery_id.id,
            "view_mode": "form",
            "target": "current",
        }


class InventorySerialReceipt(models.Model):
    _inherit = "inventory.serial.receipt"

    ddhl_historical_regularization_id = fields.Many2one(
        "doorandoor.historic.regularization",
        string="Regularización histórica recuperada",
        readonly=True,
        copy=False,
        index=True,
    )

    def _check_access_and_document(self):
        recovery = self.filtered("ddhl_historical_regularization_id")
        normal = self - recovery
        if normal:
            super(InventorySerialReceipt, normal)._check_access_and_document()
        for receipt in recovery:
            regularization = receipt.ddhl_historical_regularization_id
            if receipt.picking_id != regularization.picking_id:
                raise UserError(_("El control no pertenece a la recepción histórica indicada."))
            if receipt.picking_id.state != "done":
                raise UserError(_("La recuperación Hanger solo aplica a una recepción ya validada."))
            if receipt.warehouse_id != regularization.warehouse_id:
                raise UserError(_("El almacén del control no coincide con la regularización histórica."))
        return True


    def action_start(self):
        recovery = self.filtered("ddhl_historical_regularization_id")
        normal = self - recovery
        for receipt in normal:
            source = receipt.picking_id.ddpc_transfer_source_picking_id
            if source and source.state != "done":
                raise UserError(_(
                    "El despacho de origen %s todavía no ha sido validado con Hanger."
                ) % source.display_name)
        if normal:
            super(InventorySerialReceipt, normal).action_start()
        for receipt in recovery.filtered(lambda item: item.state == "draft"):
            line = receipt.ddhl_historical_regularization_id.line_ids.filtered(
                lambda item: item.product_id == receipt.product_id
            )
            expected = line.mapped("serial_ids").filtered("active")
            if len(expected) != receipt.quantity:
                raise UserError(_(
                    "La regularización tiene %(labels)s labels de %(product)s y el control espera %(quantity)s."
                ) % {
                    "labels": len(expected),
                    "product": receipt.product_id.display_name,
                    "quantity": receipt.quantity,
                })
            receipt.sudo().write({
                "expected_serial_ids": [(6, 0, expected.ids)],
                "state": "scanning",
            })
        return True

    def action_scan(self):
        self.ensure_one()
        if not self.ddhl_historical_regularization_id:
            return super().action_scan()
        if self.state != "scanning":
            raise UserError(_("La operación no está esperando labels."))
        code = (self.scan_code or "").strip()
        serial = self.env["inventory.unit.serial"].sudo().search([
            ("code", "=", code), ("active", "=", True),
        ], limit=1)
        if not serial:
            raise UserError(_("El label %s no existe en DoorAndDoor.") % code)
        controls = self.sudo().search([
            ("ddhl_historical_regularization_id", "=", self.ddhl_historical_regularization_id.id),
            ("state", "!=", "cancel"),
        ])
        target = controls.filtered(lambda control: serial in control.expected_serial_ids)[:1]
        if not target:
            raise UserError(_(
                "El label %(label)s no pertenece a ningún ITEM esperado de %(document)s."
            ) % {"label": code, "document": self.picking_id.display_name})
        if serial in controls.mapped("serial_ids"):
            raise UserError(_("El label %s ya fue contado en esta operación.") % code)
        target.serial_ids = [(4, serial.id)]
        if not self.env["ddmh.picking.serial.scan"].search_count([
            ("picking_id", "=", self.picking_id.id),
            ("serial_id", "=", serial.id),
        ]):
            self.env["ddmh.picking.serial.scan"].create({
                "picking_id": self.picking_id.id,
                "serial_id": serial.id,
                "user_id": self.env.user.id,
            })
        self.env["ddmh.hanger.scan.event"].sudo().create({
            "picking_id": self.picking_id.id,
            "user_id": self.env.user.id,
            "code": serial.code,
            "product_id": serial.product_id.id,
            "serial_id": serial.id,
            "status": "accepted",
            "message": _("Label histórico aceptado en conteo físico libre."),
        })
        self.scan_code = False
        # The active screen stays open as a document-level scanner.  A label
        # may belong to any ITEM and operators must not be forced through a
        # product sequence in a high-volume receiving operation.
        if target.scanned_count == target.quantity:
            target.state = "ready"
        return True

    def action_finalize_historical_recovery(self):
        self.ensure_one()
        regularization = self.ddhl_historical_regularization_id
        if not regularization:
            raise UserError(_("Esta acción solo aplica a recuperaciones históricas."))
        controls = self.sudo().search([
            ("ddhl_historical_regularization_id", "=", regularization.id),
            ("state", "!=", "cancel"),
        ])
        if not controls.mapped("serial_ids"):
            raise UserError(_("No se contó ningún label físico; no puede finalizar la recepción."))
        complete = all(
            control.scanned_count == control.quantity
            for control in controls
        )
        if complete:
            controls.sudo().write({"state": "ready"})
            return controls.sudo().action_confirm()
        for control in controls:
            control.state = "done" if control.scanned_count == control.quantity else "incomplete"
        self.closure_note = _(
            "Conteo físico aleatorio finalizado por el operador; los labels no leídos quedan pendientes."
        )
        return self.action_close_incomplete()

    def action_close_incomplete(self):
        self.ensure_one()
        if not self.ddhl_historical_regularization_id:
            return super().action_close_incomplete()
        regularization = self.ddhl_historical_regularization_id
        operator = self.env["res.users"].browse(
            self.env.context.get("ddhl_operator_user_id")
        ).exists() or self.env.user
        controls = self.sudo().search([
            ("ddhl_historical_regularization_id", "=", regularization.id),
            ("state", "!=", "cancel"),
        ])
        if len(controls) != len(regularization.line_ids.filtered(
            lambda line: line.physical_quantity > 0
        )):
            raise UserError(_("Prepare todos los ITEM antes de cerrar con faltantes."))
        if not (self.closure_note or "").strip():
            raise UserError(_("Escriba la observación del faltante antes de cerrar."))
        # A historical recovery is reviewed ITEM by ITEM.  Closing one
        # incomplete control must advance to the next product instead of
        # finalizing the whole receipt prematurely.
        if self.missing_serial_ids:
            self.state = "incomplete"
        pending_controls = controls.filtered(
            lambda control: control.id != self.id
            and control.state in ("scanning", "ready")
        ).sorted("id")
        if pending_controls:
            self.message_post(body=Markup(
                "<p><strong>ITEM revisado con faltantes.</strong></p>"
                "<p>Contados: %(counted)s de %(expected)s. Se continúa con %(next)s.</p>"
                "<p>Observación: %(note)s</p>"
            ) % {
                "counted": self.scanned_count,
                "expected": self.quantity,
                "next": escape(pending_controls[0].product_id.display_name),
                "note": escape(self.closure_note),
            })
            return pending_controls[:1].get_formview_action()
        received = controls.mapped("serial_ids").filtered("active")
        if not received:
            raise UserError(_("No se contó ningún label físico; no puede cerrar la recuperación."))
        expected = controls.mapped("expected_serial_ids").filtered("active")
        missing = expected - received
        if not missing:
            raise UserError(_("No hay faltantes. Confirme cada control completo."))

        received_by_product = {
            control.product_id: len(control.serial_ids.filtered("active"))
            for control in controls
        }
        missing_by_product = {
            control.product_id: len(control.missing_serial_ids.filtered("active"))
            for control in controls
            if control.missing_serial_ids
        }

        receipt = regularization.picking_id
        returned_by_product = {}
        for move in receipt.return_ids.filtered(lambda item: item.state == "done").move_ids:
            returned_by_product[move.product_id] = (
                returned_by_product.get(move.product_id, 0) + move.quantity
            )
        fully_reverted = all(
            returned_by_product.get(move.product_id, 0) >= move.quantity
            for move in receipt.move_ids.filtered(lambda item: item.state == "done")
        )
        if fully_reverted:
            # The erroneous 20-unit receipt was fully reversed before the live
            # count. Re-enter only the labels physically scanned by Hanger.
            correction = self.env["stock.picking"].create({
                "picking_type_id": receipt.picking_type_id.id,
                "location_id": receipt.location_id.id,
                "location_dest_id": receipt.location_dest_id.id,
                "partner_id": receipt.partner_id.id,
                "company_id": receipt.company_id.id,
                "origin": _("Conteo físico Hanger de %s") % receipt.name,
            })
            for original in receipt.move_ids.filtered(lambda item: item.state == "done"):
                quantity = received_by_product.get(original.product_id, 0)
                if not quantity:
                    continue
                self.env["stock.move"].create({
                    "name": original.name,
                    "product_id": original.product_id.id,
                    "product_uom_qty": quantity,
                    "product_uom": original.product_uom.id,
                    "location_id": receipt.location_id.id,
                    "location_dest_id": receipt.location_dest_id.id,
                    "picking_id": correction.id,
                    "company_id": receipt.company_id.id,
                })
            correction.action_confirm()
        else:
            # DD/IN was already posted with the document quantity. Return only
            # the unverified difference and preserve an auditable correction.
            return_wizard = self.env["stock.return.picking"].with_context(
                active_model="stock.picking",
                active_id=receipt.id,
                active_ids=receipt.ids,
            ).create({"picking_id": receipt.id})
            return_wizard.product_return_moves.write({"quantity": 0.0})
            for return_line in return_wizard.product_return_moves:
                return_line.quantity = missing_by_product.get(return_line.product_id, 0)
            correction = return_wizard._create_return()
        # The historical receipt was posted without native stock move lines
        # because its DoorAndDoor labels live in inventory.unit.serial.  The
        # standard return wizard therefore creates the corrective demand but
        # cannot infer the executed quantity for storable products.  Explicitly
        # apply that demand before validation so the return changes the quants,
        # while the external label audit remains in the recovery controls.
        for move in correction.move_ids.filtered(lambda item: item.state != "cancel"):
            move.quantity = move.product_uom_qty
        correction.with_user(SUPERUSER_ID).with_context(
            skip_immediate=True,
            skip_backorder=True,
            picking_ids_not_to_backorder=correction.ids,
            ddhl_historical_validation=True,
            ddmh_operator_user_id=operator.id,
        ).button_validate()
        correction.invalidate_recordset(["state"])
        if correction.state != "done":
            raise UserError(_("La corrección de la recepción no pudo validarse automáticamente."))

        controls._ddic_apply_received_serials()
        for control in controls:
            control.state = "incomplete" if control.missing_serial_ids else "done"
        for line in regularization.line_ids:
            line.serial_ids = [(6, 0, controls.filtered(
                lambda control: control.product_id == line.product_id
            ).mapped("serial_ids").ids)]
            line.physical_quantity = received_by_product.get(line.product_id, 0)
        regularization.sudo().write({
            "state": "done",
            "validated_by_id": operator.id,
            "validated_at": fields.Datetime.now(),
        })

        dispatch = regularization.historical_delivery_id.transfer_dispatch_id
        if dispatch:
            chain = dispatch | regularization.historical_delivery_id.transfer_receipt_id | regularization.historical_delivery_id.picking_id
            for operation in chain.filtered(lambda picking: picking.state not in ("done", "cancel")):
                if operation.state == "assigned":
                    operation.do_unreserve()
                for move in operation.move_ids.filtered(lambda item: item.state != "cancel"):
                    quantity = received_by_product.get(move.product_id, 0)
                    if quantity:
                        move.product_uom_qty = quantity
                    else:
                        move._action_cancel()
            received.sudo().write({
                "reserved_picking_id": dispatch.id,
                "reserved_by_id": operator.id,
                "reserved_at": fields.Datetime.now(),
            })
            dispatch.action_assign()
        body = Markup(
            "<p><strong>Recuperación Hanger cerrada con faltantes.</strong></p>"
            "<p>Recepción ya validada: %(receipt)s<br/>Recibidos y comprobados: %(received)s<br/>"
            "Faltantes: %(missing)s<br/>Corrección: %(correction)s<br/>Operador: %(user)s.</p>"
            "<p><strong>Labels faltantes:</strong> %(labels)s</p>"
            "<p><strong>Observación:</strong> %(note)s</p>"
        ) % {
            "receipt": escape(regularization.picking_id.display_name),
            "received": len(received),
            "missing": len(missing),
            "correction": escape(correction.display_name),
            "user": escape(operator.display_name),
            "labels": escape(", ".join(missing.mapped("code"))),
            "note": escape(self.closure_note),
        }
        regularization.message_post(body=body)
        regularization.historical_delivery_id.message_post(body=body)
        regularization.picking_id.message_post(body=body)
        if dispatch:
            dispatch.message_post(body=body)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_skip_historical_item(self):
        self.ensure_one()
        if not self.ddhl_historical_regularization_id:
            raise UserError(_("Esta acción solo aplica a recuperaciones históricas."))
        if self.serial_ids:
            raise UserError(_(
                "Este ITEM ya tiene labels contados. Use Cerrar con faltantes para conservarlos."
            ))
        self.closure_note = _(
            "ITEM no recibido físicamente durante la comprobación Hanger."
        )
        return self.action_close_incomplete()

    def _ddic_expected_dispatch_serials(self):
        self.ensure_one()
        source = self.picking_id.ddpc_transfer_source_picking_id
        if source and "ddmh.picking.serial.scan" in self.env.registry:
            scans = self.env["ddmh.picking.serial.scan"].sudo().search([
                ("picking_id", "=", source.id),
                ("product_id", "=", self.product_id.id),
            ])
            return scans.mapped("serial_id").filtered("active")
        return super()._ddic_expected_dispatch_serials()

    def action_confirm(self):
        recovery_controls = self.filtered("ddhl_historical_regularization_id")
        normal_controls = self - recovery_controls
        result = True
        if normal_controls:
            result = super(InventorySerialReceipt, normal_controls).action_confirm()
        if recovery_controls:
            # The warehouse operator has already passed the controlled Hanger
            # scan and the historical-document checks.  Elevate only this
            # internal serial confirmation; do not grant the operator general
            # Inventory Manager privileges or relax normal receipts.
            result = super(
                InventorySerialReceipt,
                recovery_controls.with_user(SUPERUSER_ID),
            ).action_confirm()
        recoveries = recovery_controls.mapped("ddhl_historical_regularization_id")
        for regularization in recoveries:
            controls = self.sudo().search([
                ("ddhl_historical_regularization_id", "=", regularization.id),
                ("state", "!=", "cancel"),
            ])
            if not controls or any(control.state != "done" for control in controls):
                continue
            regularization.sudo().write({
                "state": "done",
                "validated_by_id": self.env.user.id,
                "validated_at": fields.Datetime.now(),
            })
            regularization._ddhl_advance_after_hanger_receipt()
            body = Markup(
                "<p><strong>Recepción histórica recuperada con Hanger.</strong></p>"
                "<p>Recepción: %(receipt)s<br/>Labels comprobados: %(labels)s<br/>"
                "Operador: %(user)s.</p>"
            ) % {
                "receipt": escape(regularization.picking_id.display_name),
                "labels": len(controls.mapped("serial_ids")),
                "user": escape(self.env.user.display_name),
            }
            regularization.message_post(body=body)
            regularization.historical_delivery_id.message_post(body=body)
            regularization.picking_id.message_post(body=body)
        receipt_pickings = self.mapped("picking_id").filtered(
            lambda picking: picking.ddpc_transfer_stage == "receipt"
        )
        History = self.env["doorandoor.historical.delivery"].sudo()
        for receipt in receipt_pickings:
            controls = self.sudo().search([("picking_id", "=", receipt.id)])
            if not controls or any(control.state != "done" for control in controls):
                continue
            histories = History.search([
                ("transfer_receipt_id", "=", receipt.id),
                ("state", "=", "transfer_pending"),
            ])
            for history in histories:
                serials = controls.mapped("serial_ids").filtered("active")
                if any(serial.current_location_id != receipt.location_dest_id for serial in serials):
                    raise UserError(_(
                        "Confirme primero todos los labels en el predespacho de destino."
                    ))
                delivery = history._ddhl_create_delivery_after_transfer_receipt(serials)
                body = Markup(
                    "<p><strong>Cadena histórica lista para entrega.</strong></p>"
                    "<p>Recepción destino: %(receipt)s<br/>Entrega: %(delivery)s<br/>"
                    "Labels: %(labels)s.</p>"
                ) % {
                    "receipt": escape(receipt.display_name),
                    "delivery": escape(delivery.display_name),
                    "labels": escape(", ".join(serials.mapped("code"))),
                }
                history.message_post(body=body)
                receipt.message_post(body=body)
                delivery.message_post(body=body)
        return result


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        """Close the historical reception after its physical Hanger count."""
        operator = self.env["res.users"].browse(
            self.env.context.get("ddmh_operator_user_id")
        ).exists() or self.env.user
        candidates = self.filtered(
            lambda picking: (
                picking.picking_type_code == "incoming"
                and picking.ddmh_serial_scan_ids
            )
        )
        regularizations = self.env["doorandoor.historic.regularization"].sudo().search([
            ("picking_id", "in", candidates.ids),
            ("state", "=", "labels_ready"),
        ])
        result = super()._action_done()
        for regularization in regularizations.filtered(
            lambda record: record.picking_id.state == "done"
        ):
            scanned = regularization.picking_id.ddmh_serial_scan_ids.mapped(
                "serial_id"
            ).filtered("active")
            if not scanned:
                continue
            received_by_product = {
                product: len(scanned.filtered(lambda serial: serial.product_id == product))
                for product in scanned.mapped("product_id")
            }
            # The original proposal may include the complete historical invoice,
            # but only the labels physically read by Hanger belong to this
            # validated reception and to its following transfer chain.  The
            # native stock backorder preserves every unreceived quantity.
            for line in regularization.line_ids:
                line.sudo().write({
                    "physical_quantity": received_by_product.get(
                        line.product_id, 0
                    ),
                })
            scanned.sudo().write({
                "current_warehouse_id": regularization.warehouse_id.id,
                "current_batch_id": False,
                "current_location_id": regularization.destination_location_id.id,
                "inventory_loaded": True,
            })
            regularization.sudo().write({
                "state": "done",
                "validated_by_id": operator.id,
                "validated_at": fields.Datetime.now(),
            })
            regularization._ddhl_advance_after_hanger_receipt()
            body = Markup(
                "<p><strong>Recepción histórica validada físicamente con Hanger.</strong></p>"
                "<p>Recepción: %(receipt)s<br/>Labels: %(labels)s<br/>"
                "Ubicación: %(location)s<br/>Operador: %(user)s.</p>"
            ) % {
                "receipt": escape(regularization.picking_id.display_name),
                "labels": escape(", ".join(scanned.mapped("code"))),
                "location": escape(regularization.picking_id.location_dest_id.display_name),
                "user": escape(operator.display_name),
            }
            regularization.message_post(body=body)
            regularization.historical_delivery_id.message_post(body=body)
            regularization.picking_id.message_post(body=body)
        return result


class StockReceiptScanWizard(models.TransientModel):
    _inherit = "ddsl.stock.receipt.scan.wizard"

    def _ddhl_recovery_controls(self):
        self.ensure_one()
        return self.env["inventory.serial.receipt"].search([
            ("picking_id", "=", self.picking_id.id),
            ("ddhl_historical_regularization_id", "!=", False),
            ("state", "!=", "cancel"),
        ], order="id")

    @api.model
    def ddsl_create_for_picking(self, picking):
        controls = self.env["inventory.serial.receipt"].search([
            ("picking_id", "=", picking.id),
            ("ddhl_historical_regularization_id", "!=", False),
            ("state", "in", ("scanning", "ready", "incomplete")),
        ], order="id")
        if not controls:
            return super().ddsl_create_for_picking(picking)
        wizard = self.create({"picking_id": picking.id})
        for control in controls:
            count = self.env["ddsl.stock.receipt.count"].search([
                ("picking_id", "=", picking.id),
                ("product_id", "=", control.product_id.id),
            ], limit=1)
            values = {
                "expected_qty": control.quantity,
                "counted_qty": control.scanned_count,
                "is_counted": bool(control.scanned_count),
                "last_scan_user_id": self.env.user.id,
            }
            if count:
                count.write(values)
            else:
                count = self.env["ddsl.stock.receipt.count"].create({
                    "picking_id": picking.id,
                    "product_id": control.product_id.id,
                    **values,
                })
            self.env["ddsl.stock.receipt.scan.wizard.line"].create({
                "wizard_id": wizard.id,
                "count_id": count.id,
                "move_id": picking.move_ids.filtered(
                    lambda move: move.product_id == control.product_id
                )[:1].id,
                "product_id": control.product_id.id,
                "expected_qty": control.quantity,
                "counted_qty": control.scanned_count,
                "is_counted": bool(control.scanned_count),
                "difference_qty": control.quantity - control.scanned_count,
            })
        return wizard

    def action_register_scan(self, scanned_code=None):
        self.ensure_one()
        controls = self._ddhl_recovery_controls()
        if not controls:
            return super().action_register_scan(scanned_code)
        code = (scanned_code or self.scan_code or "").strip()
        receiver = controls.filtered(lambda control: control.state in ("scanning", "ready"))[:1]
        if not receiver:
            raise UserError(_("El conteo histórico ya fue finalizado."))
        receiver.scan_code = code
        receiver.action_scan()
        target = controls.filtered(
            lambda control: code in control.expected_serial_ids.mapped("code")
        )[:1]
        line = self.line_ids.filtered(lambda item: item.product_id == target.product_id)[:1]
        if line:
            line.with_context(ddhl_sync=True).write({
                "counted_qty": target.scanned_count,
                "is_counted": True,
            })
        self.scan_code = False
        return {
            "continuous_scan": True,
            "product_id": target.product_id.id,
            "product_name": target.product_id.display_name,
            "barcode": code,
            "expected_qty": target.quantity,
            "counted_qty": target.scanned_count,
            "difference_qty": target.quantity - target.scanned_count,
        }

    def action_apply_count(self):
        self.ensure_one()
        if self._ddhl_recovery_controls():
            return True
        return super().action_apply_count()

    def action_apply_and_validate_operation(self):
        self.ensure_one()
        controls = self._ddhl_recovery_controls()
        if not controls:
            return super().action_apply_and_validate_operation()
        receiver = controls.filtered(lambda control: control.state in ("scanning", "ready"))[:1]
        if not receiver:
            raise UserError(_("El conteo histórico ya fue finalizado."))
        self.picking_id._ddmh_check_mobile_warehouse_access()
        receiver.sudo().with_context(
            ddhl_operator_user_id=self.env.user.id
        ).action_finalize_historical_recovery()
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


class DoorAndDoorHistoricRegularizationLine(models.Model):
    _name = "doorandoor.historic.regularization.line"
    _description = "Producto localizado para regularización histórica"
    _order = "id"

    regularization_id = fields.Many2one(
        "doorandoor.historic.regularization", required=True,
        ondelete="cascade", index=True,
    )
    historical_line_id = fields.Many2one(
        "doorandoor.historical.delivery.line", string="Línea histórica",
        required=True, ondelete="restrict",
        domain="[('delivery_id', '=', parent.historical_delivery_id)]",
    )
    product_id = fields.Many2one(
        related="historical_line_id.product_id", store=True, readonly=True,
        string="ITEM",
    )
    expected_quantity = fields.Float(
        related="historical_line_id.quantity", readonly=True,
        string="Cantidad histórica",
    )
    already_regularized = fields.Float(
        string="Ya regularizado", compute="_compute_pending", readonly=True,
    )
    pending_before = fields.Float(
        string="Pendiente antes de esta recepción", compute="_compute_pending",
        readonly=True,
    )
    physical_quantity = fields.Integer(
        string="Cantidad física contada", required=True, default=0,
    )
    candidate_batch_ids = fields.Many2many(
        "inventory.serial.label.batch", compute="_compute_candidate_batches",
        string="Lotes compatibles",
    )
    batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote / posición",
        domain="[('id', 'in', candidate_batch_ids)]",
    )
    new_batch_reference = fields.Char(
        string="Nuevo lote / posición",
        help="Úselo únicamente si no existe un lote compatible para este ITEM en el almacén.",
    )
    serial_ids = fields.Many2many(
        "inventory.unit.serial", "ddhl_regularization_line_serial_rel",
        "line_id", "serial_id", string="Labels preparados", readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        related="regularization_id.company_id", store=True, readonly=True,
    )

    @api.depends("historical_line_id", "regularization_id.state")
    def _compute_pending(self):
        for line in self:
            completed = self.search([
                ("id", "!=", line.id),
                ("historical_line_id", "=", line.historical_line_id.id),
                ("regularization_id.state", "=", "done"),
            ])
            line.already_regularized = sum(completed.mapped("physical_quantity"))
            line.pending_before = max(
                line.expected_quantity - line.already_regularized, 0.0
            )

    @api.depends(
        "regularization_id.warehouse_id", "product_id",
        "regularization_id.destination_mode",
    )
    def _compute_candidate_batches(self):
        Batch = self.env["inventory.serial.label.batch"]
        for line in self:
            if not line.regularization_id.warehouse_id or not line.product_id:
                line.candidate_batch_ids = False
                continue
            line.candidate_batch_ids = Batch.search([
                ("warehouse_id", "=", line.regularization_id.warehouse_id.id),
                ("product_id", "=", line.product_id.id),
                ("state", "=", "generated"),
            ])

    @api.onchange("batch_id")
    def _onchange_batch_id(self):
        if self.batch_id:
            self.new_batch_reference = False

    @api.onchange("new_batch_reference")
    def _onchange_new_batch_reference(self):
        if self.new_batch_reference:
            self.batch_id = False

    @api.constrains("physical_quantity", "historical_line_id")
    def _check_quantity_constraint(self):
        for line in self:
            if line.regularization_id.state == "draft":
                line._ddhl_check_quantity()

    def _ddhl_check_quantity(self):
        self.ensure_one()
        if self.physical_quantity <= 0:
            raise ValidationError(_("La cantidad física debe ser mayor que cero."))
        rounding = self.product_id.uom_id.rounding or 1.0
        if float_compare(
            self.physical_quantity,
            self.pending_before,
            precision_rounding=rounding,
        ) > 0:
            raise ValidationError(_(
                "La cantidad física de %(product)s (%(physical)s) supera lo pendiente (%(pending)s)."
            ) % {
                "product": self.product_id.display_name,
                "physical": self.physical_quantity,
                "pending": self.pending_before,
            })
        if (
            self.regularization_id.destination_mode != "predispatch"
            and not self.batch_id
            and not (self.new_batch_reference or "").strip()
        ):
            raise ValidationError(_(
                "Seleccione un lote compatible o escriba el nuevo lote/posición para %s."
            ) % self.product_id.display_name)
        return True

    def _ddhl_prepare_labels(self, campaign):
        self.ensure_one()
        if self.serial_ids:
            return self.serial_ids
        batch = self.batch_id
        if batch:
            if batch.warehouse_id != self.regularization_id.warehouse_id:
                raise ValidationError(_("El lote pertenece a otro almacén."))
            if batch.product_id != self.product_id:
                raise ValidationError(_("El lote pertenece a otro ITEM."))
            serials = batch._ddic_add_serial_units(self.physical_quantity)
        else:
            reference = (self.new_batch_reference or "").strip().upper()
            if not reference and self.regularization_id.destination_mode == "predispatch":
                reference = "PRE-%s-%s" % (
                    self.regularization_id.name.replace("/", "-"), self.id,
                )
            if self.env["inventory.serial.label.batch"].search_count([
                ("campaign_id", "=", campaign.id), ("name", "=", reference),
            ]):
                raise ValidationError(_(
                    "El lote %s ya existe en la campaña de regularización. Selecciónelo en lugar de crearlo."
                ) % reference)
            batch = self.env["inventory.serial.label.batch"].create({
                "name": reference,
                "campaign_id": campaign.id,
                "warehouse_id": self.regularization_id.warehouse_id.id,
                "product_id": self.product_id.id,
                "quantity": self.physical_quantity,
            })
            batch.action_generate_serials()
            serials = batch.serial_ids.filtered("active")
        self.write({
            "batch_id": batch.id,
            "new_batch_reference": False,
            "serial_ids": [(6, 0, serials.ids)],
        })
        return serials
