from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPickupOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Pickup DDSN"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Pickup DDSN",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
            }
        )

    def _create_customer_invoice(self):
        return self.env["account.move"].create(
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
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def test_create_pickup_order_from_invoice(self):
        move = self._create_customer_invoice()
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total)

        move.action_create_pickup_orders()

        self.assertTrue(move.pickup_order_ids)
        pickup_order = move.pickup_order_ids[:1]
        self.assertTrue(pickup_order.pickup_line_ids)
        self.assertEqual(pickup_order.move_id, move)
        self.assertIn(pickup_order.state, ("pending", "ready"))
        self.assertEqual(
            pickup_order.state,
            "ready" if pickup_order.picking_id.state in ("assigned", "done") else "pending",
        )

    def test_mark_pickup_order_as_delivered(self):
        move = self._create_customer_invoice()
        move.action_post()
        move._ddsn_apply_release_for_amount(move.amount_total)
        move.action_create_pickup_orders()

        pickup_order = move.pickup_order_ids[:1]
        pickup_order.action_mark_delivered()

        self.assertEqual(pickup_order.state, "delivered")
        self.assertTrue(pickup_order.delivered_by_id)
        self.assertTrue(pickup_order.delivered_date)
        self.assertTrue(all(line.qty_delivered == line.product_uom_qty for line in pickup_order.pickup_line_ids))
