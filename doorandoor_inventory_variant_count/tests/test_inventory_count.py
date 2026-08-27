from odoo import fields
from odoo.exceptions import UserError
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
