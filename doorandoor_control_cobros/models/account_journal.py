from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ddc_requires_payment_control = fields.Boolean(
        string="Requiere control de cobro",
        help="Si esta activo, los cobros reportados en este diario deben pasar por revision antes de darse por validados.",
    )
    ddc_payment_flow = fields.Selection(
        selection=[
            ("immediate", "Validacion inmediata"),
            ("controlled", "Requiere revision"),
            ("authorized_credit", "Credito con autorizacion del cliente"),
        ],
        string="Flujo de cobro",
        default="immediate",
        required=True,
    )
    ddc_credit_parent_account_id = fields.Many2one(
        "account.account",
        string="Cuenta madre de creditos autorizados",
        check_company=True,
        domain="[('account_type', '=', 'asset_receivable'), ('reconcile', '=', True)]",
        help=(
            "Cuenta madre que identifica la cartera financiada. Cada cliente "
            "recibira automaticamente una subcuenta conciliable propia. Este "
            "diario no admite pagos manuales de entrada ni salida."
        ),
    )

    def write(self, vals):
        self._sync_control_flags(vals)
        return super().write(vals)

    @staticmethod
    def _sync_control_flags(vals):
        if "ddc_payment_flow" in vals and "ddc_requires_payment_control" not in vals:
            vals["ddc_requires_payment_control"] = vals["ddc_payment_flow"] == "controlled"
        elif "ddc_requires_payment_control" in vals and "ddc_payment_flow" not in vals:
            vals["ddc_payment_flow"] = "controlled" if vals["ddc_requires_payment_control"] else "immediate"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_control_flags(vals)
        return super().create(vals_list)
