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
    ddfc_pricing_source = fields.Char(string="Fuente de precio", default="base", readonly=True)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        super()._onchange_partner_id()
        if self.partner_id:
            self.ddfc_builder_id = self.partner_id.ddfc_builder_id
        self._apply_builder_discount()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._apply_builder_discount()
        return orders

    def write(self, vals):
        result = super().write(vals)
        if any(key in vals for key in ["partner_id", "ddfc_builder_id", "order_line"]):
            self._apply_builder_discount()
        return result

    def _apply_builder_discount(self):
        for order in self:
            if not order.ddfc_builder_id or not order.ddfc_builder_id.discount_active:
                order.ddfc_pricing_source = "base"
                for line in order.order_line:
                    line.discount = 0.0
                continue
            order.ddfc_pricing_source = "constructor"
            for line in order.order_line:
                line.discount = order.ddfc_builder_id.discount_percent

    def action_apply_builder_discount(self):
        self._apply_builder_discount()
        return True


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
