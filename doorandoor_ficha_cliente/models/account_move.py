# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddfc_builder_id = fields.Many2one(
        "ddfc.builder.profile",
        string="Constructor asociado",
        tracking=True,
        index=True,
        store=True,
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

    @api.depends("ddfc_builder_id", "ddfc_builder_id.ddfc_discount_for_new_process")
    def _compute_ddfc_pricing_source(self):
        for move in self:
            move.ddfc_pricing_source = (
                "constructor"
                if move.ddfc_builder_id and move.ddfc_builder_id.ddfc_discount_for_new_process
                else "base"
            )

    @api.model
    def _ddfc_resolve_builder_id(self, vals, move=False):
        # 1) Respect explicit user value when provided.
        if "ddfc_builder_id" in vals:
            return vals.get("ddfc_builder_id") or False

        # 2) For refunds, inherit constructor from the reversed invoice when available.
        reversed_entry_id = vals.get("reversed_entry_id") or (move.reversed_entry_id.id if move else False)
        if reversed_entry_id:
            reversed_entry = self.browse(reversed_entry_id)
            if reversed_entry.ddfc_builder_id:
                return reversed_entry.ddfc_builder_id.id

        # 3) Fallback to the current partner default constructor.
        partner_id = vals.get("partner_id") or (move.partner_id.id if move else False)
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            if partner.ddfc_builder_id:
                return partner.ddfc_builder_id.id

        return False

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
            elif "ddfc_builder_id" not in prepared_vals:
                prepared_vals["ddfc_builder_id"] = self._ddfc_resolve_builder_id(prepared_vals)
            prepared_vals_list.append(prepared_vals)
        return super().create(prepared_vals_list)

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

        if self.env.context.get("ddfc_skip_auto_builder"):
            return result

        # Re-sync builder only when partner/refund origin changes and no explicit builder was sent.
        if "ddfc_builder_id" in vals:
            return result
        if not any(key in vals for key in ["partner_id", "reversed_entry_id"]):
            return result

        for move in self:
            resolved_builder_id = self._ddfc_resolve_builder_id(vals, move=move)
            if (move.ddfc_builder_id.id or False) != resolved_builder_id:
                move.with_context(ddfc_skip_auto_builder=True).write({"ddfc_builder_id": resolved_builder_id})

        return result

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
                "ddfc_source_model": "account.move",
                "ddfc_source_id": self.id,
                "form_view_initial_mode": "edit",
            },
        }
