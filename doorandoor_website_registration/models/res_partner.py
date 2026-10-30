from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddwr_customer_type = fields.Selection(
        [
            ("individual", "Cliente particular"),
            ("builder", "Constructor / empresa constructora"),
            ("builder_client", "Cliente asociado a una constructora"),
        ],
        string="Tipo de cliente web",
        tracking=True,
    )
    ddwr_builder_name_claim = fields.Char(
        string="Constructora declarada",
        tracking=True,
        help="Nombre escrito por el cliente. Debe verificarse internamente antes de vincular un constructor.",
    )
    ddwr_builder_license = fields.Char(string="Licencia del constructor", tracking=True)
    ddwr_state_name = fields.Char(string="Estado / provincia declarado")
    ddwr_project_interest = fields.Text(string="Proyecto o interés declarado")
    ddwr_registration_status = fields.Selection(
        [
            ("pending", "Pendiente de revisión"),
            ("verified", "Verificado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado del registro web",
        default="pending",
        tracking=True,
        copy=False,
    )
    ddwr_privacy_consent = fields.Boolean(string="Consentimiento de privacidad", copy=False)
    ddwr_privacy_consent_date = fields.Datetime(string="Fecha del consentimiento", copy=False, readonly=True)

