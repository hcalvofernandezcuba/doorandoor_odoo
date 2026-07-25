# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

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
        for move in self:
            state = move.company_id.ddts_state_id
            county_name = (move.company_id.ddts_county_name or "").strip()
            rule = self.env["doorandoor.tax.state.rule"]
            if county_name:
                rule = rule.search(
                    [
                        ("company_id", "=", move.company_id.id),
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
                        ("company_id", "=", move.company_id.id),
                        ("state_id", "=", state.id),
                        "|",
                        ("county_name", "=", False),
                        ("county_name", "=", ""),
                        ("active", "=", True),
                    ],
                    limit=1,
                    order="sequence, id",
                )
            move.ddts_tax_state_id = state
            move.ddts_tax_rule_id = rule

    @api.onchange("company_id")
    def _onchange_company_id_ddts_apply_tax_rule(self):
        for move in self:
            move._compute_ddts_tax_state_fields()
            move.invoice_line_ids._compute_tax_ids()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.invoice_line_ids._ddts_apply_company_sale_tax()
        return moves

    def write(self, vals):
        result = super().write(vals)
        if {"company_id", "invoice_line_ids", "fiscal_position_id"}.intersection(vals):
            self.invoice_line_ids._ddts_apply_company_sale_tax()
        return result
