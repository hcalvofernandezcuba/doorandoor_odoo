from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddc_advance_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de pagos anticipados",
        company_dependent=True,
        domain="[('account_type', '=', 'liability_current'), ('reconcile', '=', True)]",
        help="Subcuenta individual del cliente bajo 120000 Pagos Anticipados.",
    )
    ddc_credit_financing_account_id = fields.Many2one(
        "account.account",
        string="Subcuenta de credito autorizado",
        company_dependent=True,
        domain="[('account_type', '=', 'asset_receivable'), ('reconcile', '=', True)]",
        help="Cuenta individual donde permanece la deuda financiada del cliente.",
    )
    ddc_credit_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del credito autorizado",
        compute="_compute_ddc_authorized_credit",
    )
    ddc_authorized_credit_limit = fields.Float(
        string="Credito autorizado",
        digits="Product Price",
        company_dependent=True,
        help="Importe maximo que DoorAndDoor permite pagar con autorizacion del cliente.",
    )
    ddc_authorized_credit_used = fields.Monetary(
        string="Credito utilizado",
        currency_field="ddc_credit_currency_id",
        compute="_compute_ddc_authorized_credit",
    )
    ddc_authorized_credit_available = fields.Monetary(
        string="Credito disponible",
        currency_field="ddc_credit_currency_id",
        compute="_compute_ddc_authorized_credit",
    )

    def _compute_ddc_authorized_credit(self):
        Authorization = self.env["doorandoor.credit.authorization"]
        company = self.env.company
        for partner in self:
            partner.ddc_credit_currency_id = company.currency_id
            commercial = partner.commercial_partner_id
            used, reserved = Authorization.credit_totals(commercial, company)
            limit_amount = commercial.with_company(company).ddc_authorized_credit_limit
            partner.ddc_authorized_credit_used = used
            partner.ddc_authorized_credit_available = max(
                limit_amount - used - reserved, 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any("ddc_authorized_credit_limit" in vals for vals in vals_list):
            self._ddc_check_credit_limit_permission()
        return super().create(vals_list)

    def write(self, vals):
        if "ddc_authorized_credit_limit" in vals:
            self._ddc_check_credit_limit_permission()
        return super().write(vals)

    def _ddc_check_credit_limit_permission(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Solo un administrador de Ajustes puede modificar el credito autorizado.")
            )
