from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.doorandoor_product_config.controllers.product_configurator import (
    DoorAndDoorSaleProductConfiguratorController,
)


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

    def test_variant_list_item_filter_searches_all_attribute_tokens(self):
        matching = self.env["product.product"].search(
            [("ddpc_item_search", "ilike", "Grande")]
        )
        impossible = self.env["product.product"].search(
            [("ddpc_item_search", "ilike", "Grande inexistente")]
        )

        self.assertIn(self.variant, matching)
        self.assertNotIn(self.variant_small, matching)
        self.assertFalse(impossible)

    def test_administrator_can_set_final_price_per_variant(self):
        self.variant.ddpc_variant_final_price = 137.5

        self.assertEqual(self.variant.ddpc_variant_extra_price, 37.5)
        self.assertEqual(self.variant.ddpc_variant_final_price, 137.5)
        self.assertEqual(self.product_template.list_price, 100.0)

    def test_sale_quote_uses_selected_item_final_price(self):
        self.variant.ddpc_variant_final_price = 137.5
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.variant.id,
            "product_uom_qty": 1.0,
        })

        self.assertEqual(line.price_unit, 137.5)

    def test_sale_quote_exposes_product_and_selected_item(self):
        with patch(
            "odoo.addons.doorandoor_policy_acceptance.models.policy_acceptance.requests.post"
        ):
            order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.variant.id,
            "product_uom_qty": 1.0,
        })

        self.assertEqual(line.product_template_id, self.product_template)
        self.assertEqual(line.ddpc_item_variant, self.variant.ddpc_item_group)
        self.assertIn("Grande", line.ddpc_item_variant)

    def test_sale_configurator_displays_selected_item_final_price(self):
        self.variant.ddpc_variant_final_price = 235.29
        pricelist = self.env["product.pricelist"].create({"name": "DDPC Test"})

        price, rule_id = self.env["product.template"]._get_configurator_display_price(
            self.variant,
            quantity=1,
            date=fields.Date.today(),
            currency=self.env.company.currency_id,
            pricelist=pricelist,
            uom=self.variant.uom_id,
        )

        self.assertEqual(price, 235.29)
        self.assertFalse(rule_id)

    def test_invoice_configurator_resolves_variant_for_limited_salesperson(self):
        dynamic_attribute = self.env["product.attribute"].create(
            {"name": "DDPC Dynamic Finish", "create_variant": "dynamic"}
        )
        finish = self.env["product.attribute.value"].create(
            {"name": "Bronze", "attribute_id": dynamic_attribute.id}
        )
        template = self.env["product.template"].create(
            {
                "name": "DDPC Dynamic Invoice Product",
                "type": "consu",
                "sale_ok": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": dynamic_attribute.id,
                            "value_ids": [Command.set(finish.ids)],
                        }
                    )
                ],
            }
        )
        combination = template.attribute_line_ids.product_template_value_ids
        salesperson = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "DDPC Limited Invoice Seller",
                "login": "ddpc-limited-invoice-seller",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("sales_team.group_sale_salesman").id,
                            self.env.ref("account.group_account_invoice").id,
                        ]
                    )
                ],
            }
        )
        with self.assertRaises(AccessError):
            template.with_user(salesperson).write({"name": "Forbidden rename"})

        fake_request = SimpleNamespace(env=self.env(user=salesperson))
        controller = DoorAndDoorSaleProductConfiguratorController()
        with patch(
            "odoo.addons.doorandoor_product_config.controllers.product_configurator.request",
            fake_request,
        ):
            endpoint = controller.sale_product_configurator_create_product
            product_id = endpoint.__wrapped__(
                controller, template.id, combination.ids
            )

        product = self.env["product.product"].browse(product_id)
        self.assertEqual(product.product_tmpl_id, template)
        self.assertTrue(product.active)
        self.assertEqual(template.name, "DDPC Dynamic Invoice Product")

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

    def test_hinges_are_required_only_for_prehung_without_creating_variants(self):
        door_type = self.env["product.attribute"].create(
            {"name": "tipo", "create_variant": "always"}
        )
        slab, prehung = self.env["product.attribute.value"].create([
            {"name": "slab door", "attribute_id": door_type.id},
            {"name": "pre-hung door RH", "attribute_id": door_type.id},
        ])
        hinges = self.env["product.attribute"].create(
            {"name": "Hinges", "create_variant": "no_variant"}
        )
        gold, silver, black = self.env["product.attribute.value"].create([
            {"name": "Gold", "attribute_id": hinges.id},
            {"name": "Silver", "attribute_id": hinges.id},
            {"name": "Black", "attribute_id": hinges.id},
        ])
        template = self.env["product.template"].create({
            "name": "Interior Door conditional hinges",
            "type": "consu",
            "attribute_line_ids": [
                (0, 0, {"attribute_id": door_type.id, "value_ids": [(6, 0, [slab.id, prehung.id])]}),
                (0, 0, {"attribute_id": hinges.id, "value_ids": [(6, 0, [gold.id, silver.id, black.id])]}),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)

        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create({
            "move_id": move.id,
            "product_id": template.product_variant_ids[:1].id,
            "name": template.name,
            "quantity": 1.0,
        })
        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        type_line = wizard.attribute_selection_line_ids.filtered(
            lambda item: item.attribute_id == door_type
        )
        prehung_ptav = type_line.available_template_value_ids.filtered(
            lambda value: value.product_attribute_value_id == prehung
        )
        type_line.selected_template_value_id = prehung_ptav
        wizard._compute_hinge_configuration()

        self.assertTrue(wizard.requires_hinges)
        self.assertEqual(
            wizard.available_hinge_template_value_ids.mapped("product_attribute_value_id"),
            gold | silver | black,
        )
        with self.assertRaises(UserError):
            wizard.action_apply_variant()

        wizard.hinge_template_value_id = wizard.available_hinge_template_value_ids.filtered(
            lambda value: value.product_attribute_value_id == gold
        )
        wizard.action_apply_variant()
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            line.ddpc_selected_option_value_ids.product_attribute_value_id,
            gold,
        )

    def test_slab_door_clears_hinges_and_does_not_store_them(self):
        door_type = self.env["product.attribute"].create(
            {"name": "tipo", "create_variant": "always"}
        )
        slab = self.env["product.attribute.value"].create(
            {"name": "slab door", "attribute_id": door_type.id}
        )
        hinges = self.env["product.attribute"].create(
            {"name": "Hinges", "create_variant": "no_variant"}
        )
        gold = self.env["product.attribute.value"].create(
            {"name": "Gold", "attribute_id": hinges.id}
        )
        template = self.env["product.template"].create({
            "name": "Interior Door slab without hinges",
            "type": "consu",
            "attribute_line_ids": [
                (0, 0, {"attribute_id": door_type.id, "value_ids": [(6, 0, slab.ids)]}),
                (0, 0, {"attribute_id": hinges.id, "value_ids": [(6, 0, gold.ids)]}),
            ],
        })
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create({
            "move_id": move.id,
            "product_id": template.product_variant_id.id,
            "name": template.name,
            "quantity": 1.0,
        })
        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        type_line = wizard.attribute_selection_line_ids.filtered(
            lambda item: item.attribute_id == door_type
        )
        type_line.selected_template_value_id = type_line.available_template_value_ids
        wizard._compute_hinge_configuration()
        self.assertFalse(wizard.requires_hinges)
        self.assertFalse(wizard.hinge_template_value_id)
        wizard.action_apply_variant()
        self.assertFalse(line.ddpc_selected_option_value_ids)

    def test_guided_selector_uses_commercial_order_and_loads_color_values(self):
        attribute_names = [
            "Swing",
            "Color",
            "Alto",
            "Ancho",
            "Modelo",
            "Marca",
            "Cristal",
        ]
        attribute_lines = []
        color_values = self.env["product.attribute.value"]
        for index, name in enumerate(attribute_names):
            attribute = self.env["product.attribute"].create(
                {"name": name, "create_variant": "always"}
            )
            values = self.env["product.attribute.value"].create(
                [
                    {"name": "%s A" % name, "attribute_id": attribute.id},
                    {"name": "%s B" % name, "attribute_id": attribute.id},
                ]
                if name == "Color"
                else [{"name": "%s A" % name, "attribute_id": attribute.id}]
            )
            if name == "Color":
                color_values = values
            attribute_lines.append(
                (
                    0,
                    0,
                    {
                        "attribute_id": attribute.id,
                        "sequence": 90 - index,
                        "value_ids": [(6, 0, values.ids)],
                    },
                )
            )
        template = self.env["product.template"].create(
            {
                "name": "Producto orden comercial DDPC",
                "type": "consu",
                "attribute_line_ids": attribute_lines,
            }
        )
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner.id}
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": template.product_variant_ids[:1].id,
                "name": template.name,
                "quantity": 1.0,
            }
        )

        action = line.action_open_ddpc_variant_selector()
        wizard = self.env["ddpc.variant.selector"].browse(action["res_id"])
        ordered_names = wizard.attribute_selection_line_ids.mapped(
            "attribute_id.name"
        )
        self.assertEqual(
            ordered_names,
            ["Marca", "Modelo", "Ancho", "Alto", "Color", "Swing", "Cristal"],
        )
        color_line = wizard.attribute_selection_line_ids.filtered(
            lambda item: item.attribute_id.name == "Color"
        )
        self.assertEqual(
            color_line.available_template_value_ids.mapped(
                "product_attribute_value_id"
            ),
            color_values,
        )
        aliases = self.env["product.attribute"].create(
            [{"name": "PH color"}, {"name": "Hand"}, {"name": "Swin"}]
        )
        alias_lines = self.env["product.template.attribute.line"]
        for index, sequence in enumerate((99, 1, 2)):
            alias_lines |= self.env["product.template.attribute.line"].new(
                {"attribute_id": aliases[index].id, "sequence": sequence}
            )
        self.assertEqual(
            [
                wizard._ddpc_attribute_display_sequence(item)
                for item in alias_lines
            ],
            [50, 60, 60],
        )

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
