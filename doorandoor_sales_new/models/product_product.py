from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    ddsn_fixed_price = fields.Boolean(
        string="Precio fijo",
        help=(
            "Impide aplicar cualquier descuento o bonificación a este ITEM, "
            "incluidos los ajustes manuales."
        ),
    )
    ddsn_product_bonus_active = fields.Boolean(
        string="Bonificación del ITEM activa", default=False,
    )
    ddsn_product_bonus_percent = fields.Float(
        string="Bonificación del ITEM (%)", default=0.0,
    )
    ddsn_product_bonus_date_from = fields.Date(string="Bonificación válida desde")
    ddsn_product_bonus_date_to = fields.Date(string="Bonificación válida hasta")
    ddsn_product_bonus_authorized_by_id = fields.Many2one(
        "res.users", string="Bonificación autorizada por", copy=False,
    )
    ddsn_product_bonus_notes = fields.Text(string="Notas de bonificación")
    ddsn_commercial_policy = fields.Selection(
        [
            ("fixed_price", "Precio fijo / Sin bonificación"),
            ("product_bonus", "Bonificación propia del ITEM"),
            ("standard", "Sin regla especial"),
        ],
        string="Política comercial",
        compute="_compute_ddsn_commercial_policy",
        store=True,
        index=True,
    )

    @api.depends("ddsn_fixed_price", "ddsn_product_bonus_active")
    def _compute_ddsn_commercial_policy(self):
        for product in self:
            if product.ddsn_fixed_price:
                product.ddsn_commercial_policy = "fixed_price"
            elif product.ddsn_product_bonus_active:
                product.ddsn_commercial_policy = "product_bonus"
            else:
                product.ddsn_commercial_policy = "standard"

    @api.constrains(
        "ddsn_product_bonus_percent",
        "ddsn_product_bonus_date_from",
        "ddsn_product_bonus_date_to",
    )
    def _check_ddsn_product_bonus(self):
        for product in self:
            if not 0.0 <= product.ddsn_product_bonus_percent <= 100.0:
                raise ValidationError(_(
                    "La bonificación del ITEM debe estar entre 0 y 100 %."
                ))
            if (
                product.ddsn_product_bonus_date_from
                and product.ddsn_product_bonus_date_to
                and product.ddsn_product_bonus_date_from
                > product.ddsn_product_bonus_date_to
            ):
                raise ValidationError(_(
                    "La fecha final de la bonificación no puede ser anterior a la inicial."
                ))

    def _ddsn_product_bonus_is_current(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return bool(
            not self.ddsn_fixed_price
            and self.ddsn_product_bonus_active
            and self.ddsn_product_bonus_percent > 0.0
            and (
                not self.ddsn_product_bonus_date_from
                or self.ddsn_product_bonus_date_from <= today
            )
            and (
                not self.ddsn_product_bonus_date_to
                or self.ddsn_product_bonus_date_to >= today
            )
        )

    @api.model
    def _ddsn_commercial_policy_fields(self):
        return {
            "ddsn_fixed_price",
            "ddsn_product_bonus_active",
            "ddsn_product_bonus_percent",
            "ddsn_product_bonus_date_from",
            "ddsn_product_bonus_date_to",
            "ddsn_product_bonus_authorized_by_id",
            "ddsn_product_bonus_notes",
        }

    @api.model_create_multi
    def create(self, vals_list):
        if any(self._ddsn_commercial_policy_fields().intersection(vals) for vals in vals_list):
            if not self.env.user.has_group("base.group_system"):
                raise AccessError(_(
                    "Solo Administrador/Ajustes puede configurar la política comercial del ITEM."
                ))
        return super().create(vals_list)

    def write(self, vals):
        if self._ddsn_commercial_policy_fields().intersection(vals):
            if not self.env.user.has_group("base.group_system"):
                raise AccessError(_(
                    "Solo Administrador/Ajustes puede configurar la política comercial del ITEM."
                ))
            if vals.get("ddsn_fixed_price"):
                vals = dict(vals, ddsn_product_bonus_active=False)
        return super().write(vals)
