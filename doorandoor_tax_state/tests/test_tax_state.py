# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDoorandoorTaxState(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
