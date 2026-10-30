# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddco_office_id = fields.Many2one(
        "doorandoor.commercial.office", string="Commercial Office", copy=True,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        tracking=True,
        help="Oficina del vendedor y origen de la tasa fiscal aplicada.",
    )

    @api.onchange("user_id", "company_id")
    def _onchange_ddco_user_office(self):
        for order in self:
            office = order.user_id.ddco_office_id
            order.ddco_office_id = office if office.company_id == order.company_id else False
            order.ddts_tax_city_rule_id = order._ddco_get_office_city_rule()
            order._ddco_apply_operational_warehouse()

    def _ddco_apply_operational_warehouse(self):
        """Keep the commercial and operational origin on the same office."""
        for order in self:
            warehouse = order.ddco_office_id.operational_warehouse_id
            if not warehouse or warehouse.company_id != order.company_id:
                continue
            order.warehouse_id = warehouse
            if "ddpa_delivery_warehouse_id" in order._fields:
                order.ddpa_delivery_warehouse_id = warehouse

    def _ddco_warehouse_lock_exempt(self):
        return (
            self.env.user.has_group("base.group_system")
            or self.env.context.get("ddco_allow_cross_warehouse")
        )

    def _ddco_required_warehouse(self):
        self.ensure_one()
        office = self.user_id.ddco_office_id or self.ddco_office_id
        return office.operational_warehouse_id if office else self.env["stock.warehouse"]

    def _ddco_validate_sales_warehouse(self):
        if self._ddco_warehouse_lock_exempt():
            return True
        for order in self:
            warehouse = order._ddco_required_warehouse()
            if not warehouse:
                raise ValidationError(_(
                    "El vendedor %(seller)s no tiene un almacén operativo configurado en su oficina."
                ) % {"seller": order.user_id.display_name})
            mismatches = []
            if order.warehouse_id != warehouse:
                mismatches.append(order.warehouse_id.display_name)
            if "ddpa_delivery_warehouse_id" in order._fields and order.ddpa_delivery_warehouse_id != warehouse:
                mismatches.append(order.ddpa_delivery_warehouse_id.display_name)
            foreign_lines = order.order_line.filtered(
                lambda line: line.ddsn_supply_warehouse_id
                and line.ddsn_supply_warehouse_id != warehouse
            )
            if mismatches or foreign_lines:
                raise ValidationError(_(
                    "Esta venta pertenece a %(office)s y solo puede usar %(warehouse)s. "
                    "No está permitido vender desde otro almacén."
                ) % {
                    "office": (order.user_id.ddco_office_id or order.ddco_office_id).display_name,
                    "warehouse": warehouse.display_name,
                })
        return True

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
            if not self.env.user.has_group("base.group_system") and not self.env.context.get("ddco_allow_cross_warehouse"):
                target_user = self.env["res.users"].browse(vals.get("user_id")) if vals.get("user_id") else self.env.user
                office = target_user.ddco_office_id
                warehouse = office.operational_warehouse_id
                if not office or not warehouse:
                    raise ValidationError(_(
                        "El vendedor %s requiere una oficina con almacén operativo antes de vender."
                    ) % target_user.display_name)
                vals["ddco_office_id"] = office.id
                vals["warehouse_id"] = warehouse.id
                if "ddpa_delivery_warehouse_id" in self._fields:
                    vals["ddpa_delivery_warehouse_id"] = warehouse.id
            if not vals.get("ddco_office_id") and vals.get("user_id"):
                user = self.env["res.users"].browse(vals["user_id"])
                if user.ddco_office_id and user.ddco_office_id.company_id.id == vals.get("company_id", self.env.company.id):
                    vals["ddco_office_id"] = user.ddco_office_id.id
            office = self.env["doorandoor.commercial.office"].browse(vals.get("ddco_office_id"))
            if office:
                if office.operational_warehouse_id:
                    vals["warehouse_id"] = office.operational_warehouse_id.id
                    if "ddpa_delivery_warehouse_id" in self._fields:
                        vals["ddpa_delivery_warehouse_id"] = office.operational_warehouse_id.id
                rule = self.env["doorandoor.tax.state.rule"].search([
                    ("company_id", "=", office.company_id.id),
                    ("county_name", "=ilike", office.city),
                    ("active", "=", True),
                ], limit=1)
                if rule:
                    vals["ddts_tax_city_rule_id"] = rule.id
        orders = super().create(vals_list)
        orders.order_line._ddco_apply_office_sale_tax()
        return orders

    def write(self, vals):
        if not self._ddco_warehouse_lock_exempt():
            for order in self:
                target_user = self.env["res.users"].browse(vals.get("user_id")) if vals.get("user_id") else order.user_id
                target_office = target_user.ddco_office_id
                target_warehouse = target_office.operational_warehouse_id
                if not target_warehouse:
                    raise ValidationError(_(
                        "El vendedor %s no tiene almacén operativo configurado."
                    ) % target_user.display_name)
                for field_name in ("warehouse_id", "ddpa_delivery_warehouse_id"):
                    if field_name in vals and vals[field_name] and vals[field_name] != target_warehouse.id:
                        raise ValidationError(_(
                            "El vendedor %(seller)s solo puede vender desde %(warehouse)s."
                        ) % {"seller": target_user.display_name, "warehouse": target_warehouse.display_name})
        result = super().write(vals)
        if {"ddco_office_id", "user_id", "company_id", "fiscal_position_id"}.intersection(vals):
            for order in self:
                rule = order._ddco_get_office_city_rule()
                if order.ddts_tax_city_rule_id != rule:
                    order.sudo().with_context(ddco_office_sync=True).write({"ddts_tax_city_rule_id": rule.id})
                if order.state in ("draft", "sent"):
                    order._ddco_apply_operational_warehouse()
            self.order_line._ddco_apply_office_sale_tax()
        return result

    def action_confirm(self):
        self._ddco_validate_sales_warehouse()
        return super().action_confirm()

    def _prepare_invoice(self):
        """Conserva la oficina del pedido cuando Odoo genera la factura."""
        values = super()._prepare_invoice()
        self.ensure_one()
        values["ddco_office_id"] = self.ddco_office_id.id
        return values


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("base.group_system") and not self.env.context.get("ddco_allow_cross_warehouse"):
            for vals in vals_list:
                order = self.env["sale.order"].browse(vals.get("order_id"))
                warehouse = order._ddco_required_warehouse() if order else self.env["stock.warehouse"]
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
            for line in self:
                warehouse = line.order_id._ddco_required_warehouse()
                if warehouse and vals["ddsn_supply_warehouse_id"] != warehouse.id:
                    raise ValidationError(_(
                        "Las líneas de %(order)s solo pueden usar el almacén %(warehouse)s."
                    ) % {"order": line.order_id.display_name, "warehouse": warehouse.display_name})
        return super().write(vals)
