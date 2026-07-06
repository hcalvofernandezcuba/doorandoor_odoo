# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class DoorandoorTaxStateGenerateWizard(models.TransientModel):
    _name = "doorandoor.tax.state.generate.wizard"
    _description = "Generate State Taxes by Company"

    company_ids = fields.Many2many(
        "res.company",
        string="Companies",
        required=True,
        default=lambda self: self.env.companies,
    )
    create_missing_taxes = fields.Boolean(default=True)
    overwrite_existing_rules = fields.Boolean(default=True)
    only_company_state = fields.Boolean(
        string="Only Current Company State",
        default=False,
        help="If enabled, generates only the rule for each company's configured Tax State.",
    )

    def action_generate(self):
        self.ensure_one()
        Rate = self.env["doorandoor.tax.state.rate"]
        Rule = self.env["doorandoor.tax.state.rule"]
        Tax = self.env["account.tax"]

        if not self.company_ids:
            raise UserError("Select at least one company.")

        for company in self.company_ids:
            states = company.ddts_state_id if self.only_company_state else self.env["res.country.state"].search(
                [("country_id.code", "=", "US")]
            )
            for state in states:
                rate_record = Rate._get_latest_rate_for_state(state, company.ddts_county_name)
                if not rate_record:
                    continue
                county_suffix = (" - %s" % rate_record.county_name) if rate_record.county_name else ""
                tax = Tax.search(
                    [
                        ("company_id", "=", company.id),
                        ("type_tax_use", "=", "sale"),
                        ("name", "=", "%s%s Sales Tax" % ((state.code or state.name), county_suffix)),
                    ],
                    limit=1,
                )
                if not tax and self.create_missing_taxes:
                    tax = Tax.create(
                        {
                            "name": "%s%s Sales Tax" % ((state.code or state.name), county_suffix),
                            "amount": rate_record.rate,
                            "amount_type": "percent",
                            "type_tax_use": "sale",
                            "company_id": company.id,
                            "description": "%s%s %.4f%%" % ((state.code or state.name), county_suffix, rate_record.rate),
                        }
                    )
                elif tax:
                    tax.write(
                        {
                            "amount": rate_record.rate,
                            "description": "%s%s %.4f%%" % ((state.code or state.name), county_suffix, rate_record.rate),
                        }
                    )

                if not tax:
                    continue

                rule = Rule.search(
                    [("company_id", "=", company.id), ("state_id", "=", state.id)],
                    limit=1,
                )
                vals = {
                    "company_id": company.id,
                    "state_id": state.id,
                    "county_name": rate_record.county_name or False,
                    "sale_tax_id": tax.id,
                    "note": "Generated from editable state rate table.",
                }
                if rule and self.overwrite_existing_rules:
                    rule.write(vals)
                elif not rule:
                    Rule.create(vals)

        return {"type": "ir.actions.act_window_close"}
