# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("product_id", "product_uom_id", "company_id", "move_id.company_id", "move_id.fiscal_position_id")
    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        self._ddts_apply_company_sale_tax()

    def _ddts_apply_company_sale_tax(self):
        for line in self:
            if not line.move_id.is_sale_document(include_receipts=True):
                continue
            if line.display_type in ("line_section", "line_note", "payment_term"):
                continue
            company = line.company_id or line.move_id.company_id
            tax = company._ddts_get_default_sale_tax()
            if not tax:
                continue
            taxes = tax._filter_taxes_by_company(company)
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = [(6, 0, taxes.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ddts_apply_company_sale_tax()
        return lines

    def write(self, vals):
        result = super().write(vals)
        fields_requiring_reapply = {"product_id", "company_id", "move_id", "display_type"}
        if fields_requiring_reapply.intersection(vals):
            self._ddts_apply_company_sale_tax()
        return result

    def _get_computed_taxes(self):
        taxes = super()._get_computed_taxes()
        self.ensure_one()
        if not self.move_id.is_sale_document(include_receipts=True):
            return taxes
        if self.display_type in ("line_section", "line_note", "payment_term"):
            return taxes

        company = self.company_id or self.move_id.company_id
        tax = company._ddts_get_default_sale_tax()
        if not tax or not company:
            return taxes

        taxes = tax._filter_taxes_by_company(company)
        if taxes and self.move_id.fiscal_position_id:
            taxes = self.move_id.fiscal_position_id.map_tax(taxes)
        return taxes
