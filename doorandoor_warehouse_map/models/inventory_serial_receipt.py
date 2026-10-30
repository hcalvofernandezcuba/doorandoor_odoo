from datetime import date

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class InventorySerialReceipt(models.Model):
    _inherit = "inventory.serial.receipt"

    picking_id = fields.Many2one(required=False)
    operation_type = fields.Selection(default="supplier")
    label_mode = fields.Selection(default="generate")
    candidate_product_ids = fields.Many2many(
        "product.product",
        compute="_compute_candidate_products",
        string="ITEM de la recepción",
    )
    new_supplier_id = fields.Many2one(
        "res.partner",
        string="Proveedor / origen",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
        copy=False,
        help="Se utiliza solamente cuando el formulario debe crear una recepción nueva.",
    )
    new_document_reference = fields.Char(
        string="Referencia de origen",
        tracking=True,
        copy=False,
        help="Factura, packing list u otra referencia de la mercancía recibida.",
    )
    picking_created_automatically = fields.Boolean(
        string="Recepción creada automáticamente",
        readonly=True,
        copy=False,
        tracking=True,
    )
    increment_session_id = fields.Many2one(
        "inventory.count.session",
        string="Sesión incremental del lote",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    candidate_empty_position_ids = fields.Many2many(
        "doorandoor.warehouse.map.position",
        compute="_compute_candidate_empty_positions",
        string="Espacios vacíos disponibles",
    )
    empty_position_id = fields.Many2one(
        "doorandoor.warehouse.map.position",
        string="Posición disponible o nueva",
        domain="[('id', 'in', candidate_empty_position_ids)]",
        tracking=True,
        help=(
            "Seleccione una posición disponible o use Crear y editar para registrar "
            "una posición nueva dentro del almacén destino. Este flujo nunca crea "
            "un almacén nuevo."
        ),
    )
    created_batch_id = fields.Many2one(
        "inventory.serial.label.batch",
        string="Lote creado en la recepción",
        readonly=True,
        copy=False,
    )
    needs_empty_position = fields.Boolean(
        compute="_compute_candidate_empty_positions",
    )
    create_new_batch = fields.Boolean(
        string="Crear un lote nuevo",
        tracking=True,
        copy=False,
        help="Úselo cuando la mercancía llega en una nueva posición, paleta o contenedor.",
    )
    new_storage_type = fields.Selection(
        [
            ("fixed", "Posición fija del mapa"),
            ("mobile_pallet", "Paleta móvil"),
            ("cargo_container", "Contenedor de carga"),
        ],
        string="Tipo del lote nuevo",
        default="fixed",
        tracking=True,
        copy=False,
    )
    new_storage_reference = fields.Char(
        string="Referencia de paleta o contenedor",
        tracking=True,
        copy=False,
        help="Código físico único visible en la paleta o el contenedor.",
    )
    recommended_position_id = fields.Many2one(
        "doorandoor.warehouse.map.position",
        string="Posición recomendada",
        compute="_compute_candidate_batches",
    )
    recommended_empty_position_id = fields.Many2one(
        "doorandoor.warehouse.map.position",
        string="Posición vacía recomendada",
        compute="_compute_candidate_empty_positions",
    )
    recommended_capacity = fields.Integer(
        string="Capacidad de la posición",
        compute="_compute_candidate_batches",
    )
    recommended_current_quantity = fields.Integer(
        string="Ocupación actual",
        compute="_compute_candidate_batches",
    )
    recommended_available_quantity = fields.Integer(
        string="Espacio disponible",
        compute="_compute_candidate_batches",
    )
    recommended_batch_is_mixed = fields.Boolean(
        string="Lote recomendado mixto",
        compute="_compute_candidate_batches",
    )
    candidate_batch_overview = fields.Text(
        string="Opciones compatibles",
        compute="_compute_candidate_batch_overview",
        help="Lotes del mismo ITEM o lotes mixtos admitidos para esta recepción.",
    )
    selected_batch_position_id = fields.Many2one(
        "doorandoor.warehouse.map.position",
        string="Posición física del lote",
        compute="_compute_selected_batch_location",
    )
    selected_batch_location = fields.Char(
        string="Ubicación física del lote seleccionado",
        compute="_compute_selected_batch_location",
    )

    @api.depends("picking_id", "picking_id.move_ids.product_id")
    def _compute_candidate_products(self):
        Product = self.env["product.product"]
        for receipt in self:
            receipt.candidate_product_ids = (
                receipt.picking_id.move_ids.filtered(
                    lambda move: move.state != "cancel"
                ).product_id
                if receipt.picking_id
                else Product.search([("is_storable", "=", True)])
            )

    @api.onchange("picking_id")
    def _onchange_picking_id_guided(self):
        result = super()._onchange_picking_id()
        if not self.picking_id:
            self.operation_type = "supplier"
            self.label_mode = "generate"
            return result
        products = self.picking_id.move_ids.filtered(
            lambda move: move.state != "cancel"
        ).product_id
        if len(products) == 1:
            self.product_id = products
            documented = sum(
                self.picking_id.move_ids.filtered(
                    lambda move: move.state != "cancel"
                    and move.product_id == products
                ).mapped("product_uom_qty")
            )
            already_prepared = sum(self.search([
                ("picking_id", "=", self.picking_id._origin.id),
                ("product_id", "=", products._origin.id),
                ("state", "!=", "cancel"),
            ]).mapped("quantity"))
            self.quantity = max(int(documented - already_prepared), 1)
        self.label_mode = (
            "existing" if self.operation_type == "internal" else "compatible"
        )
        return result

    @api.onchange("operation_type")
    def _onchange_new_operation_type(self):
        if self.picking_id:
            return
        self.label_mode = (
            "existing" if self.operation_type == "internal" else "generate"
        )
        if self.operation_type != "supplier":
            self.new_supplier_id = False

    @api.depends(
        "batch_id", "batch_id.name", "batch_id.warehouse_id",
        "batch_id.ddwm_storage_type", "batch_id.ddwm_position_id",
    )
    def _compute_selected_batch_location(self):
        storage_labels = dict(
            self.env["inventory.serial.label.batch"]._fields[
                "ddwm_storage_type"
            ].selection
        )
        for receipt in self:
            batch = receipt.batch_id
            position = batch._ddwm_resolved_position() if batch else False
            receipt.selected_batch_position_id = position
            if position:
                receipt.selected_batch_location = position.display_name
            elif batch:
                storage_type = storage_labels.get(batch.ddwm_storage_type) or _(
                    "Lote físico"
                )
                receipt.selected_batch_location = "%s: %s" % (
                    storage_type, batch.display_name,
                )
            else:
                receipt.selected_batch_location = False

    @api.depends(
        "warehouse_id", "picking_id", "picking_id.move_ids.product_id",
        "product_id", "destination_purpose", "quantity",
    )
    def _compute_candidate_batches(self):
        super()._compute_candidate_batches()
        for receipt in self:
            eligible = []
            for batch in receipt.candidate_batch_ids:
                snapshot = batch._ddwm_capacity_snapshot()
                if (
                    snapshot.get("unlimited")
                    or snapshot["known"] and snapshot["available"] >= receipt.quantity
                ):
                    eligible.append((batch, snapshot))
            eligible.sort(key=lambda item: (
                # Never send a product to a consolidation area while a lot of
                # that exact ITEM can receive it.  Mixed lots are the explicit
                # fallback and remain unlimited by design.
                bool(item[0].is_mixed_batch),
                item[1]["available"], -item[1]["current"], item[0].name or "",
            ))
            if eligible:
                receipt.recommended_batch_id = eligible[0][0]
                receipt.recommended_batch_is_mixed = bool(
                    eligible[0][0].is_mixed_batch
                )
                snapshot = eligible[0][1]
                receipt.recommended_position_id = snapshot["position"]
                receipt.recommended_capacity = snapshot["capacity"]
                receipt.recommended_current_quantity = snapshot["current"]
                receipt.recommended_available_quantity = snapshot["available"]
            else:
                receipt.recommended_batch_id = False
                receipt.recommended_batch_is_mixed = False
                receipt.recommended_position_id = False
                receipt.recommended_capacity = 0
                receipt.recommended_current_quantity = 0
                receipt.recommended_available_quantity = 0

    @api.depends(
        "candidate_batch_ids", "candidate_batch_ids.product_id",
        "candidate_batch_ids.current_serial_ids",
        "candidate_batch_ids.ddwm_position_id", "product_id", "quantity",
    )
    def _compute_candidate_batch_overview(self):
        for receipt in self:
            options = []
            for batch in receipt.candidate_batch_ids:
                snapshot = batch._ddwm_capacity_snapshot()
                if not (
                    snapshot.get("unlimited")
                    or snapshot.get("known") and snapshot["available"] >= receipt.quantity
                ):
                    continue
                products = batch.current_serial_ids.filtered("active").mapped("product_id")
                item = (
                    _("Mixto: %s") % ", ".join(products.mapped("display_name"))
                    if batch.is_mixed_batch else batch.product_id.display_name
                )
                position = snapshot["position"]
                availability = _("sin límite") if snapshot.get("unlimited") else _("%s libres") % snapshot["available"]
                options.append("%s — %s — %s — %s" % (
                    batch.display_name, item,
                    position.display_name if position else batch.display_name,
                    availability,
                ))
            receipt.candidate_batch_overview = "\n".join(options) or _(
                "No existe lote compatible con capacidad; seleccione una posición nueva."
            )

    @api.depends(
        "warehouse_id", "product_id", "destination_purpose",
        "create_new_batch", "new_storage_type", "quantity",
        "recommended_batch_id",
    )
    def _compute_candidate_empty_positions(self):
        Position = self.env["doorandoor.warehouse.map.position"]
        Batch = self.env["inventory.serial.label.batch"]
        for receipt in self:
            needs_position = bool(
                receipt.destination_purpose == "storage"
                and receipt.warehouse_id
                and receipt.product_id
                and not receipt.recommended_batch_id
            )
            positions = Position
            if needs_position or (
                receipt.destination_purpose == "storage"
                and receipt.warehouse_id
                and receipt.product_id
                and receipt.create_new_batch
                and receipt.new_storage_type == "fixed"
            ):
                occupied = {
                    (name or "").strip().upper()
                    for name in Batch.search([
                        ("warehouse_id", "=", receipt.warehouse_id.id),
                        ("state", "in", ("draft", "generated")),
                    ]).mapped("name")
                }
                positions = Position.search([
                    ("warehouse_id", "=", receipt.warehouse_id.id),
                    ("active", "=", True),
                    ("status", "=", "available"),
                ]).filtered(
                    lambda position: position.name.upper() not in occupied
                    and receipt._ddwm_fixed_position_accepts_product(
                        position, receipt.product_id, receipt.quantity,
                    )
                )
            receipt.candidate_empty_position_ids = positions
            receipt.needs_empty_position = needs_position
            receipt.recommended_empty_position_id = receipt._ddwm_nearest_empty_position(
                positions
            )

    @api.model
    def _ddwm_axis_value(self, value):
        """Return a stable numeric value for numeric or alphabetic map axes."""
        text = (str(value or "").strip().upper())
        if text.isdigit():
            return int(text)
        result = 0
        for character in text:
            if "A" <= character <= "Z":
                result = result * 26 + ord(character) - 64
        return result

    def _ddwm_position_coordinates(self, position):
        return (
            self._ddwm_axis_value(position.aisle),
            self._ddwm_axis_value(position.horizontal_position),
            int(position.vertical_position or 0),
            0 if position.side == "L" else 1 if position.side == "R" else 2,
            int(position.slot_number or 1),
        )

    def _ddwm_nearest_empty_position(self, positions):
        self.ensure_one()
        if not positions:
            return positions
        Batch = self.env["inventory.serial.label.batch"]
        anchors = Batch.search([
            ("warehouse_id", "=", self.warehouse_id.id),
            ("product_id", "=", self.product_id.id),
            ("state", "=", "generated"),
        ]).mapped("ddwm_position_id").filtered("active")
        if not anchors:
            return positions.sorted(
                lambda position: self._ddwm_position_coordinates(position)
            )[:1]

        anchor_coordinates = [
            self._ddwm_position_coordinates(position) for position in anchors
        ]

        def distance(position):
            coordinates = self._ddwm_position_coordinates(position)
            nearest = min(
                sum(abs(left - right) * weight for left, right, weight in zip(
                    coordinates, anchor, (10000, 1000, 100, 10, 1),
                ))
                for anchor in anchor_coordinates
            )
            return (nearest, coordinates, position.id)

        return positions.sorted(distance)[:1]

    @api.onchange(
        "warehouse_id", "product_id", "destination_purpose",
        "create_new_batch", "new_storage_type", "quantity",
    )
    def _onchange_empty_position_scope(self):
        if self.empty_position_id not in self.candidate_empty_position_ids:
            self.empty_position_id = False
        if self.create_new_batch:
            self.batch_id = False
        if self.new_storage_type == "fixed":
            self.new_storage_reference = False
        else:
            self.empty_position_id = False
        if (
            self.needs_empty_position
            and self.new_storage_type == "fixed"
            and not self.empty_position_id
        ):
            self.empty_position_id = self.recommended_empty_position_id

    @api.onchange("batch_id")
    def _onchange_existing_batch(self):
        if self.batch_id:
            self.create_new_batch = False
            self.empty_position_id = False
            self.new_storage_reference = False

    @api.model
    def _ddwm_new_batch_values(self, vals, warehouse, product, quantity):
        storage_type = vals.get("new_storage_type") or "fixed"
        position = self.env["doorandoor.warehouse.map.position"].browse(
            vals.get("empty_position_id")
        ).exists()
        reference = (vals.get("new_storage_reference") or "").strip().upper()
        if storage_type == "fixed":
            if not position:
                raise ValidationError(_(
                    "Seleccione una posición fija disponible para el lote nuevo."
                ))
            if position.warehouse_id != warehouse:
                raise ValidationError(_(
                    "La posición física debe pertenecer al almacén de destino."
                ))
            if position.status != "available":
                raise ValidationError(_(
                    "La posición %s no está disponible."
                ) % position.display_name)
            if position.capacity and quantity > position.capacity:
                raise ValidationError(_(
                    "La posición %(position)s admite %(capacity)s unidades y la recepción trae %(quantity)s."
                ) % {
                    "position": position.display_name,
                    "capacity": position.capacity,
                    "quantity": quantity,
                })
            self._ddwm_check_fixed_position_product_rule(
                position, product, quantity,
            )
            reference = position.name
        elif not reference:
            raise ValidationError(_(
                "Indique la referencia física de la paleta o del contenedor."
            ))

        Batch = self.env["inventory.serial.label.batch"]
        if Batch.search_count([
            ("warehouse_id", "=", warehouse.id),
            ("name", "=ilike", reference),
            ("state", "in", ("draft", "generated")),
        ]):
            raise ValidationError(_(
                "La referencia %(reference)s ya está usada en %(warehouse)s."
            ) % {
                "reference": reference,
                "warehouse": warehouse.display_name,
            })
        return {
            "name": reference,
            "warehouse_id": warehouse.id,
            "product_id": product.id,
            "quantity": quantity,
            "ddwm_storage_type": storage_type,
            "ddwm_position_id": position.id if storage_type == "fixed" else False,
        }

    @api.model
    def _ddwm_fixed_position_root(self, position):
        return "%s%s%s%s" % (
            (position.warehouse_prefix or "").strip().upper(),
            (position.aisle or "").strip().upper(),
            (position.horizontal_position or "").strip().upper(),
            position.vertical_position or "",
        )

    @api.model
    def _ddwm_fixed_root_batches(self, position):
        root = self._ddwm_fixed_position_root(position)
        batches = self.env["inventory.serial.label.batch"].search([
            ("warehouse_id", "=", position.warehouse_id.id),
            ("state", "in", ("draft", "generated")),
        ])
        return batches.filtered(lambda batch: (
            batch._ddwm_resolved_position()
            and self._ddwm_fixed_position_root(
                batch._ddwm_resolved_position()
            ) == root
        ))

    @api.model
    def _ddwm_check_fixed_position_product_rule(
        self, position, product, incoming_quantity,
    ):
        siblings = self._ddwm_fixed_root_batches(position)
        if siblings.filtered("is_mixed_batch"):
            return True
        other_products = siblings.filtered(
            lambda batch: batch.product_id != product
        )
        protected = siblings.filtered(
            lambda batch: batch.product_id != product
            and batch._ddwm_capacity_snapshot()["current"] > 5
        )
        if protected:
            protected_batch = protected[0]
            current = protected_batch._ddwm_capacity_snapshot()["current"]
            raise ValidationError(_(
                "La posición %(root)s está reservada para %(product)s porque contiene "
                "%(quantity)s unidades. Seleccione otra posición para %(incoming_product)s."
            ) % {
                "root": self._ddwm_fixed_position_root(position),
                "product": protected_batch.product_id.display_name,
                "quantity": current,
                "incoming_product": product.display_name,
            })
        if incoming_quantity > 5 and other_products:
            raise ValidationError(_(
                "Las %(quantity)s unidades de %(product)s requieren una posición exclusiva. "
                "La posición %(root)s ya contiene otro ITEM; seleccione otra."
            ) % {
                "quantity": incoming_quantity,
                "product": product.display_name,
                "root": self._ddwm_fixed_position_root(position),
            })
        return True

    @api.model
    def _ddwm_fixed_position_accepts_product(
        self, position, product, incoming_quantity,
    ):
        siblings = self._ddwm_fixed_root_batches(position)
        if siblings.filtered("is_mixed_batch"):
            return True
        other_products = siblings.filtered(
            lambda batch: batch.product_id != product
        )
        if any(
            batch._ddwm_capacity_snapshot()["current"] > 5
            for batch in other_products
        ):
            return False
        if incoming_quantity > 5 and other_products:
            return False
        return True

    @api.model
    def _ddwm_operational_campaign(self, company):
        Campaign = self.env["inventory.serial.campaign"].sudo()
        name = _("Ingresos operativos %s") % date.today().year
        campaign = Campaign.search([
            ("company_id", "=", company.id),
            ("name", "=", name),
            ("state", "=", "open"),
        ], limit=1)
        return campaign or Campaign.create({
            "name": name,
            "company_id": company.id,
        })

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        created_batches = []
        Position = self.env["doorandoor.warehouse.map.position"]
        Batch = self.env["inventory.serial.label.batch"]
        for incoming in vals_list:
            vals = dict(incoming)
            if not vals.get("picking_id"):
                vals["picking_id"] = self._ddwm_create_official_receipt(vals).id
                vals["picking_created_automatically"] = True
                vals["operation_type"] = "supplier"
                vals["label_mode"] = "generate"
            else:
                picking = self.env["stock.picking"].browse(
                    vals["picking_id"]
                ).exists()
                internal = picking.location_id.usage in ("internal", "transit")
                vals["operation_type"] = "internal" if internal else "supplier"
                vals["label_mode"] = "existing" if internal else "compatible"
            batch = Batch
            position = Position.browse(vals.get("empty_position_id")).exists()
            if (
                vals.get("destination_purpose", "storage") == "storage"
                and not vals.get("batch_id")
                and (vals.get("create_new_batch") or position or vals.get("new_storage_reference"))
            ):
                warehouse = self.env["stock.warehouse"].browse(
                    vals.get("warehouse_id")
                ).exists()
                product = self.env["product.product"].browse(
                    vals.get("product_id")
                ).exists()
                quantity = int(vals.get("quantity") or 0)
                campaign = self._ddwm_operational_campaign(warehouse.company_id)
                batch_vals = self._ddwm_new_batch_values(
                    vals, warehouse, product, quantity,
                )
                batch_values = {
                    "campaign_id": campaign.id,
                    **batch_vals,
                }
                if vals.get("label_mode") != "generate":
                    batch_values["state"] = "generated"
                batch = Batch.create(batch_values)
                if vals.get("label_mode") == "generate":
                    batch.action_generate_serials()
                vals["batch_id"] = batch.id
            prepared.append(vals)
            created_batches.append(batch)

        receipts = super().create(prepared)
        for receipt, batch in zip(receipts, created_batches):
            if not batch:
                continue
            serials = batch.serial_ids.filtered("active")
            serials.sudo().write({
                "current_warehouse_id": receipt.warehouse_id.id,
                "current_batch_id": batch.id,
                "current_location_id": receipt.picking_id.location_dest_id.id,
                "source_receipt_id": receipt.id,
            })
            receipt.write({
                "created_batch_id": batch.id,
                "serial_ids": [(6, 0, serials.ids)],
            })
            receipt.message_post(body=Markup(
                "<strong>Nuevo lote de almacenamiento creado</strong>"
                "<p>Se creó el lote %(batch)s para %(product)s en %(warehouse)s. "
                "Su tipo y referencia física fueron seleccionados expresamente por el operador.</p>"
            ) % {
                "batch": escape(batch.display_name),
                "product": escape(receipt.product_id.display_name),
                "warehouse": escape(receipt.warehouse_id.display_name),
            })
        return receipts

    @api.model
    def _ddwm_create_official_receipt(self, vals):
        warehouse = self.env["stock.warehouse"].browse(
            vals.get("warehouse_id")
        ).exists()
        product = self.env["product.product"].browse(
            vals.get("product_id")
        ).exists()
        quantity = int(vals.get("quantity") or 0)
        operation_type = vals.get("operation_type") or "supplier"
        if not warehouse or not product or quantity <= 0:
            raise ValidationError(_(
                "Seleccione almacén, ITEM y cantidad antes de crear la recepción."
            ))
        self.env["inventory.serial.label.batch"]._ddic_check_warehouse_access(
            warehouse
        )
        if operation_type != "supplier":
            raise ValidationError(_(
                "Para recibir un traslado interno seleccione el documento enviado "
                "por el almacén de origen. Solo las recepciones de proveedor pueden "
                "crearse desde este formulario."
            ))
        source = self.env.ref("stock.stock_location_suppliers")
        picking_type = warehouse.in_type_id
        partner = self.env["res.partner"].browse(
            vals.get("new_supplier_id")
        ).exists()
        if not picking_type:
            raise ValidationError(_(
                "El almacén no tiene configurado el tipo de operación necesario."
            ))
        reference = (vals.get("new_document_reference") or "").strip()
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": warehouse.lot_stock_id.id,
            "partner_id": partner.id,
            "origin": reference or _("Recepción creada desde ingreso guiado"),
        })
        self.env["stock.move"].create({
            "name": product.display_name,
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom_qty": quantity,
            "product_uom": product.uom_id.id,
            "location_id": source.id,
            "location_dest_id": warehouse.lot_stock_id.id,
        })
        picking.action_confirm()
        picking.message_post(body=Markup(
            "<strong>Recepción oficial creada desde el ingreso guiado</strong>"
            "<p>Almacén: %(warehouse)s<br/>ITEM: %(product)s<br/>Cantidad: %(quantity)s"
            "<br/>Referencia: %(reference)s</p>"
        ) % {
            "warehouse": escape(warehouse.display_name),
            "product": escape(product.display_name),
            "quantity": quantity,
            "reference": escape(reference or _("Sin referencia externa")),
        })
        return picking

    def _ddwm_create_batch_from_storage_reference(self):
        for receipt in self.filtered(
            lambda item: item.state == "draft"
            and item.destination_purpose == "storage"
            and not item.batch_id
            and (item.needs_empty_position or item.create_new_batch)
        ):
            Batch = self.env["inventory.serial.label.batch"]
            if (
                receipt.new_storage_type == "fixed"
                and receipt.empty_position_id not in receipt.candidate_empty_position_ids
            ):
                raise ValidationError(_(
                    "El espacio %s ya no está disponible para este almacén."
                ) % receipt.empty_position_id.display_name)
            campaign = self._ddwm_operational_campaign(receipt.company_id)
            batch_vals = self._ddwm_new_batch_values({
                "new_storage_type": receipt.new_storage_type,
                "empty_position_id": receipt.empty_position_id.id,
                "new_storage_reference": receipt.new_storage_reference,
            }, receipt.warehouse_id, receipt.product_id, receipt.quantity)
            batch_values = {
                "campaign_id": campaign.id,
                **batch_vals,
            }
            if receipt.label_mode != "generate":
                batch_values["state"] = "generated"
            batch = Batch.create(batch_values)
            if receipt.label_mode == "generate":
                batch.action_generate_serials()
            receipt.write({
                "batch_id": batch.id,
                "created_batch_id": batch.id,
                "serial_ids": [(6, 0, batch.serial_ids.filtered("active").ids)],
            })
            batch.serial_ids.filtered("active").sudo().write({
                "current_warehouse_id": receipt.warehouse_id.id,
                "current_batch_id": batch.id,
                "current_location_id": receipt.picking_id.location_dest_id.id,
                "source_receipt_id": receipt.id,
            })

    def action_scan(self):
        self.ensure_one()
        if not (
            self.label_mode == "compatible"
            and self.created_batch_id
            and self.batch_id == self.created_batch_id
        ):
            return super().action_scan()
        if self.state != "scanning":
            raise UserError(_("La operación no está esperando labels."))
        code = (self.scan_code or "").strip()
        if not code:
            raise UserError(_("Escanee o escriba un código."))
        if self.scanned_count >= self.quantity:
            raise UserError(_("Ya se alcanzó la cantidad declarada."))
        Serial = self.env["inventory.unit.serial"].sudo()
        if Serial.search_count([("code", "=", code)]):
            raise UserError(_(
                "El label %s ya existe; revise que corresponda al documento de origen."
            ) % code)
        serial = Serial.create({
            "code": code,
            "batch_id": self.batch_id.id,
            "product_id": self.product_id.id,
            "current_warehouse_id": self.warehouse_id.id,
            "current_batch_id": self.batch_id.id,
            "source_receipt_id": self.id,
        })
        self.serial_ids = [(4, serial.id)]
        self.scan_code = False
        if self.scanned_count == self.quantity:
            self.state = "ready"
        return True

    def _ddwm_check_selected_batch_capacity(self):
        for receipt in self.filtered(
            lambda item: item.state == "draft"
            and item.destination_purpose == "storage"
            and item.batch_id
        ):
            snapshot = receipt.batch_id._ddwm_capacity_snapshot()
            if (
                snapshot["known"]
                and snapshot["current"] + receipt.quantity > snapshot["capacity"]
            ):
                raise ValidationError(_(
                    "El lote %(batch)s está en %(position)s: capacidad %(capacity)s, "
                    "ocupación %(current)s y espacio disponible %(available)s. "
                    "Seleccione otra posición para las %(incoming)s unidades recibidas."
                ) % {
                    "batch": receipt.batch_id.display_name,
                    "position": snapshot["position"].display_name,
                    "capacity": snapshot["capacity"],
                    "current": snapshot["current"],
                    "available": snapshot["available"],
                    "incoming": receipt.quantity,
                })

    def action_start(self):
        historic_serials = {
            receipt.id: receipt.batch_id.serial_ids
            for receipt in self
            if receipt.id and receipt.batch_id and receipt.batch_id.serial_ids
        }
        self._ddwm_create_batch_from_storage_reference()
        self._ddwm_check_selected_batch_capacity()
        result = super().action_start()
        Session = self.env["inventory.count.session"].sudo()
        for receipt in self.filtered(
            lambda item: item.label_mode == "generate"
            and item.destination_purpose == "storage"
            and item.batch_id
            and item.id in historic_serials
        ):
            new_serials = receipt.serial_ids - historic_serials[receipt.id]
            if not new_serials:
                continue
            active_session = Session.search([
                ("serial_batch_id", "=", receipt.batch_id.id),
                ("state", "in", ("counting", "review")),
            ], limit=1)
            if active_session:
                if not receipt.batch_id.is_mixed_batch:
                    raise UserError(_(
                        "El lote %(batch)s ya tiene la sesión %(session)s en proceso. "
                        "Termine esa lectura antes de agregar más unidades."
                    ) % {
                        "batch": receipt.batch_id.display_name,
                        "session": active_session.display_name,
                    })
                # A mixed position is intentionally a permanent receiving area.
                # Its additive IC must accept successive products and label
                # generations without discarding claims already scanned there.
                if active_session.state == "review":
                    active_session.action_back_to_counting()
                line = active_session.line_ids.filtered(
                    lambda item: item.product_id == receipt.product_id
                    and not item.lot_id and not item.package_id and not item.owner_id
                )[:1]
                if not line:
                    line = self.env["inventory.count.line"].sudo().create({
                        "session_id": active_session.id,
                        "product_id": receipt.product_id.id,
                        "expected_qty": 0.0,
                    })
                receipt.increment_session_id = active_session
                active_session.message_post(body=Markup(
                    "<p>El lote mixto recibió %(quantity)s labels nuevos de "
                    "%(product)s mediante %(receipt)s. La sesión permanece "
                    "en conteo para admitir productos y cargas sucesivas; las "
                    "lecturas anteriores se conservaron.</p>"
                ) % {
                    "quantity": len(new_serials),
                    "product": escape(receipt.product_id.display_name),
                    "receipt": escape(receipt.display_name),
                })
                continue
            session = Session.search([
                ("serial_batch_id", "=", receipt.batch_id.id),
                ("count_mode", "=", "additive"),
                ("state", "=", "done"),
            ], order="id desc", limit=1)
            if not session:
                raise UserError(_(
                    "El lote %(batch)s no tiene una sesión aditiva validada para "
                    "reabrir. Revise su carga inicial antes de agregar unidades."
                ) % {"batch": receipt.batch_id.display_name})
            line = session.line_ids.filtered(
                lambda item: item.product_id == receipt.product_id
            )[:1]
            if not line:
                if not receipt.batch_id.is_mixed_batch:
                    raise UserError(_(
                        "La sesión %(session)s no contiene el ITEM %(product)s."
                    ) % {
                        "session": session.display_name,
                        "product": receipt.product_id.display_name,
                    })
                line = self.env["inventory.count.line"].sudo().create({
                    "session_id": session.id,
                    "product_id": receipt.product_id.id,
                    "expected_qty": 0.0,
                })
            line.write({"counted_qty": 0.0, "is_counted": False})
            session.write({"state": "counting"})
            receipt.increment_session_id = session
            session.message_post(body=Markup(
                "<p>Sesión reabierta desde %(receipt)s para leer únicamente "
                "%(quantity)s labels nuevos del lote %(batch)s. Las lecturas "
                "históricas permanecen aplicadas.</p>"
            ) % {
                "receipt": escape(receipt.display_name),
                "quantity": len(new_serials),
                "batch": escape(receipt.batch_id.display_name),
            })
        return result

    def action_confirm(self):
        assignments = {
            receipt.id: {
                "batch": receipt.batch_id,
                "position": receipt.selected_batch_location,
                "serials": receipt.serial_ids.filtered("active"),
            }
            for receipt in self
        }
        result = super().action_confirm()
        for receipt in self:
            assignment = assignments.get(receipt.id, {})
            batch = assignment.get("batch")
            if not batch:
                continue
            labels = ", ".join(assignment["serials"].mapped("code"))
            destination_type = _("Lote mixto") if batch.is_mixed_batch else _(
                "Lote del mismo ITEM"
            )
            body = Markup(
                "<strong>Ubicación física confirmada</strong>"
                "<p>Tipo de destino: %(destination_type)s<br/>"
                "Lote: %(batch)s<br/>Posición: %(position)s<br/>"
                "ITEM: %(product)s<br/>Cantidad: %(quantity)s<br/>"
                "Labels: %(labels)s</p>"
            ) % {
                "destination_type": escape(destination_type),
                "batch": escape(batch.display_name),
                "position": escape(assignment["position"] or batch.display_name),
                "product": escape(receipt.product_id.display_name),
                "quantity": receipt.quantity,
                "labels": escape(labels or _("Sin labels")),
            }
            receipt.message_post(body=body)
            receipt.picking_id.message_post(body=body)
        return result


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddwm_operator_locations_html = fields.Html(
        string="Ubicaciones para la operación",
        compute="_compute_ddwm_operator_locations_html",
        sanitize=False,
    )

    def _ddwm_operation_warehouse(self):
        self.ensure_one()
        if self.picking_type_code == "incoming":
            return self.ddpc_dest_warehouse_id or self.picking_type_id.warehouse_id
        return self.ddpc_source_warehouse_id or self.picking_type_id.warehouse_id

    def _ddwm_recommended_destination(self, product, quantity, warehouse):
        """Read-only recommendation using the receipt's exact-ITEM-first rule."""
        Batch = self.env["inventory.serial.label.batch"]
        candidates = Batch.search([
            ("warehouse_id", "=", warehouse.id),
            ("state", "=", "generated"),
            "|", ("product_id", "=", product.id), ("is_mixed_batch", "=", True),
        ])
        eligible = []
        for batch in candidates:
            snapshot = batch._ddwm_capacity_snapshot()
            if snapshot.get("unlimited") or (
                snapshot["known"] and snapshot["available"] >= quantity
            ):
                eligible.append((batch, snapshot))
        eligible.sort(key=lambda item: (
            bool(item[0].is_mixed_batch),
            item[1]["available"], -item[1]["current"], item[0].name or "",
        ))
        if eligible:
            batch, snapshot = eligible[0]
            position = snapshot["position"]
            return {
                "batch": batch.display_name,
                "position": position.display_name if position else batch.display_name,
                "kind": _("Lote mixto") if batch.is_mixed_batch else _("Mismo ITEM"),
                "available": _("Sin límite") if snapshot.get("unlimited") else snapshot["available"],
            }
        occupied = {
            (name or "").strip().upper()
            for name in Batch.search([
                ("warehouse_id", "=", warehouse.id),
                ("state", "in", ("draft", "generated")),
            ]).mapped("name")
        }
        position = self.env["doorandoor.warehouse.map.position"].search([
            ("warehouse_id", "=", warehouse.id),
            ("active", "=", True),
            ("status", "=", "available"),
        ], order="aisle, horizontal_position, vertical_position, side, slot_number").filtered(
            lambda item: item.name.upper() not in occupied
        )[:1]
        return {
            "batch": False,
            "position": position.display_name if position else _("Sin posición disponible"),
            "kind": _("Nueva posición") if position else _("Revisión necesaria"),
            "available": position.capacity if position else 0,
        }

    def _ddwm_operator_location_rows(self):
        """Return current locations or incoming suggestions without mutations."""
        self.ensure_one()
        warehouse = self._ddwm_operation_warehouse()
        if not warehouse:
            return []
        rows = []
        moves = self.move_ids.filtered(lambda move: move.state != "cancel")
        if self.picking_type_code == "incoming":
            for move in moves:
                recommendation = self._ddwm_recommended_destination(
                    move.product_id, move.product_uom_qty, warehouse,
                )
                rows.append({
                    "mode": "destination", "product": move.product_id,
                    "quantity": move.product_uom_qty, "warehouse": warehouse.display_name,
                    "batch": recommendation["batch"] or "",
                    "position": recommendation["position"],
                    "location": warehouse.lot_stock_id.display_name, "labels": [],
                    "kind": recommendation["kind"], "available": recommendation["available"],
                })
            return rows

        Serial = self.env["inventory.unit.serial"]
        for move in moves:
            serials = self.ddmh_reserved_serial_ids.filtered(
                lambda serial: serial.active and serial.product_id == move.product_id
            )
            if not serials:
                serials = Serial.search([
                    ("active", "=", True), ("inventory_loaded", "=", True),
                    ("product_id", "=", move.product_id.id),
                    ("current_warehouse_id", "=", warehouse.id),
                    "|", ("reserved_picking_id", "=", False),
                    ("reserved_picking_id", "=", self.id),
                ], order="current_batch_id, code")
            grouped = {}
            for serial in serials:
                batch = serial.current_batch_id
                position = batch._ddwm_resolved_position() if batch else False
                key = (batch.id, serial.current_location_id.id)
                data = grouped.setdefault(key, {
                    "mode": "source", "product": move.product_id,
                    "quantity": move.product_uom_qty, "warehouse": warehouse.display_name,
                    "batch": batch.display_name if batch else "",
                    "position": position.display_name if position else (
                        batch.display_name if batch else _("Sin lote físico")
                    ),
                    "location": serial.current_location_id.display_name, "labels": [],
                    "kind": _("Reservado") if serial.reserved_picking_id == self else _("Disponible"),
                    "available": 0,
                })
                data["labels"].append(serial.code)
                data["available"] += 1
            if grouped:
                rows.extend(grouped.values())
            else:
                rows.append({
                    "mode": "source", "product": move.product_id,
                    "quantity": move.product_uom_qty, "warehouse": warehouse.display_name,
                    "batch": "", "position": _("No localizado"), "location": "",
                    "labels": [], "kind": _("Sin existencia localizada"), "available": 0,
                })
        return rows

    @api.depends(
        "move_ids.product_id", "move_ids.product_uom_qty", "move_ids.state",
        "ddmh_reserved_serial_ids", "ddmh_reserved_serial_ids.current_batch_id",
        "ddmh_reserved_serial_ids.current_location_id",
    )
    def _compute_ddwm_operator_locations_html(self):
        for picking in self:
            rows = picking._ddwm_operator_location_rows()
            if not rows:
                picking.ddwm_operator_locations_html = False
                continue
            title = _("Destino sugerido para recibir") if picking.picking_type_code == "incoming" else _("Ubicación para recoger")
            body = ["<div class='alert alert-info'><strong>%s</strong><br/>%s</div>" % (
                escape(title), escape(_("Información operativa; no mueve ni reserva inventario automáticamente.")),
            ), "<div class='table-responsive'><table class='table table-sm table-striped'><thead><tr>"]
            for heading in (_("ITEM"), _("Cantidad"), _("Almacén"), _("Lote / posición"), _("Ubicación"), _("Labels / estado")):
                body.append("<th>%s</th>" % escape(heading))
            body.append("</tr></thead><tbody>")
            for row in rows:
                labels = ", ".join(row["labels"]) or "%s: %s" % (row["kind"], row["available"])
                body.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s<br/><small>%s</small></td><td>%s</td><td>%s</td></tr>" % (
                    escape(row["product"].display_name), escape(row["quantity"]),
                    escape(row["warehouse"]), escape(row["position"]), escape(row["kind"]),
                    escape(row["location"]), escape(labels),
                ))
            body.append("</tbody></table></div>")
            picking.ddwm_operator_locations_html = Markup("".join(body))

    def _ddwm_receipt_destination_rows(self):
        self.ensure_one()
        rows = []
        controls = self.serial_receipt_ids.filtered(
            lambda receipt: receipt.state != "cancel" and receipt.batch_id
        )
        for receipt in controls:
            rows.append({
                "product": receipt.product_id,
                "quantity": receipt.quantity,
                "batch": receipt.batch_id.display_name,
                "destination_type": _("Mixto")
                if receipt.batch_id.is_mixed_batch else _("Mismo ITEM"),
                "position": receipt.selected_batch_location
                or receipt.batch_id.display_name,
                "labels": receipt.serial_ids.filtered("active").mapped("code"),
            })
        return rows


class StockMove(models.Model):
    _inherit = "stock.move"

    ddwm_operator_location_summary = fields.Text(
        string="Ubicación física / destino propuesto",
        compute="_compute_ddwm_operator_location_summary",
    )

    @api.depends(
        "picking_id.ddwm_operator_locations_html", "product_id",
        "product_uom_qty", "state",
    )
    def _compute_ddwm_operator_location_summary(self):
        by_picking = {}
        for move in self:
            picking = move.picking_id
            if not picking or move.state == "cancel":
                move.ddwm_operator_location_summary = False
                continue
            if picking.id not in by_picking:
                by_picking[picking.id] = picking._ddwm_operator_location_rows()
            rows = [row for row in by_picking[picking.id] if row["product"] == move.product_id]
            details = []
            for row in rows:
                if row["mode"] == "destination":
                    details.append(_(
                        "Propuesto: %(position)s (%(kind)s) · %(warehouse)s · %(available)s disponibles"
                    ) % {
                        "position": row["position"], "kind": row["kind"],
                        "warehouse": row["warehouse"], "available": row["available"],
                    })
                else:
                    labels = ", ".join(row["labels"])
                    details.append(_(
                        "Recoger: %(position)s · %(location)s · %(available)s disponibles%(labels)s"
                    ) % {
                        "position": row["position"], "location": row["location"],
                        "available": row["available"],
                        "labels": (" · Labels: %s" % labels) if labels else "",
                    })
            move.ddwm_operator_location_summary = "\n".join(details) or _("No localizado")
