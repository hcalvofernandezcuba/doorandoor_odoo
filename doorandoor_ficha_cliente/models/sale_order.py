# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddfc_builder_id = fields.Many2one(
        "ddfc.builder.profile",
        string="Constructor asociado",
        related="partner_id.ddfc_builder_id",
        store=True,
        readonly=False,
        index=True,
    )
    ddfc_builder_partner_id = fields.Many2one(
        "res.partner",
        related="ddfc_builder_id.partner_id",
        string="Contacto del constructor",
        store=False,
    )
    ddfc_builder_discount_percent = fields.Float(
        related="ddfc_builder_id.discount_percent",
        string="Descuento constructor (%)",
        store=False,
    )
    ddfc_builder_discount_active = fields.Boolean(
        related="ddfc_builder_id.discount_active",
        string="Descuento constructor activo",
        store=False,
    )
    ddfc_builder_discount_for_new_process = fields.Boolean(
        related="ddfc_builder_id.ddfc_discount_for_new_process",
        string="Constructor nuevo para descuento",
        store=False,
    )
    ddfc_builder_name_text = fields.Char(
        string="Constructor / instalador",
        help="Escribe el nombre y se creará o vinculará automáticamente.",
        copy=False,
        store=False,
    )
    ddfc_pricing_source = fields.Char(
        string="Fuente de precio",
        compute="_compute_ddfc_pricing_source",
        readonly=True,
        store=True,
    )

    @api.depends(
        "partner_id",
        "partner_id.ddfc_builder_id",
        "ddfc_builder_id",
        "ddfc_builder_id.discount_active",
        "ddfc_builder_id.ddfc_discount_for_new_process",
        "order_line.ddsn_bonus_source",
    )
    def _compute_ddfc_pricing_source(self):
        for order in self:
            sources = order.order_line.filtered("ddsn_bonus_source").mapped("ddsn_bonus_source")
            order.ddfc_pricing_source = sources[0] if sources else "base"

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        super()._onchange_partner_id()
        if self.partner_id:
            self.ddfc_builder_id = self.partner_id.ddfc_builder_id
        self._apply_builder_discount()

    @api.onchange("ddfc_builder_name_text")
    def _onchange_ddfc_builder_name_text(self):
        if not self.ddfc_builder_name_text:
            return

        normalized_name = self.ddfc_builder_name_text.strip()
        if not normalized_name:
            return

        if self.ddfc_builder_id and self.ddfc_builder_id.name == normalized_name:
            return

        builder = self.env["ddfc.builder.profile"].resolve_or_create_from_name(
            normalized_name,
            document=self,
        )
        if builder:
            self.ddfc_builder_id = builder
            self.ddfc_builder_name_text = builder.name

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            if prepared_vals.get("ddfc_builder_name_text") and not prepared_vals.get("ddfc_builder_id"):
                builder = self.env["ddfc.builder.profile"].resolve_or_create_from_name(
                    prepared_vals.get("ddfc_builder_name_text"),
                    document=False,
                )
                if builder:
                    prepared_vals["ddfc_builder_id"] = builder.id
                    prepared_vals["ddfc_builder_name_text"] = builder.name
            prepared_vals_list.append(prepared_vals)

        orders = super().create(prepared_vals_list)
        orders._apply_builder_discount()
        return orders

    def write(self, vals):
        if "ddfc_builder_name_text" in vals and vals.get("ddfc_builder_name_text"):
            normalized_name = vals.get("ddfc_builder_name_text").strip()
            builder = self.env["ddfc.builder.profile"].resolve_or_create_from_name(
                normalized_name,
                document=False,
            )
            if builder:
                vals["ddfc_builder_id"] = builder.id
                vals["ddfc_builder_name_text"] = builder.name

        result = super().write(vals)
        if self.env.context.get("skip_builder_discount"):
            return result
        if any(key in vals for key in ["partner_id", "ddfc_builder_id", "order_line", "ddfc_builder_name_text"]):
            self._apply_builder_discount()
        return result

    def _apply_builder_discount(self):
        for order in self:
            for line in order.order_line:
                line.with_context(
                    skip_builder_discount=True,
                    ddsn_automatic_pricing=True,
                )._ddsn_apply_automatic_bonus()
        self._compute_ddfc_pricing_source()

    def action_apply_builder_discount(self):
        self._apply_builder_discount()
        return True

    def ddfc_action_open_builder_wizard(self):
        """Abre el formulario estándar de contacto para crear un constructor"""
        return {
            "type": "ir.actions.act_window",
            "name": "Crear Constructor",
            "res_model": "res.partner",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_is_company": True,
                "default_company_type": "company",
                "default_customer_rank": 1,
                "default_supplier_rank": 1,
                "default_ddfc_is_builder_creation": True,
                "ddfc_source_model": "sale.order",
                "ddfc_source_id": self.id,
                "form_view_initial_mode": "edit",
            },
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ddfc_builder_id = fields.Many2one(
        related="order_id.ddfc_builder_id",
        string="Constructor asociado",
        store=True,
        readonly=True,
    )
    ddfc_pricing_source = fields.Char(related="order_id.ddfc_pricing_source", store=False, readonly=True)
    ddfc_discount_percent = fields.Float(related="order_id.ddfc_builder_discount_percent", store=False, readonly=True)

    def _ddsn_get_automatic_bonus_candidate(self):
        self.ensure_one()
        base_candidate = super()._ddsn_get_automatic_bonus_candidate()
        if base_candidate[1] in ("product", "partner", "fixed_price"):
            return base_candidate
        builder = self.order_id.ddfc_builder_id
        if builder and builder._ddfc_discount_is_current():
            return (
                builder.discount_percent,
                "constructor",
                builder.display_name,
                builder.discount_authorized_by_id,
            )
        return base_candidate
