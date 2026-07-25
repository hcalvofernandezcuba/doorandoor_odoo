from odoo import fields, models


class ResPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    ddsn_bonus_percent = fields.Float(
        string="Group Bonus %",
        default=0.0,
        help="Default commercial bonus percentage for partners in this group.",
    )

    ddsn_bonus_notes = fields.Text(
        string="Group Bonus Notes",
        help="Internal notes about the commercial bonus for this group.",
    )
