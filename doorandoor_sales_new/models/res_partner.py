from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddsn_bonus_percent = fields.Float(
        string="Customer Bonus %",
        default=0.0,
        tracking=True,
        help="Default commercial bonus percentage to apply on quotations for this customer.",
    )

    ddsn_bonus_notes = fields.Text(
        string="Bonus Notes",
        tracking=True,
        help="Internal notes about bonus agreements for this customer.",
    )

    ddsn_bonus_active = fields.Boolean(
        string="Customer Bonus Active", default=True, tracking=True,
    )
    ddsn_bonus_date_from = fields.Date(string="Bonus Valid From", tracking=True)
    ddsn_bonus_date_to = fields.Date(string="Bonus Valid Until", tracking=True)
    ddsn_bonus_authorized_by_id = fields.Many2one(
        "res.users", string="Bonus Authorized By", copy=False, tracking=True,
    )

    @api.model
    def _ddsn_customer_bonus_fields(self):
        return {
            "ddsn_bonus_percent",
            "ddsn_bonus_notes",
            "ddsn_bonus_active",
            "ddsn_bonus_date_from",
            "ddsn_bonus_date_to",
            "ddsn_bonus_authorized_by_id",
        }

    @api.model
    def _ddsn_check_customer_bonus_access(self, vals, creating=False):
        changed = self._ddsn_customer_bonus_fields().intersection(vals)
        if not changed:
            return
        # Creating an ordinary contact may include harmless field defaults.
        # Only a real bonus configuration is privileged during create; every
        # later policy change is privileged.
        if creating:
            meaningful = bool(
                vals.get("ddsn_bonus_percent")
                or vals.get("ddsn_bonus_notes")
                or vals.get("ddsn_bonus_date_from")
                or vals.get("ddsn_bonus_date_to")
                or vals.get("ddsn_bonus_authorized_by_id")
                or vals.get("ddsn_bonus_active") is False
            )
            if not meaningful:
                return
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_(
                "Solo Administrador/Ajustes puede configurar bonificaciones de clientes."
            ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._ddsn_check_customer_bonus_access(vals, creating=True)
        return super().create(vals_list)

    def write(self, vals):
        self._ddsn_check_customer_bonus_access(vals)
        return super().write(vals)

    @api.constrains("ddsn_bonus_percent", "ddsn_bonus_date_from", "ddsn_bonus_date_to")
    def _check_ddsn_bonus_percent(self):
        for partner in self:
            if not 0.0 <= partner.ddsn_bonus_percent <= 100.0:
                raise ValidationError("La bonificación del cliente debe estar entre 0 y 100 %.")
            if (
                partner.ddsn_bonus_date_from
                and partner.ddsn_bonus_date_to
                and partner.ddsn_bonus_date_from > partner.ddsn_bonus_date_to
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

    def _ddsn_get_group_bonus_percent(self):
        self.ensure_one()
        bonus_groups = self.category_id.filtered(lambda category: category._ddsn_bonus_is_current())
        if not bonus_groups:
            return 0.0
        return max(bonus_groups.mapped("ddsn_bonus_percent"))

    def _ddsn_get_group_bonus_category(self):
        self.ensure_one()
        groups = self.category_id.filtered(lambda category: category._ddsn_bonus_is_current())
        return groups.sorted(key=lambda category: (category.ddsn_bonus_percent, category.id), reverse=True)[:1]
