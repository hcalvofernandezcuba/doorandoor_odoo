from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInvoiceToSaleOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Pruebas DoorAndDoor",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Prueba DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 120.0,
            }
        )
        cls.stock_product = cls.env["product.product"].create(
            {
                "name": "Producto Stock DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 150.0,
            }
        )
        cls.component_product = cls.env["product.product"].create(
            {
                "name": "Componente DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 10.0,
            }
        )
        cls.manufactured_product = cls.env["product.product"].create(
            {
                "name": "Producto Fabricado DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 300.0,
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.manufactured_product.product_tmpl_id.id,
                "product_uom_id": cls.manufactured_product.uom_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.component_product.id,
                            "product_qty": 1.0,
                            "product_uom_id": cls.component_product.uom_id.id,
                        },
                    )
                ],
            }
        )

    def _create_customer_invoice(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 2.0,
                            "price_unit": 120.0,
                        },
                    )
                ],
            }
        )
        self._accept_current_policy(move)
        return move

    def test_reposting_invoice_preserves_original_fiscal_number(self):
        move = self._create_customer_invoice()
        move.action_post()
        original_name = move.name
        original_prefix = move.sequence_prefix
        original_number = move.sequence_number

        move.button_draft()
        self.assertEqual(move.name, original_name)
        move.action_post()

        self.assertEqual(move.name, original_name)
        self.assertEqual(move.sequence_prefix, original_prefix)
        self.assertEqual(move.sequence_number, original_number)

    def _create_manufacturing_invoice(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.manufactured_product.id,
                            "name": self.manufactured_product.display_name,
                            "quantity": 2.0,
                            "price_unit": 300.0,
                        },
                    )
                ],
            }
        )
        self._accept_current_policy(move)
        return move

    def _create_stock_invoice(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.stock_product.id,
                            "name": self.stock_product.display_name,
                            "quantity": 2.0,
                            "price_unit": 150.0,
                        },
                    )
                ],
            }
        )
        self._accept_current_policy(move)
        return move

    def _accept_current_policy(self, move):
        """Keep fulfillment tests aligned with the mandatory policy gate."""
        if not hasattr(move, "_ddpa_get_or_create_request"):
            return
        if move.partner_id._ddpa_get_valid_acceptance():
            return
        move._ddpa_get_or_create_request("present")._accept(
            "Cliente Pruebas DoorAndDoor",
            ip_address="127.0.0.1",
            user_agent="Odoo test suite",
            document_language="en",
        )

    def _approve_current_production_need(self, move):
        """Follow the active daily-planning flow when Factory Control is installed."""
        fulfillment = move.fulfillment_line_ids
        if "ddfc.production.need" not in self.env.registry:
            return fulfillment.mrp_production_id
        need = fulfillment.production_need_ids
        self.assertEqual(len(need), 1)
        self.assertEqual(need.requested_qty, fulfillment.qty_released)
        production_warehouse = self.env["stock.warehouse"].search(
            [
                ("company_id", "=", move.company_id.id),
                ("name", "ilike", "Tampa Produccion"),
            ],
            limit=1,
        ) or move.sale_order_id.warehouse_id
        destination = (
            production_warehouse.manu_type_id.default_location_src_id
            or production_warehouse.lot_stock_id
        )
        plan = self.env["ddfc.daily.plan"].create({
            "plan_date": fields.Date.today() + timedelta(days=1000),
            "production_warehouse_id": production_warehouse.id,
            "material_destination_location_id": destination.id,
        })
        self.env["ddfc.daily.plan.line"].with_context(
            ddfc_snapshot_loading=True
        ).create({
            "plan_id": plan.id,
            "warehouse_id": need.warehouse_id.id,
            "product_id": need.product_id.id,
            "bom_id": self.bom.id,
            "requested_qty": need.requested_qty,
            "approved_qty": need.requested_qty,
            "need_ids": [Command.set(need.ids)],
        })
        plan.write({
            "snapshot_at": fields.Datetime.now(),
            "snapshot_user_id": self.env.user.id,
            "snapshot_locked": True,
        })
        plan.action_approve()
        return fulfillment.mrp_production_id

    def test_invoice_post_creates_sale_order_and_fulfillment(self):
        move = self._create_customer_invoice()

        move.action_post()

        self.assertTrue(move.sale_order_id, "La factura debe generar un pedido de venta interno.")
        self.assertEqual(move.sale_order_id.state, "sale")
        self.assertEqual(len(move.sale_order_id.order_line), 1)
        self.assertEqual(len(move.fulfillment_line_ids), 1)

        invoice_line = move.invoice_line_ids.filtered(lambda line: line.product_id)
        fulfillment_line = move.fulfillment_line_ids

        self.assertEqual(invoice_line.generated_sale_line_id, move.sale_order_id.order_line)
        self.assertEqual(invoice_line.fulfillment_line_id, fulfillment_line)
        self.assertEqual(fulfillment_line.qty_invoiced, 2.0)
        self.assertEqual(fulfillment_line.qty_pending_payment, 2.0)
        self.assertEqual(fulfillment_line.qty_pending_delivery, 2.0)

    def test_invoice_line_shows_stock_visibility(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            warehouse.lot_stock_id,
            6.0,
        )
        move = self._create_customer_invoice()
        invoice_line = move.invoice_line_ids.filtered(lambda line: line.product_id)

        self.assertEqual(invoice_line.ddsn_available_qty, 6.0)
        self.assertIn("6.00", invoice_line.ddsn_stock_display)
        self.assertIn(warehouse.code or warehouse.name, invoice_line.ddsn_warehouse_stock_display)
        self.assertIn(warehouse.code or warehouse.name, invoice_line.ddsn_warehouse_stock_text)

    def test_invoice_line_shows_net_stock_after_previous_posted_commitment(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.stock_product,
            warehouse.lot_stock_id,
            6.0,
        )

        previous_move = self._create_stock_invoice()
        previous_move.action_post()

        new_move = self._create_stock_invoice()
        invoice_line = new_move.invoice_line_ids.filtered(lambda line: line.product_id == self.stock_product)

        self.assertEqual(invoice_line.ddsn_available_qty, 4.0)
        self.assertIn("4.00", invoice_line.ddsn_stock_display)
        self.assertIn("4.00", invoice_line.ddsn_warehouse_stock_display)

    def test_invoice_line_shows_net_stock_after_active_quote_reservation(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.stock_product,
            warehouse.lot_stock_id,
            6.0,
        )
        reserved_move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.stock_product.id,
                            "name": self.stock_product.display_name,
                            "quantity": 2.0,
                            "price_unit": 150.0,
                        },
                    )
                ],
            }
        )
        self.assertTrue(reserved_move.ddsn_reservation_active)

        new_move = self._create_stock_invoice()
        invoice_line = new_move.invoice_line_ids.filtered(lambda line: line.product_id == self.stock_product)

        self.assertEqual(invoice_line.ddsn_available_qty, 4.0)
        self.assertIn("4.00", invoice_line.ddsn_stock_display)

    def test_preinvoice_reservation_is_released_when_posting_invoice(self):
        move = self._create_stock_invoice()

        self.assertTrue(move.ddsn_reservation_active)
        move.action_post()

        self.assertFalse(move.ddsn_reservation_expires_at)
        self.assertFalse(move.ddsn_reservation_active)

    def test_expired_preinvoice_reservation_is_released(self):
        move = self._create_stock_invoice()
        move.write({"ddsn_reservation_expires_at": fields.Datetime.now() - timedelta(hours=1)})

        released_count = self.env["account.move"]._ddsn_release_expired_preinvoice_reservations()

        self.assertEqual(released_count, 1)
        self.assertFalse(move.ddsn_reservation_expires_at)
        self.assertFalse(move.ddsn_reservation_active)

    def test_old_preinvoice_is_deleted_after_cleanup_window(self):
        move = self._create_stock_invoice()
        move.write(
            {
                "ddsn_reservation_expires_at": False,
                "create_date": fields.Datetime.now() - timedelta(hours=49),
            }
        )

        processed_count = self.env["account.move"]._ddsn_release_expired_preinvoice_reservations()

        self.assertEqual(processed_count, 1)
        self.assertFalse(move.exists())

    def test_posting_same_invoice_does_not_duplicate_fulfillment_lines(self):
        move = self._create_customer_invoice()

        move.action_post()
        first_sale_order = move.sale_order_id
        first_fulfillment_count = len(move.fulfillment_line_ids)
        move._ddsn_create_sale_orders_and_fulfillment()

        self.assertEqual(move.sale_order_id, first_sale_order)
        self.assertEqual(len(move.fulfillment_line_ids), first_fulfillment_count)

    def test_prorated_release_updates_fulfillment_lines(self):
        move = self._create_customer_invoice()
        move.payment_release_policy = "prorated"
        move.action_post()

        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        fulfillment_line = move.fulfillment_line_ids
        self.assertEqual(fulfillment_line.qty_released, 1.0)
        self.assertEqual(fulfillment_line.qty_pending_payment, 1.0)
        self.assertEqual(move.release_state, "partially_released")

    def test_release_creates_stock_picking(self):
        move = self._create_customer_invoice()
        move.action_post()

        move._ddsn_apply_release_for_amount(move.amount_total)

        fulfillment_line = move.fulfillment_line_ids
        self.assertTrue(fulfillment_line.picking_id, "La liberacion debe crear un picking de salida.")
        self.assertEqual(fulfillment_line.qty_sent_stock, fulfillment_line.qty_released)
        self.assertEqual(fulfillment_line.state, "in_process")
        self.assertEqual(move.picking_count, 1)
        self.assertEqual(len(move.pickup_order_ids), 1)
        self.assertEqual(move.pickup_order_ids.picking_id, fulfillment_line.picking_id)
        self.assertEqual(len(move.pickup_order_ids.pickup_line_ids), 1)
        self.assertEqual(
            move.pickup_order_ids.pickup_line_ids.product_uom_qty,
            fulfillment_line.qty_released,
        )

        move._ddsn_apply_release_for_amount(move.amount_total)

        self.assertEqual(len(move.pickup_order_ids), 1)
        self.assertEqual(len(move.pickup_order_ids.pickup_line_ids), 1)

    def test_release_reuses_existing_sale_picking_without_duplicate_moves(self):
        move = self._create_customer_invoice()
        move.action_post()

        sale_order = move.sale_order_id
        sale_order.action_confirm()
        warehouse = sale_order.warehouse_id or self.env["stock.warehouse"].search(
            [("company_id", "=", move.company_id.id)],
            limit=1,
        )
        picking_type = warehouse.out_type_id
        customer_location = move.partner_id.property_stock_customer or self.env.ref(
            "stock.stock_location_customers"
        )
        existing_picking = self.env["stock.picking"].create(
            {
                "partner_id": move.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": customer_location.id,
                "origin": sale_order.name,
                "company_id": move.company_id.id,
                "move_type": "direct",
            }
        )
        existing_move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "picking_id": existing_picking.id,
                "company_id": move.company_id.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": existing_picking.location_id.id,
                "location_dest_id": existing_picking.location_dest_id.id,
                "sale_line_id": sale_order.order_line.id,
                "origin": sale_order.name,
            }
        )

        move._ddsn_apply_release_for_amount(move.amount_total)

        fulfillment_line = move.fulfillment_line_ids
        self.assertEqual(fulfillment_line.picking_id, existing_picking)
        self.assertEqual(
            len(existing_picking.move_ids.filtered(lambda stock_move: stock_move.sale_line_id == sale_order.order_line)),
            1,
            "La factura debe reutilizar el movimiento existente del pedido y no crear otro duplicado.",
        )
        self.assertEqual(existing_move.product_uom_qty, 3.0)

    def test_partial_payment_does_not_create_stock_picking(self):
        move = self._create_customer_invoice()
        move.action_post()

        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        fulfillment_line = move.fulfillment_line_ids
        self.assertFalse(fulfillment_line.picking_id, "No debe crearse picking con pago parcial.")
        self.assertEqual(fulfillment_line.qty_sent_stock, 0.0)
        self.assertEqual(fulfillment_line.state, "ready_stock")

    def test_full_release_confirms_generated_sale_before_creating_delivery(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.stock_product,
            warehouse.lot_stock_id,
            4.0,
        )
        move = self._create_stock_invoice()
        move.action_post()

        # Simulate a legacy invoice whose generated commercial order remained
        # technically in draft before this regression fix.
        self.env.cr.execute(
            "UPDATE sale_order SET state = 'draft' WHERE id = %s",
            [move.sale_order_id.id],
        )
        move.sale_order_id.invalidate_recordset(["state"])

        move._ddsn_apply_release_for_amount(move.amount_total)

        self.assertEqual(move.sale_order_id.state, "sale")
        self.assertTrue(move.fulfillment_line_ids.picking_id)
        self.assertEqual(len(move.fulfillment_line_ids.picking_id), 1)

    def test_manual_inventory_adjustment_cannot_reduce_below_released_qty(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.stock_product,
            warehouse.lot_stock_id,
            6.0,
        )
        move = self._create_stock_invoice()
        move.payment_release_policy = "prorated"
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        quant = self.env["stock.quant"]._gather(
            self.stock_product,
            warehouse.lot_stock_id,
            strict=True,
        )[:1].with_context(inventory_mode=True)
        quant.inventory_quantity = 0.0

        with self.assertRaises(UserError):
            quant.action_apply_inventory()

    def test_manual_inventory_adjustment_can_keep_released_qty_protected(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.stock_product,
            warehouse.lot_stock_id,
            6.0,
        )
        move = self._create_stock_invoice()
        move.payment_release_policy = "prorated"
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        quant = self.env["stock.quant"]._gather(
            self.stock_product,
            warehouse.lot_stock_id,
            strict=True,
        )[:1].with_context(inventory_mode=True)
        quant.inventory_quantity = 1.0
        quant.action_apply_inventory()

        self.assertEqual(quant.quantity, 1.0)

    def test_release_creates_production_need_and_plan_creates_mrp(self):
        move = self._create_manufacturing_invoice()
        move.fulfillment_route_policy = "force_mrp"
        move.mrp_creation_policy = "per_line"
        move.action_post()

        move._ddsn_apply_release_for_amount(move.amount_total)

        fulfillment_line = move.fulfillment_line_ids
        self._approve_current_production_need(move)
        self.assertTrue(fulfillment_line.mrp_production_id, "La liberacion debe crear una orden de fabricacion.")
        self.assertEqual(fulfillment_line.qty_sent_mrp, fulfillment_line.qty_released)
        self.assertEqual(fulfillment_line.state, "in_process")
        self.assertEqual(move.mrp_production_count, 1)

    def test_partial_payment_can_create_mrp_production(self):
        move = self._create_manufacturing_invoice()
        move.fulfillment_route_policy = "force_mrp"
        move.mrp_creation_policy = "per_line"
        move.payment_release_policy = "prorated"
        move.action_post()

        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        fulfillment_line = move.fulfillment_line_ids
        self._approve_current_production_need(move)
        self.assertTrue(
            fulfillment_line.mrp_production_id,
            "La fabricacion debe poder generarse con pago parcial.",
        )
        self.assertEqual(fulfillment_line.qty_released, 1.0)
        self.assertEqual(fulfillment_line.qty_sent_mrp, fulfillment_line.qty_released)

    def test_completed_mrp_creates_outgoing_picking(self):
        move = self._create_manufacturing_invoice()
        move.fulfillment_route_policy = "force_mrp"
        move.mrp_creation_policy = "per_line"
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total)

        fulfillment_line = move.fulfillment_line_ids
        self._approve_current_production_need(move)
        picking = move._ddsn_sync_finished_mrp_to_outgoing_picking(fulfillment_line)

        self.assertTrue(picking, "La produccion terminada debe preparar un picking de salida.")
        self.assertEqual(fulfillment_line.picking_id, picking)
        self.assertEqual(fulfillment_line.qty_sent_stock, fulfillment_line.qty_sent_mrp)

    def test_completed_mrp_does_not_create_outgoing_picking_with_partial_payment(self):
        move = self._create_manufacturing_invoice()
        move.fulfillment_route_policy = "force_mrp"
        move.mrp_creation_policy = "per_line"
        move.payment_release_policy = "prorated"
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total / 2)

        fulfillment_line = move.fulfillment_line_ids
        picking = move._ddsn_sync_finished_mrp_to_outgoing_picking(fulfillment_line)

        self.assertFalse(picking, "No debe generarse picking de salida si la factura no esta totalmente pagada.")
        self.assertFalse(fulfillment_line.picking_id)
        self.assertEqual(fulfillment_line.qty_sent_stock, 0.0)
