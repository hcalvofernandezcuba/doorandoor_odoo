from odoo import fields
from odoo.exceptions import UserError
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
                "product_id": self.variant.id,
                "name": "Linea configurable",
                "quantity": 1.0,
            }
        )

        wizard_action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(wizard_action["res_id"])
        target_values = self.variant_small.product_template_attribute_value_ids
        for selection_line in wizard.attribute_selection_line_ids:
            selection_line.selected_template_value_id = target_values.filtered(
                lambda value: value.attribute_id == selection_line.attribute_id
            )[:1]
        wizard.action_apply_variant()

        self.assertEqual(line.product_id, self.variant_small)
        self.assertEqual(line.price_unit, 115.0)

    def test_invoice_uses_template_selector_without_variant_list(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].new(
            {"move_id": move.id, "name": "Producto por configurar", "quantity": 1.0}
        )
        line.ddpc_product_template_id = self.product_template
        line._onchange_ddpc_product_template_id()
        self.assertFalse(
            line.product_id,
            "La variante definitiva solo debe asignarse al confirmar el configurador",
        )
        self.assertTrue(line.ddpc_configurator_token)

    def test_configurator_action_can_find_saved_line_by_token(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.variant.id,
                "name": self.variant.display_name,
                "quantity": 1.0,
            }
        )
        action = self.env["account.move.line"].action_open_ddpc_variant_selector_by_token(
            move.id, line.ddpc_configurator_token
        )
        self.assertEqual(action["res_model"], "ddpc.variant.selector")

    def test_guided_selector_requires_value_for_each_variant_attribute(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.variant.id,
                "name": self.variant.display_name,
                "quantity": 1.0,
            }
        )
        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        with self.assertRaises(UserError):
            wizard.action_apply_variant()

    def test_guided_preview_does_not_expose_archived_variant(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.variant.id,
                "name": self.variant.display_name,
                "quantity": 1.0,
            }
        )
        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        target_values = self.variant.product_template_attribute_value_ids
        for selection_line in wizard.attribute_selection_line_ids:
            selection_line.selected_template_value_id = target_values.filtered(
                lambda value: value.attribute_id == selection_line.attribute_id
            )[:1]
        self.variant.active = False
        wizard._compute_preview()
        self.assertFalse(wizard.variant_id)
        self.assertIn("reactivara", wizard.variant_preview_name)
        applied_variant = wizard._ddpc_get_guided_variant()
        self.assertEqual(applied_variant, self.variant)
        self.assertTrue(applied_variant.active)

    def test_guided_selector_opens_without_preselected_options(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.variant.id,
                "name": self.variant.display_name,
                "quantity": 1.0,
            }
        )
        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        self.assertTrue(wizard.attribute_selection_line_ids)
        self.assertFalse(
            wizard.attribute_selection_line_ids.filtered("selected_template_value_id")
        )
        self.assertFalse(wizard.option_line_ids.filtered("selected"))

    def test_selector_creates_only_requested_custom_variant(self):
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
        initial_variant_count = len(self.product_template.with_context(active_test=False).product_variant_ids)
        wizard_action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(wizard_action["res_id"])
        wizard.write(
            {
                "selection_mode": "custom",
                "custom_attribute_id": self.attribute.id,
                "custom_value": "84x36x30",
                "custom_default_code": "DDPC-84X36X30",
                "custom_extra_price": 40.0,
            }
        )
        wizard.action_apply_variant()

        custom_variant = line.product_id
        self.assertTrue(custom_variant.ddpc_is_custom_variant)
        self.assertEqual(custom_variant.default_code, "DDPC-84X36X30")
        self.assertEqual(custom_variant.ddpc_origin_invoice_id, move)
        self.assertEqual(custom_variant.ddpc_variant_extra_price, 40.0)
        self.assertEqual(line.price_unit, 140.0)
        self.assertEqual(
            len(self.product_template.with_context(active_test=False).product_variant_ids),
            initial_variant_count + 1,
        )

        custom_variant.active = False
        second_line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.variant.id,
                "name": self.variant.display_name,
                "quantity": 1.0,
            }
        )
        second_action = second_line.action_open_ddpc_variant_selector()
        second_wizard = self.env["ddpc.variant.selector"].browse(second_action["res_id"])
        second_wizard.write(
            {
                "selection_mode": "custom",
                "custom_attribute_id": self.attribute.id,
                "custom_value": "84X36X30",
                "custom_extra_price": 40.0,
            }
        )
        second_wizard.action_apply_variant()
        self.assertEqual(second_line.product_id, custom_variant)
        self.assertTrue(custom_variant.active)
