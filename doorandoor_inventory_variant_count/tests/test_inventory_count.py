from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestInventoryCount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env["stock.location"].create({
            "name": "Test Count Bin", "location_id": cls.env.ref("stock.stock_location_stock").id,
            "usage": "internal",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Counted Variant", "is_storable": True,
        })
        cls.item_a = cls.env["product.count.item"].create({
            "name": "Component A", "product_id": cls.product.id,
            "code": "A", "barcode": "COUNT-A", "qty_per_product": 2,
        })
        cls.item_b = cls.env["product.count.item"].create({
            "name": "Component B", "product_id": cls.product.id,
            "code": "B", "barcode": "COUNT-B", "qty_per_product": 1,
        })
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.location, 5)

    def test_snapshot_and_derived_count(self):
        session = self.env["inventory.count.session"].create({"location_id": self.location.id})
        session.action_start()
        self.assertEqual(len(session.line_ids), 1)
        self.assertEqual(len(session.item_line_ids), 2)
        for line in session.item_line_ids:
            line.write({"counted_qty": 8 if line.item_id == self.item_a else 4, "is_counted": True})
        session.action_review()
        session._derive_variant_counts()
        self.assertEqual(session.line_ids.counted_qty, 4)

    def test_count_user_can_review_but_cannot_validate(self):
        warehouse = self.location.warehouse_id
        count_location = warehouse.lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            self.product, count_location, 5
        )
        operator = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Review Only Count Operator",
            "login": "review-only-count-operator@example.com",
            "groups_id": [Command.set([
                self.env.ref("base.group_user").id,
                self.env.ref(
                    "doorandoor_inventory_variant_count.group_inventory_count_user"
                ).id,
            ])],
            "ddpc_warehouse_ids": [Command.set(warehouse.ids)],
        })
        session = self.env["inventory.count.session"].create({
            "location_id": count_location.id,
        })
        session.action_start()
        session.line_ids.write({"counted_qty": 5, "is_counted": True})
        session.with_user(operator).action_review()

        self.assertEqual(session.state, "review")
        with self.assertRaises(AccessError):
            session.with_user(operator).action_validate()

    def test_count_operator_cannot_read_or_write_operational_prices(self):
        warehouse = self.location.warehouse_id
        operator = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Count Operator Without Prices",
            "login": "count-operator-without-prices@example.com",
            "groups_id": [Command.set([
                self.env.ref("base.group_user").id,
                self.env.ref(
                    "doorandoor_inventory_variant_count.group_inventory_count_user"
                ).id,
            ])],
            "ddpc_warehouse_ids": [Command.set(warehouse.ids)],
        })

        self.assertNotIn(
            "cost_price",
            self.env["inventory.count.line"].with_user(operator).fields_get(),
        )
        self.assertNotIn(
            "sale_price",
            self.env["inventory.count.line"].with_user(operator).fields_get(),
        )
        self.assertNotIn(
            "cost_price",
            self.env["inventory.count.variant.selector"].with_user(operator).fields_get(),
        )
        self.assertNotIn(
            "ddivc_unit_cost",
            self.env["stock.quant"].with_user(operator).fields_get(),
        )

        session = self.env["inventory.count.session"].create({
            "location_id": warehouse.lot_stock_id.id,
        })
        session.action_start()
        wizard = self.env["inventory.count.variant.selector"].with_user(operator).create({
            "session_id": session.id,
            "product_template_id": self.product.product_tmpl_id.id,
            "counted_qty": 1,
        })

        wizard.action_add_and_close()

        count_line = session.line_ids.filtered(
            lambda line: line.product_id == self.product
        )
        self.assertFalse(count_line.price_configured)

    def test_empty_location_can_start_initial_inventory(self):
        empty_location = self.env["stock.location"].create({
            "name": "Empty Initial Inventory Bin",
            "location_id": self.env.ref("stock.stock_location_stock").id,
            "usage": "internal",
        })
        session = self.env["inventory.count.session"].create({
            "location_id": empty_location.id,
        })

        session.action_start()

        self.assertEqual(session.state, "counting")
        self.assertFalse(session.line_ids)

    def test_location_autocomplete_is_filtered_server_side(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        other_warehouse = self.env["stock.warehouse"].create({
            "name": "Other Count Warehouse",
            "code": "OCW",
        })
        operator = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Restricted Count Operator",
            "login": "restricted-count-operator@example.com",
            "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            "ddpc_warehouse_ids": [Command.set(warehouse.ids)],
        })
        Location = self.env["stock.location"].with_user(operator).with_context(
            ddic_authorized_location_search=True,
            allowed_company_ids=operator.company_ids.ids,
        )
        Warehouse = self.env["stock.warehouse"].with_user(operator).with_context(
            ddic_authorized_warehouse_search=True,
            allowed_company_ids=operator.company_ids.ids,
        )

        result_ids = [record_id for record_id, _name in Location.name_search("", limit=100)]
        search_more_ids = Location.search([]).ids
        warehouse_result_ids = [
            record_id for record_id, _name in Warehouse.name_search("", limit=100)
        ]
        warehouse_search_more_ids = Warehouse.search([]).ids

        self.assertIn(warehouse.lot_stock_id.id, result_ids)
        self.assertNotIn(other_warehouse.lot_stock_id.id, result_ids)
        self.assertEqual(result_ids, [warehouse.lot_stock_id.id])
        self.assertEqual(search_more_ids, [warehouse.lot_stock_id.id])
        self.assertEqual(warehouse_result_ids, [warehouse.id])
        self.assertEqual(warehouse_search_more_ids, [warehouse.id])

    def test_assigned_warehouses_precede_administrator_global_scope(self):
        warehouse_a = self.env["stock.warehouse"].create({
            "name": "Assigned Administrative Warehouse",
            "code": "AAW",
        })
        warehouse_b = self.env["stock.warehouse"].create({
            "name": "Other Administrative Warehouse",
            "code": "OAW",
        })
        assigned_session = self.env["inventory.count.session"].create({
            "location_id": warehouse_a.lot_stock_id.id,
            "load_reference": "TEST-ASSIGNED-ADMIN",
        })
        other_session = self.env["inventory.count.session"].create({
            "location_id": warehouse_b.lot_stock_id.id,
            "load_reference": "TEST-OTHER-ADMIN",
        })
        administrator = self.env.ref("base.user_admin")
        administrator.sudo().write({
            "groups_id": [Command.link(
                self.env.ref(
                    "doorandoor_inventory_variant_count.group_inventory_count_manager"
                ).id
            )],
            "ddpc_warehouse_ids": [Command.set(warehouse_a.ids)],
            "ddpc_default_warehouse_id": warehouse_a.id,
        })

        visible_sessions = self.env["inventory.count.session"].with_user(
            administrator
        ).search([
            ("id", "in", (assigned_session | other_session).ids),
        ])

        self.assertIn(assigned_session, visible_sessions)
        self.assertNotIn(other_session, visible_sessions)

    def test_serial_receipt_guides_multiwarehouse_operator(self):
        warehouse_a = self.env["stock.warehouse"].create({
            "name": "Receipt Warehouse A",
            "code": "RWA",
        })
        warehouse_b = self.env["stock.warehouse"].create({
            "name": "Receipt Warehouse B",
            "code": "RWB",
        })
        unauthorized_warehouse = self.env["stock.warehouse"].create({
            "name": "Unauthorized Receipt Warehouse",
            "code": "URW",
        })
        # Reuse Odoo's administrator user because an optional installed module adds a
        # required SQL column to res_users but is loaded after this module's
        # tests. Creating a user here would therefore fail before that optional
        # Python field is registered, even though the receipt behavior is valid.
        # TransactionCase restores its original groups and assignments.
        operator = self.env.ref("base.user_admin")
        operator.sudo().write({
            "active": True,
            "groups_id": [Command.set([
                self.env.ref("base.group_user").id,
                self.env.ref(
                    "doorandoor_inventory_variant_count.group_inventory_count_user"
                ).id,
            ])],
            "ddpc_warehouse_ids": [Command.set((warehouse_a | warehouse_b).ids)],
            "ddpc_default_warehouse_id": warehouse_b.id,
        })
        supplier_location = self.env.ref("stock.stock_location_suppliers")

        def _incoming(warehouse):
            return self.env["stock.picking"].create({
                "picking_type_id": warehouse.in_type_id.id,
                "location_id": supplier_location.id,
                "location_dest_id": warehouse.lot_stock_id.id,
            })

        picking_a = _incoming(warehouse_a)
        picking_b = _incoming(warehouse_b)
        unauthorized_picking = _incoming(unauthorized_warehouse)
        Receipt = self.env["inventory.serial.receipt"].with_user(operator)

        defaults = Receipt.default_get(["warehouse_id"])
        self.assertEqual(defaults["warehouse_id"], warehouse_b.id)

        operator.ddpc_default_warehouse_id = False
        receipt = Receipt.new({"warehouse_id": False})
        candidate_ids = {
            candidate._origin.id for candidate in receipt.candidate_picking_ids
        }
        self.assertTrue(receipt.can_select_warehouse)
        self.assertIn(picking_a.id, candidate_ids)
        self.assertIn(picking_b.id, candidate_ids)
        self.assertNotIn(unauthorized_picking.id, candidate_ids)

        receipt.picking_id = picking_a
        onchange_result = receipt._onchange_picking_id()
        self.assertNotIn("warning", onchange_result or {})
        self.assertEqual(receipt.warehouse_id, warehouse_a)
        self.assertEqual(receipt.operation_type, "supplier")

    def test_guided_selector_creates_dynamic_variant_and_count_line(self):
        attribute = self.env["product.attribute"].create({
            "name": "Inventory Test Swing",
            "create_variant": "dynamic",
        })
        value_rh, value_lh = self.env["product.attribute.value"].create([
            {"name": "RH", "attribute_id": attribute.id},
            {"name": "LH", "attribute_id": attribute.id},
        ])
        template = self.env["product.template"].create({
            "name": "Guided Inventory Door",
            "is_storable": True,
            "list_price": 100,
            "attribute_line_ids": [Command.create({
                "attribute_id": attribute.id,
                "value_ids": [Command.set((value_rh | value_lh).ids)],
            })],
        })
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        wizard = self.env["inventory.count.variant.selector"].create({
            "session_id": session.id,
            "product_template_id": template.id,
            "counted_qty": 3,
            "cost_price": 60,
            "sale_price": 145,
        })
        wizard._load_attribute_lines()
        rh_template_value = template.attribute_line_ids.product_template_value_ids.filtered(
            lambda item: item.product_attribute_value_id == value_rh
        )
        wizard.attribute_line_ids.selected_template_value_id = rh_template_value

        wizard.action_add_and_close()

        count_line = session.line_ids.filtered(
            lambda item: item.product_id.product_tmpl_id == template
        )
        self.assertEqual(len(count_line), 1)
        self.assertEqual(count_line.counted_qty, 3)
        self.assertTrue(count_line.is_counted)
        self.assertFalse(count_line.price_configured)
        self.assertTrue(count_line.product_id.barcode)
        self.assertIn(
            rh_template_value,
            count_line.product_id.product_template_attribute_value_ids,
        )
        session.action_review()
        session.action_validate()
        self.assertEqual(count_line.product_id.standard_price, 0)
        self.assertEqual(count_line.product_id.product_tmpl_id.list_price, 100)
        self.assertEqual(count_line.product_id.ddpc_variant_extra_price, 0)

    def test_guided_selector_shows_no_variant_attributes_but_blocks_count(self):
        attribute = self.env["product.attribute"].create({
            "name": "Inventory Test Finish",
            "create_variant": "no_variant",
        })
        value = self.env["product.attribute.value"].create({
            "name": "Painted",
            "attribute_id": attribute.id,
        })
        template = self.env["product.template"].create({
            "name": "Guided Inventory Non Variant",
            "is_storable": True,
            "attribute_line_ids": [Command.create({
                "attribute_id": attribute.id,
                "value_ids": [Command.set(value.ids)],
            })],
        })
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        wizard = self.env["inventory.count.variant.selector"].create({
            "session_id": session.id,
            "product_template_id": template.id,
            "counted_qty": 1,
        })

        wizard._load_attribute_lines()

        self.assertEqual(wizard.attribute_line_ids.attribute_id, attribute)
        wizard.attribute_line_ids.selected_template_value_id = (
            template.attribute_line_ids.product_template_value_ids
        )
        with self.assertRaises(UserError):
            wizard.action_add_and_close()

    def test_inconsistent_items_are_blocked(self):
        session = self.env["inventory.count.session"].create({"location_id": self.location.id})
        session.action_start()
        for line in session.item_line_ids:
            line.write({"counted_qty": 8 if line.item_id == self.item_a else 3, "is_counted": True})
        with self.assertRaises(UserError):
            session._derive_variant_counts()

    def test_product_variant_barcode_adds_direct_count(self):
        self.product.barcode = "DIRECT-VARIANT-COUNT"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        session.write({
            "barcode_input": self.product.barcode,
            "scan_qty": 2,
        })
        session.action_scan()
        self.assertEqual(session.line_ids.counted_qty, 2)
        self.assertTrue(session.line_ids.is_counted)
        self.assertFalse(any(session.item_line_ids.mapped("is_counted")))
        session.action_review()
        session._derive_variant_counts()
        self.assertEqual(session.line_ids.counted_qty, 2)

    def test_direct_barcode_argument_does_not_require_saved_input(self):
        self.product.barcode = "DIRECT-RPC-BARCODE"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()

        session.action_scan(self.product.barcode)

        self.assertFalse(session.barcode_input)
        self.assertEqual(session.line_ids.counted_qty, 1)
        self.assertTrue(session.line_ids.is_counted)

    def test_lot_label_records_quantity_on_exact_lot_line(self):
        lot_product = self.env["product.product"].create({
            "name": "Quantity Bearing Hinges",
            "is_storable": True,
            "tracking": "lot",
        })
        lot = self.env["stock.lot"].create({
            "name": "HINGE-BATCH-001",
            "product_id": lot_product.id,
            "company_id": self.env.company.id,
        })
        self.env["stock.quant"]._update_available_quantity(
            lot_product, self.location, 10, lot_id=lot
        )
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "absolute",
            "load_reference": "HINGE-CHECK-001",
        })
        session.action_start()
        session.scan_qty = 4

        result = session.action_scan(lot.name)

        line = session.line_ids.filtered(lambda count: count.lot_id == lot)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.expected_qty, 10)
        self.assertEqual(line.counted_qty, 4)
        self.assertTrue(line.is_counted)
        self.assertEqual(result["lot_name"], lot.name)

    def test_additive_lot_label_creates_traced_quantity_line(self):
        lot_product = self.env["product.product"].create({
            "name": "New Quantity Bearing Hinges",
            "is_storable": True,
            "tracking": "lot",
        })
        lot = self.env["stock.lot"].create({
            "name": "HINGE-BATCH-NEW",
            "product_id": lot_product.id,
            "company_id": self.env.company.id,
        })
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "HINGE-LOAD-NEW",
        })
        session.action_start()
        session.scan_qty = 25

        session.action_scan(lot.name)

        line = session.line_ids.filtered(lambda count: count.lot_id == lot)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.expected_qty, 0)
        self.assertEqual(line.counted_qty, 25)
        self.assertEqual(line.result_qty, 25)
        session.action_review()
        session.action_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                lot_product, self.location, lot_id=lot
            ),
            25,
        )

    def test_direct_and_component_scans_cannot_be_mixed(self):
        self.product.barcode = "DIRECT-NO-MIX"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        session.write({"barcode_input": self.item_a.barcode, "scan_qty": 1})
        session.action_scan()
        session.barcode_input = self.product.barcode
        with self.assertRaises(UserError):
            session.action_scan()

    def test_scan_adds_unexpected_variant_with_zero_expected_stock(self):
        unexpected = self.env["product.product"].create({
            "name": "Unexpected Physical Variant",
            "is_storable": True,
            "barcode": "UNEXPECTED-VARIANT-001",
        })
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        session.write({
            "barcode_input": unexpected.barcode,
            "scan_qty": 1,
        })

        session.action_scan()

        line = session.line_ids.filtered(lambda count: count.product_id == unexpected)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.expected_qty, 0)
        self.assertEqual(line.counted_qty, 1)
        self.assertTrue(line.is_counted)

    def test_partial_count_validates_only_scanned_variants(self):
        untouched = self.env["product.product"].create({
            "name": "Untouched Variant",
            "is_storable": True,
            "barcode": "UNTOUCHED-VARIANT-001",
        })
        self.env["stock.quant"]._update_available_quantity(
            untouched, self.location, 7
        )
        self.product.barcode = "PARTIAL-COUNT-001"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
        })
        session.action_start()
        session.action_scan(self.product.barcode)

        session.action_review()
        session.action_validate()

        untouched_qty = self.env["stock.quant"]._get_available_quantity(
            untouched, self.location
        )
        self.assertEqual(untouched_qty, 7)
        self.assertEqual(session.state, "done")

    def test_additive_pallet_adds_to_snapshot_quantity(self):
        self.product.barcode = "ADDITIVE-PALLET-001"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "test-pallet-001",
        })
        session.action_start()
        self.assertEqual(session.line_ids.expected_qty, 5)

        session.write({"scan_qty": 3})
        session.action_scan(self.product.barcode)

        self.assertEqual(session.line_ids.counted_qty, 3)
        self.assertEqual(session.line_ids.difference_qty, 3)
        self.assertEqual(session.line_ids.result_qty, 8)
        session.action_review()
        session.action_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product, self.location
            ),
            8,
        )

    def test_additive_pallet_uses_current_stock_when_snapshot_changed(self):
        self.product.barcode = "ADDITIVE-PALLET-STALE"
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "test-pallet-stale",
        })
        session.action_start()
        session.action_scan(self.product.barcode)
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.location, 1
        )
        session.action_review()

        session.action_validate()

        self.assertEqual(session.state, "done")
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product, self.location
            ),
            7,
        )

    def test_additive_pallet_reference_is_unique_per_location(self):
        values = {
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "TEST-PALLET-UNIQUE",
        }
        self.env["inventory.count.session"].create(values)
        with self.assertRaises(ValidationError):
            self.env["inventory.count.session"].create(values)

    def test_vacated_serial_batch_releases_additive_session_reference(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "RELEASE ADDITIVE REFERENCE",
        })
        historic_batch = self.env["inventory.serial.label.batch"].create({
            "name": "5C3",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        historic_batch.action_generate_serials()
        historic_session = self.env["inventory.count.session"].create({
            "location_id": warehouse.lot_stock_id.id,
            "count_mode": "additive",
            "load_reference": "5C3",
            "serial_campaign_id": campaign.id,
            "serial_batch_id": historic_batch.id,
        })
        historic_batch.serial_ids.write({"current_batch_id": False})
        historic_batch.action_vacate()

        replacement_batch = self.env["inventory.serial.label.batch"].create({
            "name": "5C3",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        replacement_session = self.env["inventory.count.session"].create({
            "location_id": warehouse.lot_stock_id.id,
            "count_mode": "additive",
            "load_reference": "5C3",
            "serial_campaign_id": campaign.id,
            "serial_batch_id": replacement_batch.id,
        })

        self.assertEqual(historic_session.load_reference, "5C3")
        self.assertEqual(replacement_session.load_reference, "5C3")

    def test_serialized_labels_are_unique_and_cannot_be_counted_twice(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "INITIAL SERIAL PILOT",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "pilot-pallet-001",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
        })

        batch.action_generate_serials()

        self.assertEqual(batch.name, "PILOT-PALLET-001")
        self.assertEqual(len(batch.serial_ids), 2)
        self.assertEqual(len(set(batch.serial_ids.mapped("code"))), 2)
        self.assertTrue(all(len(code) == 8 for code in batch.serial_ids.mapped("code")))
        payloads = batch._label_payloads()
        self.assertEqual({item["product_code"] for item in payloads}, set(batch.serial_ids.mapped("code")))
        self.assertTrue(all(item["is_unit_serial"] for item in payloads))
        expected_variant_values = ", ".join(
            batch.product_id.product_template_attribute_value_ids.mapped("name")
        )
        self.assertTrue(all(item["variant_values"] == expected_variant_values for item in payloads))
        self.assertTrue(all(item["product_name"] not in item["variant_values"] for item in payloads))
        expected_variant_description = " · ".join(
            "%s: %s" % (
                (value.attribute_id.display_name or "").removeprefix("PH ").upper(),
                value.name or "",
            )
            for value in batch.product_id.product_template_attribute_value_ids
            if value.name
        )
        self.assertTrue(all(
            item["variant_description"] == expected_variant_description
            for item in payloads
        ))

        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "PILOT-PALLET-001",
            "serial_campaign_id": campaign.id,
            "serial_batch_id": batch.id,
        })

        session.action_start()
        first_serial = batch.serial_ids[0]
        session.action_scan(first_serial.code)
        self.assertEqual(session.line_ids.filtered("is_counted").counted_qty, 1)
        audit = session._serial_audit_report_data()
        self.assertEqual(audit["expected"], 2)
        self.assertEqual(audit["counted"], 1)
        self.assertEqual(audit["pending"], 1)
        self.assertEqual(audit["rows"][0]["batch"], "PILOT-PALLET-001")
        self.assertEqual(
            [
                detail["code"]
                for detail in audit["rows"][0]["details"]
                if detail["status"] == "Pendiente"
            ],
            (batch.serial_ids - first_serial).mapped("code"),
        )

        with self.assertRaises(UserError):
            session.action_scan(first_serial.code)

        concurrent = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "additive",
            "load_reference": "PILOT-PALLET-002",
            "serial_campaign_id": campaign.id,
            "serial_batch_id": batch.id,
        })
        concurrent.action_start()
        with self.assertRaises(UserError):
            concurrent.action_scan(first_serial.code)

        with self.assertRaises(UserError):
            session.action_review()
        session.note = "Un serial impreso no apareció físicamente durante el conteo."
        session.action_review()
        session.action_validate()
        self.assertTrue(first_serial.inventory_loaded)
        self.assertEqual(first_serial.loaded_session_id, session)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(self.product, self.location),
            6,
        )

    def test_vacated_batch_releases_reference_for_new_batch(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "REUSE CANCELLED BATCH REFERENCE",
        })
        vacated = self.env["inventory.serial.label.batch"].create({
            "name": "5C3",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
        })
        vacated.action_generate_serials()
        vacated.serial_ids.write({"current_batch_id": False})
        vacated.action_vacate()

        replacement = self.env["inventory.serial.label.batch"].create({
            "name": "5c3",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 3,
        })

        self.assertEqual(replacement.name, "5C3")
        self.assertEqual(vacated.name, "5C3-VACIADO-%s" % vacated.id)
        self.assertEqual(vacated.state, "vacated")
        self.assertTrue(vacated.serial_ids.filtered("active"))

        replacement.action_generate_serials()
        replacement.serial_ids.write({"current_batch_id": False})
        replacement.action_vacate()
        another_campaign = self.env["inventory.serial.campaign"].create({
            "name": "REUSE PHYSICAL REFERENCE IN ANOTHER CAMPAIGN",
        })
        cross_campaign = self.env["inventory.serial.label.batch"].create({
            "name": "5C3",
            "campaign_id": another_campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        self.assertEqual(cross_campaign.name, "5C3")

        with self.assertRaises(ValidationError):
            self.env["inventory.serial.label.batch"].create({
                "name": "5C3",
                "campaign_id": campaign.id,
                "warehouse_id": warehouse.id,
                "product_id": self.product.id,
                "quantity": 1,
            })

    def test_serialized_label_keeps_complete_item_when_product_has_no_attributes(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        product = self.env["product.product"].create({
            "name": "Impact single doors (RH, bronze, 39, 96, gwi)",
            "is_storable": True,
        })
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "LABEL ITEM FALLBACK TEST",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "D39A1-TEST",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": product.id,
            "quantity": 1,
        })
        batch.action_generate_serials()

        payload = batch._label_payloads()[0]

        self.assertEqual(payload["product_name"], "Impact single doors")
        self.assertEqual(
            payload["variant_description"],
            "ITEM: RH | bronze | 39 | 96 | gwi",
        )

    def test_increment_keeps_historical_serials_and_prints_only_new_units(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "INCREMENT SERIAL TEST",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "INCREMENT-UNIT-LOT",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 2,
        })
        batch.action_generate_serials()
        historical = batch.serial_ids
        historical.write({"inventory_loaded": True})

        new_serials = batch._ddic_add_serial_units(
            3,
            codes=["INC-UNIT-001", "INC-UNIT-002", "INC-UNIT-003"],
        )

        self.assertEqual(batch.quantity, 5)
        self.assertEqual(len(batch.serial_ids), 5)
        self.assertEqual(len(new_serials), 3)
        self.assertTrue(all(historical.mapped("inventory_loaded")))
        self.assertFalse(any(new_serials.mapped("inventory_loaded")))
        self.assertEqual(len(batch._label_payloads(new_serials)), 3)

    def test_shared_lot_increment_prints_increment_not_accumulated_total(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        product = self.env["product.product"].create({
            "name": "Shared Label Increment Product",
            "is_storable": True,
        })
        product.product_tmpl_id.ddic_shared_lot_serial = True
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "INCREMENT SHARED TEST",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "INCREMENT-SHARED-LOT",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": product.id,
            "quantity": 100,
        })
        batch.action_generate_serials()
        original_code = batch.serial_ids.code
        batch.serial_ids.write({"inventory_loaded": True})

        shared_serial = batch._ddic_add_serial_units(3)
        payloads = batch._label_payloads(shared_serial, shared_quantity=3)

        self.assertEqual(batch.quantity, 103)
        self.assertEqual(len(batch.serial_ids), 1)
        self.assertEqual(shared_serial.code, original_code)
        self.assertEqual(len(payloads), 3)
        self.assertEqual({payload["unit_serial"] for payload in payloads}, {original_code})

    def test_serial_from_another_campaign_is_rejected_by_lot_session(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        origin_campaign = self.env["inventory.serial.campaign"].create({
            "name": "SERIAL ORIGIN CAMPAIGN",
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "ORIGIN-PALLET",
            "campaign_id": origin_campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        batch.action_generate_serials()
        future_campaign = self.env["inventory.serial.campaign"].create({
            "name": "FUTURE PHYSICAL COUNT",
        })
        future_batch = self.env["inventory.serial.label.batch"].create({
            "name": "FUTURE-LOT",
            "campaign_id": future_campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        future_batch.action_generate_serials()
        session = self.env["inventory.count.session"].create({
            "location_id": self.location.id,
            "count_mode": "absolute",
            "serial_campaign_id": future_campaign.id,
            "serial_batch_id": future_batch.id,
        })
        session.action_start()

        with self.assertRaises(UserError):
            session.action_scan(batch.serial_ids.code)
        self.assertFalse(session.serial_claim_ids)

    def test_button_generates_ordered_ean13_barcodes(self):
        products = self.env["product.product"].create([
            {"name": "On-demand Barcode A"},
            {"name": "On-demand Barcode B"},
        ])
        self.assertFalse(products[0].barcode)
        self.assertFalse(products[1].barcode)
        products.action_generate_doorandoor_barcode()
        self.assertRegex(products[0].barcode, r"^\d{13}$")
        self.assertRegex(products[1].barcode, r"^\d{13}$")
        self.assertNotEqual(products[0].barcode, products[1].barcode)
        self.assertEqual(products[0].barcode[:8], fields.Date.context_today(products[0]).strftime("%Y%m%d"))
        self.assertEqual(int(products[1].barcode[8:12]), int(products[0].barcode[8:12]) + 1)
        for product in products:
            expected_digit = product._doorandoor_ean13_check_digit(product.barcode[:12])
            self.assertEqual(product.barcode[-1], expected_digit)

    def test_manual_product_barcode_is_preserved(self):
        product = self.env["product.product"].create({
            "name": "Manual Barcode",
            "barcode": "MANUAL-CODE-001",
        })
        self.assertEqual(product.barcode, "MANUAL-CODE-001")
        with self.assertRaises(UserError):
            product.action_generate_doorandoor_barcode()

    def test_variant_label_payloads_use_variant_barcodes(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        self.product.barcode = "VARIANT-COUNT-A"
        wizard = self.env["ddsl.product.label.wizard"].create({
            "product_tmpl_id": self.product.product_tmpl_id.id,
            "warehouse_id": warehouse.id,
            "company_id": self.env.company.id,
            "quantity": 2,
            "label_scope": "variants",
            "variant_ids": [(6, 0, self.product.ids)],
        })
        payloads = wizard._prepare_label_payloads()
        self.assertEqual(len(payloads), 2)
        self.assertEqual({payload["product_code"] for payload in payloads}, {"VARIANT-COUNT-A"})
        self.assertTrue(all(payload["variant_name"] for payload in payloads))
        self.assertTrue(all("variant_attributes" in payload for payload in payloads))
        self.assertEqual(wizard.selected_variant_count, 1)
        self.assertEqual(wizard.total_batches, 1)

        wizard.batch_number = 2
        with self.assertRaises(UserError):
            wizard._prepare_label_payloads()

        wizard.write({"batch_number": 1, "quantity": 51})
        with self.assertRaises(UserError):
            wizard._prepare_label_payloads()

    def test_variant_label_generates_and_persists_missing_barcode(self):
        warehouse = self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        self.product.barcode = False
        wizard = self.env["ddsl.product.label.wizard"].create({
            "product_tmpl_id": self.product.product_tmpl_id.id,
            "warehouse_id": warehouse.id,
            "company_id": self.env.company.id,
            "quantity": 1,
            "label_scope": "variants",
            "variant_ids": [(6, 0, self.product.ids)],
        })

        payloads = wizard._prepare_label_payloads()

        self.assertTrue(self.product.barcode)
        self.assertEqual(payloads[0]["product_code"], self.product.barcode)
