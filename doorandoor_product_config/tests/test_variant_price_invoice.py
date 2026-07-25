from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVariantPriceInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente DDPC"})
        cls.attribute = cls.env["product.attribute"].create({"name": "Medida SLAP"})
        cls.attribute_value = cls.env["product.attribute.value"].create(
            {
                "name": "Grande",
                "attribute_id": cls.attribute.id,
            }
        )
        cls.attribute_value_small = cls.env["product.attribute.value"].create(
            {
                "name": "Pequena",
                "attribute_id": cls.attribute.id,
            }
        )
        cls.product_template = cls.env["product.template"].create(
            {
                "name": "Producto Configurable DDPC",
                "type": "consu",
                "list_price": 100.0,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": cls.attribute.id,
                            "value_ids": [(6, 0, [cls.attribute_value.id, cls.attribute_value_small.id])],
                        },
                    )
                ],
            }
        )
        cls.variant = cls.product_template.product_variant_ids.filtered(
            lambda product: cls.attribute_value in product.product_template_attribute_value_ids.product_attribute_value_id
        )[:1]
        cls.variant_small = (cls.product_template.product_variant_ids - cls.variant)[:1]

    def test_invoice_line_uses_base_price_plus_variant_extra(self):
        self.variant.ddpc_variant_extra_price = 25.0

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
                            "product_id": self.variant.id,
                            "name": self.variant.display_name,
                            "quantity": 2.0,
                        },
                    )
                ],
            }
        )
        line = move.invoice_line_ids.filtered(lambda item: item.product_id == self.variant)

        self.assertEqual(line.ddpc_base_price, 100.0)
        self.assertEqual(line.ddpc_variant_extra_price, 25.0)
        self.assertEqual(line.price_unit, 125.0)
        self.assertEqual(line.ddpc_configured_price_unit, 125.0)
        self.assertEqual(line.price_subtotal, 250.0)

    def test_invoice_line_falls_back_to_base_price_when_variant_has_no_extra(self):
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
                            "product_id": self.variant.id,
                            "name": self.variant.display_name,
                            "quantity": 1.0,
                        },
                    )
                ],
            }
        )
        line = move.invoice_line_ids.filtered(lambda item: item.product_id == self.variant)

        self.assertEqual(line.price_unit, 100.0)
        self.assertEqual(line.ddpc_variant_extra_price, 0.0)

    def test_variant_selector_applies_variant_and_price_on_invoice_line(self):
        self.variant_small.ddpc_variant_extra_price = 15.0
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
            }
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "name": "Linea configurable",
                "quantity": 1.0,
            }
        )

        wizard_action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(wizard_action["res_id"])
        wizard.product_template_id = self.product_template
        wizard.variant_id = self.variant_small
        wizard.action_apply_variant()

        self.assertEqual(line.product_id, self.variant_small)
        self.assertEqual(line.price_unit, 115.0)
