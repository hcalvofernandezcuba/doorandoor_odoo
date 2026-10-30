import unicodedata

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self.env.context.get("ddic_authorized_warehouse_search"):
            allowed = self.env[
                "inventory.serial.label.batch"
            ]._ddic_allowed_warehouses()
            domain = expression.AND([domain, [("id", "in", allowed.ids)]])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
        )


class InventorySerialCampaign(models.Model):
    _name = "inventory.serial.campaign"
    _description = "Inventory Serial Campaign"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    state = fields.Selection(
        [("open", "Abierta"), ("closed", "Cerrada")],
        default="open", required=True, tracking=True,
    )
    batch_ids = fields.One2many(
        "inventory.serial.label.batch", "campaign_id", string="Lotes"
    )
    serial_count = fields.Integer(compute="_compute_counts")
    claimed_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for campaign in self:
            serials = campaign.batch_ids.serial_ids
            campaign.serial_count = sum(
                batch.quantity if batch.shared_serial else len(batch.serial_ids)
                for batch in campaign.batch_ids.filtered(lambda item: item.state != "cancel")
            )
            campaign.claimed_count = sum(
                sum(batch.serial_ids.claim_ids.mapped("counted_qty"))
                if batch.shared_serial else len(batch.serial_ids.filtered("inventory_loaded"))
                for batch in campaign.batch_ids.filtered(lambda item: item.state != "cancel")
            )

    def action_close(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "open"})

    def _serial_audit_payload(self, session=None, warehouse=None, batch=None):
        self.ensure_one()
        batches = self.batch_ids.filtered(lambda batch: batch.state != "cancel")
        if batch:
            batches = batches.filtered(lambda item: item == batch)
        if warehouse:
            batches = batches.filtered(lambda batch: batch.warehouse_id == warehouse)
        rows = []
        total_expected = total_counted = total_other = 0
        for batch in batches.sorted(lambda item: (item.warehouse_id.display_name, item.name, item.id)):
            serials = batch.serial_ids.filtered("active").sorted("id")
            counted = serials.filtered(
                lambda serial: any(
                    claim.session_id == session for claim in serial.claim_ids
                )
            ) if session else serials.filtered("claim_ids")
            counted_other = serials.filtered(
                lambda serial: session and any(
                    claim.session_id != session for claim in serial.claim_ids
                )
            )
            details = []
            for serial in serials:
                current_claim = serial.claim_ids.filtered(
                    lambda claim: session and claim.session_id == session
                )[:1]
                other_claim = serial.claim_ids.filtered(
                    lambda claim: not session or claim.session_id != session
                )[:1]
                if current_claim:
                    status = _("Contado en esta sesión")
                    session_name = session.display_name
                elif other_claim:
                    status = _("Contado en otra sesión")
                    session_name = other_claim.session_id.display_name
                elif serial.inventory_loaded:
                    status = _("Aplicado al inventario")
                    session_name = serial.loaded_session_id.display_name
                else:
                    status = _("Pendiente")
                    session_name = ""
                details.append({
                    "code": serial.code,
                    "status": status,
                    "session": session_name,
                })
            expected_count = batch.quantity if batch.shared_serial else len(serials)
            counted_count = (
                sum(counted.claim_ids.filtered(
                    lambda claim: not session or claim.session_id == session
                ).mapped("counted_qty"))
                if batch.shared_serial else len(counted)
            )
            counted_count = min(counted_count, expected_count)
            total_expected += expected_count
            total_counted += counted_count
            total_other += len(counted_other)
            rows.append({
                "batch": batch.name,
                "warehouse": batch.warehouse_id.display_name,
                "product": batch.product_id.display_name,
                "expected": expected_count,
                "counted": counted_count,
                "counted_other": len(counted_other),
                "pending": expected_count - counted_count,
                "details": details,
            })
        return {
            "campaign": self.display_name,
            "warehouse": warehouse.display_name if warehouse else _("Todos"),
            "session": session.display_name if session else "",
            "expected": total_expected,
            "counted": total_counted,
            "counted_other": total_other,
            "pending": total_expected - total_counted,
            "rows": rows,
        }

    def _serial_audit_report_data(self):
        self.ensure_one()
        return self._serial_audit_payload()

    def action_print_serial_audit(self):
        self.ensure_one()
        return self.env.ref(
            "doorandoor_inventory_variant_count.action_report_serial_campaign_audit"
        ).report_action(self)


class InventorySerialLabelBatch(models.Model):
    _name = "inventory.serial.label.batch"
    _description = "Inventory Serial Label Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Referencia del lote", required=True, tracking=True)
    campaign_id = fields.Many2one(
        "inventory.serial.campaign", required=True, ondelete="restrict", tracking=True
    )
    company_id = fields.Many2one(related="campaign_id.company_id", store=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, tracking=True,
        context={"ddic_authorized_warehouse_search": True},
    )
    allowed_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        compute="_compute_allowed_warehouse_ids",
        string="Almacenes autorizados",
    )
    product_id = fields.Many2one(
        "product.product", tracking=True,
        domain="[('is_storable', '=', True)]",
    )
    is_mixed_batch = fields.Boolean(
        string="Lote mixto", tracking=True, copy=False,
        help=(
            "Permite varios ITEM y cantidades superiores al límite normal de "
            "la posición, conservando serial, almacén e historial por unidad."
        ),
    )
    mixed_product_count = fields.Integer(
        string="ITEM distintos", compute="_compute_mixed_product_count",
    )
    quantity = fields.Integer(required=True, default=1, tracking=True)
    shared_serial = fields.Boolean(
        string="Serial compartido",
        related="product_id.product_tmpl_id.ddic_shared_lot_serial",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("generated", "Generado"),
            ("vacated", "Posición liberada"),
            ("cancel", "Anulado"),
        ],
        default="draft", required=True, tracking=True,
    )
    serial_ids = fields.One2many(
        "inventory.unit.serial", "batch_id", string="Seriales", copy=False
    )
    current_serial_ids = fields.One2many(
        "inventory.unit.serial", "current_batch_id", string="Contenido actual", readonly=True
    )
    serial_count = fields.Integer(compute="_compute_serial_count")
    counted_serial_count = fields.Integer(
        string="Contados", compute="_compute_serial_progress", store=True
    )
    validated_serial_count = fields.Integer(
        string="Validados", compute="_compute_serial_progress", store=True
    )
    pending_serial_count = fields.Integer(
        string="Pendientes", compute="_compute_serial_progress", store=True
    )

    _sql_constraints = [
        (
            "campaign_batch_reference_unique",
            "unique(campaign_id, name)",
            "La referencia del lote debe ser única dentro de la campaña.",
        ),
        ("quantity_positive", "check(quantity >= 0)", "La cantidad no puede ser negativa."),
    ]

    @api.depends("current_serial_ids.active", "current_serial_ids.product_id")
    def _compute_mixed_product_count(self):
        for batch in self:
            batch.mixed_product_count = len(
                batch.current_serial_ids.filtered("active").mapped("product_id")
            )

    @api.constrains("is_mixed_batch", "product_id", "quantity")
    def _check_product_scope(self):
        for batch in self:
            if not batch.is_mixed_batch and not batch.product_id:
                raise ValidationError(_("Seleccione el ITEM del lote."))
            if batch.is_mixed_batch and batch.quantity and not batch.product_id:
                raise ValidationError(_(
                    "Seleccione el primer ITEM del lote mixto o deje la cantidad en cero."
                ))

    @api.depends("serial_ids")
    def _compute_serial_count(self):
        for batch in self:
            batch.serial_count = len(batch.serial_ids)

    @api.depends(
        "quantity", "shared_serial", "serial_ids.active",
        "serial_ids.claim_ids.state", "serial_ids.claim_ids.counted_qty",
    )
    def _compute_serial_progress(self):
        for batch in self:
            active_serials = batch.serial_ids.filtered("active")
            if batch.shared_serial and not batch.is_mixed_batch:
                counted_qty = sum(active_serials.claim_ids.mapped("counted_qty"))
                validated_qty = sum(
                    active_serials.claim_ids.filtered(
                        lambda claim: claim.state == "applied"
                    ).mapped("counted_qty")
                )
                batch.counted_serial_count = min(int(counted_qty), batch.quantity)
                batch.validated_serial_count = min(int(validated_qty), batch.quantity)
                batch.pending_serial_count = max(
                    batch.quantity - batch.counted_serial_count, 0
                )
                continue
            counted_serials = active_serials.filtered("claim_ids")
            validated_serials = active_serials.filtered(
                lambda serial: any(
                    claim.state == "applied" for claim in serial.claim_ids
                )
            )
            batch.counted_serial_count = len(counted_serials)
            batch.validated_serial_count = len(validated_serials)
            batch.pending_serial_count = len(active_serials - counted_serials)

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_allowed_warehouse_ids(self):
        warehouses = self._ddic_allowed_warehouses()
        for batch in self:
            batch.allowed_warehouse_ids = warehouses

    @api.model
    def _ddic_allowed_warehouses(self):
        user = self.env.user
        global_access = (
            user.has_group("base.group_system")
            or user.has_group("doorandoor_process_control.group_ddpc_manager")
            or user.has_group(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
        )
        warehouses = user.with_context(
            ddic_authorized_warehouse_search=False
        ).ddpc_warehouse_ids
        if not warehouses and global_access:
            warehouses = self.env["stock.warehouse"].sudo().with_context(
                ddic_authorized_warehouse_search=False
            ).search([("company_id", "in", self.env.companies.ids)])
        return warehouses.filtered(
            lambda warehouse: warehouse.active
            and warehouse.company_id in self.env.companies
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_mixed_batch") and not vals.get("product_id"):
                vals["quantity"] = 0
            warehouse = self.env["stock.warehouse"].browse(
                vals.get("warehouse_id")
            ).exists()
            self._ddic_check_warehouse_access(warehouse)
            if vals.get("name"):
                vals["name"] = vals["name"].strip().upper()
                occupied = self.sudo().with_context(active_test=False).search([
                    ("warehouse_id", "=", warehouse.id),
                    ("name", "=", vals["name"]),
                    ("state", "in", ("draft", "generated")),
                ], limit=1)
                if occupied:
                    raise ValidationError(_(
                        "La referencia física %(reference)s ya está ocupada por un lote activo en %(warehouse)s."
                    ) % {
                        "reference": vals["name"],
                        "warehouse": warehouse.display_name,
                    })
                campaign_id = vals.get("campaign_id")
                if campaign_id:
                    self.env.cr.execute(
                        """
                        UPDATE inventory_serial_label_batch AS batch
                           SET name = batch.name || '-CANCEL-' || batch.id,
                               write_uid = %s,
                               write_date = NOW() AT TIME ZONE 'UTC'
                         WHERE batch.campaign_id = %s
                           AND batch.name = %s
                           AND batch.state IN ('cancel', 'vacated')
                           AND NOT EXISTS (
                               SELECT 1
                                 FROM inventory_unit_serial AS serial
                                WHERE serial.batch_id = batch.id
                                  AND serial.active
                           )
                     RETURNING batch.id, batch.name
                        """,
                        [self.env.uid, campaign_id, vals["name"]],
                    )
                    row = self.env.cr.fetchone()
                    if row:
                        cancelled = self.sudo().with_context(active_test=False).browse(row[0])
                        cancelled.invalidate_recordset(["name", "write_uid", "write_date"])
                        archived_name = row[1]
                        cancelled.message_post(body=Markup(
                            "<strong>Referencia física liberada</strong>"
                            "<p>La referencia %(reference)s quedó disponible para un lote nuevo. "
                            "Este registro cancelado se conserva como %(archived)s para mantener su historial.</p>"
                        ) % {
                            "reference": escape(vals["name"]),
                            "archived": escape(archived_name),
                        })
                    else:
                        blocked = self.sudo().with_context(active_test=False).search([
                            ("campaign_id", "=", campaign_id),
                            ("name", "=", vals["name"]),
                            ("state", "in", ("cancel", "vacated")),
                        ], limit=1)
                        if blocked and blocked.serial_ids.filtered("active"):
                            raise ValidationError(_(
                                "El lote cancelado %(batch)s todavía conserva labels activos y no puede liberar su referencia."
                            ) % {"batch": blocked.display_name})
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("name"):
            vals["name"] = vals["name"].strip().upper()
        protected = {"campaign_id", "warehouse_id", "product_id", "quantity", "name", "is_mixed_batch"}
        if protected.intersection(vals) and any(batch.state != "draft" for batch in self):
            raise UserError(_("No puede modificar un lote después de generar sus seriales."))
        if vals.get("warehouse_id"):
            warehouse = self.env["stock.warehouse"].browse(vals["warehouse_id"]).exists()
            self._ddic_check_warehouse_access(warehouse)
        return super().write(vals)

    @api.model
    def _ddic_check_warehouse_access(self, warehouse):
        user = self.env.user
        global_access = (
            user.has_group("base.group_system")
            or user.has_group("doorandoor_process_control.group_ddpc_manager")
            or user.has_group(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
        )
        allowed = user.ddpc_warehouse_ids
        if not allowed and global_access:
            return True
        if not allowed:
            raise AccessError(_(
                "Su usuario no tiene almacenes autorizados para generar labels."
            ))
        if not warehouse or warehouse not in allowed:
            raise AccessError(_(
                "El almacén %(warehouse)s no está autorizado para su usuario."
            ) % {"warehouse": warehouse.display_name if warehouse else "-"})
        return True

    def action_generate_serials(self):
        for batch in self:
            batch._ddic_check_warehouse_access(batch.warehouse_id)
            if batch.state != "draft":
                continue
            if batch.campaign_id.state != "open":
                raise UserError(_("La campaña debe estar abierta para generar etiquetas."))
            if batch.is_mixed_batch and not batch.product_id:
                super(InventorySerialLabelBatch, batch).write({"state": "generated"})
                batch.message_post(body=Markup(
                    "<strong>Lote mixto activado</strong>"
                    "<p>Los labels se generarán desde cada ingreso, usando su ITEM.</p>"
                ))
                continue
            if not batch.is_mixed_batch and batch.quantity > 500:
                raise ValidationError(_("El piloto admite hasta 500 unidades por lote."))
            values = []
            serial_quantity = (
                1 if batch.shared_serial and not batch.is_mixed_batch
                else batch.quantity
            )
            for _index in range(serial_quantity):
                code = self.env["ir.sequence"].next_by_code("inventory.unit.serial")
                if not code:
                    raise UserError(_("No se pudo generar la secuencia de seriales."))
                while (
                    self.env["product.product"].search_count([("barcode", "=", code)])
                    or self.env["product.count.item"].search_count([("barcode", "=", code)])
                ):
                    code = self.env["ir.sequence"].next_by_code("inventory.unit.serial")
                values.append({
                    "code": code,
                    "batch_id": batch.id,
                    "product_id": batch.product_id.id,
                })
            self.env["inventory.unit.serial"].sudo().create(values)
            batch.state = "generated"
        return True

    def action_cancel(self):
        for batch in self:
            if batch.serial_ids.filtered("inventory_loaded"):
                raise UserError(_("No puede anular un lote con unidades ya aplicadas."))
            batch.serial_ids.sudo().write({"active": False})
            batch.state = "cancel"

    def action_vacate(self):
        """Release an empty physical position without cancelling its history."""
        for batch in self:
            batch._ddic_check_warehouse_access(batch.warehouse_id)
            if batch.state != "generated":
                raise UserError(_("Solo puede liberar una posición desde un lote generado."))
            current = batch.current_serial_ids.filtered("active")
            if current:
                raise UserError(_(
                    "La posición %(batch)s todavía contiene %(quantity)s labels activos. "
                    "Mueva o retire físicamente esas unidades antes de liberarla."
                ) % {"batch": batch.display_name, "quantity": len(current)})
            original_name = batch.name
            archived_name = "%s-VACIADO-%s" % (original_name, batch.id)
            super(InventorySerialLabelBatch, batch).write({
                "name": archived_name,
                "state": "vacated",
            })
            batch.message_post(body=Markup(
                "<strong>Posición física liberada</strong>"
                "<p>La referencia %(reference)s quedó disponible para una nueva carga. "
                "Este ciclo conserva sus sesiones y labels históricos como %(archived)s; "
                "no se canceló la campaña ni se cerraron sus documentos terminados.</p>"
            ) % {
                "reference": escape(original_name),
                "archived": escape(archived_name),
            })
        return True

    def _label_payloads(self, serials=None, shared_quantity=None):
        self.ensure_one()
        if self.state == "draft":
            self.action_generate_serials()
        if self.state != "generated":
            raise UserError(_("Solo puede imprimir un lote generado."))
        serials = serials if serials is not None else self.serial_ids.filtered("active")
        payloads = []
        for serial in serials.filtered("active").sorted("id"):
            product = serial.product_id
            attributes = [
                {"name": value.attribute_id.display_name or "", "value": value.name or ""}
                for value in product.product_template_attribute_value_ids
            ]
            variant_values = ", ".join(
                value.name or "" for value in product.product_template_attribute_value_ids if value.name
            )
            product_name = product.product_tmpl_id.display_name or product.product_tmpl_id.name or ""
            variant_description = " | ".join(
                "%s: %s" % ((value.attribute_id.display_name or "").removeprefix("PH ").upper(), value.name or "")
                for value in product.product_template_attribute_value_ids if value.name
            )
            if not attributes and product_name.endswith(")") and "(" in product_name:
                base_name, _separator, raw_values = product_name.rpartition("(")
                fallback_values = [value.strip() for value in raw_values[:-1].split(",") if value.strip()]
                if base_name.strip() and fallback_values:
                    product_name = base_name.strip()
                    variant_description = "ITEM: %s" % " | ".join(fallback_values)
            variant_description_pdf = unicodedata.normalize(
                "NFKD", variant_description
            ).encode("ascii", "ignore").decode("ascii")
            payloads.append({
                "product_name": product_name,
                "warehouse_name": self.warehouse_id.display_name or "",
                "variant_name": product.display_name or "",
                "variant_attributes": attributes,
                "variant_values": variant_values,
                "variant_description": variant_description_pdf,
                "is_variant_label": True,
                "is_unit_serial": True,
                "serial_batch": self.name,
                "unit_serial": serial.code,
                "product_code": serial.code,
                "barcode_src": product.ddsl_get_label_barcode_src(serial.code),
            })
        # Shared-lot products use the same printed code for every physical
        # label. This preserves the requested number of labels without
        # exhausting the unique serial sequence.
        if self.shared_serial and payloads:
            copies = self.quantity if shared_quantity is None else int(shared_quantity)
            return payloads * copies
        return payloads

    def action_print_labels(self):
        self.ensure_one()
        self._ddic_check_warehouse_access(self.warehouse_id)
        action = self.env.ref(
            "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
        )
        return action.report_action(self, data={"labels": self._label_payloads()})

    def action_print_unloaded_labels(self):
        """Print only serials that have not created inventory yet.

        This is the safe reprint path for an increment on a previously
        validated batch: historical labels remain untouched and the operator
        receives only the new physical-unit labels.
        """
        self.ensure_one()
        self._ddic_check_warehouse_access(self.warehouse_id)
        serials = self.serial_ids.filtered(
            lambda serial: serial.active and not serial.inventory_loaded
        )
        if not serials:
            raise UserError(_("No hay labels nuevos pendientes de cargar."))
        action = self.env.ref(
            "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
        )
        return action.report_action(
            self, data={"labels": self._label_payloads(serials=serials)}
        )

    def _ddic_add_serial_units(self, quantity, codes=None, source_receipt=None, product=None):
        """Append protected unit serials without rewriting historical units."""
        self.ensure_one()
        self._ddic_check_warehouse_access(self.warehouse_id)
        if self.state != "generated":
            raise UserError(_("Solo puede agregar unidades a un lote generado."))
        quantity = int(quantity or 0)
        if quantity <= 0 or quantity > 500:
            raise ValidationError(_("La cantidad debe estar entre 1 y 500."))
        if codes and len(codes) != quantity:
            raise ValidationError(_("La cantidad de códigos no coincide con la cantidad nueva."))
        self.env.cr.execute(
            "SELECT id FROM inventory_serial_label_batch WHERE id=%s FOR UPDATE",
            (self.id,),
        )
        self.invalidate_recordset()
        product = product or self.product_id
        if not product:
            raise ValidationError(_("Indique el ITEM que recibirá el lote mixto."))
        if not self.is_mixed_batch and product != self.product_id:
            raise ValidationError(_("El ITEM no corresponde al lote seleccionado."))
        if self.shared_serial and not self.is_mixed_batch:
            if codes:
                current_code = self.serial_ids.filtered("active")[:1].code
                if any((code or "").strip() != current_code for code in codes):
                    raise ValidationError(_(
                        "Este producto usa un serial compartido. Los nuevos labels deben conservar el codigo %s."
                    ) % current_code)
            super(InventorySerialLabelBatch, self).write({
                "quantity": self.quantity + quantity,
            })
            self.message_post(body=Markup(
                "<strong>Nuevas unidades del lote compartido</strong><p>Se agregaron %(qty)s unidades conservando el serial %(code)s mediante %(source)s.</p>"
            ) % {
                "qty": quantity,
                "code": escape(self.serial_ids.filtered("active")[:1].code),
                "source": escape(source_receipt.display_name if source_receipt else _("operación autorizada")),
            })
            return self.serial_ids.filtered("active")[:1]
        values = []
        for index in range(quantity):
            code = codes[index] if codes else self.env["ir.sequence"].next_by_code(
                "inventory.unit.serial"
            )
            code = (code or "").strip()
            if not code:
                raise UserError(_("No se pudo obtener un código de label."))
            if self.env["inventory.unit.serial"].sudo().search_count([("code", "=", code)]):
                raise UserError(_("El label %s ya existe.") % code)
            values.append({
                "code": code,
                "batch_id": self.id,
                "product_id": product.id,
                "current_warehouse_id": self.warehouse_id.id,
                "current_batch_id": self.id,
                "source_receipt_id": source_receipt.id if source_receipt else False,
            })
        serials = self.env["inventory.unit.serial"].sudo().create(values)
        batch_values = {"quantity": self.quantity + quantity}
        if self.is_mixed_batch and not self.product_id:
            batch_values["product_id"] = product.id
        super(InventorySerialLabelBatch, self).write(batch_values)
        self.message_post(body=Markup(
            "<strong>Nuevas unidades etiquetadas</strong><p>Se agregaron %(qty)s labels mediante %(source)s: %(codes)s.</p>"
        ) % {
            "qty": quantity,
            "source": escape(source_receipt.display_name if source_receipt else _("operación autorizada")),
            "codes": escape(", ".join(serials.mapped("code"))),
        })
        return serials


class InventoryUnitSerial(models.Model):
    _name = "inventory.unit.serial"
    _description = "Inventory Unit Serial"
    _order = "id desc"

    code = fields.Char(required=True, readonly=True, index=True)
    active = fields.Boolean(default=True)
    batch_id = fields.Many2one(
        "inventory.serial.label.batch", required=True, ondelete="restrict", index=True
    )
    campaign_id = fields.Many2one(related="batch_id.campaign_id", store=True, index=True)
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    product_id = fields.Many2one("product.product", required=True, readonly=True, index=True)
    inventory_loaded = fields.Boolean(readonly=True, copy=False)
    loaded_session_id = fields.Many2one(
        "inventory.count.session", readonly=True, copy=False, ondelete="restrict"
    )
    claim_ids = fields.One2many(
        "inventory.serial.claim", "serial_id", string="Lecturas", readonly=True
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "El serial de unidad debe ser único."),
    ]


class InventorySerialClaim(models.Model):
    _name = "inventory.serial.claim"
    _description = "Inventory Serial Count Claim"
    _order = "scan_at desc, id desc"

    campaign_id = fields.Many2one(
        "inventory.serial.campaign", required=True, ondelete="restrict", index=True
    )
    serial_id = fields.Many2one(
        "inventory.unit.serial", required=True, ondelete="restrict", index=True
    )
    session_id = fields.Many2one(
        "inventory.count.session", required=True, ondelete="cascade", index=True
    )
    location_id = fields.Many2one(related="session_id.location_id", store=True)
    company_id = fields.Many2one(related="campaign_id.company_id", store=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    scan_at = fields.Datetime(required=True, default=fields.Datetime.now)
    counted_qty = fields.Float(
        string="Cantidad contada", default=1.0, required=True,
        digits="Product Unit of Measure",
    )
    scan_count = fields.Integer(string="Lecturas", default=1, required=True)
    last_scan_at = fields.Datetime(string="Ultima lectura", default=fields.Datetime.now)
    state = fields.Selection(
        [("counted", "Contado"), ("applied", "Aplicado")],
        default="counted", required=True,
    )

    _sql_constraints = [
        (
            "campaign_serial_unique",
            "unique(campaign_id, serial_id)",
            "Esta unidad ya fue contada en la campaña.",
        ),
    ]
