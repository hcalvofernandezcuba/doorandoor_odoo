from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    ddsn_bonus_active = fields.Boolean(string="Group Bonus Active", default=True)
    ddsn_bonus_date_from = fields.Date(string="Bonus Valid From")
    ddsn_bonus_date_to = fields.Date(string="Bonus Valid Until")
    ddsn_bonus_authorized_by_id = fields.Many2one(
        "res.users", string="Bonus Authorized By", copy=False
    )

    @api.constrains("ddsn_bonus_percent", "ddsn_bonus_date_from", "ddsn_bonus_date_to")
    def _check_ddsn_bonus_percent(self):
        for category in self:
            if not 0.0 <= category.ddsn_bonus_percent <= 100.0:
                raise ValidationError("La bonificación del grupo debe estar entre 0 y 100 %.")
            if (
                category.ddsn_bonus_date_from
                and category.ddsn_bonus_date_to
                and category.ddsn_bonus_date_from > category.ddsn_bonus_date_to
            ):
                raise ValidationError("La fecha final de la bonificación no puede ser anterior a la inicial.")

    def _ddsn_bonus_is_current(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return bool(
            self.ddsn_bonus_active
            and self.ddsn_bonus_percent > 0.0
            and (not self.ddsn_bonus_date_from or self.ddsn_bonus_date_from <= today)
            and (not self.ddsn_bonus_date_to or self.ddsn_bonus_date_to >= today)
        )
