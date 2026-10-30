# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    ddco_office_id = fields.Many2one(
        "doorandoor.commercial.office", string="Commercial Office", copy=True,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        tracking=True,
        readonly=False,
        help="Oficina del vendedor que determinó el impuesto de esta factura.",
    )

    @api.onchange("invoice_user_id", "company_id")
    def _onchange_ddco_invoice_user_office(self):
        for move in self:
            office = move.invoice_user_id.ddco_office_id
            move.ddco_office_id = office if office.company_id == move.company_id else False
            move.ddts_tax_city_rule_id = move._ddco_get_office_city_rule()

    def _ddco_get_office_city_rule(self):
        self.ensure_one()
        office = self.ddco_office_id
        if not office:
            return self.env["doorandoor.tax.state.rule"]
        return self.env["doorandoor.tax.state.rule"].search([
            ("company_id", "=", self.company_id.id),
            ("county_name", "=ilike", office.city),
            ("active", "=", True),
        ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("move_type", "out_invoice") not in ("out_invoice", "out_refund"):
                continue
            if not self.env.user.has_group("base.group_system") and not self.env.context.get("ddco_allow_cross_warehouse"):
                target_user = self.env["res.users"].browse(vals.get("invoice_user_id")) if vals.get("invoice_user_id") else self.env.user
                office = target_user.ddco_office_id
                if not office or not office.operational_warehouse_id:
                    raise ValidationError(_(
                        "El vendedor %s requiere una oficina con almacén operativo antes de facturar."
                    ) % target_user.display_name)
                vals["ddco_office_id"] = office.id
            if not vals.get("ddco_office_id"):
                user = self.env["res.users"].browse(vals.get("invoice_user_id")) if vals.get("invoice_user_id") else self.env.user
                if user.ddco_office_id and user.ddco_office_id.company_id.id == vals.get("company_id", self.env.company.id):
                    vals["ddco_office_id"] = user.ddco_office_id.id
            office = self.env["doorandoor.commercial.office"].browse(vals.get("ddco_office_id"))
            if office:
                rule = self.env["doorandoor.tax.state.rule"].search([
                    ("company_id", "=", office.company_id.id),
                    ("county_name", "=ilike", office.city),
                    ("active", "=", True),
                ], limit=1)
                if rule:
                    vals["ddts_tax_city_rule_id"] = rule.id
        moves = super().create(vals_list)
        if not self.env.user.has_group("base.group_system") and not self.env.context.get("ddco_allow_cross_warehouse"):
            for move in moves.filtered(lambda record: record.move_type in ("out_invoice", "out_refund")):
                user = move.invoice_user_id or self.env.user
                office = user.ddco_office_id or move.ddco_office_id
                warehouse = office.operational_warehouse_id if office else self.env["stock.warehouse"]
                if warehouse:
                    move.invoice_line_ids.filtered(
                        lambda line: line.display_type not in ("line_section", "line_note")
                        and line.ddsn_supply_warehouse_id != warehouse
                    ).with_context(ddco_allow_cross_warehouse=True).write({
                        "ddsn_supply_warehouse_id": warehouse.id,
                    })
        moves.invoice_line_ids._ddco_apply_office_sale_tax()
        return moves

    def write(self, vals):
        if (
            not self.env.user.has_group("base.group_system")
            and not self.env.context.get("ddco_allow_cross_warehouse")
        ):
            for move in self.filtered(lambda record: record.move_type in ("out_invoice", "out_refund")):
                target_user = self.env["res.users"].browse(vals.get("invoice_user_id")) if vals.get("invoice_user_id") else move.invoice_user_id
                target_office = target_user.ddco_office_id
                if "ddco_office_id" in vals and vals["ddco_office_id"] != target_office.id:
                    raise ValidationError(_(
                        "La factura debe conservar la oficina y el almacén asignados al vendedor %s."
                    ) % target_user.display_name)
        result = super().write(vals)
        if {"ddco_office_id", "invoice_user_id", "company_id", "fiscal_position_id"}.intersection(vals):
            for move in self:
                rule = move._ddco_get_office_city_rule()
                if move.ddts_tax_city_rule_id != rule:
                    move.sudo().with_context(ddco_office_sync=True).write({"ddts_tax_city_rule_id": rule.id})
            self.invoice_line_ids._ddco_apply_office_sale_tax()
        return result

    def _ddco_validate_invoice_warehouse(self):
        if self.env.user.has_group("base.group_system") or self.env.context.get("ddco_allow_cross_warehouse"):
            return True
        for move in self.filtered(lambda record: record.move_type in ("out_invoice", "out_refund")):
            user = move.invoice_user_id or self.env.user
            office = user.ddco_office_id or move.ddco_office_id
            warehouse = office.operational_warehouse_id if office else self.env["stock.warehouse"]
            if not warehouse:
                raise ValidationError(_(
                    "El vendedor %s no tiene almacén operativo configurado."
                ) % user.display_name)
            foreign_lines = move.invoice_line_ids.filtered(
                lambda line: line.ddsn_supply_warehouse_id
                and line.ddsn_supply_warehouse_id != warehouse
            )
            if move.ddco_office_id != office or foreign_lines:
                raise ValidationError(_(
                    "La factura %(invoice)s solo puede vender desde %(warehouse)s, "
                    "almacén asignado a %(seller)s."
                ) % {
                    "invoice": move.display_name,
                    "warehouse": warehouse.display_name,
                    "seller": user.display_name,
                })
        return True

    def action_post(self):
        self._ddco_validate_invoice_warehouse()
        return super().action_post()

    def _ddsn_prepare_sale_order_vals(self):
        """Factura directa: el pedido operativo hereda la misma oficina."""
        values = super()._ddsn_prepare_sale_order_vals()
        self.ensure_one()
        values["ddco_office_id"] = self.ddco_office_id.id
        warehouse = self.ddco_office_id.operational_warehouse_id
        if warehouse and warehouse.company_id == self.company_id:
            values["warehouse_id"] = warehouse.id
            if "ddpa_delivery_warehouse_id" in self.env["sale.order"]._fields:
                values["ddpa_delivery_warehouse_id"] = warehouse.id
        return values


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _ddco_required_invoice_warehouse(self):
        self.ensure_one()
        user = self.move_id.invoice_user_id or self.env.user
        office = user.ddco_office_id or self.move_id.ddco_office_id
        return office.operational_warehouse_id if office else self.env["stock.warehouse"]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("base.group_system") and not self.env.context.get("ddco_allow_cross_warehouse"):
            for vals in vals_list:
                move = self.env["account.move"].browse(vals.get("move_id"))
                if not move or move.move_type not in ("out_invoice", "out_refund"):
                    continue
                user = move.invoice_user_id or self.env.user
                office = user.ddco_office_id or move.ddco_office_id
                warehouse = office.operational_warehouse_id if office else self.env["stock.warehouse"]
                if warehouse:
                    vals["ddsn_supply_warehouse_id"] = warehouse.id
        return super().create(vals_list)

    def write(self, vals):
        if (
            "ddsn_supply_warehouse_id" in vals
            and vals["ddsn_supply_warehouse_id"]
            and not self.env.user.has_group("base.group_system")
            and not self.env.context.get("ddco_allow_cross_warehouse")
        ):
            for line in self.filtered(lambda item: item.move_id.move_type in ("out_invoice", "out_refund")):
                warehouse = line._ddco_required_invoice_warehouse()
                if warehouse and vals["ddsn_supply_warehouse_id"] != warehouse.id:
                    raise ValidationError(_(
                        "La factura %(invoice)s solo puede vender desde %(warehouse)s."
                    ) % {"invoice": line.move_id.display_name, "warehouse": warehouse.display_name})
        return super().write(vals)
