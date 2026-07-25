# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    ddpfw_enforced_warehouse_id = fields.Many2one(
        "stock.warehouse",
        compute="_compute_ddpfw_enforced_warehouse_id",
        string="Configured Purchase Warehouse",
    )
    ddpfw_receipt_picking_id = fields.Many2one(
        "stock.picking",
        compute="_compute_ddpfw_receipt_picking_id",
        string="Primary Receipt",
    )

    @api.depends("company_id")
    def _compute_ddpfw_enforced_warehouse_id(self):
        for order in self:
            order.ddpfw_enforced_warehouse_id = order._ddpfw_get_configured_warehouse(
                company=order.company_id
            )

    @api.depends("picking_ids.state", "picking_ids.picking_type_id", "picking_ids.scheduled_date")
    def _compute_ddpfw_receipt_picking_id(self):
        for order in self:
            order.ddpfw_receipt_picking_id = order._ddpfw_get_target_receipt_picking()

    @api.model
    def _ddpfw_get_configured_warehouse(self, company=None):
        warehouse_id = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "doorandoor_purchase_fixed_warehouse.purchase_warehouse_id", default="0"
            )
            or 0
        )
        if not warehouse_id:
            return self.env["stock.warehouse"]
        warehouse = self.env["stock.warehouse"].browse(warehouse_id).exists()
        if company and warehouse and warehouse.company_id != company:
            return self.env["stock.warehouse"]
        return warehouse

    @api.model
    def _ddpfw_get_incoming_picking_type(self, company=None):
        warehouse = self._ddpfw_get_configured_warehouse(company=company)
        if not warehouse:
            return self.env["stock.picking.type"]
        picking_type = warehouse.in_type_id
        if not picking_type:
            raise UserError(
                _(
                    'El almacen configurado "%(warehouse)s" no tiene un tipo de operacion de recepcion.'
                )
                % {"warehouse": warehouse.display_name}
            )
        return picking_type

    def _ddpfw_apply_configured_picking_type(self):
        for order in self:
            picking_type = order._ddpfw_get_incoming_picking_type(company=order.company_id)
            if picking_type:
                order.picking_type_id = picking_type

    @api.onchange("company_id")
    def _onchange_company_id_ddpfw_apply_picking_type(self):
        self._ddpfw_apply_configured_picking_type()

    @api.onchange("picking_type_id")
    def _onchange_picking_type_id_ddpfw_enforce(self):
        for order in self:
            picking_type = order._ddpfw_get_incoming_picking_type(company=order.company_id)
            if picking_type and order.picking_type_id != picking_type:
                order.picking_type_id = picking_type
                return {
                    "warning": {
                        "title": _("Almacen de compras obligatorio"),
                        "message": _(
                            "El tipo de operacion de la compra se ajusto al almacen configurado."
                        ),
                    }
                }

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        picking_type = self._ddpfw_get_incoming_picking_type(
            company=self.env.company,
        )
        if picking_type and "picking_type_id" in self._fields:
            values["picking_type_id"] = picking_type.id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = self.env["res.company"].browse(vals.get("company_id")) if vals.get("company_id") else self.env.company
            picking_type = self._ddpfw_get_incoming_picking_type(company=company)
            if picking_type:
                vals["picking_type_id"] = picking_type.id
        orders = super().create(vals_list)
        orders._ddpfw_validate_picking_type()
        return orders

    def write(self, vals):
        if "company_id" in vals or "picking_type_id" in vals:
            for order in self:
                company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else order.company_id
                picking_type = order._ddpfw_get_incoming_picking_type(company=company)
                if picking_type:
                    vals = dict(vals, picking_type_id=picking_type.id)
                    break
        result = super().write(vals)
        self._ddpfw_validate_picking_type()
        return result

    def _ddpfw_validate_picking_type(self):
        for order in self:
            picking_type = order._ddpfw_get_incoming_picking_type(company=order.company_id)
            if picking_type and order.picking_type_id != picking_type:
                raise UserError(
                    _(
                        'La compra "%(order)s" debe usar el tipo de recepcion del almacen configurado "%(warehouse)s".'
                    )
                    % {
                        "order": order.display_name,
                        "warehouse": picking_type.warehouse_id.display_name,
                    }
                )

    def _ddpfw_get_target_receipt_picking(self):
        self.ensure_one()
        incoming_pickings = self.picking_ids.filtered(
            lambda picking: picking.picking_type_id.code == "incoming" and picking.state != "cancel"
        )
        prioritized_states = ("assigned", "confirmed", "waiting", "draft", "done")
        for state in prioritized_states:
            picking = incoming_pickings.filtered(lambda candidate: candidate.state == state)[:1]
            if picking:
                return picking
        return incoming_pickings[:1]

    def _ddpfw_get_receipt_for_labels(self):
        self.ensure_one()
        picking = self.ddpfw_receipt_picking_id or self._ddpfw_get_target_receipt_picking()
        if not picking:
            raise UserError(
                _("La orden de compra no tiene una recepcion de entrada disponible para registrar lotes o imprimir etiquetas.")
            )
        return picking

    def action_open_ddpfw_serial_wizard(self):
        self.ensure_one()
        picking = self._ddpfw_get_receipt_for_labels()
        return picking.action_open_ddsl_serial_wizard()

    def action_open_ddpfw_label_wizard(self):
        self.ensure_one()
        picking = self._ddpfw_get_receipt_for_labels()
        return picking.action_open_ddsl_label_wizard()
