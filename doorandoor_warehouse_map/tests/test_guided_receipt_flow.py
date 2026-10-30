from lxml import etree

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGuidedReceiptFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.product = cls.env["product.product"].create({
            "name": "ITEM prueba recepción guiada",
            "default_code": "TEST-GUIDED-RECEIPT",
            "is_storable": True,
        })

    def _picking(self, source, destination, picking_type, quantity=2):
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
        })
        self.env["stock.move"].create({
            "name": self.product.display_name,
            "picking_id": picking.id,
            "product_id": self.product.id,
            "product_uom_qty": quantity,
            "product_uom": self.product.uom_id.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
        })
        picking.action_confirm()
        return picking

    def test_product_locator_accepts_complete_variant_display_name(self):
        attribute = self.env["product.attribute"].create({
            "name": "Atributo localizador completo",
        })
        value = self.env["product.attribute.value"].create({
            "name": "VALOR COMPLETO",
            "attribute_id": attribute.id,
        })
        template = self.env["product.template"].create({
            "name": "ITEM localizador variante",
            "is_storable": True,
            "attribute_line_ids": [(0, 0, {
                "attribute_id": attribute.id,
                "value_ids": [(6, 0, value.ids)],
            })],
        })
        product = template.product_variant_id
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA LOCALIZADOR NOMBRE COMPLETO",
            "company_id": self.env.company.id,
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "Z99A1-L",
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": product.id,
            "quantity": 1,
        })
        batch.action_generate_serials()
        batch.serial_ids.write({
            "current_warehouse_id": self.warehouse.id,
            "current_batch_id": batch.id,
            "current_location_id": self.warehouse.lot_stock_id.id,
            "inventory_loaded": True,
        })

        rows = self.env["inventory.serial.label.batch"].ddwm_find_product_locations(
            product.display_name,
            warehouse_id=self.warehouse.id,
        )

        self.assertEqual([row["batch_id"] for row in rows], [batch.id])

    def test_batch_trace_keeps_document_label_and_map_summary(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA TRAZABILIDAD DOCUMENTAL",
            "company_id": self.env.company.id,
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "Z99B1-L",
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
        })
        batch.action_generate_serials()
        batch.serial_ids.write({
            "current_warehouse_id": self.warehouse.id,
            "current_batch_id": batch.id,
            "current_location_id": self.warehouse.lot_stock_id.id,
            "inventory_loaded": True,
        })
        picking = self._picking(
            self.warehouse.lot_stock_id,
            self.env.ref("stock.stock_location_customers"),
            self.warehouse.out_type_id,
            quantity=2,
        )
        scanned, reserved = batch.serial_ids.sorted("id")
        scan = self.env["ddmh.picking.serial.scan"].create({
            "picking_id": picking.id,
            "serial_id": scanned.id,
        })
        reserved.write({
            "reserved_picking_id": picking.id,
            "reserved_by_id": self.env.user.id,
            "reserved_at": fields.Datetime.now(),
        })
        self.assertEqual(scan.batch_id, batch)
        self.env.flush_all()

        trace = self.env["doorandoor.batch.document.movement"].search([
            ("batch_id", "=", batch.id),
            ("picking_id", "=", picking.id),
        ])
        self.assertEqual(len(trace), 2)
        self.assertEqual(set(trace.mapped("serial_id").ids), {scanned.id, reserved.id})
        self.assertEqual(set(trace.mapped("movement_kind")), {"out"})
        self.assertEqual(
            set(trace.mapped("evidence_kind")), {"scan", "reservation"}
        )

        payload = batch.ddwm_map_payload(self.warehouse.id)
        row = next(
            item
            for zone in payload["zones"]
            for horizontal in zone["horizontal_positions"]
            for item in horizontal["items"]
            if item.get("batch_id") == batch.id
        )
        self.assertEqual(row["out_document_count"], 1)
        self.assertEqual(row["out_pending_qty"], 2)
        self.assertEqual(row["out_documents"][0]["id"], picking.id)

    def test_supplier_receipt_without_batch_creates_selected_position(self):
        picking = self._picking(
            self.supplier, self.warehouse.lot_stock_id, self.warehouse.in_type_id
        )
        position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "warehouse_prefix": "Z",
            "aisle": "9",
            "horizontal_position": "Z",
            "vertical_position": 9,
            "side": "L",
            "slot_number": 9,
            "status": "available",
        })

        picking.action_prepare_serial_receipt_lines()
        control = picking.serial_receipt_ids
        self.assertEqual(control.destination_purpose, "storage")
        self.assertFalse(control.batch_id)
        self.assertTrue(control.needs_empty_position)
        control.empty_position_id = position
        control.action_start()

        self.assertEqual(control.label_mode, "compatible")
        self.assertEqual(control.state, "scanning")
        self.assertEqual(control.created_batch_id.name, position.name)
        self.assertFalse(control.created_batch_id.serial_ids)
        for code in ("VENDOR-TEST-0001", "VENDOR-TEST-0002"):
            control.scan_code = code
            control.action_scan()
        self.assertEqual(control.state, "ready")
        self.assertEqual(control.scanned_count, 2)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product, self.warehouse.lot_stock_id
            ),
            0.0,
        )
        picking.action_validate_serial_receipt()
        self.assertEqual(picking.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product, self.warehouse.lot_stock_id
            ),
            2.0,
        )

    def test_batch_position_creation_inherits_authorized_warehouse(self):
        position_field = self.env[
            "doorandoor.warehouse.map.position"
        ]._fields["warehouse_id"]
        self.assertTrue(position_field.context["ddic_authorized_warehouse_search"])

        view = self.env.ref(
            "doorandoor_warehouse_map.view_inventory_serial_batch_storage_tracking"
        )
        arch = etree.fromstring(view.arch_db)
        nodes = arch.xpath(".//field[@name='ddwm_position_id']")
        self.assertEqual(len(nodes), 1)
        field_context = nodes[0].get("context", "")
        self.assertIn("'default_warehouse_id': warehouse_id", field_context)
        self.assertIn("'ddic_authorized_warehouse_search': True", field_context)

        defaults = self.env[
            "doorandoor.warehouse.map.position"
        ].with_context(
            default_warehouse_id=self.warehouse.id,
            ddic_authorized_warehouse_search=True,
            ddwm_batch_position_create=True,
        ).default_get(["warehouse_id"])
        self.assertEqual(defaults["warehouse_id"], self.warehouse.id)

    def test_selected_existing_batch_always_displays_its_physical_location(self):
        position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "warehouse_prefix": "Z",
            "aisle": "8",
            "horizontal_position": "A",
            "vertical_position": 2,
            "side": "R",
            "slot_number": 1,
            "status": "available",
        })
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA UBICACIÓN LOTE SELECCIONADO",
            "company_id": self.env.company.id,
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": position.id,
        })
        batch.action_generate_serials()
        picking = self._picking(
            self.supplier, self.warehouse.lot_stock_id, self.warehouse.in_type_id
        )
        receipt = self.env["inventory.serial.receipt"].create({
            "picking_id": picking.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "batch_id": batch.id,
            "quantity": 2,
            "operation_type": "supplier",
            "label_mode": "generate",
            "destination_purpose": "storage",
        })

        self.assertEqual(receipt.selected_batch_position_id, position)
        self.assertEqual(receipt.selected_batch_location, position.display_name)

        view = self.env["inventory.serial.receipt"].get_view(
            view_id=self.env.ref(
                "doorandoor_inventory_variant_count.view_inventory_serial_receipt_form"
            ).id,
            view_type="form",
        )
        arch = etree.fromstring(view["arch"])
        self.assertEqual(
            len(arch.xpath(".//field[@name='selected_batch_location']")), 1
        )

    def test_mixed_batch_accepts_multiple_items_without_capacity_limit(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA LOTE MIXTO SIN LÍMITE",
            "company_id": self.env.company.id,
        })
        position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "7",
            "horizontal_position": "M",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "capacity": 33,
            "status": "available",
        })
        mixed = self.env["inventory.serial.label.batch"].create({
            "name": position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "is_mixed_batch": True,
            "quantity": 0,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": position.id,
        })
        self.assertEqual(mixed.quantity, 0)
        mixed.action_generate_serials()

        hinges = self.env["product.product"].create({
            "name": "Bisagra para lote mixto",
            "default_code": "TEST-MIXED-HINGE",
            "is_storable": True,
        })
        mixed._ddic_add_serial_units(34, product=self.product)
        mixed._ddic_add_serial_units(40, product=hinges)

        snapshot = mixed._ddwm_capacity_snapshot()
        self.assertTrue(snapshot["unlimited"])
        self.assertFalse(snapshot["known"])
        self.assertEqual(snapshot["current"], 74)
        self.assertEqual(mixed.quantity, 74)
        self.assertEqual(mixed.mixed_product_count, 2)
        self.assertEqual(mixed.current_serial_ids.mapped("product_id"), self.product | hinges)
        payload = mixed.ddwm_map_payload(self.warehouse.id)
        mixed_zone_entries = [
            entry
            for zone in payload["zones"]
            for horizontal in zone["horizontal_positions"]
            for entry in horizontal["items"]
            if entry.get("batch_id") == mixed.id
        ]
        self.assertEqual(len(mixed_zone_entries), 1)
        self.assertIn("Mixto", mixed_zone_entries[0]["product"])

        normal_position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "7",
            "horizontal_position": "N",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "capacity": 33,
            "status": "available",
        })
        normal = self.env["inventory.serial.label.batch"].create({
            "name": normal_position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": normal_position.id,
        })
        normal_snapshot = normal._ddwm_capacity_snapshot()
        self.assertTrue(normal_snapshot["known"])
        self.assertEqual(normal_snapshot["capacity"], 33)
        self.assertFalse(normal_snapshot["unlimited"])

    def test_recommendation_prefers_exact_item_before_mixed_batch(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA PRIORIDAD ITEM EXACTO",
            "company_id": self.env.company.id,
        })
        exact_position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "91",
            "horizontal_position": "E",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "capacity": 33,
            "status": "available",
        })
        mixed_position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "90",
            "horizontal_position": "M",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "capacity": 33,
            "status": "available",
        })
        exact = self.env["inventory.serial.label.batch"].create({
            "name": exact_position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": exact_position.id,
        })
        exact.action_generate_serials()
        mixed = self.env["inventory.serial.label.batch"].create({
            "name": mixed_position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "is_mixed_batch": True,
            "quantity": 0,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": mixed_position.id,
        })
        mixed.action_generate_serials()

        receipt = self.env["inventory.serial.receipt"].new({
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "destination_purpose": "storage",
        })
        receipt._compute_candidate_batches()

        self.assertEqual(receipt.recommended_batch_id._origin, exact)
        self.assertFalse(receipt.recommended_batch_is_mixed)

        exact.serial_ids.write({"current_batch_id": False})
        exact.action_vacate()
        receipt._compute_candidate_batches()
        self.assertEqual(receipt.recommended_batch_id._origin, mixed)
        self.assertTrue(receipt.recommended_batch_is_mixed)

    def test_mixed_batch_keeps_initial_product_and_generates_first_load(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA MIXTA CON PRIMER ITEM",
            "company_id": self.env.company.id,
        })
        mixed = self.env["inventory.serial.label.batch"].create({
            "name": "MIXED-FIRST-ITEM",
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 3,
            "is_mixed_batch": True,
        })
        self.assertEqual(mixed.product_id, self.product)
        self.assertEqual(mixed.quantity, 3)

        mixed.action_generate_serials()

        self.assertEqual(mixed.state, "generated")
        self.assertEqual(len(mixed.current_serial_ids), 3)
        self.assertEqual(mixed.current_serial_ids.mapped("product_id"), self.product)

    def test_mixed_batch_reuses_open_ic_for_new_product_labels(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA MIXTA IC ABIERTA",
            "company_id": self.env.company.id,
        })
        mixed = self.env["inventory.serial.label.batch"].create({
            "name": "MIXED-OPEN-IC",
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "is_mixed_batch": True,
        })
        mixed.action_generate_serials()
        session = self.env["inventory.count.session"].create({
            "name": "IC MIXTA EN ESPERA",
            "location_id": self.warehouse.lot_stock_id.id,
            "count_mode": "additive",
            "load_reference": mixed.name,
            "serial_campaign_id": campaign.id,
            "serial_batch_id": mixed.id,
        })
        session.action_start()
        first_line = session.line_ids.filtered(
            lambda line: line.product_id == self.product
        )[:1]
        if not first_line:
            first_line = self.env["inventory.count.line"].create({
                "session_id": session.id,
                "product_id": self.product.id,
                "expected_qty": 0.0,
            })
        first_line.write({"counted_qty": 1.0, "is_counted": True})
        second_product = self.env["product.product"].create({
            "name": "ITEM adicional lote mixto",
            "default_code": "TEST-MIXED-OPEN-IC-SECOND",
            "is_storable": True,
        })
        receipt = self.env["inventory.serial.receipt"].create({
            "warehouse_id": self.warehouse.id,
            "product_id": second_product.id,
            "batch_id": mixed.id,
            "quantity": 40,
            "destination_purpose": "storage",
        })

        receipt.action_start()

        self.assertEqual(receipt.state, "ready")
        self.assertEqual(len(receipt.serial_ids), 40)
        self.assertEqual(receipt.increment_session_id, session)
        self.assertEqual(session.state, "counting")
        self.assertTrue(session.line_ids.filtered(
            lambda line: line.product_id == second_product
        ))
        self.assertEqual(first_line.counted_qty, 1.0)
        self.assertTrue(first_line.is_counted)
        self.assertEqual(mixed.quantity, 41)

    def test_guided_form_starts_with_editable_warehouse_and_document_products(self):
        picking = self._picking(
            self.supplier, self.warehouse.lot_stock_id, self.warehouse.in_type_id,
            quantity=4,
        )
        receipt = self.env["inventory.serial.receipt"].new({
            "warehouse_id": self.warehouse.id,
            "picking_id": picking.id,
        })
        receipt._onchange_picking_id_guided()
        self.assertEqual(receipt.candidate_product_ids._origin, self.product)
        self.assertEqual(receipt.product_id._origin, self.product)
        self.assertEqual(receipt.quantity, 4)
        self.assertEqual(receipt.label_mode, "compatible")

        view = self.env["inventory.serial.receipt"].get_view(
            view_id=self.env.ref(
                "doorandoor_inventory_variant_count.view_inventory_serial_receipt_form"
            ).id,
            view_type="form",
        )
        arch = etree.fromstring(view["arch"])
        warehouse = arch.xpath(".//field[@name='warehouse_id']")[0]
        product = arch.xpath(".//field[@name='product_id']")[0]
        self.assertEqual(warehouse.get("readonly"), "state != 'draft'")
        self.assertEqual(warehouse.get("domain"), "[]")
        self.assertIn("'ddic_authorized_warehouse_search': True", warehouse.get("context"))
        self.assertIn("'no_create': True", warehouse.get("options"))
        self.assertIn("'no_create_edit': True", warehouse.get("options"))
        self.assertIn("'no_open': True", warehouse.get("options"))
        self.assertIn("candidate_product_ids", product.get("domain"))

    def test_capacity_33_and_nearest_empty_position_are_recommended(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA CAPACIDAD 33",
            "company_id": self.env.company.id,
        })
        occupied = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "8",
            "horizontal_position": "B",
            "vertical_position": 2,
            "side": "L",
            "slot_number": 1,
            "status": "available",
        })
        occupied_tie = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "9",
            "horizontal_position": "B",
            "vertical_position": 2,
            "side": "L",
            "slot_number": 1,
            "status": "available",
        })
        near = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "8",
            "horizontal_position": "B",
            "vertical_position": 2,
            "side": "R",
            "slot_number": 1,
            "status": "available",
        })
        self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "20",
            "horizontal_position": "Z",
            "vertical_position": 9,
            "side": "R",
            "slot_number": 1,
            "status": "available",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": occupied.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 30,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": occupied.id,
        })
        batch.action_generate_serials()
        batch.serial_ids.write({
            "current_warehouse_id": self.warehouse.id,
            "current_batch_id": batch.id,
            "current_location_id": self.warehouse.lot_stock_id.id,
            "inventory_loaded": True,
        })
        batch_tie = self.env["inventory.serial.label.batch"].create({
            "name": occupied_tie.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 30,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": occupied_tie.id,
        })
        batch_tie.action_generate_serials()
        batch_tie.serial_ids.write({
            "current_warehouse_id": self.warehouse.id,
            "current_batch_id": batch_tie.id,
            "current_location_id": self.warehouse.lot_stock_id.id,
            "inventory_loaded": True,
        })

        receipt = self.env["inventory.serial.receipt"].new({
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 3,
            "destination_purpose": "storage",
        })
        receipt._compute_candidate_batches()
        self.assertEqual(receipt.recommended_batch_id._origin, batch)
        self.assertEqual(receipt.recommended_capacity, 33)
        self.assertEqual(receipt.recommended_available_quantity, 3)

        receipt.quantity = 4
        receipt._compute_candidate_batches()
        receipt._compute_candidate_empty_positions()
        self.assertFalse(receipt.recommended_batch_id)
        self.assertEqual(receipt.recommended_empty_position_id._origin, near)

    def test_vacated_batch_position_returns_to_receipt_selector(self):
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "CAMPAÑA LIBERAR POSICIÓN",
            "company_id": self.env.company.id,
        })
        position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "98",
            "horizontal_position": "Z",
            "vertical_position": 3,
            "status": "available",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": position.name,
            "campaign_id": campaign.id,
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "ddwm_storage_type": "fixed",
            "ddwm_position_id": position.id,
        })
        batch.action_generate_serials()
        batch.serial_ids.write({"current_batch_id": False})

        batch.action_vacate()

        receipt = self.env["inventory.serial.receipt"].new({
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
            "destination_purpose": "storage",
            "create_new_batch": True,
            "new_storage_type": "fixed",
        })
        receipt._compute_candidate_batches()
        receipt._compute_candidate_empty_positions()

        self.assertEqual(batch.state, "vacated")
        self.assertIn(position, receipt.candidate_empty_position_ids)

    def test_without_pending_document_creates_official_supplier_receipt(self):
        position = self.env["doorandoor.warehouse.map.position"].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "7",
            "horizontal_position": "C",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "status": "available",
        })
        receipt = self.env["inventory.serial.receipt"].create({
            "warehouse_id": self.warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
            "operation_type": "supplier",
            "label_mode": "generate",
            "destination_purpose": "storage",
            "new_document_reference": "PACKING-TEST-001",
            "create_new_batch": True,
            "new_storage_type": "fixed",
            "empty_position_id": position.id,
        })
        self.assertTrue(receipt.picking_id)
        self.assertEqual(receipt.picking_id.origin, "PACKING-TEST-001")
        self.assertEqual(receipt.picking_id.location_dest_id, self.warehouse.lot_stock_id)
        self.assertEqual(receipt.picking_id.move_ids.product_id, self.product)
        self.assertEqual(receipt.picking_id.move_ids.product_uom_qty, 2)
        self.assertEqual(receipt.created_batch_id.ddwm_position_id, position)
        self.assertTrue(receipt.picking_created_automatically)
        self.assertEqual(receipt.label_mode, "generate")
        self.assertEqual(len(receipt.serial_ids), 2)

    def test_internal_transfer_reuses_hanger_dispatch_labels(self):
        source = self.env["stock.warehouse"].create({
            "name": "Origen prueba recepción Hanger",
            "code": "TRH",
        })
        self.env["stock.quant"]._update_available_quantity(
            self.product, source.lot_stock_id, 2
        )
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "Campaña traslado Hanger %s" % fields.Datetime.now(),
            "company_id": self.env.company.id,
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "TEST-HANGER-SOURCE",
            "campaign_id": campaign.id,
            "warehouse_id": source.id,
            "product_id": self.product.id,
            "quantity": 2,
        })
        batch.action_generate_serials()
        batch.serial_ids.write({
            "current_warehouse_id": source.id,
            "current_batch_id": batch.id,
            "current_location_id": source.lot_stock_id.id,
            "inventory_loaded": True,
        })
        destination_position = self.env[
            "doorandoor.warehouse.map.position"
        ].create({
            "warehouse_id": self.warehouse.id,
            "aisle": "6",
            "horizontal_position": "D",
            "vertical_position": 1,
            "side": "L",
            "slot_number": 1,
            "status": "available",
        })
        picking = self._picking(
            source.lot_stock_id,
            self.warehouse.lot_stock_id,
            source.int_type_id,
        )
        for serial in batch.serial_ids:
            self.env["ddmh.picking.serial.scan"].create({
                "picking_id": picking.id,
                "serial_id": serial.id,
            })

        picking.action_prepare_serial_receipt_lines()
        control = picking.serial_receipt_ids
        self.assertEqual(control.operation_type, "internal")
        self.assertEqual(control.label_mode, "existing")
        self.assertFalse(control.picking_created_automatically)
        original_serial_ids = batch.serial_ids.ids
        with self.assertRaises(ValidationError):
            control.write({"label_mode": "generate"})
        control.empty_position_id = destination_position
        serial_count_before = self.env["inventory.unit.serial"].search_count([])
        control.action_start()
        self.assertTrue(control.created_batch_id)
        self.assertFalse(control.created_batch_id.serial_ids)
        self.assertEqual(
            self.env["inventory.unit.serial"].search_count([]), serial_count_before
        )
        for serial in batch.serial_ids:
            control.scan_code = serial.code
            control.action_scan()
        self.assertEqual(control.state, "ready")
        self.assertEqual(control.scanned_count, 2)
        picking.action_validate_serial_receipt()
        self.assertEqual(picking.state, "done")
        self.assertEqual(control.state, "done")
        self.assertEqual(control.serial_ids, batch.serial_ids)
        self.assertEqual(set(control.serial_ids.ids), set(original_serial_ids))
        self.assertTrue(all(
            serial.current_batch_id == control.created_batch_id
            for serial in control.serial_ids
        ))
