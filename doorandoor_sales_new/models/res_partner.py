from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddsn_bonus_percent = fields.Float(
        string="Customer Bonus %",
        default=0.0,
        help="Default commercial bonus percentage to apply on quotations for this customer.",
    )

    ddsn_bonus_notes = fields.Text(
        string="Bonus Notes",
        help="Internal notes about bonus agreements for this customer.",
    )

    def _ddsn_get_group_bonus_percent(self):
        self.ensure_one()
        bonus_groups = self.category_id.filtered(lambda category: category.ddsn_bonus_percent > 0.0)
        if not bonus_groups:
            return 0.0
        return max(bonus_groups.mapped("ddsn_bonus_percent"))
