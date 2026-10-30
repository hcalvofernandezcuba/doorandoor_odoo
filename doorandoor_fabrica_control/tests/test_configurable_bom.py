from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConfigurablePrehungBom(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Attribute = cls.env["product.attribute"]
        Value = cls.env["product.attribute.value"]

        cls.type_attribute = Attribute.create({"name": "DDFC Test Type"})
        cls.width_attribute = Attribute.create({"name": "DDFC Test Width"})
        cls.hand_attribute = Attribute.create({"name": "DDFC Test Hand"})
        cls.hinge_attribute = Attribute.create({"name": "DDFC Test Hinge"})
        cls.prehung_value = Value.create({
            "name": "Prehung RH", "attribute_id": cls.type_attribute.id,
        })
        cls.slab_value = Value.create({
            "name": "Slab", "attribute_id": cls.type_attribute.id,
        })
        cls.width_value = Value.create({
            "name": "30", "attribute_id": cls.width_attribute.id,
        })
        cls.hand_value = Value.create({
            "name": "RH", "attribute_id": cls.hand_attribute.id,
        })
        cls.hinge_value = Value.create({
            "name": "Silver", "attribute_id": cls.hinge_attribute.id,
        })

        cls.finished_template = cls.env["product.template"].create({
            "name": "DDFC Test Prehung",
            "is_storable": True,
            "attribute_line_ids": [
                (0, 0, {"attribute_id": cls.type_attribute.id, "value_ids": [(6, 0, cls.prehung_value.ids)]}),
                (0, 0, {"attribute_id": cls.width_attribute.id, "value_ids": [(6, 0, cls.width_value.ids)]}),
                (0, 0, {"attribute_id": cls.hand_attribute.id, "value_ids": [(6, 0, cls.hand_value.ids)]}),
                (0, 0, {"attribute_id": cls.hinge_attribute.id, "value_ids": [(6, 0, cls.hinge_value.ids)]}),
            ],
        })
        cls.slab_template = cls.env["product.template"].create({
            "name": "DDFC Test Slab",
            "is_storable": True,
            "attribute_line_ids": [
                (0, 0, {"attribute_id": cls.type_attribute.id, "value_ids": [(6, 0, cls.slab_value.ids)]}),
                (0, 0, {"attribute_id": cls.width_attribute.id, "value_ids": [(6, 0, cls.width_value.ids)]}),
            ],
        })
        cls.jamb = cls.env["product.product"].create({
            "name": "DDFC Test Jamb 30 RH", "is_storable": True,
        })
        cls.hinges = cls.env["product.product"].create({
            "name": "DDFC Test Silver Hinges", "is_storable": True,
        })
        cls.hinges.product_tmpl_id.ddic_shared_lot_serial = True
        cls.family = cls.env["ddfc.prehung.family"].create({
            "name": "DDFC Test Family",
            "finished_product_tmpl_id": cls.finished_template.id,
            "slab_product_tmpl_id": cls.slab_template.id,
            "type_attribute_id": cls.type_attribute.id,
            "prehung_type_value_ids": [(6, 0, cls.prehung_value.ids)],
            "slab_type_value_id": cls.slab_value.id,
            "slab_ignored_attribute_ids": [(6, 0, [cls.hand_attribute.id, cls.hinge_attribute.id])],
            "component_rule_ids": [
                (0, 0, {
                    "role": "jamb",
                    "required_value_ids": [(6, 0, [cls.width_value.id, cls.hand_value.id])],
                    "component_product_id": cls.jamb.id,
                    "quantity": 1.0,
                }),
                (0, 0, {
                    "role": "hinge",
                    "required_value_ids": [(6, 0, cls.hinge_value.ids)],
                    "component_product_id": cls.hinges.id,
                    "quantity": 3.0,
                }),
            ],
        })

    def test_generates_exact_native_bom_and_is_idempotent(self):
        finished = self.finished_template.product_variant_id
        bom = self.family._ddfc_get_or_create_bom(finished)
        self.assertEqual(bom, self.family._ddfc_get_or_create_bom(finished))
        self.assertEqual(bom.product_id, finished)
        self.assertEqual(len(bom.bom_line_ids), 3)
        by_role = {line.ddfc_component_role: line for line in bom.bom_line_ids}
        self.assertEqual(by_role["slab"].product_id, self.slab_template.product_variant_id)
        self.assertEqual(by_role["jamb"].product_id, self.jamb)
        self.assertEqual(by_role["hinge"].product_id, self.hinges)
        self.assertEqual(by_role["slab"].ddfc_label_policy, "unique")
        self.assertEqual(by_role["jamb"].ddfc_label_policy, "unique")
        self.assertEqual(by_role["hinge"].ddfc_label_policy, "shared")
        self.assertEqual(bom.ddfc_bom_kind, "prehung")

    def test_blocks_incorrect_shared_label_policy(self):
        self.hinges.product_tmpl_id.ddic_shared_lot_serial = False
        with self.assertRaisesRegex(UserError, "bisagras.*label compartido"):
            self.family._ddfc_get_or_create_bom(self.finished_template.product_variant_id)

    def test_specific_rule_wins_over_general_rule(self):
        other_jamb = self.env["product.product"].create({
            "name": "DDFC Test Generic Jamb", "is_storable": True,
        })
        self.env["ddfc.prehung.component.rule"].create({
            "family_id": self.family.id,
            "role": "jamb",
            "component_product_id": other_jamb.id,
            "quantity": 1.0,
        })
        rule = self.family._ddfc_resolve_rule_role(
            self.finished_template.product_variant_id, "jamb"
        )
        self.assertEqual(rule.component_product_id, self.jamb)

    def test_bom_classification_keeps_special_and_stock_separate(self):
        special_template = self.env["product.template"].create({
            "name": "DDFC Test Special", "is_storable": True,
            "ddsp_is_special": True,
        })
        special_bom = self.env["mrp.bom"].create({
            "product_tmpl_id": special_template.id,
            "product_qty": 1.0,
        })
        stock_template = self.env["product.template"].create({
            "name": "DDFC Test Stock", "is_storable": True,
        })
        stock_bom = self.env["mrp.bom"].create({
            "product_tmpl_id": stock_template.id,
            "product_qty": 1.0,
            "ddfc_stock_production": True,
        })
        self.assertEqual(special_bom.ddfc_bom_kind, "special")
        self.assertEqual(stock_bom.ddfc_bom_kind, "stock")
