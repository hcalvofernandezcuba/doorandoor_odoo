from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDoorAndDoorAuditLog(TransactionCase):
    def test_product_price_change_is_audited_and_immutable(self):
        product = self.env["product.template"].create({
            "name": "Audit Test Product",
            "list_price": 100.0,
        })
        product.list_price = 125.0

        log = self.env["doorandoor.audit.log"].search([
            ("model_name", "=", "product.template"),
            ("record_id", "=", product.id),
            ("field_name", "=", "list_price"),
            ("operation", "=", "write"),
        ])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.old_value, "100.0")
        self.assertEqual(log.new_value, "125.0")
        self.assertEqual(log.user_id, self.env.user)
        with self.assertRaises(AccessError):
            log.write({"new_value": "999"})
        with self.assertRaises(AccessError):
            log.unlink()

    def test_variant_price_and_user_warehouse_are_audited(self):
        template = self.env["product.template"].create({"name": "Audit Variant"})
        variant = template.product_variant_id
        variant.ddpc_variant_extra_price = 15.0
        self.assertTrue(self.env["doorandoor.audit.log"].search_count([
            ("model_name", "=", "product.product"),
            ("record_id", "=", variant.id),
            ("field_name", "=", "ddpc_variant_extra_price"),
        ]))

        warehouse = self.env["stock.warehouse"].create({"name": "Audit WH", "code": "AUWH"})
        user = self.env["res.users"].create({
            "name": "Audit Operator",
            "login": "audit.operator@example.test",
        })
        user.ddpc_warehouse_ids = warehouse
        self.assertTrue(self.env["doorandoor.audit.log"].search_count([
            ("model_name", "=", "res.users"),
            ("record_id", "=", user.id),
            ("field_name", "=", "ddpc_warehouse_ids"),
        ]))

    def test_filtered_report_action(self):
        product = self.env["product.template"].create({
            "name": "Audit Report Product", "list_price": 50.0,
        })
        product.list_price = 75.0
        wizard = self.env["doorandoor.audit.report.wizard"].create({
            "date_from": fields.Date.today(),
            "date_to": fields.Date.today(),
            "price_changes_only": True,
        })
        action = wizard.action_print_report()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], "doorandoor_audit_log.report_audit_log_document")
