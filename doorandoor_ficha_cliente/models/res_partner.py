# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddfc_builder_id = fields.Many2one(
        "ddfc.builder.profile",
        string="Constructor asociado",
        tracking=True,
        help=(
            "Constructor, instalador o aliado comercial vinculado a este cliente "
            "para marketing, postventa y garantias."
        ),
    )
    ddfc_builder_discount_percent = fields.Float(
        related="ddfc_builder_id.discount_percent",
        string="Descuento constructor (%)",
        readonly=True,
        store=False,
    )
    ddfc_builder_discount_active = fields.Boolean(
        related="ddfc_builder_id.discount_active",
        string="Descuento constructor activo",
        readonly=True,
        store=False,
    )
    ddfc_builder_name = fields.Char(
        related="ddfc_builder_id.name",
        string="Nombre de constructor",
        readonly=True,
        store=False,
    )
