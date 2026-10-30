from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoorAndDoorPolicyDocument(models.Model):
    _name = "doorandoor.policy.document"
    _description = "Versión de políticas DoorAndDoor"
    _order = "effective_date desc, id desc"

    name = fields.Char(required=True)
    version = fields.Char(required=True, index=True)
    effective_date = fields.Date(required=True)
    pdf_url = fields.Char(required=True)
    sha256 = fields.Char(required=True, readonly=True)
    pdf_url_es = fields.Char(string="PDF en español")
    sha256_es = fields.Char(string="SHA-256 en español", readonly=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("version_unique", "unique(version)", "La versión de políticas debe ser única."),
    ]

    @api.constrains("sha256", "sha256_es")
    def _check_sha256(self):
        for policy in self:
            for value in filter(None, (policy.sha256, policy.sha256_es)):
                value = value.strip().lower()
                if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                    raise ValidationError(_("La huella SHA-256 de la política no es válida."))

    @api.model
    def get_current_policy(self):
        today = fields.Date.context_today(self)
        return self.search(
            [("active", "=", True), ("effective_date", "<=", today)],
            order="effective_date desc, id desc",
            limit=1,
        )
