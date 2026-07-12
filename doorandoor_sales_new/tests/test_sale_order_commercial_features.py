from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderCommercialFeatures(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bonus_group = cls.env["res.partner.category"].create(
            {
                "name": "Mayoristas DDSN",
                "ddsn_bonus_percent": 5.0,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Comercial DDSN",
                "ddsn_bonus_percent": 7.5,
                "category_id": [(6, 0, [cls.bonus_group.id])],
            }
        )
        cls.group_only_partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Grupo DDSN",
                "category_id": [(6, 0, [cls.bonus_group.id])],
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Comercial DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 50.0,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )

    def test_sale_order_line_shows_stock_for_order_warehouse(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            self.warehouse.lot_stock_id,
            8.0,
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 2.0,
                "price_unit": 50.0,
            }
        )

        self.assertEqual(line.ddsn_available_qty, 8.0)
        self.assertEqual(line.ddsn_stock_uom_name, self.product.uom_id.display_name)
        self.assertIn("8.00", line.ddsn_stock_display)
        self.assertIn("8.00", line.ddsn_warehouse_stock_display)
        self.assertIn(self.warehouse.code or self.warehouse.name, line.ddsn_warehouse_stock_display)
        self.assertIn(self.warehouse.code or self.warehouse.name, line.ddsn_warehouse_stock_html)

    def test_sale_order_starts_unregistered_without_sequence(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )

        self.assertFalse(sale_order.ddsn_quote_registered)
        self.assertEqual(sale_order.name, "New")

    def test_register_quote_assigns_sequence(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )

        sale_order.action_ddsn_register_quote()

        self.assertTrue(sale_order.ddsn_quote_registered)
        self.assertNotEqual(sale_order.name, "New")

    def test_validate_quote_creates_preinvoice(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_uom_qty": 2.0,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )

        sale_order.action_ddsn_register_quote()

        self.assertTrue(sale_order.ddsn_preinvoice_move_id)
        self.assertEqual(sale_order.ddsn_flow_stage, "preinvoice")
        self.assertEqual(sale_order.ddsn_preinvoice_move_id.state, "draft")
        self.assertEqual(sale_order.ddsn_preinvoice_move_id.sale_order_id, sale_order)

    def test_posting_preinvoice_confirms_sale_order(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_uom_qty": 1.0,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )

        sale_order.action_ddsn_register_quote()
        preinvoice = sale_order.ddsn_preinvoice_move_id
        preinvoice.action_post()

        self.assertEqual(sale_order.state, "sale")
        self.assertEqual(sale_order.ddsn_flow_stage, "invoiced")
        self.assertEqual(sale_order.ddsn_invoice_move_id, preinvoice)

    def test_sale_order_line_shows_net_stock_after_active_preinvoice_reservation(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            self.warehouse.lot_stock_id,
            8.0,
        )
        self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 3.0,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )
        visible_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        visible_line = self.env["sale.order.line"].create(
            {
                "order_id": visible_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
            }
        )

        self.assertEqual(visible_line.ddsn_available_qty, 5.0)
        self.assertIn("5.00", visible_line.ddsn_stock_display)

    def test_sale_order_line_shows_net_stock_after_posted_invoice_commitment(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            self.warehouse.lot_stock_id,
            8.0,
        )
        committed_move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 3.0,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )
        committed_move.action_post()

        visible_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        visible_line = self.env["sale.order.line"].create(
            {
                "order_id": visible_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
            }
        )

        self.assertEqual(visible_line.ddsn_available_qty, 5.0)
        self.assertIn("5.00", visible_line.ddsn_stock_display)

    def test_partner_bonus_is_applied_when_line_has_no_discount(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        line = self.env["sale.order.line"].new(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
            }
        )

        line._onchange_product_id()
        line._onchange_ddsn_apply_partner_bonus()

        self.assertEqual(line.discount, 7.5)
        self.assertEqual(line.ddsn_bonus_percent, 7.5)
        self.assertEqual(line.ddsn_bonus_source, "partner")

    def test_partner_bonus_does_not_override_existing_discount(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        line = self.env["sale.order.line"].new(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
                "discount": 12.0,
            }
        )

        line._onchange_product_id()
        line._onchange_ddsn_apply_partner_bonus()

        self.assertEqual(line.discount, 12.0)
        self.assertEqual(line.ddsn_bonus_percent, 12.0)
        self.assertEqual(line.ddsn_bonus_source, "manual")

    def test_group_bonus_is_applied_when_partner_has_no_specific_bonus(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.group_only_partner.id,
                "warehouse_id": self.warehouse.id,
            }
        )
        line = self.env["sale.order.line"].new(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
            }
        )

        line._onchange_product_id()
        line._onchange_ddsn_apply_partner_bonus()

        self.assertEqual(line.discount, 5.0)
        self.assertEqual(line.ddsn_bonus_percent, 5.0)
        self.assertEqual(line.ddsn_bonus_source, "group")
