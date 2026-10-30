from datetime import datetime, time

from odoo import _, fields, models
from odoo.exceptions import UserError


class DoorAndDoorAuditReportWizard(models.TransientModel):
    _name = "doorandoor.audit.report.wizard"
    _description = "Asistente de reporte de auditoría"

    date_from = fields.Date(
        string="Desde", required=True, default=fields.Date.context_today
    )
    date_to = fields.Date(
        string="Hasta", required=True, default=fields.Date.context_today
    )
    user_id = fields.Many2one("res.users", string="Usuario")
    model_name = fields.Char(string="Modelo técnico")
    operation = fields.Selection(
        [("create", "Creación"), ("write", "Modificación"), ("unlink", "Eliminación")],
        string="Operación",
    )
    price_changes_only = fields.Boolean(string="Solo precios y costos")

    def _report_domain(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("La fecha inicial no puede ser posterior a la fecha final."))
        date_from = fields.Datetime.to_string(datetime.combine(self.date_from, time.min))
        date_to = fields.Datetime.to_string(datetime.combine(self.date_to, time.max))
        domain = [("event_date", ">=", date_from), ("event_date", "<=", date_to)]
        if self.user_id:
            domain.append(("user_id", "=", self.user_id.id))
        if self.model_name:
            domain.append(("model_name", "ilike", self.model_name.strip()))
        if self.operation:
            domain.append(("operation", "=", self.operation))
        if self.price_changes_only:
            domain.append((
                "field_name",
                "in",
                ["list_price", "standard_price", "ddpc_variant_extra_price", "price_extra"],
            ))
        return domain

    def action_print_report(self):
        self.ensure_one()
        logs = self.env["doorandoor.audit.log"].search(
            self._report_domain(), order="event_date, id"
        )
        if not logs:
            raise UserError(_("No existen trazas para los filtros seleccionados."))
        return self.env.ref("doorandoor_audit_log.action_report_audit_log").report_action(logs)
