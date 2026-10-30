# -*- coding: utf-8 -*-

import base64

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDoorandoorTaxState(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # These tests exercise only fiscal behavior.  Local may intentionally
        # route policy invitations through Telegram, which is an external side
        # effect and must not be triggered by an unrelated tax regression.
        cls.env = cls.env(context={**cls.env.context, "ddpa_skip_auto_policy": True})
        us_country = cls.env.ref("base.us")
        cls.state = cls.env["res.country.state"].create(
            {
                "name": "Florida Test",
                "code": "FLX",
                "country_id": us_country.id,
            }
        )
        cls.company = cls.env.company
        cls.company.partner_id.state_id = cls.state
        cls.default_tax = cls.env["account.tax"].create(
            {
                "name": "Default Sale Tax",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.state_tax = cls.env["account.tax"].create(
            {
                "name": "Florida State Tax",
                "amount": 7.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.rule = cls.env["doorandoor.tax.state.rule"].create(
            {
                "company_id": cls.company.id,
                "state_id": cls.state.id,
                "sale_tax_id": cls.state_tax.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Tax State"})
        cls.valid_pdf = base64.b64encode(b"%PDF-1.4\n%%EOF\n")
        cls.sales_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Tax Exemption Sales Test",
                "login": "tax.exemption.sales.test",
                "groups_id": [
                    (6, 0, [cls.env.ref("sales_team.group_sale_salesman").id])
                ],
            }
        )
        cls.accounting_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Tax Exemption Accounting Test",
                "login": "tax.exemption.accounting.test",
                "groups_id": [
                    (6, 0, [cls.env.ref("account.group_account_user").id])
                ],
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Tax State",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
                "taxes_id": [(6, 0, cls.default_tax.ids)],
            }
        )

    def test_sale_order_line_uses_company_state_tax(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "company_id": self.company.id,
            }
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 100.0,
            }
        )

        self.assertEqual(order.ddts_tax_rule_id, self.rule)
        self.assertEqual(line.tax_id, self.state_tax)

    def test_invoice_line_uses_company_state_tax(self):
        income_account = (
            self.product.property_account_income_id
            or self.product.categ_id.property_account_income_categ_id
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "company_id": self.company.id,
            }
        )
        line = self.env["account.move.line"].new(
            {
                "move_id": move.id,
                "product_id": self.product.id,
                "company_id": self.company.id,
                "account_id": income_account.id,
                "name": self.product.display_name,
                "quantity": 1.0,
                "price_unit": 100.0,
            }
        )

        self.assertEqual(move.ddts_tax_rule_id, self.rule)
        self.assertEqual(line._get_computed_taxes(), self.state_tax)

    def test_tax_exempt_partner_requires_registration_number(self):
        with self.assertRaises(ValidationError):
            self.partner.write({"ddts_tax_exempt": True})

    def test_tax_exempt_partner_requires_valid_pdf(self):
        with self.assertRaises(ValidationError):
            self.partner.write(
                {
                    "ddts_tax_exempt": True,
                    "ddts_tax_exemption_number": "FL-EXEMPT-12345",
                }
            )
        with self.assertRaises(ValidationError):
            self.partner.write(
                {
                    "ddts_tax_exemption_document": base64.b64encode(b"not a pdf"),
                    "ddts_tax_exemption_document_name": "certificate.pdf",
                }
            )

    def test_sales_can_read_but_cannot_edit_tax_exemption(self):
        self.partner.write(
            {
                "ddts_tax_exempt": True,
                "ddts_tax_exemption_number": "FL-EXEMPT-READONLY",
                "ddts_tax_exemption_document": self.valid_pdf,
                "ddts_tax_exemption_document_name": "certificate.pdf",
            }
        )
        partner_as_sales = self.partner.with_user(self.sales_user)
        self.assertTrue(partner_as_sales.ddts_tax_exempt)
        self.assertEqual(
            partner_as_sales.ddts_tax_exemption_number, "FL-EXEMPT-READONLY"
        )
        self.assertTrue(partner_as_sales.ddts_tax_exemption_document)
        with self.assertRaises(ValidationError):
            partner_as_sales.write({"ddts_tax_exemption_number": "FORBIDDEN"})

    def test_sales_can_create_regular_customer_with_empty_exemption_fields(self):
        partner = self.env["res.partner"].with_user(self.sales_user).create(
            {
                "name": "Cliente regular creado por Ventas",
                "ddts_tax_exempt": False,
                "ddts_tax_exemption_number": False,
                "ddts_tax_exemption_document": False,
                "ddts_tax_exemption_document_name": False,
            }
        )
        self.assertTrue(partner)
        self.assertFalse(partner.ddts_tax_exempt)

    def test_sales_cannot_create_tax_exempt_customer(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].with_user(self.sales_user).create(
                {
                    "name": "Cliente exento no autorizado",
                    "ddts_tax_exempt": True,
                }
            )

    def test_accounting_can_edit_tax_exemption(self):
        self.partner.with_user(self.accounting_user).write(
            {
                "ddts_tax_exempt": True,
                "ddts_tax_exemption_number": "FL-EXEMPT-ACCOUNTING",
                "ddts_tax_exemption_document": self.valid_pdf,
                "ddts_tax_exemption_document_name": "accounting-certificate.pdf",
            }
        )
        self.assertTrue(self.partner.ddts_tax_exemption_uploaded_at)
        self.assertEqual(
            self.partner.ddts_tax_exemption_uploaded_by, self.accounting_user
        )
        self.partner.with_user(self.accounting_user).write(
            {"name": "Cliente actualizado por Contabilidad"}
        )
        self.assertEqual(self.partner.name, "Cliente actualizado por Contabilidad")

    def test_tax_exempt_partner_removes_sale_and_invoice_taxes(self):
        self.partner.write(
            {
                "ddts_tax_exempt": True,
                "ddts_tax_exemption_number": "FL-EXEMPT-12345",
                "ddts_tax_exemption_document": self.valid_pdf,
                "ddts_tax_exemption_document_name": "certificate.pdf",
            }
        )
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "company_id": self.company.id}
        )
        sale_line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "price_unit": 100.0,
            }
        )
        self.assertTrue(order.ddts_partner_tax_exempt)
        self.assertEqual(order.ddts_tax_exemption_number, "FL-EXEMPT-12345")
        self.assertFalse(sale_line.tax_id)
        self.assertEqual(order.amount_tax, 0.0)

        income_account = (
            self.product.property_account_income_id
            or self.product.categ_id.property_account_income_categ_id
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "account_id": income_account.id,
                            "name": self.product.display_name,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        self.assertTrue(invoice.ddts_partner_tax_exempt)
        self.assertEqual(invoice.ddts_tax_exemption_number, "FL-EXEMPT-12345")
        self.assertFalse(invoice.invoice_line_ids.filtered(lambda line: not line.display_type).tax_ids)
        self.assertEqual(invoice.amount_tax, 0.0)
