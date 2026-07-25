# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ddts_state_id = fields.Many2one(
        "res.country.state",
        string="Tax State",
        related="partner_id.state_id",
        readonly=False,
        store=True,
    )
    ddts_county_name = fields.Char(string="Tax County")
    ddts_tax_rule_ids = fields.One2many(
        "doorandoor.tax.state.rule",
        "company_id",
        string="State Tax Rules",
    )
    ddts_default_sale_tax_id = fields.Many2one(
        "account.tax",
        string="Default State Sale Tax",
        compute="_compute_ddts_default_sale_tax_id",
        store=False,
    )

    @api.depends(
        "ddts_state_id",
        "ddts_county_name",
        "ddts_tax_rule_ids.state_id",
        "ddts_tax_rule_ids.county_name",
        "ddts_tax_rule_ids.sale_tax_id",
        "ddts_tax_rule_ids.active",
    )
    def _compute_ddts_default_sale_tax_id(self):
        for company in self:
            company.ddts_default_sale_tax_id = company._ddts_get_default_sale_tax()

    def _ddts_get_default_sale_tax(self):
        self.ensure_one()
        Rule = self.env["doorandoor.tax.state.rule"]
        county_name = (self.ddts_county_name or "").strip()
        if county_name:
            rule = Rule.search(
                [
                    ("company_id", "=", self.id),
                    ("state_id", "=", self.ddts_state_id.id),
                    ("county_name", "=", county_name),
                    ("active", "=", True),
                ],
                limit=1,
                order="sequence, id",
            )
            if rule:
                return rule.sale_tax_id
        rule = Rule.search(
            [
                ("company_id", "=", self.id),
                ("state_id", "=", self.ddts_state_id.id),
                "|",
                ("county_name", "=", False),
                ("county_name", "=", ""),
                ("active", "=", True),
            ],
            limit=1,
            order="sequence, id",
        )
        return rule.sale_tax_id
