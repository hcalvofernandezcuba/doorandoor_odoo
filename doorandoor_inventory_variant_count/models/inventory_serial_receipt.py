import base64

from datetime import date

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    ddic_is_predispatch = fields.Boolean(
        string="Ubicación de predespacho DoorAndDoor",
        help="Permite seleccionar esta ubicación para agrupar mercancía destinada a entregas.",
    )
    ddic_is_predispatch_root = fields.Boolean(
        string="Pasillo virtual de predespacho", copy=False,
    )
    ddic_predispatch_picking_id = fields.Many2one(
        "stock.picking", string="Documento de predespacho", readonly=True,
        copy=False, ondelete="restrict", index=True,
    )

    _sql_constraints = [
        ("ddic_predispatch_picking_unique", "unique(ddic_predispatch_picking_id)",
         "Cada documento solo puede tener un área de predespacho."),
    ]


class InventoryUnitSerial(models.Model):
    _inherit = "inventory.unit.serial"

    current_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén actual", index=True, copy=False,
        help="Almacén físico confirmado más reciente del serial.",
    )
    current_batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote actual", index=True,
        copy=False, ondelete="restrict",
        help="Lote de almacenamiento actual; el lote de origen permanece en Lote impreso.",
    )
    current_location_id = fields.Many2one(
        "stock.location", string="Ubicación operativa actual", index=True,
        copy=False, ondelete="restrict",
    )
    source_receipt_id = fields.Many2one(
        "inventory.serial.receipt", string="Ingreso de origen", readonly=True,
        copy=False, ondelete="set null",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("current_warehouse_id") and vals.get("batch_id"):
                batch = self.env["inventory.serial.label.batch"].browse(vals["batch_id"])
                vals["current_warehouse_id"] = batch.warehouse_id.id
            if not vals.get("current_batch_id") and vals.get("batch_id"):
                vals["current_batch_id"] = vals["batch_id"]
            if not vals.get("current_location_id") and vals.get("current_warehouse_id"):
                warehouse = self.env["stock.warehouse"].browse(vals["current_warehouse_id"])
                vals["current_location_id"] = warehouse.lot_stock_id.id
        return super().create(vals_list)

    def init(self):
        self.env.cr.execute("""
            UPDATE inventory_unit_serial serial
               SET current_warehouse_id = batch.warehouse_id
              FROM inventory_serial_label_batch batch
             WHERE serial.batch_id = batch.id
               AND serial.current_warehouse_id IS NULL
        """)
        self.env.cr.execute("""
            UPDATE inventory_unit_serial serial
               SET current_location_id = warehouse.lot_stock_id
              FROM stock_warehouse warehouse
             WHERE serial.current_warehouse_id = warehouse.id
               AND serial.current_location_id IS NULL
        """)
        self.env.cr.execute("""
            UPDATE inventory_unit_serial
               SET current_batch_id = batch_id
             WHERE current_batch_id IS NULL
        """)


class InventorySerialReceipt(models.Model):
    _name = "inventory.serial.receipt"
    _description = "Ingreso serializado de mercancía"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False)
    operation_type = fields.Selection(
        [("internal", "Traslado interno"), ("supplier", "Recepción de proveedor")],
        required=True, tracking=True,
    )
    label_mode = fields.Selection(
        [("existing", "Labels existentes"), ("compatible", "Labels compatibles del proveedor"),
         ("generate", "Generar labels DoorAndDoor")],
        required=True, tracking=True,
    )
    destination_purpose = fields.Selection(
        [("storage", "Almacenar en lote"), ("delivery", "Traslado para entrega")],
        string="Destino operativo", required=True, default="storage", tracking=True,
    )
    source_group_key = fields.Char(readonly=True, copy=False, index=True)
    destination_reference = fields.Char(
        string="Documento destino", readonly=True, copy=False, tracking=True,
    )
    destination_picking_id = fields.Many2one(
        "stock.picking", string="Entrega asociada", readonly=True,
        copy=False, ondelete="restrict", tracking=True,
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Recepción / traslado", required=True,
        tracking=True, ondelete="restrict",
        domain="[('id', 'in', candidate_picking_ids)]",
    )
    company_id = fields.Many2one(related="picking_id.company_id", store=True)
    allowed_warehouse_ids = fields.Many2many(
        "stock.warehouse", compute="_compute_warehouse_options",
        string="Almacenes autorizados",
    )
    can_select_warehouse = fields.Boolean(compute="_compute_warehouse_options")
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén de destino", required=True,
        default=lambda self: self._default_warehouse(), tracking=True,
        context={"ddic_authorized_warehouse_search": True},
        domain="[('id', 'in', allowed_warehouse_ids)]",
    )
    candidate_picking_ids = fields.Many2many(
        "stock.picking", compute="_compute_candidate_pickings",
        string="Documentos del almacén",
    )
    source_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén de origen", compute="_compute_logistics",
        store=True, readonly=True,
    )
    predispatch_location_id = fields.Many2one(
        "stock.location", string="Ubicación de predespacho", tracking=True,
        domain="[('usage','=','internal'), ('warehouse_id','=',warehouse_id), ('ddic_is_predispatch','=',True)]",
    )
    product_id = fields.Many2one(
        "product.product", required=True, tracking=True,
        domain="[('is_storable', '=', True)]",
    )
    candidate_batch_ids = fields.Many2many(
        "inventory.serial.label.batch", compute="_compute_candidate_batches",
        string="Lotes compatibles",
    )
    recommended_batch_id = fields.Many2one(
        "inventory.serial.label.batch", compute="_compute_candidate_batches",
        string="Lote recomendado",
    )
    batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote de destino",
        tracking=True,
        domain="[('id', 'in', candidate_batch_ids)]",
    )
    batch_serial_ids = fields.One2many(
        related="batch_id.current_serial_ids", string="Contenido actual del lote", readonly=True,
    )
    quantity = fields.Integer(string="Cantidad nueva", required=True, default=1, tracking=True)
    document_quantity = fields.Float(
        string="Cantidad del documento", compute="_compute_document_quantity",
        digits="Product Unit of Measure",
    )
    scan_code = fields.Char(string="Escanear label", copy=False)
    serial_ids = fields.Many2many(
        "inventory.unit.serial", "inventory_serial_receipt_unit_rel",
        "receipt_id", "serial_id", string="Labels de esta operación", readonly=True,
        copy=False,
    )
    expected_serial_ids = fields.Many2many(
        "inventory.unit.serial", "inventory_serial_receipt_expected_rel",
        "receipt_id", "serial_id", string="Labels esperados desde despacho",
        readonly=True, copy=False,
    )
    missing_serial_ids = fields.Many2many(
        "inventory.unit.serial", compute="_compute_missing_serials",
        string="Labels faltantes",
    )
    missing_count = fields.Integer(compute="_compute_missing_serials")
    closure_note = fields.Text(string="Observación del faltante", copy=False)
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment", "inventory_serial_receipt_evidence_rel",
        "receipt_id", "attachment_id", string="Evidencias del faltante", copy=False,
    )
    transport_driver_name = fields.Char(
        string="Chofer", compute="_compute_transport_info",
    )
    transport_vehicle_name = fields.Char(
        string="Vehículo", compute="_compute_transport_info",
    )
    transport_license_plate = fields.Char(
        string="Matrícula", compute="_compute_transport_info",
    )
    transport_plan_names = fields.Char(
        string="Plan de carga", compute="_compute_transport_info",
    )
    damaged_serial_ids = fields.Many2many(
        "inventory.unit.serial", "inventory_serial_receipt_damage_rel",
        "receipt_id", "serial_id", string="Labels recibidos con daño", copy=False,
        domain="[('id', 'in', serial_ids)]",
    )
    damage_note = fields.Text(string="Descripción del daño", copy=False)
    damage_attachment_ids = fields.Many2many(
        "ir.attachment", "inventory_serial_receipt_damage_attachment_rel",
        "receipt_id", "attachment_id", string="Evidencias del daño", copy=False,
    )
    return_picking_id = fields.Many2one(
        "stock.picking", string="Devolución por daño", readonly=True,
        copy=False, ondelete="restrict",
    )
    scanned_count = fields.Integer(compute="_compute_scanned_count")
    state = fields.Selection(
        [("draft", "Borrador"), ("scanning", "Etiquetando / escaneando"),
         ("ready", "Listo para validar"), ("done", "Confirmado"),
         ("incomplete", "Cerrado con faltantes"), ("cancel", "Cancelado")],
        default="draft", required=True, tracking=True,
    )

    _sql_constraints = [
        ("quantity_positive", "check(quantity > 0)", "La cantidad nueva debe ser mayor que cero."),
    ]

    @api.depends("serial_ids")
    def _compute_scanned_count(self):
        for receipt in self:
            receipt.scanned_count = (
                receipt.quantity
                if receipt.batch_id.shared_serial and receipt.serial_ids
                else len(receipt.serial_ids)
            )

    @api.depends("expected_serial_ids", "serial_ids")
    def _compute_missing_serials(self):
        for receipt in self:
            missing = receipt.expected_serial_ids - receipt.serial_ids
            receipt.missing_serial_ids = missing
            receipt.missing_count = len(missing)

    @api.depends("picking_id")
    def _compute_transport_info(self):
        for receipt in self:
            load_model_available = "doorandoor.load.plan" in self.env.registry
            if load_model_available and receipt.picking_id and hasattr(receipt.picking_id, "ddcc_load_stop_ids"):
                plans = receipt.picking_id.ddcc_load_stop_ids.mapped("plan_id").sorted(
                    lambda plan: plan.id, reverse=True
                )
            else:
                plans = self.env["doorandoor.load.plan"].browse() if load_model_available else False
            plan = plans[:1] if plans else False
            receipt.transport_driver_name = plan.driver_id.display_name if plan and plan.driver_id else ""
            receipt.transport_vehicle_name = plan.vehicle_name if plan else ""
            receipt.transport_license_plate = plan.license_plate if plan else ""
            receipt.transport_plan_names = ", ".join(plans.mapped("name")) if plans else ""

    def _ddic_expected_dispatch_serials(self):
        self.ensure_one()
        if "ddmh.picking.serial.scan" not in self.env.registry:
            return self.env["inventory.unit.serial"]
        scans = self.env["ddmh.picking.serial.scan"].sudo().search([
            ("picking_id", "=", self.picking_id.id),
            ("product_id", "=", self.product_id.id),
        ])
        return scans.mapped("serial_id").filtered("active")

    def _ddic_management_partners(self):
        groups = (
            self.env.ref("base.group_system")
            | self.env.ref("stock.group_stock_manager")
            | self.env.ref(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
        )
        load_manager = self.env.ref(
            "doorandoor_cargas_control.group_load_control_manager",
            raise_if_not_found=False,
        )
        if load_manager:
            groups |= load_manager
        return groups.sudo().users.filtered("active").partner_id

    @api.depends("picking_id", "picking_id.move_ids.product_uom_qty", "product_id")
    def _compute_document_quantity(self):
        for receipt in self:
            moves = receipt.picking_id.move_ids.filtered(
                lambda move: move.state != "cancel" and move.product_id == receipt.product_id
            )
            receipt.document_quantity = sum(
                move.product_uom._compute_quantity(
                    move.product_uom_qty, receipt.product_id.uom_id
                ) for move in moves
            )

    @api.depends(
        "warehouse_id", "picking_id", "picking_id.move_ids.product_id",
        "product_id", "destination_purpose",
    )
    def _compute_candidate_batches(self):
        Batch = self.env["inventory.serial.label.batch"]
        for receipt in self:
            batches = Batch
            if receipt.warehouse_id and receipt.destination_purpose == "storage":
                domain = [
                    ("warehouse_id", "=", receipt.warehouse_id.id),
                    ("state", "=", "generated"),
                ]
                if receipt.product_id:
                    domain += [
                        "|", ("is_mixed_batch", "=", True),
                        ("product_id", "=", receipt.product_id.id),
                    ]
                elif receipt.picking_id:
                    domain.append((
                        "product_id", "in", receipt.picking_id.move_ids.product_id.ids,
                    ))
                batches = Batch.search(domain)
            receipt.candidate_batch_ids = batches
            receipt.recommended_batch_id = batches.sorted(
                lambda batch: (-len(batch.current_serial_ids), batch.id)
            )[:1]

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_warehouse_options(self):
        user = self.env.user
        warehouses = self.env[
            "inventory.serial.label.batch"
        ]._ddic_allowed_warehouses()
        can_select = bool(
            user.has_group("base.group_system")
            or user.has_group("doorandoor_process_control.group_ddpc_manager")
            or user.has_group(
                "doorandoor_inventory_variant_count.group_inventory_count_manager"
            )
            or len(warehouses) > 1
        )
        for receipt in self:
            receipt.allowed_warehouse_ids = warehouses
            receipt.can_select_warehouse = can_select

    @api.model
    def _default_warehouse(self):
        warehouses = self.env[
            "inventory.serial.label.batch"
        ]._ddic_allowed_warehouses()
        default_warehouse = self.env.user.ddpc_default_warehouse_id
        if default_warehouse in warehouses:
            return default_warehouse
        return warehouses if len(warehouses) == 1 else False

    @api.depends("warehouse_id")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_candidate_pickings(self):
        Picking = self.env["stock.picking"]
        allowed_warehouses = self.env[
            "inventory.serial.label.batch"
        ]._ddic_allowed_warehouses()
        for receipt in self:
            pickings = Picking
            warehouses = receipt.warehouse_id or allowed_warehouses
            if warehouses:
                pickings = Picking.search([
                    ("picking_type_code", "in", ("incoming", "internal")),
                    ("state", "not in", ("done", "cancel")),
                    ("location_dest_id", "child_of", warehouses.view_location_id.ids),
                ])
            receipt.candidate_picking_ids = pickings

    @api.model
    def _warehouse_from_location(self, location):
        if not location:
            return self.env["stock.warehouse"]
        parents = self.env["stock.location"]
        current = location
        while current:
            parents |= current
            current = current.location_id
        return self.env["stock.warehouse"].search([
            ("view_location_id", "in", parents.ids),
        ], limit=1)

    @api.depends("picking_id", "picking_id.location_id")
    def _compute_logistics(self):
        for receipt in self:
            receipt.source_warehouse_id = receipt._warehouse_from_location(
                receipt.picking_id.location_id
            ) if receipt.picking_id else False

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        picking = self.env["stock.picking"].browse(
            values.get("picking_id") or self.env.context.get("default_picking_id")
        ).exists()
        if picking and "warehouse_id" in fields_list:
            values["warehouse_id"] = self._warehouse_from_location(
                picking.location_dest_id
            ).id
        elif "warehouse_id" in fields_list and not values.get("warehouse_id"):
            default_warehouse = self._default_warehouse()
            values["warehouse_id"] = default_warehouse.id if default_warehouse else False
        return values

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id(self):
        if self.picking_id and self._warehouse_from_location(
            self.picking_id.location_dest_id
        ) != self.warehouse_id:
            self.picking_id = False
        self.batch_id = False
        self.product_id = False
        self.predispatch_location_id = False

    @api.onchange("picking_id")
    def _onchange_picking_id(self):
        self.product_id = False
        self.batch_id = False
        if self.picking_id:
            document_warehouse = self._warehouse_from_location(
                self.picking_id.location_dest_id
            )
            allowed_warehouses = self.env[
                "inventory.serial.label.batch"
            ]._ddic_allowed_warehouses()
            if document_warehouse not in allowed_warehouses:
                self.picking_id = False
                return {
                    "warning": {
                        "title": _("Documento no autorizado"),
                        "message": _(
                            "La recepción o traslado no pertenece a uno de sus almacenes autorizados."
                        ),
                    }
                }
            if self.warehouse_id and document_warehouse != self.warehouse_id:
                self.picking_id = False
                return {
                    "warning": {
                        "title": _("Documento de otro almacén"),
                        "message": _(
                            "Seleccione una recepción o traslado cuyo destino sea el almacén elegido."
                        ),
                    }
                }
            if not self.warehouse_id:
                self.warehouse_id = document_warehouse
            self.operation_type = (
                "supplier" if self.picking_id.location_id.usage == "supplier" else "internal"
            )
            self.label_mode = "existing" if self.operation_type == "internal" else "generate"
            self.destination_purpose = "storage"
            return {"domain": {"product_id": [("id", "in", self.picking_id.move_ids.product_id.ids)]}}

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if (
            self.batch_id
            and not self.batch_id.is_mixed_batch
            and self.batch_id.product_id != self.product_id
        ):
            self.batch_id = False

    @api.onchange("batch_id", "destination_purpose")
    def _onchange_batch_id(self):
        if self.destination_purpose == "storage" and self.batch_id:
            if not self.batch_id.is_mixed_batch:
                self.product_id = self.batch_id.product_id
        elif self.destination_purpose == "delivery":
            self.batch_id = False

    @api.constrains("operation_type", "label_mode", "destination_purpose")
    def _check_mode(self):
        for receipt in self:
            if receipt.operation_type == "internal" and receipt.label_mode != "existing":
                raise ValidationError(_("Un traslado interno debe reutilizar los labels existentes."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.serial.receipt"
                ) or _("Nuevo")
            if not vals.get("warehouse_id") and vals.get("picking_id"):
                picking = self.env["stock.picking"].browse(vals["picking_id"])
                vals["warehouse_id"] = self._warehouse_from_location(
                    picking.location_dest_id
                ).id
            if (
                vals.get("destination_purpose") == "delivery"
                and not vals.get("predispatch_location_id")
                and vals.get("picking_id")
            ):
                picking = self.env["stock.picking"].browse(vals["picking_id"])
                vals["predispatch_location_id"] = (
                    picking._ddic_get_or_create_predispatch_location().id
                )
        records = super().create(vals_list)
        records._check_access_and_document()
        return records

    def write(self, vals):
        protected = {"operation_type", "label_mode", "destination_purpose", "predispatch_location_id", "warehouse_id", "picking_id", "product_id", "batch_id", "quantity"}
        if protected.intersection(vals) and any(r.state != "draft" for r in self):
            raise UserError(_("No puede cambiar documento, producto, lote o cantidad después de iniciar."))
        result = super().write(vals)
        if vals.get("destination_purpose") == "delivery":
            for receipt in self.filtered(lambda item: not item.predispatch_location_id):
                receipt.predispatch_location_id = (
                    receipt.picking_id._ddic_get_or_create_predispatch_location()
                )
        if protected.intersection(vals):
            self._check_access_and_document()
        return result

    def _check_access_and_document(self):
        for receipt in self:
            if not receipt.picking_id:
                continue
            if not receipt.warehouse_id:
                raise ValidationError(_("No se pudo determinar el almacén de destino."))
            self.env["inventory.serial.label.batch"]._ddic_check_warehouse_access(
                receipt.warehouse_id
            )
            if receipt.picking_id.picking_type_code not in ("incoming", "internal"):
                raise ValidationError(_("Seleccione una recepción o un traslado interno."))
            document_warehouse = receipt._warehouse_from_location(
                receipt.picking_id.location_dest_id
            )
            if document_warehouse != receipt.warehouse_id:
                raise ValidationError(_(
                    "El documento seleccionado no tiene como destino el almacén elegido."
                ))
            source_usage = receipt.picking_id.location_id.usage
            if receipt.operation_type == "internal" and source_usage not in ("internal", "transit"):
                raise ValidationError(_("El documento seleccionado no es la recepción de un traslado interno."))
            if receipt.operation_type == "supplier" and source_usage != "supplier":
                raise ValidationError(_("El documento seleccionado no es una recepción de proveedor."))
            if receipt.product_id not in receipt.picking_id.move_ids.product_id:
                raise ValidationError(_("El producto no pertenece al documento seleccionado."))
            other_quantity = sum(self.search([
                ("id", "!=", receipt.id),
                ("picking_id", "=", receipt.picking_id.id),
                ("product_id", "=", receipt.product_id.id),
                ("state", "!=", "cancel"),
            ]).mapped("quantity"))
            if receipt.quantity + other_quantity > receipt.document_quantity:
                raise ValidationError(_(
                    "La cantidad de labels (%(labels)s) supera las %(document)s unidades "
                    "del producto en el documento."
                ) % {
                    "labels": receipt.quantity + other_quantity,
                    "document": receipt.document_quantity,
                })
            if receipt.destination_purpose == "storage":
                if not receipt.batch_id:
                    if receipt.state == "draft":
                        continue
                    raise ValidationError(_("Seleccione el lote de destino recomendado o uno compatible."))
                if (
                    receipt.batch_id.warehouse_id != receipt.warehouse_id
                    or (
                        not receipt.batch_id.is_mixed_batch
                        and receipt.batch_id.product_id != receipt.product_id
                    )
                    or receipt.batch_id.state != "generated"
                ):
                    raise ValidationError(_("El lote debe corresponder al producto y almacén de destino."))
            elif receipt.batch_id and receipt.operation_type != "supplier":
                raise ValidationError(_("Un traslado para entrega no debe asignarse a un lote de almacenamiento."))
            if receipt.destination_purpose == "delivery":
                if not receipt.predispatch_location_id:
                    raise ValidationError(_("Seleccione una ubicación de predespacho."))
                if (
                    not receipt.predispatch_location_id.ddic_is_predispatch
                    or receipt.predispatch_location_id.warehouse_id != receipt.warehouse_id
                ):
                    raise ValidationError(_("La ubicación de predespacho debe pertenecer al almacén destino."))

    def _ddic_operational_campaign(self):
        self.ensure_one()
        Campaign = self.env["inventory.serial.campaign"].sudo()
        name = _("Recepciones operativas %s") % date.today().year
        campaign = Campaign.search([
            ("company_id", "=", self.company_id.id),
            ("name", "=", name),
            ("state", "=", "open"),
        ], limit=1)
        return campaign or Campaign.create({
            "name": name,
            "company_id": self.company_id.id,
        })

    def _ddic_prepare_predispatch_label_batch(self):
        self.ensure_one()
        if self.batch_id or self.operation_type != "supplier" or self.destination_purpose != "delivery":
            return
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "PRE-%s-%s-%s" % (
                self.picking_id.name.replace("/", "-"), self.product_id.id, self.id,
            ),
            "campaign_id": self._ddic_operational_campaign().id,
            "warehouse_id": self.warehouse_id.id,
            "product_id": self.product_id.id,
            "quantity": self.quantity,
        })
        batch.action_generate_serials()
        self.write({
            "batch_id": batch.id,
            "serial_ids": [(6, 0, batch.serial_ids.filtered("active").ids)],
        })

    def action_start(self):
        for receipt in self:
            receipt._ddic_prepare_predispatch_label_batch()
            receipt._check_access_and_document()
            if receipt.state != "draft":
                continue
            if receipt.operation_type == "internal" and receipt.label_mode == "existing":
                expected_serials = receipt._ddic_expected_dispatch_serials()
                if not expected_serials:
                    raise UserError(_(
                        "Este traslado no tiene labels contados en el despacho. "
                        "El almacén de origen debe contar los labels con Hanger antes de recibir."
                    ))
                if len(expected_serials) != receipt.quantity:
                    raise UserError(_(
                        "El despacho registró %(labels)s labels de %(product)s, pero la "
                        "recepción declara %(quantity)s unidades. Corrija el documento antes de continuar."
                    ) % {
                        "labels": len(expected_serials),
                        "product": receipt.product_id.display_name,
                        "quantity": receipt.quantity,
                    })
                receipt.expected_serial_ids = expected_serials
            if receipt.label_mode == "generate":
                if not receipt.batch_id:
                    raise UserError(_("Seleccione el lote antes de generar labels."))
                if not receipt.serial_ids:
                    serials = receipt.batch_id._ddic_add_serial_units(
                        receipt.quantity, source_receipt=receipt,
                        product=receipt.product_id,
                    )
                    receipt.serial_ids = serials
                receipt.state = "ready"
            else:
                receipt.state = "scanning"
        return True

    def action_scan(self):
        self.ensure_one()
        if self.state != "scanning":
            raise UserError(_("La operación no está esperando labels."))
        code = (self.scan_code or "").strip()
        if not code:
            raise UserError(_("Escanee o escriba un código."))
        if self.scanned_count >= self.quantity:
            raise UserError(_("Ya se alcanzó la cantidad declarada."))
        Serial = self.env["inventory.unit.serial"].sudo()
        serial = Serial.search([("code", "=", code)], limit=1)
        if self.label_mode == "existing":
            if not serial:
                raise UserError(_("El label no existe en DoorAndDoor."))
            if serial.product_id != self.product_id:
                raise UserError(_("El label pertenece a otro producto."))
            if self.source_warehouse_id and serial.current_warehouse_id != self.source_warehouse_id:
                raise UserError(_("El label no está confirmado en el almacén de origen."))
            if not self.source_warehouse_id and serial.current_warehouse_id == self.warehouse_id:
                raise UserError(_("El label ya está confirmado en el almacén de destino."))
            if self.expected_serial_ids and serial not in self.expected_serial_ids:
                raise UserError(_(
                    "El label %(label)s no fue contado en el despacho de %(document)s."
                ) % {"label": serial.code, "document": self.picking_id.display_name})
        else:
            if not self.batch_id:
                raise UserError(_("Seleccione un lote para adoptar labels del proveedor."))
            if serial:
                raise UserError(_("El código ya existe y no puede adoptarse nuevamente."))
            serial = self.batch_id._ddic_add_serial_units(
                1, codes=[code], source_receipt=self,
                product=self.product_id,
            )
        if serial in self.serial_ids:
            raise UserError(_("Este label ya fue escaneado en la operación."))
        self.serial_ids = [(4, serial.id)]
        self.scan_code = False
        if self.scanned_count == self.quantity:
            self.state = "ready"
        return True

    def _ddic_apply_received_serials(self):
        for receipt in self:
            receipt.serial_ids.sudo().write({
                "current_warehouse_id": receipt.warehouse_id.id,
                "current_batch_id": (
                    receipt.batch_id.id if receipt.destination_purpose == "storage" else False
                ),
                "current_location_id": (
                    receipt.predispatch_location_id.id
                    if receipt.destination_purpose == "delivery"
                    else receipt.picking_id.location_dest_id.id
                ),
                "inventory_loaded": True,
                "source_receipt_id": receipt.id,
            })

    def action_close_incomplete(self):
        self.ensure_one()
        self._check_access_and_document()
        if self.operation_type != "internal" or self.label_mode != "existing":
            raise UserError(_(
                "El cierre con faltantes aplica a recepciones de traslados internos con labels existentes."
            ))
        if self.state not in ("scanning", "ready"):
            raise UserError(_("La recepción no está en proceso de conteo."))
        if not (self.closure_note or "").strip():
            raise UserError(_("Escriba la observación del faltante antes de cerrar."))
        if not self.expected_serial_ids:
            raise UserError(_("No existen labels de despacho para determinar los faltantes."))
        if not self.missing_serial_ids:
            raise UserError(_("No hay faltantes. Use Confirmar ingreso para una recepción completa."))

        controls = self.search([
            ("picking_id", "=", self.picking_id.id),
            ("state", "in", ("scanning", "ready")),
            ("operation_type", "=", "internal"),
            ("label_mode", "=", "existing"),
        ])
        move_products = self.picking_id.move_ids.filtered(
            lambda move: move.state != "cancel"
        ).mapped("product_id")
        missing_controls = move_products - controls.mapped("product_id")
        if missing_controls:
            raise UserError(_(
                "Antes de cerrar el traslado, prepare el control de labels para: %s."
            ) % ", ".join(missing_controls.mapped("display_name")))
        if any(not control.expected_serial_ids for control in controls):
            raise UserError(_(
                "Todos los productos deben conservar los labels esperados del despacho."
            ))
        if not controls.mapped("serial_ids"):
            raise UserError(_("No se contó ningún label recibido; no puede cerrarse la recepción."))

        MoveLine = self.env["stock.move.line"]
        for move in self.picking_id.move_ids.filtered(lambda item: item.state != "cancel"):
            product_controls = controls.filtered(lambda item: item.product_id == move.product_id)
            received_qty = len(product_controls.mapped("serial_ids"))
            move.move_line_ids.write({"quantity": 0.0})
            line = move.move_line_ids[:1]
            values = {
                "picking_id": self.picking_id.id,
                "move_id": move.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "quantity": received_qty,
            }
            if line:
                line.write(values)
            elif received_qty:
                MoveLine.create(values)

        result = self.picking_id.with_context(
            skip_backorder=True,
            picking_ids_not_to_backorder=self.picking_id.ids,
        ).button_validate()
        if self.picking_id.state != "done":
            raise UserError(_(
                "Odoo requiere una decisión adicional para cerrar el traslado: %s"
            ) % (result.get("name") if isinstance(result, dict) else _("asistente pendiente")))

        controls._ddic_apply_received_serials()
        for control in controls:
            control.state = "incomplete" if control.missing_serial_ids else "done"

        missing = controls.mapped("missing_serial_ids")
        driver = self.transport_driver_name or _("Sin chofer asociado")
        vehicle = " ".join(filter(None, [
            self.transport_vehicle_name,
            self.transport_license_plate and "(%s)" % self.transport_license_plate,
        ])) or _("Sin vehículo asociado")
        body = Markup(
            "<strong>Recepción cerrada con faltantes</strong>"
            "<p>Documento: %(document)s<br/>Origen: %(origin)s<br/>Destino: %(destination)s<br/>"
            "Chofer: %(driver)s<br/>Vehículo: %(vehicle)s<br/>Plan de carga: %(plan)s<br/>"
            "Recibidos: %(received)s<br/>Faltantes: %(missing_count)s</p>"
            "<p><strong>Labels faltantes:</strong> %(labels)s</p>"
            "<p><strong>Observación:</strong> %(note)s</p>"
        ) % {
            "document": escape(self.picking_id.display_name),
            "origin": escape(self.source_warehouse_id.display_name or self.picking_id.location_id.display_name),
            "destination": escape(self.warehouse_id.display_name),
            "driver": escape(driver),
            "vehicle": escape(vehicle),
            "plan": escape(self.transport_plan_names or _("Sin plan asociado")),
            "received": len(controls.mapped("serial_ids")),
            "missing_count": len(missing),
            "labels": escape(", ".join(missing.mapped("code"))),
            "note": escape(self.closure_note),
        }
        self.picking_id.message_post(
            body=body,
            partner_ids=self._ddic_management_partners().ids,
            attachment_ids=self.evidence_attachment_ids.ids,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        for control in controls:
            control.message_post(body=body, attachment_ids=self.evidence_attachment_ids.ids)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_create_damage_return(self):
        self.ensure_one()
        if self.state not in ("done", "incomplete") or self.picking_id.state != "done":
            raise UserError(_("Primero debe cerrar la recepción antes de crear la devolución."))
        if self.return_picking_id:
            raise UserError(_("Esta recepción ya tiene una devolución por daño."))
        if not self.damaged_serial_ids:
            raise UserError(_("Seleccione los labels recibidos con daño."))
        if self.damaged_serial_ids - self.serial_ids:
            raise UserError(_("Solo puede devolver labels realmente recibidos y contados."))
        if not (self.damage_note or "").strip():
            raise UserError(_("Describa el daño y la causa observada."))
        if not self.damage_attachment_ids:
            raise UserError(_("Adjunte al menos una imagen como evidencia del daño."))

        wizard = self.env["stock.return.picking"].with_context(
            active_model="stock.picking",
            active_id=self.picking_id.id,
            active_ids=self.picking_id.ids,
        ).create({"picking_id": self.picking_id.id})
        wizard.product_return_moves.write({"quantity": 0.0})
        return_line = wizard.product_return_moves.filtered(
            lambda line: line.product_id == self.product_id
        )[:1]
        if not return_line:
            raise UserError(_("El producto dañado no existe en la recepción validada."))
        return_line.quantity = len(self.damaged_serial_ids)
        return_picking = wizard._create_return()
        return_picking.write({"ddic_damage_receipt_id": self.id})
        self.return_picking_id = return_picking

        body = Markup(
            "<strong>Devolución creada por daño durante traslado</strong>"
            "<p>Recepción: %(receipt)s<br/>Devolución: %(return)s<br/>Chofer: %(driver)s<br/>"
            "Vehículo: %(vehicle)s<br/>Labels afectados: %(labels)s</p>"
            "<p><strong>Daño observado:</strong> %(note)s</p>"
        ) % {
            "receipt": escape(self.picking_id.display_name),
            "return": escape(return_picking.display_name),
            "driver": escape(self.transport_driver_name or _("Sin chofer asociado")),
            "vehicle": escape(self.transport_vehicle_name or _("Sin vehículo asociado")),
            "labels": escape(", ".join(self.damaged_serial_ids.mapped("code"))),
            "note": escape(self.damage_note),
        }
        return_picking.message_post(
            body=body,
            partner_ids=self._ddic_management_partners().ids,
            attachment_ids=self.damage_attachment_ids.ids,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        self.message_post(body=body, attachment_ids=self.damage_attachment_ids.ids)
        return {
            "type": "ir.actions.act_window",
            "name": _("Devolución por daño"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": return_picking.id,
            "target": "current",
        }

    def action_print_labels(self):
        self.ensure_one()
        if self.label_mode != "generate" or not self.serial_ids:
            raise UserError(_("Esta operación no generó labels DoorAndDoor."))
        return self.env.ref(
            "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
        ).report_action(self.batch_id, data={
            "labels": self.batch_id._label_payloads(
                self.serial_ids, shared_quantity=self.quantity,
            ),
        })

    def action_confirm(self):
        if not (self.env.user.has_group("base.group_system") or self.env.user.has_group(
            "doorandoor_inventory_variant_count.group_inventory_count_manager"
        )):
            raise AccessError(_("Solo Inventarios o Administrador/Ajustes puede confirmar el ingreso."))
        for receipt in self:
            if receipt.state != "ready" or receipt.scanned_count != receipt.quantity:
                raise UserError(_("Debe completar todos los labels antes de confirmar."))
            if receipt.picking_id.state != "done":
                raise UserError(_("Valide primero la recepción o traslado de inventario."))
            receipt._ddic_apply_received_serials()
            receipt.state = "done"
            receipt.message_post(body=Markup(
                "<strong>Ingreso serializado confirmado</strong><p>%(qty)s labels del producto "
                "%(product)s quedaron confirmados en %(warehouse)s contra %(picking)s.</p>"
            ) % {
                "qty": receipt.quantity,
                "product": escape(receipt.product_id.display_name),
                "warehouse": escape(receipt.warehouse_id.display_name),
                "picking": escape(receipt.picking_id.display_name),
            })
        return True


class StockPicking(models.Model):
    _inherit = "stock.picking"

    serial_receipt_ids = fields.One2many(
        "inventory.serial.receipt", "picking_id", string="Control de labels"
    )
    serial_receipt_count = fields.Integer(compute="_compute_serial_receipt_count")
    ddic_predispatch_location_id = fields.Many2one(
        "stock.location", string="Área de predespacho", readonly=True,
        copy=False, ondelete="restrict",
    )
    ddic_damage_receipt_id = fields.Many2one(
        "inventory.serial.receipt", string="Recepción origen del daño",
        readonly=True, copy=False, ondelete="restrict",
    )

    @api.depends("serial_receipt_ids")
    def _compute_serial_receipt_count(self):
        for picking in self:
            picking.serial_receipt_count = len(picking.serial_receipt_ids)

    def action_open_serial_receipts(self):
        self.ensure_one()
        action = self.env.ref(
            "doorandoor_inventory_variant_count.action_inventory_serial_receipt"
        ).sudo().read()[0]
        action["domain"] = [("picking_id", "=", self.id)]
        action["context"] = {"default_picking_id": self.id}
        return action

    def _ddic_receipt_product_quantities(self):
        """Cantidad documentada por ITEM, expresada en la UdM del producto."""
        self.ensure_one()
        quantities = {}
        for move in self.move_ids.filtered(lambda item: item.state != "cancel"):
            quantity = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id
            )
            quantities[move.product_id] = quantities.get(move.product_id, 0.0) + quantity
        return quantities

    def _ddic_receipt_groups(self):
        """Punto de extensión para clasificar cada cantidad recibida.

        Otros módulos pueden dividir un mismo ITEM entre almacenamiento y
        predespacho, conservando una clave estable para evitar duplicados.
        """
        self.ensure_one()
        operation_type = "supplier" if self.location_id.usage == "supplier" else "internal"
        return [{
            "key": "product:%s:storage" % product.id,
            "product": product,
            "quantity": quantity,
            "destination_purpose": "storage",
            "destination_reference": False,
            "destination_picking": self.env["stock.picking"],
            "operation_type": operation_type,
            "label_mode": "generate" if operation_type == "supplier" else "existing",
        } for product, quantity in self._ddic_receipt_product_quantities().items()]

    def action_prepare_serial_receipt_lines(self):
        self.ensure_one()
        if self.picking_type_code not in ("incoming", "internal"):
            raise UserError(_("Esta acción solo aplica a recepciones y traslados internos."))
        if self.state in ("done", "cancel"):
            raise UserError(_("El documento ya está cerrado y no admite una nueva preparación."))
        warehouse = self.env["inventory.serial.receipt"]._warehouse_from_location(
            self.location_dest_id
        )
        self.env["inventory.serial.label.batch"]._ddic_check_warehouse_access(warehouse)
        groups = self._ddic_receipt_groups()
        if not groups:
            raise UserError(_("El documento no contiene productos pendientes de recepción."))
        Receipt = self.env["inventory.serial.receipt"]
        created = Receipt
        for group in groups:
            quantity = group["quantity"]
            if quantity <= 0:
                continue
            if abs(quantity - round(quantity)) > 1e-6:
                raise UserError(_(
                    "El ITEM %(product)s tiene %(quantity)s unidades. El etiquetado unitario "
                    "requiere una cantidad entera."
                ) % {"product": group["product"].display_name, "quantity": quantity})
            key = group["key"]
            receipt = self.serial_receipt_ids.filtered(
                lambda item: item.source_group_key == key and item.state != "cancel"
            )[:1]
            if receipt:
                if receipt.state != "draft":
                    continue
                receipt.write({
                    "quantity": int(round(quantity)),
                    "destination_reference": group.get("destination_reference"),
                    "destination_picking_id": group.get("destination_picking").id,
                })
                created |= receipt
                continue
            values = {
                "picking_id": self.id,
                "warehouse_id": warehouse.id,
                "product_id": group["product"].id,
                "quantity": int(round(quantity)),
                "operation_type": group["operation_type"],
                "label_mode": group["label_mode"],
                "destination_purpose": group["destination_purpose"],
                "source_group_key": key,
                "destination_reference": group.get("destination_reference"),
                "destination_picking_id": group.get("destination_picking").id,
            }
            receipt = Receipt.create(values)
            if receipt.destination_purpose == "storage" and receipt.recommended_batch_id:
                receipt.batch_id = receipt.recommended_batch_id
            created |= receipt
        self.message_post(body=Markup(
            "<strong>Recepción preparada por ITEM</strong>"
            "<p>Se clasificaron %(count)s líneas entre lote y predespacho. "
            "El destino sigue siendo confirmable antes de generar labels.</p>"
        ) % {"count": len(created)})
        return self.action_open_serial_receipts()

    def _ddic_pending_receipt_controls(self):
        self.ensure_one()
        expected = sum(self._ddic_receipt_product_quantities().values())
        controls = self.serial_receipt_ids.filtered(lambda item: item.state != "cancel")
        controlled = sum(controls.mapped("quantity"))
        if abs(expected - controlled) > 1e-6:
            raise UserError(_(
                "Las líneas de control cubren %(controlled)s de %(expected)s unidades. "
                "Pulse Preparar recepción por ITEM antes de continuar."
            ) % {"controlled": controlled, "expected": expected})
        return controls

    def action_prepare_all_serial_receipt_labels(self):
        self.ensure_one()
        controls = self._ddic_pending_receipt_controls()
        # A supplier receipt whose operator asks to prepare and print labels
        # must leave the document with printable DoorAndDoor labels.  The
        # "compatible" mode is only meaningful when physical supplier codes
        # will be adopted one by one; it must not turn this bulk button into a
        # detour through every ISR form.
        supplier_without_codes = controls.filtered(
            lambda item: (
                item.operation_type == "supplier"
                and item.label_mode == "compatible"
                and not item.serial_ids
                and item.state in ("draft", "scanning")
            )
        )
        if supplier_without_codes:
            # Restore the empty controls to draft first so the model's own
            # immutable-after-start guard remains effective for every control
            # that already contains a scanned supplier code.
            supplier_without_codes.sudo().write({"state": "draft"})
            supplier_without_codes.sudo().write({"label_mode": "generate"})
        for receipt in controls.filtered(lambda item: item.state == "draft"):
            receipt.action_start()
        pending = controls.filtered(lambda item: item.state not in ("ready", "done"))
        if pending:
            return pending[:1].get_formview_action()
        return self.action_print_associated_labels()

    def _ddic_associated_serials(self):
        """Return the exact active labels auditable from this operation."""
        self.ensure_one()
        controls = self.serial_receipt_ids.filtered(lambda item: item.state != "cancel")
        serials = controls.mapped("serial_ids") | controls.mapped("expected_serial_ids")
        if "ddmh_serial_scan_ids" in self._fields:
            serials |= self.ddmh_serial_scan_ids.mapped("serial_id")
        return serials.filtered("active")

    def action_print_associated_labels(self):
        """Print one consolidated PDF and preserve it in the picking chatter."""
        self.ensure_one()
        serials = self._ddic_associated_serials()
        if not serials:
            raise UserError(_(
                "Este documento todavía no tiene labels asociados. En una recepción "
                "de proveedor pulse primero 'Preparar e imprimir labels'."
            ))
        payloads = []
        for batch in serials.mapped("batch_id"):
            batch_serials = serials.filtered(lambda item: item.batch_id == batch)
            payloads.extend(batch._label_payloads(serials=batch_serials))
        report = self.env.ref(
            "doorandoor_inventory_variant_count.action_report_inventory_serial_labels"
        ).sudo()
        data = {"labels": payloads}
        pdf, __content_type = report._render_qweb_pdf(
            report.report_name,
            res_ids=serials[:1].batch_id.ids,
            data=data,
        )
        filename = "%s_labels_asociados.pdf" % self.name.replace("/", "-")
        Attachment = self.env["ir.attachment"].sudo()
        attachment = Attachment.search([
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("name", "=", filename),
        ], limit=1)
        values = {
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(pdf),
            "mimetype": "application/pdf",
            "res_model": self._name,
            "res_id": self.id,
        }
        if attachment:
            attachment.write(values)
        else:
            attachment = Attachment.create(values)
        self.message_post(
            body=Markup(
                "<strong>Labels asociados listos para imprimir</strong>"
                "<p>Documento: %(document)s<br/>Cantidad: %(quantity)s<br/>"
                "Preparado por: %(user)s.</p>"
            ) % {
                "document": escape(self.display_name),
                "quantity": len(serials),
                "user": escape(self.env.user.display_name),
            },
            attachment_ids=attachment.ids,
        )
        return report.report_action(
            serials[:1].batch_id,
            data=data,
        )

    def action_print_serial_receipt_labels(self):
        return self.action_print_associated_labels()

    def _ddic_apply_controlled_move_lines(self, controls):
        self.ensure_one()
        MoveLine = self.env["stock.move.line"]
        for move in self.move_ids.filtered(lambda item: item.state != "cancel"):
            remaining = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id
            )
            product_controls = controls.filtered(
                lambda item: item.product_id == move.product_id
            )
            move.move_line_ids.unlink()
            for control in product_controls:
                if remaining <= 1e-6:
                    break
                already = sum(
                    line.quantity for line in MoveLine.search([
                        ("picking_id", "=", self.id),
                        ("product_id", "=", move.product_id.id),
                        ("location_dest_id", "=", (
                            control.predispatch_location_id.id
                            if control.destination_purpose == "delivery"
                            else self.location_dest_id.id
                        )),
                    ])
                )
                available = max(control.quantity - already, 0.0)
                quantity = min(remaining, available)
                if quantity <= 1e-6:
                    continue
                MoveLine.create({
                    "picking_id": self.id,
                    "move_id": move.id,
                    "product_id": move.product_id.id,
                    "product_uom_id": move.product_uom.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": (
                        control.predispatch_location_id.id
                        if control.destination_purpose == "delivery"
                        else self.location_dest_id.id
                    ),
                    "quantity": move.product_id.uom_id._compute_quantity(
                        quantity, move.product_uom
                    ),
                })
                remaining -= quantity
            if remaining > 1e-6:
                raise UserError(_(
                    "No se pudo distribuir toda la cantidad de %(product)s entre sus destinos."
                ) % {"product": move.product_id.display_name})

    def action_validate_serial_receipt(self):
        self.ensure_one()
        if not (self.env.user.has_group("base.group_system") or self.env.user.has_group(
            "doorandoor_inventory_variant_count.group_inventory_count_manager"
        )):
            raise AccessError(_("Solo Inventarios o Administrador/Ajustes puede validar la recepción."))
        controls = self._ddic_pending_receipt_controls()
        invalid = controls.filtered(
            lambda item: item.state != "ready" or item.scanned_count != item.quantity
        )
        if invalid:
            raise UserError(_(
                "Complete el etiquetado o lectura de todas las líneas antes de validar: %s"
            ) % ", ".join(invalid.mapped("product_id.display_name")))
        self._ddic_apply_controlled_move_lines(controls)
        result = self.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=self.ids,
        ).button_validate()
        if self.state != "done":
            raise UserError(_(
                "Odoo requiere una decisión adicional antes de cerrar la recepción: %s"
            ) % (result.get("name") if isinstance(result, dict) else _("asistente pendiente")))
        controls.action_confirm()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_open_predispatch_location(self):
        self.ensure_one()
        if not self.ddic_predispatch_location_id:
            raise UserError(_("Este documento todavía no tiene área de predespacho."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Área de predespacho"),
            "res_model": "stock.location",
            "view_mode": "form",
            "res_id": self.ddic_predispatch_location_id.id,
            "target": "current",
        }

    def _action_done(self):
        result = super()._action_done()
        for picking in self.filtered("ddic_damage_receipt_id"):
            receipt = picking.ddic_damage_receipt_id
            warehouse = receipt._warehouse_from_location(picking.location_dest_id)
            receipt.damaged_serial_ids.sudo().write({
                "current_warehouse_id": warehouse.id or False,
                "current_batch_id": False,
                "current_location_id": picking.location_dest_id.id,
                "source_receipt_id": receipt.id,
            })
            receipt.message_post(body=Markup(
                "<strong>Devolución por daño validada</strong>"
                "<p>%(return)s trasladó %(qty)s labels dañados a %(destination)s. "
                "Los seriales permanecen fuera de un lote vendible hasta decisión de Gerencia.</p>"
            ) % {
                "return": escape(picking.display_name),
                "qty": len(receipt.damaged_serial_ids),
                "destination": escape(picking.location_dest_id.display_name),
            })
        return result

    def _ddic_get_or_create_predispatch_location(self):
        self.ensure_one()
        if self.ddic_predispatch_location_id:
            return self.ddic_predispatch_location_id
        location = self.location_dest_id
        parents = self.env["stock.location"]
        while location:
            parents |= location
            location = location.location_id
        warehouse = self.env["stock.warehouse"].search([
            ("view_location_id", "in", parents.ids),
        ], limit=1)
        if not warehouse:
            raise UserError(_(
                "No se pudo determinar el almacén para crear el área de predespacho."
            ))
        Location = self.env["stock.location"].sudo()
        root = Location.search([
            ("location_id", "=", warehouse.view_location_id.id),
            ("ddic_is_predispatch_root", "=", True),
        ], limit=1)
        if not root:
            root = Location.create({
                "name": "PRE-DESPACHO",
                "location_id": warehouse.view_location_id.id,
                "usage": "view",
                "ddic_is_predispatch_root": True,
            })
        area = Location.create({
            "name": self.name.replace("/", "-") or str(self.id),
            "location_id": root.id,
            "usage": "internal",
            "ddic_is_predispatch": True,
            "ddic_predispatch_picking_id": self.id,
        })
        self.sudo().write({"ddic_predispatch_location_id": area.id})
        self.message_post(body=Markup(
            "<strong>Área de predespacho creada</strong><p>%(area)s agrupará todos "
            "los productos y labels de este documento.</p>"
        ) % {"area": escape(area.complete_name)})
        return area
