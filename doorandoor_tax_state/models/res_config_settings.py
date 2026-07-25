# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ddts_company_tax_state_id = fields.Many2one(
        related="company_id.ddts_state_id",
        readonly=False,
        string="Company Tax State",
    )
    ddts_company_tax_county_name = fields.Char(
        related="company_id.ddts_county_name",
        readonly=False,
        string="Company Tax County",
    )
