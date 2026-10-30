# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


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
    ddts_tax_city_rule_id = fields.Many2one(
        "doorandoor.tax.state.rule", string="Ciudad de venta",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        copy=False,
        help="Jurisdicción de la venta. Los administradores pueden cambiarla antes de confirmar.",
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

    @api.depends("ddts_tax_city_rate")
    def _compute_ddts_tax_city_rate_display(self):
        for order in self:
            order.ddts_tax_city_rate_display = order._ddts_format_percent(
                order.ddts_tax_city_rate
            )

    @api.model
    def _ddts_format_percent(self, rate):
        text = ("%.10f" % (rate or 0.0)).rstrip("0").rstrip(".")
        return text.replace(".", ",")

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

    @api.onchange("ddts_tax_city_rule_id")
    def _onchange_ddts_tax_city_rule_id(self):
        self.order_line._compute_tax_id()

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
        return super().create(vals_list)

    def write(self, vals):
        if "ddts_tax_city_rule_id" in vals and not self.env.context.get("ddco_office_sync"):
            if not self.env.user.has_group("base.group_system"):
                raise AccessError(_("Solo los administradores pueden cambiar la ciudad de venta."))
            if any(order.state not in ("draft", "sent") for order in self):
                raise ValidationError(_("La ciudad de venta solo puede cambiarse antes de confirmar el pedido."))
        result = super().write(vals)
        if {"company_id", "ddts_tax_city_rule_id"}.intersection(vals):
            self.order_line._compute_tax_id()
        return result

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.ddts_tax_city_rule_id:
            vals["ddts_tax_city_rule_id"] = self.ddts_tax_city_rule_id.id
        return vals
