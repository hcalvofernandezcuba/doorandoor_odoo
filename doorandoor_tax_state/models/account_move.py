# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


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
    ddts_tax_city_rule_id = fields.Many2one(
        "doorandoor.tax.state.rule", string="Ciudad de venta",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        copy=False,
    )
    ddts_tax_city_name = fields.Char(
        related="ddts_tax_city_rule_id.county_name",
        string="Ciudad de venta",
        readonly=True,
    )
    ddts_tax_city_rate = fields.Float(
        related="ddts_tax_city_rule_id.sale_tax_id.amount",
        string="Tasa de impuesto",
        readonly=True,
    )
    ddts_tax_city_rate_display = fields.Char(
        string="Tasa de impuesto visible",
        compute="_compute_ddts_tax_city_rate_display",
        readonly=True,
    )
    ddts_partner_tax_exempt = fields.Boolean(
        string="Cliente exento de impuestos",
        related="partner_id.commercial_partner_id.ddts_tax_exempt",
        store=True,
        readonly=True,
    )
    ddts_tax_exemption_number = fields.Char(
        string="Registro fiscal de exención",
        related="partner_id.commercial_partner_id.ddts_tax_exemption_number",
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

    @api.depends("ddts_tax_city_rate")
    def _compute_ddts_tax_city_rate_display(self):
        for move in self:
            move.ddts_tax_city_rate_display = move._ddts_format_percent(
                move.ddts_tax_city_rate
            )

    @api.model
    def _ddts_format_percent(self, rate):
        """Return a compact Spanish percentage without changing the rate."""
        text = ("%.10f" % (rate or 0.0)).rstrip("0").rstrip(".")
        return text.replace(".", ",")

    @api.onchange("company_id")
    def _onchange_company_id_ddts_apply_tax_rule(self):
        for move in self:
            move._compute_ddts_tax_state_fields()
            move.invoice_line_ids._compute_tax_ids()

    @api.onchange("ddts_tax_city_rule_id")
    def _onchange_ddts_tax_city_rule_id(self):
        for move in self:
            move.invoice_line_ids.with_context(check_move_validity=False)._compute_tax_ids()
            refresh_fee = getattr(move, "_ddtp_refresh_card_fee_after_tax_change", None)
            if refresh_fee:
                refresh_fee()

    @api.model_create_multi
    def create(self, vals_list):
        Rule = self.env["doorandoor.tax.state.rule"]
        city = (self.env.user.partner_id.city or "").strip()
        for vals in vals_list:
            if not vals.get("ddts_tax_city_rule_id") and city:
                company_id = vals.get("company_id") or self.env.company.id
                rule = Rule.search([("company_id", "=", company_id), ("county_name", "=ilike", city), ("active", "=", True)], limit=1)
                if rule:
                    vals["ddts_tax_city_rule_id"] = rule.id
        moves = super().create(vals_list)
        moves.invoice_line_ids._ddts_apply_company_sale_tax()
        return moves

    def write(self, vals):
        if "ddts_tax_city_rule_id" in vals and not self.env.context.get("ddco_office_sync"):
            if not self.env.user.has_group("base.group_system"):
                raise AccessError(_("Solo los administradores pueden cambiar la ciudad de venta."))
            if any(move.state != "draft" for move in self):
                raise ValidationError(_("La ciudad de venta solo puede cambiarse en una factura borrador."))
        result = super().write(vals)
        if {"company_id", "invoice_line_ids", "fiscal_position_id", "ddts_tax_city_rule_id"}.intersection(vals):
            self.invoice_line_ids.with_context(check_move_validity=False)._ddts_apply_company_sale_tax()
            for move in self:
                refresh_fee = getattr(move, "_ddtp_refresh_card_fee_after_tax_change", None)
                if refresh_fee:
                    refresh_fee()
                imbalance = sum(move.line_ids.mapped("balance"))
                if not move.company_currency_id.is_zero(imbalance):
                    raise ValidationError(_(
                        "El cambio de ciudad no dejó la factura balanceada. Diferencia: %(amount)s."
                    ) % {"amount": move.company_currency_id.format(imbalance)})
        return result
