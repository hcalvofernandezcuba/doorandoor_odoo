from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare


class StockLocation(models.Model):
    _inherit = "stock.location"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self.env.context.get("ddic_authorized_location_search"):
            allowed = self.env["inventory.count.session"]._ddic_allowed_locations()
            domain = expression.AND([domain, [("id", "in", allowed.ids)]])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
        )


class InventoryCountSession(models.Model):
    _name = "inventory.count.session"
    _description = "Inventory Count Session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False)
    date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, required=True, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    location_id = fields.Many2one(
        "stock.location", required=True, tracking=True,
        context={"ddic_authorized_location_search": True},
    )
    allowed_location_ids = fields.Many2many(
        "stock.location",
        compute="_compute_allowed_location_ids",
        string="Ubicaciones autorizadas",
    )
    count_mode = fields.Selection(
        [
            ("additive", "Carga inicial por lote"),
            ("absolute", "Conteo físico total"),
        ],
        string="Modo de conteo",
        default="additive",
        required=True,
        tracking=True,
        help=(
            "El conteo total sustituye la existencia por la cantidad contada. "
            "La carga por lote suma lo contado a la existencia capturada al iniciar."
        ),
    )
    load_reference = fields.Char(
        string="Referencia del lote",
        copy=False,
        tracking=True,
        help="Identificador único del lote físico para evitar cargas repetidas.",
    )
    serial_campaign_id = fields.Many2one(
        "inventory.serial.campaign",
        string="Campaña de seriales",
        tracking=True,
        domain="[('state', '=', 'open'), ('company_id', '=', company_id)]",
        help="Si se selecciona, esta sesión admite únicamente seriales únicos impresos.",
    )
    serial_batch_id = fields.Many2one(
        "inventory.serial.label.batch",
        string="Lote",
        tracking=True,
        help="Área o lote físico cuyos labels serán controlados en esta sesión.",
    )
    allowed_serial_batch_ids = fields.Many2many(
        "inventory.serial.label.batch",
        compute="_compute_allowed_serial_batch_ids",
        string="Lotes disponibles",
    )
    serial_claim_ids = fields.One2many(
        "inventory.serial.claim", "session_id", string="Seriales contados", copy=False
    )
    state = fields.Selection(
        [("draft", "Draft"), ("counting", "Counting"),
         ("review", "Review"), ("done", "Validated"), ("cancel", "Cancelled")],
        default="draft", required=True, tracking=True,
    )
    line_ids = fields.One2many(
        "inventory.count.line", "session_id", copy=False, string="Variant Counts"
    )
    item_line_ids = fields.One2many(
        "inventory.count.item.line", "session_id", copy=False, string="Item Counts"
    )
    barcode_input = fields.Char(
        string="Scan Barcode", copy=False,
        help="Scan an item barcode and press Enter, or type it manually."
    )
    scan_qty = fields.Float(default=1.0, digits="Product Unit of Measure")
    note = fields.Text()
    line_count = fields.Integer(compute="_compute_totals")
    difference_count = fields.Integer(compute="_compute_totals")
    counted_line_ids = fields.Many2many(
        "inventory.count.line",
        string="Products Counted in This Session",
        compute="_compute_counted_lines",
    )
    last_scanned_product_id = fields.Many2one(
        "product.product", string="Last Counted Product", readonly=True, copy=False
    )
    last_scanned_barcode = fields.Char(
        string="Last Barcode", readonly=True, copy=False
    )
    last_scanned_qty = fields.Float(
        string="Accumulated Count", readonly=True, copy=False,
        digits="Product Unit of Measure",
    )
    last_scan_at = fields.Datetime(
        string="Last Scan At", readonly=True, copy=False
    )
    serial_expected_count = fields.Integer(
        string="Seriales esperados", compute="_compute_serial_audit_totals"
    )
    serial_counted_count = fields.Integer(
        string="Seriales contados", compute="_compute_serial_audit_totals"
    )
    serial_pending_count = fields.Integer(
        string="Seriales pendientes", compute="_compute_serial_audit_totals"
    )

    @api.model
    def _ddic_has_global_warehouse_access(self):
        user = self.env.user
        return (
            user.has_group("base.group_system")
            or user.has_group(
                "doorandoor_process_control.group_ddpc_manager"
            )
            or user.has_group(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
        )

    @api.model
    def _ddic_allowed_locations(self):
        user = self.env.user
        warehouses = user.ddpc_warehouse_ids
        if not warehouses and self._ddic_has_global_warehouse_access():
            warehouses = self.env["stock.warehouse"].sudo().search([
                ("company_id", "in", self.env.companies.ids),
            ])
        warehouses = warehouses.filtered(
            lambda warehouse: warehouse.active
            and warehouse.company_id in self.env.companies
        )
        return warehouses.with_context(
            ddic_authorized_location_search=False
        ).mapped("lot_stock_id")

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_allowed_location_ids(self):
        allowed_locations = self._ddic_allowed_locations()
        for session in self:
            session.allowed_location_ids = allowed_locations

    @api.depends("serial_campaign_id", "location_id", "company_id")
    def _compute_allowed_serial_batch_ids(self):
        Batch = self.env["inventory.serial.label.batch"]
        for session in self:
            warehouse = session.location_id.warehouse_id
            if not session.serial_campaign_id or not warehouse:
                session.allowed_serial_batch_ids = Batch
                continue
            session.allowed_serial_batch_ids = Batch.search([
                ("campaign_id", "=", session.serial_campaign_id.id),
                ("warehouse_id", "=", warehouse.id),
                ("state", "=", "generated"),
            ])

    @api.onchange("serial_campaign_id", "location_id")
    def _onchange_serial_scope(self):
        for session in self:
            if session.serial_batch_id not in session.allowed_serial_batch_ids:
                session.serial_batch_id = False

    @api.model
    def _ddic_check_location_access(self, location):
        allowed = self.env.user.ddpc_warehouse_ids
        if not allowed and self._ddic_has_global_warehouse_access():
            return True
        allowed_locations = self._ddic_allowed_locations()
        if not allowed_locations:
            raise AccessError(_(
                "Su usuario no tiene almacenes autorizados. Solicite a Gerencia "
                "que configure sus almacenes operativos."
            ))
        if location not in allowed_locations:
            raise AccessError(_(
                "La ubicación %(location)s no pertenece a sus almacenes autorizados: "
                "%(warehouses)s."
            ) % {
                "location": location.display_name,
                "warehouses": ", ".join(allowed.mapped("display_name")) or _("Todos"),
            })
        return True

    @api.constrains("count_mode", "load_reference", "company_id", "location_id")
    def _check_additive_load_reference(self):
        for session in self:
            if session.count_mode != "additive":
                continue
            reference = (session.load_reference or "").strip()
            if not reference:
                raise ValidationError(_(
                    "Indique una referencia única para el lote antes de iniciar la carga."
                ))
            duplicates = self.search([
                ("id", "!=", session.id),
                ("company_id", "=", session.company_id.id),
                ("location_id", "=", session.location_id.id),
                ("count_mode", "=", "additive"),
                ("load_reference", "=ilike", reference),
                ("state", "!=", "cancel"),
            ])
            # A finished session remains part of the audit trail after its
            # physical position is emptied.  Once the linked serialized batch
            # is explicitly marked as vacated, that historic session must no
            # longer reserve the physical reference.  References without a
            # serialized batch and references linked to an active batch keep
            # their original uniqueness protection.
            blocking_duplicates = duplicates.filtered(
                lambda previous: not previous._ddic_is_released_reference_history()
            )
            if blocking_duplicates:
                raise ValidationError(_(
                    "La referencia de lote %(reference)s ya fue utilizada en esta ubicación."
                ) % {"reference": reference})

    def _ddic_is_released_reference_history(self):
        """Return whether this session is history and no longer occupies its lot.

        The session and its original labels remain untouched.  Reuse is allowed
        only after the linked batch reached an explicit terminal/released state
        and no active serial currently points to that batch as its location.
        """
        self.ensure_one()
        batch = self.serial_batch_id
        return bool(
            batch
            and batch.state in ("cancel", "vacated")
            and not batch.current_serial_ids.filtered("active")
        )

    @api.depends("line_ids", "line_ids.difference_qty")
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.difference_count = len(rec.line_ids.filtered(
                lambda line: not fields.Float.is_zero(
                    line.difference_qty,
                    precision_rounding=line.uom_id.rounding,
                )
            ))

    @api.depends("line_ids.is_counted", "line_ids.counted_qty", "line_ids.write_date")
    def _compute_counted_lines(self):
        for rec in self:
            rec.counted_line_ids = rec.line_ids.filtered("is_counted").sorted(
                key=lambda line: (line.write_date or line.create_date, line.id),
                reverse=True,
            )

    @api.depends(
        "serial_campaign_id",
        "serial_batch_id",
        "location_id",
        "serial_claim_ids",
        "serial_campaign_id.batch_ids.serial_ids.active",
        "serial_batch_id.serial_ids.active",
    )
    def _compute_serial_audit_totals(self):
        for session in self:
            if not session.serial_campaign_id or not session.location_id:
                session.serial_expected_count = 0
                session.serial_counted_count = 0
                session.serial_pending_count = 0
                continue
            audit = session._serial_audit_report_data()
            session.serial_expected_count = audit["expected"]
            session.serial_counted_count = audit["counted"]
            session.serial_pending_count = audit["pending"]

    def _serial_audit_report_data(self):
        self.ensure_one()
        if not self.serial_campaign_id:
            return {
                "campaign": "", "warehouse": "", "session": self.display_name,
                "expected": 0, "counted": 0, "counted_other": 0,
                "pending": 0, "rows": [],
            }
        return self.serial_campaign_id._serial_audit_payload(
            session=self,
            warehouse=self.location_id.warehouse_id,
            batch=self.serial_batch_id,
        )

    def action_print_serial_audit(self):
        self.ensure_one()
        if not self.serial_campaign_id:
            raise UserError(_("Seleccione una campaña de seriales para generar el reporte."))
        return self.env.ref(
            "doorandoor_inventory_variant_count.action_report_serial_session_audit"
        ).report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            location = self.env["stock.location"].browse(vals.get("location_id")).exists()
            if location:
                self._ddic_check_location_access(location)
            if vals.get("load_reference"):
                vals["load_reference"] = vals["load_reference"].strip().upper()
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.count.session"
                ) or _("New")
        return super().create(vals_list)

    def write(self, vals):
        protected = {
            "count_mode", "load_reference", "location_id", "company_id",
            "serial_campaign_id", "serial_batch_id",
        }
        if protected.intersection(vals) and any(session.state != "draft" for session in self):
            raise UserError(_(
                "El modo, la referencia, la empresa y la ubicación no pueden cambiarse "
                "después de iniciar el conteo."
            ))
        if vals.get("load_reference"):
            vals["load_reference"] = vals["load_reference"].strip().upper()
        if vals.get("location_id"):
            location = self.env["stock.location"].browse(vals["location_id"]).exists()
            if location:
                self._ddic_check_location_access(location)
        return super().write(vals)

    def action_start(self):
        for session in self:
            session._ddic_check_location_access(session.location_id)
            if session.state != "draft":
                continue
            if session.serial_campaign_id and not session.serial_batch_id:
                raise UserError(_(
                    "Seleccione el lote que se contará dentro de la campaña."
                ))
            if session.serial_batch_id:
                warehouse = session.location_id.warehouse_id
                if (
                    session.serial_batch_id.campaign_id != session.serial_campaign_id
                    or session.serial_batch_id.warehouse_id != warehouse
                    or session.serial_batch_id.state != "generated"
                ):
                    raise UserError(_(
                        "El lote seleccionado no pertenece a la campaña y al almacén "
                        "de esta sesión, o todavía no ha sido generado."
                    ))
            session._check_additive_load_reference()
            session._load_snapshot()
            session.state = "counting"
        return True

    def _load_snapshot(self):
        self.ensure_one()
        if self.line_ids:
            raise UserError(_("This session already contains count lines."))
        Quant = self.env["stock.quant"]
        quants = Quant.search([
            ("location_id", "=", self.location_id.id),
            ("product_id.is_storable", "=", True),
        ])
        quantities = {}
        for quant in quants:
            key = (quant.product_id, quant.lot_id, quant.package_id, quant.owner_id)
            quantities[key] = quantities.get(key, 0.0) + quant.quantity
        line_commands = []
        for (product, lot, package, owner), qty in quantities.items():
            line_commands.append((0, 0, {
                "product_id": product.id,
                "lot_id": lot.id,
                "package_id": package.id,
                "owner_id": owner.id,
                "expected_qty": qty,
            }))
        self.line_ids = line_commands
        item_commands = []
        for line in self.line_ids:
            for item in line.product_id.count_item_ids.filtered("active"):
                item_commands.append((0, 0, {
                    "variant_line_id": line.id,
                    "item_id": item.id,
                    "expected_qty": (
                        0.0 if self.count_mode == "additive"
                        else line.expected_qty * item.qty_per_product
                    ),
                }))
        self.item_line_ids = item_commands

    def action_open_configured_product(self):
        self.ensure_one()
        if self.state != "counting":
            raise UserError(_("Configured products can only be added while counting."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Add Configured Product"),
            "res_model": "inventory.count.variant.selector",
            "view_mode": "form",
            "view_id": self.env.ref(
                "doorandoor_inventory_variant_count.view_inventory_count_variant_selector_form"
            ).id,
            "target": "new",
            "context": {"default_session_id": self.id},
        }

    def action_scan(self, scanned_barcode=None):
        self.ensure_one()
        self._ddic_check_location_access(self.location_id)
        if self.state != "counting":
            raise UserError(_("Barcodes can only be recorded while counting."))
        # Mobile camera widgets send the decoded value directly. This avoids a
        # client-side race where the button RPC could run before barcode_input
        # had been persisted on the session. The stored field remains supported
        # for manual entry and conventional USB/Bluetooth scanners.
        barcode = (scanned_barcode or self.barcode_input or "").strip()
        if not barcode:
            raise ValidationError(_("Scan or enter a barcode first."))
        scan_qty = self.scan_qty or 1.0
        if scan_qty <= 0:
            raise ValidationError(_("The scan quantity must be greater than zero."))
        product = self.env["product.product"].search([
            ("barcode", "=", barcode), ("active", "=", True)
        ], limit=1)
        item = self.env["product.count.item"].search([
            ("barcode", "=", barcode), ("active", "=", True)
        ], limit=1)
        unit_serial = self.env["inventory.unit.serial"].search([
            ("code", "=", barcode), ("active", "=", True)
        ], limit=1)
        if unit_serial:
            if not self.serial_campaign_id:
                raise UserError(_(
                    "El código %(code)s es un serial único. Seleccione su campaña "
                    "en la sesión antes de contarlo."
                ) % {"code": barcode})
            if unit_serial.campaign_id != self.serial_campaign_id:
                raise UserError(_(
                    "El serial %(code)s pertenece a la campaña %(campaign)s."
                ) % {
                    "code": barcode,
                    "campaign": unit_serial.campaign_id.display_name,
                })
            if self.serial_batch_id and unit_serial.batch_id != self.serial_batch_id:
                raise UserError(_(
                    "El serial %(code)s pertenece al lote %(serial_batch)s, no al "
                    "lote seleccionado (%(session_batch)s)."
                ) % {
                    "code": barcode,
                    "serial_batch": unit_serial.batch_id.display_name,
                    "session_batch": self.serial_batch_id.display_name,
                })
            session_warehouse = self.location_id.warehouse_id
            if session_warehouse and unit_serial.batch_id.warehouse_id != session_warehouse:
                raise UserError(_(
                    "El serial %(code)s fue emitido para %(serial_warehouse)s, no para "
                    "el almacén de esta sesión (%(session_warehouse)s)."
                ) % {
                    "code": barcode,
                    "serial_warehouse": unit_serial.batch_id.warehouse_id.display_name,
                    "session_warehouse": session_warehouse.display_name,
                })
            if self.count_mode == "additive" and unit_serial.inventory_loaded:
                raise UserError(_(
                    "El serial %(code)s ya creó inventario en la sesión %(session)s."
                ) % {
                    "code": barcode,
                    "session": unit_serial.loaded_session_id.display_name,
                })
            previous = self.env["inventory.serial.claim"].search([
                ("campaign_id", "=", self.serial_campaign_id.id),
                ("serial_id", "=", unit_serial.id),
            ], limit=1)
            shared_serial = unit_serial.product_id.product_tmpl_id.ddic_shared_lot_serial
            if previous and (not shared_serial or previous.session_id != self):
                raise UserError(_(
                    "El serial %(code)s ya fue contado en %(session)s, ubicación "
                    "%(location)s, por %(user)s. No se incrementó el inventario."
                ) % {
                    "code": barcode,
                    "session": previous.session_id.display_name,
                    "location": previous.location_id.display_name,
                    "user": previous.user_id.display_name,
                })
            lines = self.line_ids.filtered(
                lambda line: line.product_id == unit_serial.product_id
                and not line.lot_id and not line.package_id and not line.owner_id
            )
            if not lines:
                lines = self.env["inventory.count.line"].create({
                    "session_id": self.id,
                    "product_id": unit_serial.product_id.id,
                    "expected_qty": 0.0,
                })
            if len(lines) != 1:
                raise UserError(_(
                    "La variante del serial aparece en varias líneas con trazabilidad."
                ))
            line = lines.ensure_one()
            if previous:
                previous.write({
                    "counted_qty": previous.counted_qty + scan_qty,
                    "scan_count": previous.scan_count + 1,
                    "last_scan_at": fields.Datetime.now(),
                })
            else:
                self.env["inventory.serial.claim"].create({
                    "campaign_id": self.serial_campaign_id.id,
                    "serial_id": unit_serial.id,
                    "session_id": self.id,
                    "counted_qty": scan_qty,
                    "scan_count": 1,
                    "last_scan_at": fields.Datetime.now(),
                })
            line.counted_qty += scan_qty
            line.is_counted = True
            result_product = unit_serial.product_id
            result_qty = line.counted_qty
            self.write({
                "barcode_input": False,
                "last_scanned_product_id": result_product.id,
                "last_scanned_barcode": barcode,
                "last_scanned_qty": result_qty,
                "last_scan_at": fields.Datetime.now(),
            })
            return {
                "product_name": result_product.display_name,
                "barcode": barcode,
                "counted_qty": result_qty,
            }
        if self.serial_campaign_id:
            raise UserError(_(
                "Esta sesión exige seriales únicos de la campaña. El código %s no es "
                "un serial válido."
            ) % barcode)
        lots = self.env["stock.lot"].search([
            ("name", "=", barcode),
            ("product_id.active", "=", True),
            ("product_id.tracking", "=", "lot"),
            ("company_id", "in", [False, self.company_id.id]),
        ])
        if len(lots) > 1:
            raise UserError(_(
                "El código de lote %(code)s corresponde a más de un producto. "
                "Corrija la referencia duplicada antes de continuar."
            ) % {"code": barcode})
        lot = lots[:1]
        if lot and product and lot.product_id != product:
            raise UserError(_(
                "El código %(code)s está asignado a un producto y también al lote "
                "de otro producto. Corrija el código duplicado antes de continuar."
            ) % {"code": barcode})
        if lot:
            product = lot.product_id
            lines = self.line_ids.filtered(
                lambda line: line.product_id == product
                and line.lot_id == lot
                and not line.package_id
                and not line.owner_id
            )
            if not lines:
                lines = self.env["inventory.count.line"].create({
                    "session_id": self.id,
                    "product_id": product.id,
                    "lot_id": lot.id,
                    "expected_qty": 0.0,
                })
            if len(lines) != 1:
                raise UserError(_(
                    "El lote %(lot)s aparece en varias líneas con paquete o propietario. "
                    "Registre la cantidad en el detalle correcto para conservar la trazabilidad."
                ) % {"lot": lot.display_name})
            line = lines.ensure_one()
            if line.item_line_ids.filtered("is_counted"):
                raise UserError(_(
                    "Ya existen componentes contados para %s. No mezcle conteo directo "
                    "por lote con conteo de componentes."
                ) % product.display_name)
            line.counted_qty += scan_qty
            line.is_counted = True
            result_product = product
            result_qty = line.counted_qty
            self.write({
                "barcode_input": False,
                "last_scanned_product_id": result_product.id,
                "last_scanned_barcode": barcode,
                "last_scanned_qty": result_qty,
                "last_scan_at": fields.Datetime.now(),
            })
            return {
                "product_name": result_product.display_name,
                "barcode": barcode,
                "lot_name": lot.name,
                "counted_qty": result_qty,
            }
        if product and item:
            raise UserError(_(
                "Barcode %s is assigned both to a product variant and to a count item. "
                "Correct the duplicate before continuing."
            ) % barcode)
        if product:
            lines = self.line_ids.filtered(lambda line: line.product_id == product)
            if not lines:
                # A physical count may reveal stock that Odoo expected to be
                # zero. Add that variant to this location's session instead of
                # rejecting a valid product label.
                lines = self.env["inventory.count.line"].create({
                    "session_id": self.id,
                    "product_id": product.id,
                    "expected_qty": 0.0,
                })
            if len(lines) > 1:
                raise UserError(_(
                    "The product variant occurs on multiple stock-detail lines. Enter "
                    "the quantity on the appropriate line to preserve lot/package/owner "
                    "traceability."
                ))
            line = lines[0]
            if line.item_line_ids.filtered("is_counted"):
                raise UserError(_(
                    "Some count items for %s were already recorded. Do not mix direct "
                    "variant scans with component counts on the same line."
                ) % product.display_name)
            line.counted_qty += scan_qty
            line.is_counted = True
            result_product = product
            result_qty = line.counted_qty
        elif item:
            lines = self.item_line_ids.filtered(lambda line: line.item_id == item)
            if not lines:
                raise UserError(_("This item is not part of the current count session."))
            if len(lines) > 1:
                raise UserError(_(
                    "The barcode occurs on multiple stock-detail lines. Enter the quantity "
                    "on the appropriate line to preserve lot/package/owner traceability."
                ))
            if lines.variant_line_id.is_counted:
                raise UserError(_(
                    "The product variant %s was already counted directly. Do not mix "
                    "component counts with direct variant scans on the same line."
                ) % lines.product_id.display_name)
            lines.counted_qty += scan_qty
            lines.is_counted = True
            result_product = lines.product_id
            result_qty = lines.counted_qty
        else:
            raise UserError(_(
                "Barcode %s is not assigned to an active product variant or count "
                "item. Print the variant label again so its inventory barcode is "
                "generated and stored on the product."
            ) % barcode)
        self.write({
            "barcode_input": False,
            "last_scanned_product_id": result_product.id,
            "last_scanned_barcode": barcode,
            "last_scanned_qty": result_qty,
            "last_scan_at": fields.Datetime.now(),
        })
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_review(self):
        for rec in self:
            rec._ddic_check_location_access(rec.location_id)
            if rec.state != "counting":
                continue
            started_lines = rec.line_ids.filtered(
                lambda line: line.is_counted or any(line.item_line_ids.mapped("is_counted"))
            )
            if not started_lines:
                raise UserError(_("Count at least one product variant before review."))
            if rec.serial_campaign_id and rec.serial_pending_count and not (rec.note or "").strip():
                raise UserError(_(
                    "Quedan %(pending)s de %(expected)s seriales emitidos sin contar. "
                    "Imprima 'Control de seriales', investigue los pendientes y escriba "
                    "una observación antes de enviar a revisión."
                ) % {
                    "pending": rec.serial_pending_count,
                    "expected": rec.serial_expected_count,
                })
            for line in started_lines.filtered(lambda count: not count.is_counted):
                missing_items = line.item_line_ids.filtered(lambda item: not item.is_counted)
                if missing_items:
                    raise UserError(_(
                        "Complete all count items for %s before review. Missing: %s."
                    ) % (
                        line.product_id.display_name,
                        ", ".join(missing_items.mapped("item_id.display_name")),
                    ))
            rec.state = "review"
            rec._notify_inventory_reviewers()
        return True

    def _notify_inventory_reviewers(self):
        notification_group = self.env.ref(
            "doorandoor_inventory_variant_count.group_inventory_count_review_notifier",
            raise_if_not_found=False,
        )
        if not notification_group:
            return
        partners = notification_group.sudo().users.filtered("active").partner_id
        if not partners:
            return
        for rec in self:
            rec.message_post(
                body=_(
                    "El conteo %(session)s fue enviado a revisión por %(user)s. "
                    "Ubicación: %(location)s. Seriales emitidos: %(expected)s; "
                    "contados: %(counted)s; pendientes: %(pending)s."
                ) % {
                    "session": rec.display_name,
                    "user": self.env.user.display_name,
                    "location": rec.location_id.complete_name,
                    "expected": rec.serial_expected_count,
                    "counted": rec.serial_counted_count,
                    "pending": rec.serial_pending_count,
                },
                partner_ids=partners.ids,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def action_back_to_counting(self):
        self.filtered(lambda rec: rec.state == "review").write({"state": "counting"})
        return True

    def action_validate(self):
        self.ensure_one()
        if not (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
        ):
            raise AccessError(_(
                "Solo Administradores de conteos o Administradores/Ajustes "
                "pueden validar y aplicar ajustes de inventario."
            ))
        self._ddic_check_location_access(self.location_id)
        if self.state != "review":
            raise UserError(_("The session must be in review before validation."))
        self._derive_variant_counts()
        counted_lines = self.line_ids.filtered("is_counted")
        if not counted_lines:
            raise UserError(_("There are no counted product variants to validate."))
        if self.serial_campaign_id:
            for line in counted_lines:
                line_claims = self.serial_claim_ids.filtered(
                    lambda claim: claim.serial_id.product_id == line.product_id
                )
                # A reopened additive session retains its historic applied
                # claims for audit. Only the newly counted claims represent
                # the increment that will be added during this validation.
                if self.count_mode == "additive":
                    line_claims = line_claims.filtered(
                        lambda claim: claim.state == "counted"
                    )
                claim_count = sum(line_claims.mapped("counted_qty"))
                if float_compare(
                    claim_count,
                    line.counted_qty,
                    precision_rounding=line.uom_id.rounding,
                ):
                    raise UserError(_(
                        "La cantidad de %(product)s no coincide con sus seriales únicos: "
                        "%(qty)s contado(s), %(serials)s serial(es)."
                    ) % {
                        "product": line.product_id.display_name,
                        "qty": line.counted_qty,
                        "serials": claim_count,
                    })
        Quant = self.env["stock.quant"]
        for line in counted_lines:
            # Un conteo físico solo ajusta cantidades. Los precios del catálogo
            # y de sus variantes son datos maestros y nunca deben alterarse al
            # contar, revisar o validar inventario, incluso si una línea
            # histórica conserva valores de costo/precio.
            quant = Quant.search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", self.location_id.id),
                ("lot_id", "=", line.lot_id.id),
                ("package_id", "=", line.package_id.id),
                ("owner_id", "=", line.owner_id.id),
            ], limit=1)
            current_qty = quant.quantity if quant else 0.0
            target_qty = (
                current_qty + line.counted_qty
                if self.count_mode == "additive"
                else line.counted_qty
            )
            if not quant:
                quant = Quant.create({
                    "product_id": line.product_id.id,
                    "location_id": self.location_id.id,
                    "lot_id": line.lot_id.id,
                    "package_id": line.package_id.id,
                    "owner_id": line.owner_id.id,
                    "inventory_quantity": target_qty,
                })
            else:
                quant.inventory_quantity = target_qty
            inventory_name = self.name
            if self.count_mode == "additive":
                inventory_name = "%s - Lote %s" % (self.name, self.load_reference)
            # The custom unit label is the traceability source for these
            # initial loads. Odoo 18 otherwise returns the native
            # ``stock.track.confirmation`` wizard for lot-tracked products;
            # ignoring that action would close the session while leaving the
            # quant unapplied. This validated workflow has already reconciled
            # the custom serial claims, so apply the inventory adjustment in
            # the same transaction.
            quant.with_context(
                inventory_name=inventory_name,
                set_inventory_quantity_auto_apply=True,
            ).action_apply_inventory()
        if self.serial_campaign_id:
            self.serial_claim_ids.write({"state": "applied"})
            if self.count_mode == "additive":
                self.serial_claim_ids.serial_id.sudo().write({
                    "inventory_loaded": True,
                    "loaded_session_id": self.id,
                })
        self.state = "done"
        if self.count_mode == "additive":
            message = _(
                "Carga inicial acumulativa aplicada a %(count)s variante(s) desde el "
                "lote %(reference)s. Las cantidades contadas se sumaron a la "
                "existencia vigente al validar."
            ) % {"count": len(counted_lines), "reference": self.load_reference}
        else:
            message = _(
                "Inventory adjustment applied to %s counted variant(s) from session %s. "
                "Uncounted variants were left unchanged."
            ) % (len(counted_lines), self.name)
        self.message_post(body=message)
        return True

    def _derive_variant_counts(self):
        for line in self.line_ids:
            if line.is_counted:
                continue
            item_lines = line.item_line_ids
            if not item_lines:
                continue
            counted_items = item_lines.filtered("is_counted")
            if not counted_items:
                # This variant was not part of the current partial count. It
                # remains untouched in stock.
                continue
            missing_items = item_lines - counted_items
            if missing_items:
                raise UserError(_(
                    "Complete all count items for %s before validation. Missing: %s."
                ) % (
                    line.product_id.display_name,
                    ", ".join(missing_items.mapped("item_id.display_name")),
                ))
            derived = [
                item_line.counted_qty / item_line.item_id.qty_per_product
                for item_line in item_lines
            ]
            rounded = [line.uom_id._compute_quantity(qty, line.uom_id) for qty in derived]
            if max(rounded) - min(rounded) > line.uom_id.rounding:
                raise UserError(_(
                    "Item counts for %s are inconsistent. Their quantities per product "
                    "produce different variant totals: %s"
                ) % (line.product_id.display_name, ", ".join(str(qty) for qty in rounded)))
            line.counted_qty = min(derived)
            line.is_counted = True

    def action_cancel(self):
        cancellable = self.filtered(lambda rec: rec.state != "done")
        cancellable.serial_claim_ids.filtered(lambda claim: claim.state == "counted").unlink()
        cancellable.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for rec in self.filtered(lambda r: r.state == "cancel"):
            rec.write({"state": "draft", "line_ids": [(5, 0, 0)],
                       "item_line_ids": [(5, 0, 0)]})
        return True


class InventoryCountLine(models.Model):
    _name = "inventory.count.line"
    _description = "Inventory Count Variant Line"
    _order = "is_counted desc, write_date desc, product_id, id"

    session_id = fields.Many2one(
        "inventory.count.session", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="session_id.company_id", store=True)
    state = fields.Selection(related="session_id.state", store=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    barcode = fields.Char(related="product_id.barcode", string="Barcode")
    uom_id = fields.Many2one(related="product_id.uom_id")
    lot_id = fields.Many2one("stock.lot")
    package_id = fields.Many2one("stock.quant.package")
    owner_id = fields.Many2one("res.partner")
    expected_qty = fields.Float(readonly=True, digits="Product Unit of Measure")
    counted_qty = fields.Float(digits="Product Unit of Measure")
    is_counted = fields.Boolean(string="Counted")
    difference_qty = fields.Float(
        compute="_compute_difference", store=True, digits="Product Unit of Measure"
    )
    result_qty = fields.Float(
        string="Existencia resultante",
        compute="_compute_result_qty",
        store=True,
        digits="Product Unit of Measure",
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    cost_price = fields.Monetary(
        string="Unit Cost",
        currency_field="currency_id",
        groups="base.group_system",
    )
    sale_price = fields.Monetary(
        string="Final Sale Price",
        currency_field="currency_id",
        groups="base.group_system",
    )
    price_configured = fields.Boolean(string="Prices Configured", default=False)
    item_line_ids = fields.One2many(
        "inventory.count.item.line", "variant_line_id", string="Items"
    )

    @api.depends("expected_qty", "counted_qty", "is_counted", "session_id.count_mode")
    def _compute_difference(self):
        for line in self:
            if not line.is_counted:
                line.difference_qty = 0.0
            elif line.session_id.count_mode == "additive":
                line.difference_qty = line.counted_qty
            else:
                line.difference_qty = line.counted_qty - line.expected_qty

    @api.depends(
        "expected_qty", "counted_qty", "is_counted", "session_id.count_mode"
    )
    def _compute_result_qty(self):
        for line in self:
            if not line.is_counted:
                line.result_qty = line.expected_qty
            elif line.session_id.count_mode == "additive":
                line.result_qty = line.expected_qty + line.counted_qty
            else:
                line.result_qty = line.counted_qty

    @api.onchange("cost_price", "sale_price")
    def _onchange_prices(self):
        self.price_configured = True


class InventoryCountItemLine(models.Model):
    _name = "inventory.count.item.line"
    _description = "Inventory Count Item Line"
    _order = "product_id, item_id, id"

    session_id = fields.Many2one(
        "inventory.count.session", required=True, ondelete="cascade", index=True
    )
    variant_line_id = fields.Many2one(
        "inventory.count.line", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="session_id.company_id", store=True)
    state = fields.Selection(related="session_id.state", store=True)
    product_id = fields.Many2one(related="variant_line_id.product_id", store=True)
    item_id = fields.Many2one("product.count.item", required=True, index=True)
    item_code = fields.Char(related="item_id.code", store=True)
    barcode = fields.Char(related="item_id.barcode", store=True)
    uom_id = fields.Many2one(related="item_id.uom_id")
    expected_qty = fields.Float(readonly=True, digits="Product Unit of Measure")
    counted_qty = fields.Float(digits="Product Unit of Measure")
    is_counted = fields.Boolean(string="Counted")
    difference_qty = fields.Float(
        compute="_compute_difference", store=True, digits="Product Unit of Measure"
    )

    @api.depends("expected_qty", "counted_qty", "is_counted")
    def _compute_difference(self):
        for line in self:
            line.difference_qty = (
                line.counted_qty - line.expected_qty if line.is_counted else 0.0
            )

    @api.onchange("counted_qty")
    def _onchange_counted_qty(self):
        self.is_counted = True
