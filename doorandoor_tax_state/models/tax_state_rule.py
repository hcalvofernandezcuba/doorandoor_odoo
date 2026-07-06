# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DoorandoorTaxStateRule(models.Model):
    _name = "doorandoor.tax.state.rule"
    _description = "DoorAndDoor Tax State Rule"
    _order = "company_id, sequence, state_id"
    _rec_name = "display_name"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        required=True,
        ondelete="restrict",
        index=True,
    )
    county_name = fields.Char(index=True)
    sale_tax_id = fields.Many2one(
        "account.tax",
        required=True,
        ondelete="restrict",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )
    note = fields.Char()
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    _sql_constraints = [
        (
            "doorandoor_tax_state_rule_company_state_county_unique",
            "unique(company_id, state_id, county_name)",
            "There is already a tax rule for this company, state and county.",
        ),
    ]

    @api.depends("company_id", "state_id", "county_name", "sale_tax_id")
    def _compute_display_name(self):
        for rule in self:
            company = rule.company_id.display_name or ""
            state = rule.state_id.display_name or ""
            county = rule.county_name or ""
            tax = rule.sale_tax_id.display_name or ""
            rule.display_name = " / ".join(part for part in (company, state, county, tax) if part)

    @api.constrains("sale_tax_id", "company_id")
    def _check_tax_company(self):
        for rule in self:
            if rule.sale_tax_id and rule.sale_tax_id.company_id != rule.company_id:
                raise ValidationError("The selected tax must belong to the same company as the rule.")
