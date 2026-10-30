# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("product_id", "company_id", "order_id.ddco_office_id", "order_id.ddts_partner_tax_exempt")
    def _compute_tax_id(self):
        super()._compute_tax_id()
        self._ddco_apply_office_sale_tax()

    def _ddco_apply_office_sale_tax(self):
        for line in self:
            order = line.order_id
            if not order or line.display_type or line.product_type == "combo":
                continue
            if order.ddts_partner_tax_exempt:
                line.tax_id = False
                continue
            office = order.ddco_office_id
            if not office or not office.sale_tax_id:
                continue
            taxes = office.sale_tax_id._filter_taxes_by_company(line.company_id)
            if taxes and order.fiscal_position_id:
                taxes = order.fiscal_position_id.map_tax(taxes)
            line.tax_id = taxes


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("product_id", "product_uom_id", "company_id", "move_id.ddco_office_id", "move_id.ddts_partner_tax_exempt")
    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        self._ddco_apply_office_sale_tax()

    def _ddco_apply_office_sale_tax(self):
        for line in self:
            if self.env.context.get("ddtp_card_fee_line") or line.move_id.ddtp_card_fee_line_id == line:
                continue
            move = line.move_id
            if not move or not move.is_sale_document(include_receipts=True) or line.display_type in ("line_section", "line_note", "payment_term"):
                continue
            if move.ddts_partner_tax_exempt:
                line.tax_ids = [(5, 0, 0)]
                continue
            office = move.ddco_office_id
            if not office or not office.sale_tax_id:
                continue
            taxes = office.sale_tax_id._filter_taxes_by_company(line.company_id)
            if taxes and move.fiscal_position_id:
                taxes = move.fiscal_position_id.map_tax(taxes)
            line.tax_ids = [(6, 0, taxes.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ddco_apply_office_sale_tax()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if {"product_id", "company_id", "move_id", "display_type"}.intersection(vals):
            self._ddco_apply_office_sale_tax()
        return result

    def _get_computed_taxes(self):
        """Evita que un recálculo estándar vuelva a sustituir la tasa de oficina."""
        taxes = super()._get_computed_taxes()
        if self.env.context.get("ddtp_card_fee_line") or self.move_id.ddtp_card_fee_line_id == self:
            return taxes
        self.ensure_one()
        move = self.move_id
        if not move.is_sale_document(include_receipts=True):
            return taxes
        if self.display_type in ("line_section", "line_note", "payment_term"):
            return taxes
        if move.ddts_partner_tax_exempt:
            return self.env["account.tax"]
        office = move.ddco_office_id
        company = self.company_id or move.company_id
        if not office or not office.sale_tax_id or not company:
            return taxes
        taxes = office.sale_tax_id._filter_taxes_by_company(company)
        if taxes and move.fiscal_position_id:
            taxes = move.fiscal_position_id.map_tax(taxes)
        return taxes
