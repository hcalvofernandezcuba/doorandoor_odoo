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
        ],
        string="Flujo de cobro",
        default="immediate",
        required=True,
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
