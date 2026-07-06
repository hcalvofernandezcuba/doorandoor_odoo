# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddts_tax_state_id = fields.Many2one(
        "res.country.state",
        string="Company Tax State",
        compute="_compute_ddts_tax_state_fields",
        store=True,
        readonly=True,
    )
    ddts_tax_rule_id = fields.Many2one(
        "doorandoor.tax.state.rule",
        string="Tax State Rule",
        compute="_compute_ddts_tax_state_fields",
        store=True,
        readonly=True,
    )

    @api.depends("company_id", "company_id.ddts_state_id", "company_id.ddts_county_name", "company_id.ddts_tax_rule_ids")
    def _compute_ddts_tax_state_fields(self):
        for order in self:
            state = order.company_id.ddts_state_id
            county_name = (order.company_id.ddts_county_name or "").strip()
            rule = self.env["doorandoor.tax.state.rule"]
            if county_name:
                rule = rule.search(
                    [
                        ("company_id", "=", order.company_id.id),
                        ("state_id", "=", state.id),
                        ("county_name", "=", county_name),
                        ("active", "=", True),
                    ],
                    limit=1,
                    order="sequence, id",
                )
            if not rule:
                rule = self.env["doorandoor.tax.state.rule"].search(
                    [
                        ("company_id", "=", order.company_id.id),
                        ("state_id", "=", state.id),
                        "|",
                        ("county_name", "=", False),
                        ("county_name", "=", ""),
                        ("active", "=", True),
                    ],
                    limit=1,
                    order="sequence, id",
                )
            order.ddts_tax_state_id = state
            order.ddts_tax_rule_id = rule

    @api.onchange("company_id")
    def _onchange_company_id_ddts_apply_tax_rule(self):
        for order in self:
            order._compute_ddts_tax_state_fields()
            order.order_line._compute_tax_id()
