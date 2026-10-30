from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRelatedWarehouseOperations(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.customer = cls.env["res.partner"].create({"name": "Related operations customer"})

    def _picking(self, picking_type, source, destination):
        return self.env["stock.picking"].create({
            "partner_id": self.customer.id,
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
        })

    def test_receipt_transfer_and_delivery_form_one_explicit_chain(self):
        supplier = self.env.ref("stock.stock_location_suppliers")
        customer_location = self.customer.property_stock_customer
        receipt = self._picking(
            self.warehouse.in_type_id, supplier, self.warehouse.lot_stock_id
        )
        dispatch = self.env["stock.picking"].create({
            "partner_id": self.customer.id,
            "picking_type_id": self.warehouse.int_type_id.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": self.warehouse.lot_stock_id.id,
            "company_id": self.warehouse.company_id.id,
        })
        transfer_receipt = self._picking(
            self.warehouse.int_type_id,
            self.warehouse.lot_stock_id,
            self.warehouse.lot_stock_id,
        )
        delivery = self._picking(
            self.warehouse.out_type_id,
            self.warehouse.lot_stock_id,
            customer_location,
        )
        dispatch.write({"ddpc_transfer_receipt_picking_id": transfer_receipt.id})
        transfer_receipt.write({"ddpc_transfer_source_picking_id": dispatch.id})

        history = self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/RELATED/001",
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago verificado para prueba",
            "picking_id": delivery.id,
            "transfer_dispatch_id": dispatch.id,
            "transfer_receipt_id": transfer_receipt.id,
            "state": "ready",
        })
        self.env["doorandoor.historic.regularization"].create({
            "historical_delivery_id": history.id,
            "warehouse_id": self.warehouse.id,
            "destination_mode": "storage",
            "destination_location_id": self.warehouse.lot_stock_id.id,
            "picking_id": receipt.id,
            "state": "done",
        })

        expected = receipt | dispatch | transfer_receipt | delivery
        for operation in expected:
            related = operation.ddhl_related_operation_ids
            self.assertEqual(related, expected - operation)
            self.assertEqual(operation.ddhl_related_operation_count, 3)

    def test_historical_cycle_includes_transfer_and_receipt_backorders(self):
        supplier = self.env.ref("stock.stock_location_suppliers")
        receipt = self._picking(
            self.warehouse.in_type_id, supplier, self.warehouse.lot_stock_id
        )
        dispatch = self._picking(
            self.warehouse.int_type_id,
            self.warehouse.lot_stock_id,
            self.warehouse.lot_stock_id,
        )
        dispatch_backorder = self._picking(
            self.warehouse.int_type_id,
            self.warehouse.lot_stock_id,
            self.warehouse.lot_stock_id,
        )
        dispatch_backorder.backorder_id = dispatch
        transfer_receipt = self._picking(
            self.warehouse.int_type_id,
            self.warehouse.lot_stock_id,
            self.warehouse.lot_stock_id,
        )
        receipt_backorder = self._picking(
            self.warehouse.int_type_id,
            self.warehouse.lot_stock_id,
            self.warehouse.lot_stock_id,
        )
        receipt_backorder.write({
            "backorder_id": transfer_receipt.id,
            "ddpc_transfer_source_picking_id": dispatch_backorder.id,
        })
        dispatch_backorder.ddpc_transfer_receipt_picking_id = receipt_backorder

        history = self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/BACKORDER/001",
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago verificado para prueba",
            "transfer_dispatch_id": dispatch.id,
            "transfer_receipt_id": transfer_receipt.id,
            "state": "transfer_pending",
        })
        self.env["doorandoor.historic.regularization"].create({
            "historical_delivery_id": history.id,
            "warehouse_id": self.warehouse.id,
            "destination_mode": "storage",
            "destination_location_id": self.warehouse.lot_stock_id.id,
            "picking_id": receipt.id,
            "state": "done",
        })

        expected = receipt | dispatch | dispatch_backorder | transfer_receipt | receipt_backorder
        self.assertEqual(history.ddhl_cycle_operation_ids, expected)
        self.assertEqual(history.ddhl_cycle_operation_count, 5)
        self.assertIn(dispatch_backorder, dispatch.ddhl_related_operation_ids)
        self.assertIn(receipt_backorder, dispatch.ddhl_related_operation_ids)

        action = receipt.action_ddhl_open_related_operations()
        self.assertEqual(action["domain"][0][:2], ("id", "in"))
        self.assertEqual(
            set(action["domain"][0][2]),
            set((expected - receipt).ids),
        )


@tagged("post_install", "-at_install")
class TestCreateNextWarehouseOperation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.customer = cls.env["res.partner"].create({
            "name": "Next operation customer",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Next operation product",
            "is_storable": True,
        })

    def _source_receipt(self, quantity=3.0, done=False):
        picking = self.env["stock.picking"].create({
            "partner_id": self.customer.id,
            "picking_type_id": self.warehouse.in_type_id.id,
            "location_id": self.env.ref("stock.stock_location_suppliers").id,
            "location_dest_id": self.warehouse.lot_stock_id.id,
            "company_id": self.warehouse.company_id.id,
        })
        self.env["stock.move"].create({
            "name": self.product.display_name,
            "product_id": self.product.id,
            "product_uom_qty": quantity,
            "product_uom": self.product.uom_id.id,
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "company_id": picking.company_id.id,
        })
        picking.action_confirm()
        if done:
            picking.write({"state": "done"})
            picking.move_ids.write({"state": "done", "quantity": quantity})
        return picking

    def test_general_receipt_creates_delivery_without_retyping_lines(self):
        receipt = self._source_receipt(quantity=3.0)
        action = receipt.action_ddhl_open_related_operations()
        self.assertEqual(
            action["res_model"],
            "doorandoor.historic.next.operation.wizard",
        )
        wizard = self.env[action["res_model"]].with_context(
            action["context"]
        ).create({
            "source_operation_id": receipt.id,
            "operation_kind": "delivery",
            "partner_id": self.customer.id,
        })
        wizard.action_create_operation()
        delivery = receipt.ddhl_created_operation_ids
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.picking_type_code, "outgoing")
        self.assertEqual(delivery.move_ids.product_id, self.product)
        self.assertEqual(delivery.move_ids.product_uom_qty, 3.0)
        self.assertEqual(delivery.ddhl_source_operation_id, receipt)

    def test_historical_panel_creates_delivery_from_confirmed_receipt(self):
        receipt = self._source_receipt(quantity=2.0, done=True)
        history = self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/NEXT/001",
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago histórico comprobado",
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 2.0,
            })],
        })
        historical_line = history.line_ids
        regularization = self.env["doorandoor.historic.regularization"].create({
            "historical_delivery_id": history.id,
            "warehouse_id": self.warehouse.id,
            "destination_mode": "predispatch",
            "destination_location_id": self.warehouse.lot_stock_id.id,
            "picking_id": receipt.id,
            "state": "done",
            "line_ids": [(0, 0, {
                "historical_line_id": historical_line.id,
                "physical_quantity": 2,
            })],
        })
        self.assertTrue(history.ddhl_can_create_next_operation)
        wizard = self.env["doorandoor.historic.next.operation.wizard"].create({
            "historical_delivery_id": history.id,
            "source_operation_id": receipt.id,
            "operation_kind": "delivery",
            "destination_warehouse_id": self.warehouse.id,
            "partner_id": self.customer.id,
        })
        wizard.action_create_operation()
        self.assertTrue(history.picking_id)
        self.assertEqual(history.picking_id.ddhl_source_operation_id, receipt)
        self.assertEqual(history.picking_id.move_ids.product_id, self.product)
        self.assertEqual(history.picking_id.move_ids.product_uom_qty, 2.0)
        self.assertEqual(history.state, "ready")
        self.assertIn(receipt, history.ddhl_cycle_operation_ids)
        self.assertIn(history.picking_id, history.ddhl_cycle_operation_ids)
        self.assertEqual(regularization.state, "done")

    def test_transfer_receipt_links_and_creates_historical_delivery(self):
        receipt = self._source_receipt(quantity=2.0, done=True)
        dispatch = self.env["stock.picking"].create({
            "partner_id": self.customer.id,
            "picking_type_id": self.warehouse.int_type_id.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": self.warehouse.lot_stock_id.id,
            "company_id": self.warehouse.company_id.id,
        })
        history = self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/TRANSFER/RECEIPT/001",
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "supply_warehouse_id": self.warehouse.id,
            "payment_note": "Pago histórico comprobado",
            "transfer_dispatch_id": dispatch.id,
            "state": "transfer_pending",
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 2.0,
            })],
        })

        history._release_after_transfer_receipt(receipt)

        self.assertEqual(history.transfer_receipt_id, receipt)
        self.assertTrue(history.picking_id)
        self.assertEqual(history.state, "ready")
        self.assertEqual(history.picking_id.move_ids.product_id, self.product)
        self.assertEqual(history.picking_id.move_ids.product_uom_qty, 2.0)


@tagged("post_install", "-at_install")
class TestHistoricalRegularizationDestination(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source_warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.destination_warehouse = cls.env["stock.warehouse"].create({
            "name": "Historical destination warehouse",
            "code": "HDW",
        })
        cls.customer = cls.env["res.partner"].create({
            "name": "Historical destination customer",
        })

    def _history(self):
        return self.env["doorandoor.historical.delivery"].create({
            "external_reference": "LEGACY/DESTINATION/001",
            "partner_id": self.customer.id,
            "warehouse_id": self.destination_warehouse.id,
            "supply_warehouse_id": self.source_warehouse.id,
            "payment_note": "Pago histórico comprobado",
        })

    def test_regularization_action_defaults_to_destination_warehouse(self):
        history = self._history()
        action = history.action_ddhl_create_regularization()
        self.assertEqual(
            action["context"]["default_warehouse_id"],
            self.destination_warehouse.id,
        )
        self.assertEqual(
            action["context"]["default_destination_location_id"],
            self.destination_warehouse.lot_stock_id.id,
        )

    def test_history_onchange_uses_destination_not_supplier(self):
        history = self._history()
        regularization = self.env["doorandoor.historic.regularization"].new({
            "historical_delivery_id": history.id,
            "destination_mode": "predispatch",
        })
        regularization._onchange_historical_delivery_id()
        self.assertEqual(
            regularization.warehouse_id,
            self.destination_warehouse,
        )
