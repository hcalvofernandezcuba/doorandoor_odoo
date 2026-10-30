from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHistoricalExistingStockAllocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.customer = cls.env["res.partner"].create({"name": "Historical stock customer"})
        cls.product = cls.env["product.product"].create({
            "name": "Historical existing stock ITEM",
            "is_storable": True,
        })
        cls.campaign = cls.env["inventory.serial.campaign"].create({
            "name": "Historical stock test campaign",
        })
        cls.batch = cls.env["inventory.serial.label.batch"].create({
            "name": "HIST-STOCK-TEST",
            "campaign_id": cls.campaign.id,
            "warehouse_id": cls.warehouse.id,
            "product_id": cls.product.id,
            "quantity": 2,
        })
        cls.serials = cls.env["inventory.unit.serial"].create([
            {
                "code": "HIST-STOCK-0001",
                "batch_id": cls.batch.id,
                "product_id": cls.product.id,
                "inventory_loaded": True,
                "current_warehouse_id": cls.warehouse.id,
                "current_batch_id": cls.batch.id,
                "current_location_id": cls.warehouse.lot_stock_id.id,
            },
            {
                "code": "HIST-STOCK-0002",
                "batch_id": cls.batch.id,
                "product_id": cls.product.id,
                "inventory_loaded": True,
                "current_warehouse_id": cls.warehouse.id,
                "current_batch_id": cls.batch.id,
                "current_location_id": cls.warehouse.lot_stock_id.id,
            },
        ])
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 2,
        )

    def _history(self, quantity=2):
        return self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/STOCK/%s" % quantity,
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago histórico comprobado",
            "ddhl_inventory_treatment": "existing_stock",
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": quantity,
            })],
        })

    def test_proposal_uses_existing_labels_without_creating_stock(self):
        history = self._history()
        picking_count = self.env["stock.picking"].search_count([])
        serial_count = self.env["inventory.unit.serial"].search_count([])
        history.action_ddhl_prepare_existing_stock()
        self.assertTrue(history.ddhl_stock_allocation_ready)
        self.assertEqual(history.ddhl_stock_allocation_ids.serial_ids, self.serials)
        self.assertEqual(
            history.ddhl_stock_allocation_ids.serial_codes,
            "HIST-STOCK-0001, HIST-STOCK-0002",
        )
        self.assertEqual(self.env["stock.picking"].search_count([]), picking_count)
        self.assertEqual(self.env["inventory.unit.serial"].search_count([]), serial_count)
        self.assertFalse(history.ddhl_regularization_ids)

    def test_shortage_creates_nothing(self):
        history = self._history(quantity=3)
        with self.assertRaises(UserError):
            history.action_ddhl_prepare_existing_stock()
        self.assertFalse(history.ddhl_stock_allocation_ids)
        self.assertFalse(history.ddhl_regularization_ids)

    def test_normal_mode_blocks_fictitious_receipt(self):
        history = self._history()
        with self.assertRaises(UserError):
            history.action_ddhl_start_predispatch_cycle()

    def test_approved_local_stock_creates_exact_delivery(self):
        history = self._history().with_context(ddhl_skip_pdf=True)
        serial_count = self.env["inventory.unit.serial"].search_count([])
        history.action_ddhl_prepare_existing_stock()
        history.action_ddhl_approve_existing_stock()

        self.assertEqual(history.state, "ready")
        self.assertTrue(history.picking_id)
        self.assertFalse(history.transfer_dispatch_id)
        self.assertEqual(
            history.picking_id.ddmh_reserved_serial_ids,
            self.serials,
        )
        self.assertEqual(
            history.ddhl_stock_allocation_ids.delivery_picking_id,
            history.picking_id,
        )
        self.assertEqual(
            self.env["inventory.unit.serial"].search_count([]), serial_count,
        )

    def test_cross_warehouse_uses_real_source_then_releases_delivery(self):
        destination = self.env["stock.warehouse"].create({
            "name": "Historical destination warehouse",
            "code": "HSDST",
        })
        history = self.env["doorandoor.historical.delivery"].with_context(
            ddhl_skip_pdf=True,
        ).create({
            "external_reference": "LEGACY/STOCK/CROSS",
            "partner_id": self.customer.id,
            "warehouse_id": destination.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago histórico comprobado",
            "ddhl_inventory_treatment": "existing_stock",
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 2,
            })],
        })
        serial_count = self.env["inventory.unit.serial"].search_count([])
        history.action_ddhl_prepare_existing_stock()
        history.action_ddhl_approve_existing_stock()

        dispatch = history.transfer_dispatch_id
        self.assertTrue(dispatch)
        self.assertEqual(history.state, "transfer_pending")
        self.assertEqual(dispatch.ddpc_source_warehouse_id, self.warehouse)
        self.assertEqual(
            dispatch.ddpc_transfer_target_location_id,
            destination.lot_stock_id,
        )
        self.assertEqual(dispatch.ddmh_reserved_serial_ids, self.serials)
        self.assertFalse(history.picking_id)

        # The final delivery remains blocked until every exact label reaches
        # the destination warehouse through the validated transfer receipt.
        self.serials.write({
            "current_warehouse_id": destination.id,
            "current_location_id": destination.lot_stock_id.id,
            "reserved_picking_id": False,
        })
        delivery = history._ddhl_try_create_existing_stock_delivery()
        self.assertTrue(delivery)
        self.assertEqual(history.state, "ready")
        self.assertEqual(delivery.ddmh_reserved_serial_ids, self.serials)
        self.assertEqual(
            self.env["inventory.unit.serial"].search_count([]), serial_count,
        )
