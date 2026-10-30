# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ddco_office_id = fields.Many2one(
        "doorandoor.commercial.office", string="Commercial Office", ondelete="restrict",
        domain="[('company_id', 'in', company_ids)]",
        help="La oficina comercial define impuesto, almacén y acceso mínimo de ventas del usuario.",
    )

    def _ddco_ensure_office_sales_access(self):
        """Grant only the minimum commercial roles required by an office user."""
        users = self.filtered("ddco_office_id")
        if not users:
            return
        sales_group = self.env.ref("sales_team.group_sale_salesman")
        invoice_group = self.env.ref("account.group_account_invoice")
        users.sudo().write({"groups_id": [(4, sales_group.id), (4, invoice_group.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._ddco_ensure_office_sales_access()
        return users

    def write(self, vals):
        result = super().write(vals)
        if "ddco_office_id" in vals and "groups_id" not in vals:
            self._ddco_ensure_office_sales_access()
        return result
