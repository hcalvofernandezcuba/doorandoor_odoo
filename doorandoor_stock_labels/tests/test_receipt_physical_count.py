from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestReceiptPhysicalCount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([
            ("company_id", "=", cls.env.company.id),
        ], limit=1)
        cls.picking_type = cls.warehouse.in_type_id
        cls.product = cls.env["product.product"].create({
            "name": "Receipt Scan Product",
            "is_storable": True,
            "barcode": "RECEIPT-SCAN-001",
        })

    def _create_picking(self):
        return self.env["stock.picking"].create({
            "picking_type_id": self.picking_type.id,
            "location_id": self.picking_type.default_location_src_id.id,
            "location_dest_id": self.picking_type.default_location_dest_id.id,
        })

    def _create_planned_move(self, picking, quantity=5.0):
        return self.env["stock.move"].create({
            "name": self.product.display_name,
            "picking_id": picking.id,
            "product_id": self.product.id,
            "product_uom": self.product.uom_id.id,
            "product_uom_qty": quantity,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        })

    def test_scan_adds_unexpected_product_and_persists_count(self):
        picking = self._create_picking()
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)

        first_result = wizard.action_register_scan(self.product.barcode)
        second_result = wizard.action_register_scan(self.product.barcode)

        count = picking.ddsl_receipt_count_ids
        self.assertEqual(len(count), 1)
        self.assertEqual(count.product_id, self.product)
        self.assertEqual(count.expected_qty, 0)
        self.assertEqual(count.counted_qty, 2)
        self.assertEqual(count.difference_qty, 2)
        self.assertEqual(first_result["counted_qty"], 1)
        self.assertEqual(second_result["counted_qty"], 2)
        self.assertEqual(second_result["product_name"], self.product.display_name)
        self.assertFalse(picking.move_ids)

        reopened = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)
        self.assertEqual(reopened.line_ids.counted_qty, 2)
        self.assertEqual(reopened.line_ids.expected_qty, 0)

    def test_apply_creates_move_without_changing_stock_until_validation(self):
        picking = self._create_picking()
        quantity_before = self.env["stock.quant"]._get_available_quantity(
            self.product, picking.location_dest_id
        )
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)
        wizard.action_register_scan(self.product.barcode)
        wizard.action_register_scan(self.product.barcode)

        wizard.action_apply_count()

        move = picking.move_ids
        self.assertEqual(len(move), 1)
        self.assertTrue(move.ddsl_receipt_scan_generated)
        self.assertEqual(move.product_uom_qty, 2)
        self.assertEqual(move.move_line_ids.quantity, 2)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product, picking.location_dest_id
            ),
            quantity_before,
        )
        reopened = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)
        self.assertEqual(reopened.line_ids.expected_qty, 0)
        self.assertEqual(reopened.line_ids.counted_qty, 2)

    def test_planned_quantity_remains_separate_from_physical_count(self):
        picking = self._create_picking()
        self._create_planned_move(picking, quantity=5)
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)

        wizard.action_register_scan(self.product.barcode)
        wizard.action_register_scan(self.product.barcode)

        count = picking.ddsl_receipt_count_ids
        self.assertEqual(count.expected_qty, 5)
        self.assertEqual(count.counted_qty, 2)
        self.assertEqual(count.difference_qty, -3)
        wizard.action_apply_count()
        self.assertEqual(picking.move_ids.product_uom_qty, 5)
        self.assertEqual(picking.move_ids.move_line_ids.quantity, 2)

    def test_product_label_code_is_accepted(self):
        picking = self._create_picking()
        self.product.product_tmpl_id.ddsl_product_label_code = "LABEL-CODE-001"
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)

        wizard.action_register_scan("LABEL-CODE-001")

        self.assertEqual(picking.ddsl_receipt_count_ids.product_id, self.product)
        self.assertEqual(picking.ddsl_receipt_count_ids.counted_qty, 1)

    def test_unknown_code_is_rejected(self):
        picking = self._create_picking()
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(picking)

        with self.assertRaises(UserError):
            wizard.action_register_scan("UNKNOWN-RECEIPT-CODE")
