# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    dd_uam_group_ids = fields.Many2many(
        related="groups_id",
        string="Grupos y permisos",
        readonly=True,
    )
    dd_uam_group_count = fields.Integer(
        string="Grupos",
        compute="_compute_dd_uam_access_data",
    )
    dd_uam_group_summary = fields.Text(
        string="Detalle de permisos",
        compute="_compute_dd_uam_access_data",
    )
    dd_uam_company_summary = fields.Char(
        string="Compañías permitidas",
        compute="_compute_dd_uam_access_data",
    )
    dd_uam_is_system_admin = fields.Boolean(
        string="Administrador de Ajustes",
        compute="_compute_dd_uam_access_data",
    )

    @api.depends(
        "groups_id",
        "groups_id.name",
        "groups_id.category_id",
        "company_ids",
        "company_ids.name",
    )
    def _compute_dd_uam_access_data(self):
        system_group = self.env.ref("base.group_system")
        for user in self:
            groups = user.groups_id.sorted(
                key=lambda group: (
                    group.category_id.name or "",
                    group.name or "",
                )
            )
            user.dd_uam_group_count = len(groups)
            user.dd_uam_is_system_admin = system_group in groups
            user.dd_uam_company_summary = ", ".join(user.company_ids.mapped("name"))
            user.dd_uam_group_summary = "\n".join(
                "%s: %s" % (group.category_id.name or "General", group.name)
                for group in groups
            )
