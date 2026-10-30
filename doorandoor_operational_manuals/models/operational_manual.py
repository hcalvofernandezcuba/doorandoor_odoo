from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorOperationalManual(models.Model):
    _name = "doorandoor.operational.manual"
    _description = "Guia operativa interna DoorAndDoor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, area, name"

    name = fields.Char(string="Titulo", required=True, tracking=True)
    code = fields.Char(string="Codigo", required=True, copy=False, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    area = fields.Selection(
        [
            ("historical", "Logistica historica"),
            ("inventory", "Inventario"),
            ("warehouse", "Almacen y Hanger"),
            ("sales", "Ventas"),
            ("payments", "Cobros y caja"),
            ("manufacturing", "Fabricacion"),
            ("support", "Soporte"),
            ("management", "Gerencia"),
        ],
        required=True,
        tracking=True,
    )
    module_name = fields.Char(string="Modulo tecnico", required=True)
    operation_name = fields.Char(string="Operacion / funcion", required=True)
    audience = fields.Char(string="Dirigido a", required=True)
    version = fields.Char(required=True, default="1.0", tracking=True)
    effective_date = fields.Date(
        string="Vigente desde", required=True, default=fields.Date.context_today
    )
    summary = fields.Text(string="Que resuelve", required=True)
    change_log = fields.Text(string="Cambios de esta version")
    state = fields.Selection(
        [("draft", "Borrador"), ("published", "Publicado"), ("archived", "Archivado")],
        default="draft",
        required=True,
        tracking=True,
    )
    pdf_file = fields.Binary(string="PDF", attachment=True)
    pdf_filename = fields.Char(string="Nombre del archivo")
    _sql_constraints = [
        (
            "doorandoor_operational_manual_code_unique",
            "UNIQUE(code)",
            "El codigo de la guia operativa debe ser unico.",
        ),
    ]

    @api.constrains("state", "pdf_file")
    def _check_published_manual(self):
        for manual in self:
            if manual.state == "published" and not manual.pdf_file:
                raise ValidationError(_("No puede publicar una guia sin archivo PDF."))
    def action_publish(self):
        self.write({"state": "published"})

    def action_archive_manual(self):
        self.write({"state": "archived"})

    def action_set_draft(self):
        self.write({"state": "draft"})

    def action_open_internal_center(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/guias-operativas",
            "target": "self",
        }
