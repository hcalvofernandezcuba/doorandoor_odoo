# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddfc_builder_id = fields.Many2one(
        "ddfc.builder.profile",
        string="Constructor asociado",
        tracking=True,
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
    ddfc_pricing_source = fields.Char(string="Fuente de precio", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.partner_id and move.partner_id.ddfc_builder_id:
                move.ddfc_builder_id = move.partner_id.ddfc_builder_id
                move.ddfc_pricing_source = "constructor"
            else:
                move.ddfc_pricing_source = "base"
        return moves

    def write(self, vals):
        result = super().write(vals)
        if any(key in vals for key in ["partner_id", "ddfc_builder_id"]):
            for move in self:
                if move.partner_id and move.partner_id.ddfc_builder_id:
                    move.ddfc_builder_id = move.partner_id.ddfc_builder_id
                    move.ddfc_pricing_source = "constructor"
                else:
                    move.ddfc_pricing_source = "base"
        return result
