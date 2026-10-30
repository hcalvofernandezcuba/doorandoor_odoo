import re

from odoo import _, api, fields, models


class InventorySerialLabelBatch(models.Model):
    _inherit = "inventory.serial.label.batch"

    _DDWM_DEFAULT_POSITION_CAPACITY = 33

    ddwm_storage_type = fields.Selection(
        [
            ("fixed", "Posición fija"),
            ("mobile_pallet", "Paleta móvil"),
            ("cargo_container", "Contenedor de carga"),
        ],
        string="Tipo de almacenamiento",
        tracking=True,
        copy=False,
        help="Identifica si el lote ocupa una posición fija o un soporte móvil.",
    )
    ddwm_position_id = fields.Many2one(
        "doorandoor.warehouse.map.position",
        string="Posición física",
        tracking=True,
        copy=False,
        domain="[('warehouse_id', '=', warehouse_id), ('active', '=', True)]",
    )
    ddwm_out_document_count = fields.Integer(
        string="Documentos de salida",
        compute="_compute_ddwm_document_trace",
    )
    ddwm_out_done_qty = fields.Integer(
        string="Unidades salidas",
        compute="_compute_ddwm_document_trace",
    )
    ddwm_out_pending_qty = fields.Integer(
        string="Unidades en proceso de salida",
        compute="_compute_ddwm_document_trace",
    )

    def _compute_ddwm_document_trace(self):
        movements = self.env["doorandoor.batch.document.movement"].search([
            ("batch_id", "in", self.ids),
            ("movement_kind", "=", "out"),
            ("document_state", "!=", "cancel"),
        ]) if self.ids else self.env["doorandoor.batch.document.movement"]
        values = {
            batch.id: {"documents": set(), "done": 0, "pending": 0}
            for batch in self
        }
        for movement in movements:
            bucket = values.setdefault(
                movement.batch_id.id,
                {"documents": set(), "done": 0, "pending": 0},
            )
            bucket["documents"].add(movement.picking_id.id)
            if movement.document_state == "done":
                bucket["done"] += int(movement.quantity)
            else:
                bucket["pending"] += int(movement.quantity)
        for batch in self:
            bucket = values.get(
                batch.id, {"documents": set(), "done": 0, "pending": 0},
            )
            batch.ddwm_out_document_count = len(bucket["documents"])
            batch.ddwm_out_done_qty = bucket["done"]
            batch.ddwm_out_pending_qty = bucket["pending"]

    def action_ddwm_open_document_movements(self):
        self.ensure_one()
        action = self.env.ref(
            "doorandoor_warehouse_map.action_ddwm_batch_document_movement"
        ).read()[0]
        action["domain"] = [("batch_id", "=", self.id)]
        action["context"] = {
            "search_default_movement_out": 1,
            "search_default_group_document": 1,
        }
        action["display_name"] = _("Movimientos documentados de %s") % self.display_name
        return action

    @api.model
    def _ddwm_out_document_summary(self, batches):
        """Return exact outgoing documents captured by labels for map cards."""
        summaries = {
            batch.id: {
                "document_count": 0,
                "done_qty": 0,
                "pending_qty": 0,
                "documents": [],
            }
            for batch in batches
        }
        if not batches:
            return summaries
        movements = self.env["doorandoor.batch.document.movement"].search([
            ("batch_id", "in", batches.ids),
            ("movement_kind", "=", "out"),
            ("document_state", "!=", "cancel"),
        ], order="movement_datetime desc, id desc")
        state_labels = dict(
            self.env["stock.picking"]._fields["state"]._description_selection(self.env)
        )
        grouped = {}
        for movement in movements:
            key = (movement.batch_id.id, movement.picking_id.id)
            document = grouped.setdefault(key, {
                "id": movement.picking_id.id,
                "name": movement.picking_id.display_name,
                "state": movement.document_state,
                "state_label": state_labels.get(
                    movement.document_state, movement.document_state or "—"
                ),
                "date": fields.Datetime.to_string(movement.movement_datetime),
                "destination": (
                    movement.destination_warehouse_id.display_name
                    or movement.destination_location_id.display_name
                    or "—"
                ),
                "quantity": 0,
                "labels": [],
            })
            document["quantity"] += int(movement.quantity)
            document["labels"].append(movement.serial_code)
        for (batch_id, __picking_id), document in grouped.items():
            summary = summaries[batch_id]
            summary["document_count"] += 1
            if document["state"] == "done":
                summary["done_qty"] += document["quantity"]
            else:
                summary["pending_qty"] += document["quantity"]
            if len(summary["documents"]) < 5:
                summary["documents"].append(document)
        return summaries

    def _ddwm_resolved_position(self):
        """Return the map position backing this batch, including legacy batches."""
        self.ensure_one()
        if self.ddwm_position_id:
            return self.ddwm_position_id
        return self.env["doorandoor.warehouse.map.position"].search([
            ("warehouse_id", "=", self.warehouse_id.id),
            ("name", "=ilike", (self.name or "").strip()),
            ("active", "=", True),
        ], limit=1)

    def _ddwm_capacity_snapshot(self):
        """Use the same physical capacity and current-stock facts as the map."""
        self.ensure_one()
        position = self._ddwm_resolved_position()
        # A mixed position is an operational consolidation area: it can hold
        # doors, hinges and other ITEMs together.  The normal 33-door rule is
        # intentionally not applicable to it.
        unlimited = bool(self.is_mixed_batch)
        capacity = int(
            position.capacity or self._DDWM_DEFAULT_POSITION_CAPACITY
        ) if position and not unlimited else 0
        # Units already assigned to the physical batch reserve capacity even
        # while their receipt is waiting for final validation.  Ignoring those
        # prepared labels could let two operators overbook the same position.
        occupied_serials = self.current_serial_ids.filtered("active")
        current = (
            int(self.quantity or 0)
            if self.shared_serial and occupied_serials
            else len(occupied_serials)
        )
        return {
            "position": position,
            "capacity": capacity,
            "current": current,
            "available": max(capacity - current, 0) if capacity else 0,
            "known": bool(capacity),
            "unlimited": unlimited,
        }

    @api.model
    def ddwm_find_product_locations(self, term, warehouse_id=False, limit=20):
        """Locate active product batches for the map and operational deliveries.

        The method deliberately observes the same warehouse authorization used by
        the map, so other clients (notably delivery picking) can reuse it without
        duplicating access or location rules.
        """
        self.check_access_rights("read")
        query = (term or "").strip()
        if len(query) < 2:
            return []

        allowed_warehouses = self._ddic_allowed_warehouses()
        allowed_ids = allowed_warehouses.ids
        if warehouse_id:
            selected_id = int(warehouse_id)
            allowed_ids = [selected_id] if selected_id in allowed_ids else []
        if not allowed_ids:
            return []

        matched_serials = self.env["inventory.unit.serial"].search([
            ("code", "ilike", query),
            ("active", "=", True),
            ("current_warehouse_id", "in", allowed_ids),
            ("current_batch_id", "!=", False),
        ], order="code, id", limit=max(1, min(int(limit or 20), 50)))
        matched_by_batch = {}
        for serial in matched_serials:
            matched_by_batch.setdefault(serial.current_batch_id.id, []).append(serial.code)

        # The product autocomplete sends the complete variant display name
        # (template plus values).  ``display_name`` is computed and a domain
        # using ``ilike`` cannot reliably resolve that complete text.  Match
        # the selected value explicitly against the active products present
        # in each physical batch, while keeping the warehouse boundary.
        normalized_query = query.casefold()
        exact_product_batch_ids = []
        candidate_batches = self.search([
            ("warehouse_id", "in", allowed_ids),
            ("state", "=", "generated"),
        ])
        for batch in candidate_batches:
            products = batch.current_serial_ids.filtered("active").mapped("product_id")
            if any(
                (product.display_name or "").strip().casefold() == normalized_query
                for product in products
            ):
                exact_product_batch_ids.append(batch.id)

        product_domain = [
            "|", "|", "|", "|", "|",
            ("product_id.product_tmpl_id.name", "ilike", query),
            ("product_id.default_code", "ilike", query),
            ("product_id.barcode", "ilike", query),
            ("product_id.product_template_attribute_value_ids.name", "ilike", query),
            ("current_serial_ids.product_id.display_name", "ilike", query),
            ("name", "ilike", query),
        ]
        directly_matched_ids = list(
            set(matched_by_batch).union(exact_product_batch_ids)
        )
        batches = self.search(
            [
                ("warehouse_id", "in", allowed_ids),
                ("state", "=", "generated"),
            ] + (["|", ("id", "in", directly_matched_ids)] + product_domain if directly_matched_ids else product_domain),
            order="warehouse_id, name, id",
            limit=max(1, min(int(limit or 20), 50)),
        )
        results = []
        for batch in batches:
            active_serials = batch.current_serial_ids.filtered("active")
            if not active_serials:
                continue
            products = active_serials.mapped("product_id")
            product_label = (
                _("Mixto (%s ITEM)") % len(products)
                if batch.is_mixed_batch else batch.product_id.display_name
            )
            results.append({
                "batch_id": batch.id,
                "batch_name": batch.name,
                "warehouse_id": batch.warehouse_id.id,
                "warehouse_name": batch.warehouse_id.display_name,
                "product_id": batch.product_id.id,
                "product": product_label,
                "barcode": batch.product_id.barcode or "",
                "default_code": batch.product_id.default_code or "",
                "serials": len(active_serials),
                "counted": batch.counted_serial_count,
                "validated": batch.validated_serial_count,
                "pending": batch.pending_serial_count,
                "matched_labels": matched_by_batch.get(batch.id, []),
                "map_key": "batch-%s" % batch.id,
            })
        return results

    @api.model
    def ddwm_map_payload(self, warehouse_id=False):
        """Return read-only map data while preserving the standard record rules."""
        self.check_access_rights("read")
        allowed_warehouses = self._ddic_allowed_warehouses()
        warehouses = [
            {"id": warehouse.id, "name": warehouse.display_name}
            for warehouse in allowed_warehouses.sorted("name")
        ]
        allowed_ids = {warehouse["id"] for warehouse in warehouses}
        warehouse_ids_with_batches = set(
            self.search([
                ("warehouse_id", "in", list(allowed_ids)),
                ("state", "=", "generated"),
            ]).mapped("warehouse_id").ids
        ) if allowed_ids else set()
        selected_id = int(warehouse_id) if warehouse_id else False
        if selected_id not in allowed_ids:
            selected_id = next(
                (
                    warehouse["id"]
                    for warehouse in warehouses
                    if warehouse["id"] in warehouse_ids_with_batches
                ),
                warehouses[0]["id"] if warehouses else False,
            )

        empty = {
            "warehouses": warehouses,
            "selected_warehouse_id": selected_id,
            "zones": [],
            "summary": {
                "batches": 0,
                "serials": 0,
                "lot_entries": 0,
                "current_stock": 0,
                "counted": 0,
                "validated": 0,
                "pending": 0,
                "available": 0,
                "reserved": 0,
                "blocked": 0,
            },
        }
        if not selected_id:
            return empty

        selected_warehouse = allowed_warehouses.filtered(
            lambda warehouse: warehouse.id == selected_id
        )[:1]
        configured_vertical_levels = (
            selected_warehouse.ddwm_vertical_level_count
            if selected_warehouse else 0
        )

        batches = self.search(
            [("warehouse_id", "=", selected_id), ("state", "=", "generated")],
            order="name asc, id asc",
        )
        sessions = self.env["inventory.count.session"].search(
            [("serial_batch_id", "in", batches.ids)],
            order="date desc, id desc",
        )
        latest_session_by_batch = {}
        for session in sessions:
            latest_session_by_batch.setdefault(session.serial_batch_id.id, session)
        out_documents_by_batch = self._ddwm_out_document_summary(batches)

        zone_values = {}
        summary = empty["summary"]
        Position = self.env["doorandoor.warehouse.map.position"]
        physical_positions = Position.search([
            ("warehouse_id", "=", selected_id), ("active", "=", True),
        ])
        position_by_reference = {
            position.name.upper(): position for position in physical_positions
        }
        occupied_references = set()
        for batch in batches:
            # Keep both operational truths visible. Inactive loaded labels are
            # historical units that entered through this batch and later left;
            # active loaded labels are the units that still remain in stock.
            all_serials = self.env["inventory.unit.serial"].with_context(
                active_test=False
            ).search([("batch_id", "=", batch.id)])
            active_serials = all_serials.filtered("active")
            products = active_serials.mapped("product_id")
            product_label = (
                _("Mixto (%s ITEM)") % len(products)
                if batch.is_mixed_batch else batch.product_id.display_name
            )
            active_count = len(active_serials)
            lot_entries = len(all_serials.filtered("inventory_loaded"))
            current_stock = len(
                active_serials.filtered("inventory_loaded")
            )
            counted = batch.counted_serial_count
            validated = batch.validated_serial_count
            pending = batch.pending_serial_count
            session = latest_session_by_batch.get(batch.id)
            out_trace = out_documents_by_batch.get(batch.id, {})
            status = self._ddwm_batch_status(
                active_count, counted, validated, pending, session
            )
            (
                zone_name,
                warehouse_code,
                aisle,
                horizontal_position,
                vertical_position,
                product_suffix,
                position_order,
            ) = (
                self._ddwm_position_parts(batch.name)
            )
            item = {
                "key": "batch-%s" % batch.id,
                "id": batch.id,
                "batch_id": batch.id,
                "position_id": position_by_reference.get(
                    (batch.name or "").strip().upper()
                ).id if position_by_reference.get((batch.name or "").strip().upper()) else False,
                "is_empty": False,
                "reference": batch.name,
                "position_order": position_order,
                "warehouse_code": warehouse_code,
                "aisle": aisle,
                "horizontal_position": horizontal_position,
                "vertical_position": vertical_position,
                "product_suffix": product_suffix,
                "side": (
                    product_suffix[0]
                    if product_suffix and product_suffix[0] in ("L", "R")
                    else "C"
                ),
                "slot_number": (
                    int(product_suffix[1:])
                    if product_suffix
                    and product_suffix[0] in ("L", "R")
                    and product_suffix[1:].isdigit()
                    else 1
                ),
                "campaign": batch.campaign_id.display_name,
                "product_id": batch.product_id.id,
                "product": product_label,
                "image_url": (
                    "/web/image/product.product/%s/image_128" % batch.product_id.id
                    if batch.product_id else False
                ),
                "quantity": batch.quantity,
                "serials": active_count,
                "lot_entries": lot_entries,
                "current_stock": current_stock,
                "counted": counted,
                "validated": validated,
                "pending": pending,
                "out_document_count": out_trace.get("document_count", 0),
                "out_done_qty": out_trace.get("done_qty", 0),
                "out_pending_qty": out_trace.get("pending_qty", 0),
                "out_documents": out_trace.get("documents", []),
                "status": status[0],
                "status_label": status[1],
                "session_id": session.id if session else False,
                "session_name": session.display_name if session else False,
                "session_state": session.state if session else False,
                "session_state_label": dict(
                    session._fields["state"]._description_selection(self.env)
                ).get(session.state) if session else False,
            }
            occupied_references.add((batch.name or "").strip().upper())
            zone_values.setdefault(zone_name, []).append(item)
            summary["batches"] += 1
            summary["serials"] += active_count
            summary["lot_entries"] += lot_entries
            summary["current_stock"] += current_stock
            summary["counted"] += counted
            summary["validated"] += validated
            summary["pending"] += pending

        for position in physical_positions:
            reference = position.name.upper()
            if reference in occupied_references:
                continue
            suffix = position.custom_suffix or False
            if not suffix and position.side in ("L", "R"):
                suffix = position.side + (
                    str(position.slot_number) if position.slot_number > 1 else ""
                )
            status_labels = {
                "available": "Vacío",
                "reserved": "Reservado",
                "blocked": "Bloqueado",
                "maintenance": "Mantenimiento",
            }
            status = position.status
            item = {
                "key": "position-%s" % position.id,
                "id": False,
                "batch_id": False,
                "position_id": position.id,
                "is_empty": True,
                "reference": position.name,
                "position_order": self._ddwm_natural_key(position.name),
                "warehouse_code": position.warehouse_prefix or False,
                "aisle": position.aisle,
                "horizontal_position": position.horizontal_position,
                "vertical_position": str(position.vertical_position),
                "product_suffix": suffix,
                "side": position.side,
                "slot_number": position.slot_number,
                "campaign": False,
                "product_id": False,
                "product": False if status == "available" else status_labels[status],
                "image_url": False,
                "quantity": 0,
                "capacity": position.capacity,
                "serials": 0,
                "lot_entries": 0,
                "current_stock": 0,
                "counted": 0,
                "validated": 0,
                "pending": 0,
                "status": status,
                "status_label": status_labels[status],
                "session_id": False,
                "session_name": False,
                "session_state": False,
                "session_state_label": False,
                "note": position.note or False,
            }
            zone_name = "%s%s" % (
                position.warehouse_prefix or "", position.aisle
            )
            zone_values.setdefault(zone_name, []).append(item)
            if status == "available":
                summary["available"] += 1
            elif status == "reserved":
                summary["reserved"] += 1
            else:
                summary["blocked"] += 1

        zones = []
        for name, items in sorted(zone_values.items(), key=lambda value: self._ddwm_natural_key(value[0])):
            items.sort(key=lambda item: item["position_order"])
            horizontal_values = {}
            for item in items:
                horizontal_values.setdefault(
                    item["horizontal_position"], []
                ).append(item)
            horizontal_positions = [
                {
                    "name": horizontal,
                    "items": horizontal_items,
                    "levels": self._ddwm_levels(horizontal_items),
                    "serials": sum(item["serials"] for item in horizontal_items),
                    "lot_entries": sum(item["lot_entries"] for item in horizontal_items),
                    "current_stock": sum(item["current_stock"] for item in horizontal_items),
                    "counted": sum(item["counted"] for item in horizontal_items),
                    "validated": sum(item["validated"] for item in horizontal_items),
                    "pending": sum(item["pending"] for item in horizontal_items),
                }
                for horizontal, horizontal_items in sorted(
                    horizontal_values.items(),
                    key=lambda value: self._ddwm_natural_key(value[0]),
                )
            ]
            structured = name != "Otras posiciones"
            if structured:
                self._ddwm_complete_visual_levels(
                    horizontal_positions,
                    items[0]["warehouse_code"],
                    items[0]["aisle"],
                    configured_vertical_levels,
                )
            for horizontal in horizontal_positions:
                # Classic view follows the physical rack: highest level first,
                # level 1 fixed at the bottom, including intermediate empties.
                horizontal["classic_items"] = [
                    item
                    for level in horizontal["levels"]
                    for item in level["items"]
                ]
            zones.append({
                "name": name,
                "structured": structured,
                "warehouse_code": items[0]["warehouse_code"] if structured else False,
                "aisle": items[0]["aisle"] if structured else False,
                "horizontal_positions": horizontal_positions,
                "horizontal_count": len(horizontal_positions),
                "product_count": len(items),
            })
        empty["zones"] = zones
        return empty

    @api.model
    def _ddwm_complete_visual_levels(
        self, horizontal_positions, warehouse_code, aisle,
        configured_vertical_levels=0,
    ):
        """Draw the physical height and keep every real out-of-range level visible."""
        numeric_levels = [
            int(level["name"])
            for horizontal in horizontal_positions
            for level in horizontal["levels"]
            if str(level["name"]).isdigit()
        ]
        if not numeric_levels and not configured_vertical_levels:
            return
        maximum = max(
            [configured_vertical_levels or 0] + numeric_levels
        )
        for horizontal in horizontal_positions:
            levels_by_name = {str(level["name"]): level for level in horizontal["levels"]}
            completed = []
            for vertical in range(maximum, 0, -1):
                name = str(vertical)
                if name in levels_by_name:
                    completed.append(levels_by_name[name])
                    continue
                reference = "%s%s%s%s" % (
                    warehouse_code or "", aisle or "",
                    horizontal["name"], vertical,
                )
                placeholder = {
                    "key": "unconfigured-%s" % reference,
                    "id": False,
                    "batch_id": False,
                    "position_id": False,
                    "is_empty": True,
                    "reference": reference,
                    "position_order": self._ddwm_natural_key(reference),
                    "warehouse_code": warehouse_code or False,
                    "aisle": aisle,
                    "horizontal_position": horizontal["name"],
                    "vertical_position": name,
                    "product_suffix": False,
                    "side": "C",
                    "slot_number": 1,
                    "campaign": False,
                    "product_id": False,
                    "product": False,
                    "image_url": False,
                    "quantity": 0,
                    "capacity": 0,
                    "serials": 0,
                    "lot_entries": 0,
                    "current_stock": 0,
                    "counted": 0,
                    "validated": 0,
                    "pending": 0,
                    "status": "unconfigured",
                    "status_label": "Vacío",
                    "session_id": False,
                    "session_name": False,
                    "session_state": False,
                    "session_state_label": False,
                    "note": "Espacio físico vacío.",
                }
                completed.append({
                    "name": name,
                    "items": [placeholder],
                    "serials": 0,
                    "left_count": 0,
                    "right_count": 0,
                    "center_count": 1,
                })
            horizontal["levels"] = completed

    @api.model
    def _ddwm_levels(self, items):
        """Group subdivisions inside their physical vertical rack level."""
        values = {}
        for item in items:
            values.setdefault(item["vertical_position"] or "—", []).append(item)
        levels = []
        for vertical, level_items in sorted(
            values.items(),
            key=lambda value: self._ddwm_natural_key(value[0]),
            reverse=True,
        ):
            level_items.sort(
                key=lambda item: (
                    {"L": 0, "C": 1, "R": 2}.get(item["side"], 1),
                    item["slot_number"],
                    item["position_order"],
                )
            )
            levels.append({
                "name": vertical,
                "items": level_items,
                "serials": sum(item["serials"] for item in level_items),
                "left_count": len([item for item in level_items if item["side"] == "L"]),
                "right_count": len([item for item in level_items if item["side"] == "R"]),
                "center_count": len([item for item in level_items if item["side"] == "C"]),
            })
        return levels

    @api.model
    def _ddwm_batch_status(self, serials, counted, validated, pending, session):
        if serials and validated >= serials:
            return ("validated", "Validado")
        if session and session.state == "review":
            return ("review", "En revisión")
        if counted and pending:
            return ("partial", "Conteo parcial")
        if counted:
            return ("counted", "Contado")
        return ("pending", "Pendiente")

    @api.model
    def _ddwm_position_parts(self, reference):
        normalized = (reference or "Sin referencia").strip().upper()
        product_suffix = False
        base_reference = normalized
        slot_match = re.match(r"^(.+?)-([A-Z0-9]+)$", normalized)
        if slot_match:
            base_reference = slot_match.group(1).rstrip()
            product_suffix = slot_match.group(2)

        complete_match = re.match(
            r"^([A-Z])(\d+)([A-Z]+)(\d+)$", base_reference
        )
        if complete_match:
            warehouse_code, aisle, horizontal, vertical = complete_match.groups()
            return (
                "%s%s" % (warehouse_code, aisle),
                warehouse_code,
                aisle,
                horizontal,
                vertical,
                product_suffix,
                self._ddwm_natural_key(normalized),
            )

        implicit_match = re.match(r"^(\d+)([A-Z]+)(\d+)$", base_reference)
        if implicit_match:
            aisle, horizontal, vertical = implicit_match.groups()
            return (
                aisle,
                False,
                aisle,
                horizontal,
                vertical,
                product_suffix,
                self._ddwm_natural_key(normalized),
            )

        return (
            "Otras posiciones",
            False,
            False,
            base_reference,
            False,
            product_suffix,
            self._ddwm_natural_key(normalized),
        )

    @api.model
    def _ddwm_natural_key(self, value):
        return tuple(
            (0, int(part)) if part.isdigit() else (1, part.lower())
            for part in re.split(r"(\d+)", value or "")
        )
