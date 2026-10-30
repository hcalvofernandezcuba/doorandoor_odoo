from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseSupplyTraceability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Proveedor SLAB prueba", "supplier_rank": 1}
        )
        cls.customer = cls.env["res.partner"].create({"name": "Cliente prueba"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "SLAB prueba de trazabilidad",
                "default_code": "SLAB-TRACE-01",
                "is_storable": True,
                "purchase_ok": True,
                "sale_ok": True,
                "ddsl_print_label_on_receipt": True,
            }
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.customer.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "quantity": 2.0,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        cls.purchase = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 5.0,
                            "product_uom": cls.product.uom_po_id.id,
                            "price_unit": 10.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )
        cls.line = cls.purchase.order_line

    def test_mixed_purchase_origin_is_visible_and_printed_on_labels(self):
        self.env["ddpfw.purchase.supply.allocation"].create(
            {
                "purchase_line_id": self.line.id,
                "quantity": 2.0,
                "origin_type": "sale",
                "invoice_id": self.invoice.id,
                "invoice_line_id": self.invoice.invoice_line_ids.id,
            }
        )
        self.env["ddpfw.purchase.supply.allocation"].create(
            {
                "purchase_line_id": self.line.id,
                "quantity": 3.0,
                "origin_type": "replenishment",
                "warehouse_id": self.purchase.picking_type_id.warehouse_id.id,
            }
        )

        self.assertIn("Mixta", self.purchase.ddpfw_supply_summary)
        self.assertEqual(self.purchase.ddpfw_source_invoice_ids, self.invoice)
        self.assertIn("Venta pendiente", self.line.ddpfw_supply_origin)

        self.purchase.button_confirm()
        wizard = self.env["ddsl.stock.label.wizard"].create(
            {
                "picking_id": self.purchase.picking_ids.id,
                "print_mode": "product_code",
                "only_flagged_products": False,
            }
        )
        payloads = wizard._iter_product_code_payloads()
        self.assertEqual(len(payloads), 5)
        self.assertEqual(len([item for item in payloads if item["origin_type"] == "sale"]), 2)
        self.assertEqual(len([item for item in payloads if item["origin_type"] == "replenishment"]), 3)
        self.assertTrue(all(item["purchase_order"] == self.purchase.name for item in payloads))
        self.assertTrue(all(item["origin_document"] for item in payloads))

        purchase_output, _content_type = self.env["ir.actions.report"]._render_qweb_pdf(
            "purchase.action_report_purchase_order", res_ids=self.purchase.ids
        )
        self.assertIn(b"Origen log", purchase_output)
        self.assertIn(b"Venta pendiente", purchase_output)
        label_output, _content_type = self.env["ir.actions.report"]._render_qweb_pdf(
            "doorandoor_stock_labels.action_report_ddsl_stock_labels",
            res_ids=wizard.ids,
            data={"labels": payloads, "picking_name": self.purchase.picking_ids.name},
        )
        self.assertIn(b"VENTA", label_output)
        self.assertIn(self.purchase.name.encode(), label_output)

    def test_allocation_cannot_exceed_purchase_quantity(self):
        with self.assertRaises(ValidationError):
            self.env["ddpfw.purchase.supply.allocation"].create(
                {
                    "purchase_line_id": self.line.id,
                    "quantity": 6.0,
                    "origin_type": "replenishment",
                }
            )

    def test_automatic_allocation_is_fifo_and_idempotent(self):
        self.invoice.action_post()
        fulfillment = self.invoice.fulfillment_line_ids.filtered(
            lambda item: item.product_id == self.product
        )
        self.assertEqual(len(fulfillment), 1)
        warehouse = (
            fulfillment.move_line_id.ddsn_supply_warehouse_id
            or fulfillment.sale_order_id.warehouse_id
            or self.purchase.picking_type_id.warehouse_id
        )
        fulfillment.write(
            {
                "qty_invoiced": 2.0,
                "qty_pending_delivery": 2.0,
                "state": "ready_stock",
            }
        )
        self.purchase.ddpfw_demand_warehouse_id = warehouse

        self.purchase.action_ddpfw_auto_allocate_supply()
        allocations = self.line.ddpfw_supply_allocation_ids
        self.assertEqual(sum(allocations.mapped("quantity")), 5.0)
        self.assertEqual(
            sum(allocations.filtered(lambda item: item.origin_type == "sale").mapped("quantity")),
            2.0,
        )
        self.assertEqual(
            sum(
                allocations.filtered(
                    lambda item: item.origin_type == "replenishment"
                ).mapped("quantity")
            ),
            3.0,
        )
        self.assertTrue(all(allocations.mapped("automatic")))

        self.purchase.action_ddpfw_auto_allocate_supply()
        self.assertEqual(len(self.line.ddpfw_supply_allocation_ids), 2)
        self.assertEqual(sum(self.line.ddpfw_supply_allocation_ids.mapped("quantity")), 5.0)

    def test_purchase_receipt_prints_unflagged_product_with_origin(self):
        self.product.product_tmpl_id.ddsl_print_label_on_receipt = False
        self.purchase.action_ddpfw_auto_allocate_supply()
        self.purchase.button_confirm()
        picking = self.purchase.picking_ids
        move = picking.move_ids.filtered(lambda item: item.product_id == self.product)
        move.quantity = 1.0

        defaults = self.env["ddsl.stock.label.wizard"].with_context(
            default_picking_id=picking.id
        ).default_get(["picking_id", "only_flagged_products", "print_mode"])
        self.assertFalse(defaults["only_flagged_products"])
        wizard = self.env["ddsl.stock.label.wizard"].create(defaults)
        payloads, missing = wizard._iter_label_payloads()

        self.assertFalse(missing)
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["purchase_order"], self.purchase.name)
        self.assertEqual(payloads[0]["origin_type"], "replenishment")

    def test_mixed_receipt_routes_sale_to_predispatch_and_stock_to_batch(self):
        """La misma recepción se divide por cantidad y conserva ambos destinos."""
        sale_allocation = self.env["ddpfw.purchase.supply.allocation"].create({
            "purchase_line_id": self.line.id,
            "quantity": 2.0,
            "origin_type": "sale",
            "invoice_id": self.invoice.id,
            "invoice_line_id": self.invoice.invoice_line_ids.id,
        })
        self.env["ddpfw.purchase.supply.allocation"].create({
            "purchase_line_id": self.line.id,
            "quantity": 3.0,
            "origin_type": "replenishment",
            "warehouse_id": self.purchase.picking_type_id.warehouse_id.id,
        })
        self.purchase.button_confirm()
        picking = self.purchase.picking_ids
        warehouse = picking.picking_type_id.warehouse_id
        campaign = self.env["inventory.serial.campaign"].create({
            "name": "Campaña prueba recepción mixta",
            "company_id": self.env.company.id,
        })
        batch = self.env["inventory.serial.label.batch"].create({
            "name": "TEST-MIXED-RECEIPT",
            "campaign_id": campaign.id,
            "warehouse_id": warehouse.id,
            "product_id": self.product.id,
            "quantity": 1,
        })
        batch.action_generate_serials()

        groups = picking._ddic_receipt_groups()
        self.assertEqual(len(groups), 2)
        delivery = [group for group in groups if group["destination_purpose"] == "delivery"]
        storage = [group for group in groups if group["destination_purpose"] == "storage"]
        self.assertEqual(delivery[0]["quantity"], 2.0)
        self.assertEqual(storage[0]["quantity"], 3.0)
        self.assertEqual(
            delivery[0]["destination_reference"], sale_allocation.origin_document
        )

        picking.action_prepare_serial_receipt_lines()
        controls = picking.serial_receipt_ids.filtered(lambda item: item.state != "cancel")
        self.assertEqual(len(controls), 2)
        delivery_control = controls.filtered(lambda item: item.destination_purpose == "delivery")
        storage_control = controls.filtered(lambda item: item.destination_purpose == "storage")
        self.assertEqual(delivery_control.quantity, 2)
        self.assertTrue(delivery_control.predispatch_location_id)
        self.assertEqual(storage_control.quantity, 3)
        self.assertEqual(storage_control.batch_id, batch)

        for control in controls:
            control.action_start()
        self.assertTrue(all(control.state == "ready" for control in controls))
        self.assertEqual(delivery_control.scanned_count, 2)
        self.assertEqual(storage_control.scanned_count, 3)
        self.assertEqual(sale_allocation.origin_type, "sale")

        picking.action_validate_serial_receipt()
        self.assertEqual(picking.state, "done")
        self.assertTrue(all(control.state == "done" for control in controls))
        stock_qty = self.env["stock.quant"]._get_available_quantity(
            self.product, warehouse.lot_stock_id
        )
        predispatch_qty = self.env["stock.quant"]._get_available_quantity(
            self.product, delivery_control.predispatch_location_id
        )
        self.assertEqual(stock_qty, 3.0)
        self.assertEqual(predispatch_qty, 2.0)
        self.assertTrue(all(storage_control.serial_ids.mapped("inventory_loaded")))
        self.assertFalse(delivery_control.serial_ids.mapped("current_batch_id"))
