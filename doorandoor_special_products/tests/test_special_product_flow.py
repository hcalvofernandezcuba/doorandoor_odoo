from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSpecialProductFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Producto Especial"})
        cls.component = cls.env["product.product"].create(
            {"name": "Componente Especial", "type": "consu", "is_storable": True}
        )
        cls.base_product = cls.env["product.product"].create(
            {"name": "Producto Base", "type": "consu", "is_storable": True, "list_price": 500.0}
        )
        cls.base_bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.base_product.product_tmpl_id.id,
                "product_uom_id": cls.base_product.uom_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 2.0, "product_uom_id": cls.component.uom_id.id})
                ],
            }
        )

    def _create_invoice_line(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (0, 0, {"product_id": self.base_product.id, "quantity": 1.0, "price_unit": 500.0})
                ],
            }
        )
        return invoice.invoice_line_ids.filtered(lambda line: line.product_id)[:1]

    def test_wizard_creates_exclusive_product_and_draft_bom(self):
        invoice_line = self._create_invoice_line()
        wizard = self.env["ddsp.special.product.wizard"].with_context(
            default_invoice_line_id=invoice_line.id
        ).create(
            {
                "invoice_line_id": invoice_line.id,
                "base_product_id": self.base_product.id,
                "name": "Producto Especial Prueba",
                "default_code": "ESP-TEST-1",
                "price_unit": 650.0,
                "special_notes": "Medida especial de prueba",
                "production_instructions": "Cortar, armar y verificar las medidas finales.",
                "width": 36.0,
                "height": 30.0,
                "base_bom_id": self.base_bom.id,
                "component_line_ids": [
                    (0, 0, {"product_id": self.component.id, "product_qty": 3.0, "product_uom_id": self.component.uom_id.id})
                ],
            }
        )
        wizard.action_create_special_product()
        special = invoice_line.product_id.product_tmpl_id
        self.assertTrue(special.ddsp_is_special)
        self.assertEqual(special.ddsp_base_product_tmpl_id, self.base_product.product_tmpl_id)
        self.assertEqual(special.ddsp_origin_invoice_line_id, invoice_line)
        self.assertEqual(special.ddsp_bom_state, "validated")
        self.assertEqual(len(special._ddsp_get_special_bom().bom_line_ids), 1)
        self.assertEqual(special.name, "Producto Base Transformado 36x30")
        self.assertEqual(invoice_line.name, "Producto Base Transformado 36x30")
        self.assertEqual(special.ddsp_dimensions_display, "36 x 30")
        self.assertTrue(special.ddsp_production_instructions)
        self.assertEqual(len(special.barcode), 13)
        self.assertTrue(special.barcode.isdigit())
        self.assertTrue(special.barcode.startswith("29"))
        weighted_sum = sum(
            int(digit) * (1 if index % 2 == 0 else 3)
            for index, digit in enumerate(special.barcode[:12])
        )
        self.assertEqual(int(special.barcode[-1]), (10 - weighted_sum % 10) % 10)

    def test_bom_edit_resets_validation(self):
        template = self.base_product.product_tmpl_id.copy(
            {"name": "Especial validado", "ddsp_is_special": True, "ddsp_bom_state": "validated"}
        )
        bom = self.base_bom.copy({"product_tmpl_id": template.id, "product_id": template.product_variant_id.id})
        template.ddsp_bom_state = "validated"
        bom.bom_line_ids[0].product_qty = 4.0
        self.assertEqual(template.ddsp_bom_state, "draft")

    def test_special_product_always_uses_mrp_route(self):
        invoice_line = self._create_invoice_line()
        invoice_line.product_id.product_tmpl_id.ddsp_is_special = True
        fulfillment = self.env["doorandoor.fulfillment.line"].create(
            {
                "move_id": invoice_line.move_id.id,
                "move_line_id": invoice_line.id,
                "qty_invoiced": 1.0,
                "amount_total": invoice_line.price_total,
            }
        )
        self.assertEqual(invoice_line.move_id._ddsn_get_line_route(fulfillment, 0.5), "ready_mrp")

    def test_configurator_creates_real_special_values_and_complete_name(self):
        finish = self.env["product.attribute"].create(
            {"name": "Acabado", "create_variant": "always"}
        )
        measure = self.env["product.attribute"].create(
            {"name": "Medida", "create_variant": "always"}
        )
        white = self.env["product.attribute.value"].create(
            {"name": "Blanco", "attribute_id": finish.id}
        )
        standard = self.env["product.attribute.value"].create(
            {"name": "30x80", "attribute_id": measure.id}
        )
        template = self.env["product.template"].create(
            {
                "name": "Puerta Base",
                "type": "consu",
                "is_storable": True,
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": finish.id, "value_ids": [(6, 0, white.ids)]}),
                    (0, 0, {"attribute_id": measure.id, "value_ids": [(6, 0, standard.ids)]}),
                ],
            }
        )
        base_variant = template.product_variant_id

        result = self.env["product.template"].ddsp_create_special_from_configurator(
            base_variant.id,
            [
                {"attribute_id": finish.id, "value": "Negro mate"},
                {"attribute_id": measure.id, "value": "33x81"},
            ],
            725.0,
            "Solicitud fuera de catálogo.",
            "Verificar todos los valores antes de fabricar.",
        )

        special = self.env["product.template"].browse(result["product_template_id"])
        self.assertEqual(special.ddsp_product_kind, "transformed")
        self.assertEqual(
            special.name,
            "Puerta Base Transformado [Acabado: Negro mate, Medida: 33x81]",
        )
        self.assertEqual(len(special.attribute_line_ids), 2)
        self.assertEqual(
            set(special.attribute_line_ids.value_ids.mapped("name")),
            {"Negro mate", "33x81"},
        )
        self.assertEqual(special._ddsp_get_special_bom().bom_line_ids.product_id, base_variant)
        self.assertEqual(special.ddsp_bom_state, "validated")

    def test_definitive_configurator_continues_to_special_bom_wizard(self):
        invoice_line = self._create_invoice_line()
        configurator = self.env["ddpc.variant.selector"].create(
            {
                "move_line_id": invoice_line.id,
                "product_template_id": self.base_product.product_tmpl_id.id,
                "quantity": 1.0,
                "ddsp_declare_special": True,
                "ddsp_width": 36.0,
                "ddsp_height": 81.0,
                "ddsp_special_notes": "Medida excepcional solicitada por el cliente.",
                "ddsp_production_instructions": "Verificar ancho y alto antes del armado.",
            }
        )
        configurator._ddpc_load_options()
        action = configurator.action_apply_variant()
        special_wizard = self.env["ddsp.special.product.wizard"].browse(action["res_id"])
        self.assertEqual(action["res_model"], "ddsp.special.product.wizard")
        self.assertEqual(special_wizard.base_product_id, self.base_product)
        self.assertEqual(special_wizard.width, 36.0)
        self.assertEqual(special_wizard.height, 81.0)
        self.assertEqual(special_wizard.name, "Producto Base Transformado 36x81")

    def test_product_can_disable_special_creation(self):
        template = self.base_product.product_tmpl_id
        attribute = self.env["product.attribute"].create(
            {"name": "Atributo bloqueado", "create_variant": "always"}
        )
        template.ddsp_allow_special = False

        with self.assertRaisesRegex(UserError, "no permite crear productos transformados"):
            self.env["product.template"].ddsp_create_special_from_configurator(
                self.base_product.id,
                [{"attribute_id": attribute.id, "value": "Valor bloqueado"}],
                100.0,
                "Especificaciones de prueba.",
                "Instrucciones de prueba.",
            )

    def test_disabled_product_is_hidden_from_legacy_special_selector(self):
        invoice_line = self._create_invoice_line()
        invoice_line.product_id.product_tmpl_id.ddsp_allow_special = False
        configurator = self.env["ddpc.variant.selector"].create(
            {
                "move_line_id": invoice_line.id,
                "product_template_id": invoice_line.product_id.product_tmpl_id.id,
                "quantity": 1.0,
            }
        )

        self.assertFalse(configurator.ddsp_can_create_special)

    def test_configurator_creates_variant_for_dynamic_attributes(self):
        width = self.env["product.attribute"].create(
            {"name": "Ancho dinamico", "create_variant": "dynamic"}
        )
        normal_width = self.env["product.attribute.value"].create(
            {"name": "30", "attribute_id": width.id}
        )
        template = self.env["product.template"].create(
            {
                "name": "Producto dinamico",
                "type": "consu",
                "is_storable": True,
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": width.id, "value_ids": [(6, 0, normal_width.ids)]}),
                ],
            }
        )
        base_variant = template._create_product_variant(
            template.attribute_line_ids.product_template_value_ids
        )

        result = self.env["product.template"].ddsp_create_special_from_configurator(
            base_variant.id,
            [{"attribute_id": width.id, "value": "35"}],
            600.0,
            "Transformacion solicitada.",
            "Verificar el ancho antes de terminar.",
        )

        self.assertTrue(result["product_id"])
        transformed = self.env["product.template"].browse(result["product_template_id"])
        self.assertEqual(transformed.product_variant_id.id, result["product_id"])

    def test_special_product_is_created_from_master_bom(self):
        attribute = self.env["product.attribute"].create(
            {"name": "Medida master", "create_variant": "dynamic"}
        )
        standard_value = self.env["product.attribute.value"].create(
            {"name": "30", "attribute_id": attribute.id}
        )
        master_template = self.env["product.template"].create(
            {
                "name": "MASTER WINDOWS",
                "ddsp_template_output_name": "Window Single Hung",
                "type": "consu",
                "is_storable": True,
                "sale_ok": False,
                "ddsp_is_manufacturing_template": True,
                "ddsp_manufacturing_family": "windows",
                "attribute_line_ids": [
                    (0, 0, {
                        "attribute_id": attribute.id,
                        "value_ids": [(6, 0, standard_value.ids)],
                    }),
                ],
            }
        )
        master_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": master_template.id,
                "product_qty": 1.0,
                "product_uom_id": master_template.uom_id.id,
                "bom_line_ids": [
                    (0, 0, {
                        "product_id": self.component.id,
                        "product_qty": 4.0,
                        "product_uom_id": self.component.uom_id.id,
                    }),
                ],
            }
        )
        self.env["ddsp.manufacturing.rule"].create(
            {
                "bom_id": master_bom.id,
                "component_product_id": self.component.id,
                "attribute_id": attribute.id,
                "base_quantity": 1.0,
                "value_factor": 0.1,
            }
        )
        sale_order = self.env["sale.order"].create({"partner_id": self.partner.id})
        wizard = self.env["ddsp.special.from.master.wizard"].create(
            {
                "sale_order_id": sale_order.id,
                "master_template_id": master_template.id,
                "master_bom_id": master_bom.id,
                "quantity": 1.0,
                "price_unit": 800.0,
                "special_notes": "WINDOW especial desde cero.",
                "production_instructions": "Fabricar segun receta maestra.",
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": attribute.id, "value": "35x81"}),
                ],
            }
        )
        wizard.action_create_special_product()

        sale_line = sale_order.order_line
        special = sale_line.product_id.product_tmpl_id
        special_bom = special._ddsp_get_special_bom()
        self.assertEqual(special.ddsp_product_kind, "special")
        self.assertEqual(special.ddsp_manufacturing_family, "windows")
        self.assertEqual(special.ddsp_source_bom_template_id, master_bom)
        self.assertEqual(special_bom.bom_line_ids.product_id, self.component)
        self.assertEqual(special_bom.bom_line_ids.product_qty, 4.5)
        self.assertNotIn(master_template.product_variant_id, special_bom.bom_line_ids.product_id)
        self.assertTrue(special.ddsp_archive_after_date)

    def test_special_from_master_keeps_base_values_and_selects_recipe(self):
        finish = self.env["product.attribute"].create(
            {"name": "Acabado especial base", "create_variant": "always"}
        )
        measure = self.env["product.attribute"].create(
            {"name": "Medida especial base", "create_variant": "always"}
        )
        white = self.env["product.attribute.value"].create(
            {"name": "Blanco", "attribute_id": finish.id}
        )
        width_30 = self.env["product.attribute.value"].create(
            {"name": "30", "attribute_id": measure.id}
        )
        master = self.env["product.template"].create(
            {
                "name": "MASTER SELECTIVO",
                "ddsp_template_output_name": "Ventana selectiva",
                "sale_ok": False,
                "ddsp_is_manufacturing_template": True,
                "ddsp_manufacturing_family": "windows",
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": finish.id, "value_ids": [(6, 0, white.ids)]}),
                    (0, 0, {"attribute_id": measure.id, "value_ids": [(6, 0, width_30.ids)]}),
                ],
            }
        )
        excluded_component = self.env["product.product"].create(
            {"name": "Componente excluido", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": master.id,
                "product_qty": 1.0,
                "product_uom_id": master.uom_id.id,
                "bom_line_ids": [
                    (0, 0, {"product_id": self.component.id, "product_qty": 2.0}),
                    (0, 0, {"product_id": excluded_component.id, "product_qty": 1.0}),
                ],
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        wizard = self.env["ddsp.special.from.master.wizard"].create(
            {
                "sale_order_id": order.id,
                "master_template_id": master.id,
                "base_variant_id": master.product_variant_id.id,
                "master_bom_id": bom.id,
                "quantity": 1.0,
                "price_unit": 900.0,
                "special_notes": "Configuración selectiva.",
                "production_instructions": "Fabricar solo con componentes marcados.",
                "attribute_line_ids": [
                    (0, 0, {"attribute_id": finish.id, "base_value": "Blanco"}),
                    (0, 0, {
                        "attribute_id": measure.id,
                        "base_value": "30",
                        "modify": True,
                        "value": "36",
                    }),
                ],
                "component_line_ids": [
                    (0, 0, {
                        "include": True,
                        "source_bom_line_id": bom.bom_line_ids[0].id,
                        "product_id": self.component.id,
                        "product_qty": 3.0,
                        "product_uom_id": self.component.uom_id.id,
                    }),
                    (0, 0, {
                        "include": False,
                        "source_bom_line_id": bom.bom_line_ids[1].id,
                        "product_id": excluded_component.id,
                        "product_qty": 1.0,
                        "product_uom_id": excluded_component.uom_id.id,
                    }),
                ],
            }
        )
        wizard.action_create_special_product()

        special = order.order_line.product_id.product_tmpl_id
        self.assertEqual(
            {item["attribute_name"]: item["value"] for item in special.ddsp_special_changes},
            {"Acabado especial base": "Blanco", "Medida especial base": "36"},
        )
        special_bom = special._ddsp_get_special_bom()
        self.assertEqual(special_bom.bom_line_ids.product_id, self.component)
        self.assertEqual(special_bom.bom_line_ids.product_qty, 3.0)
