from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


class DoorandoorHelpdeskDailyReport(models.TransientModel):
    _name = "doorandoor.helpdesk.daily.report"
    _description = "Reporte diario de soporte técnico"

    report_date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, default=lambda self: self.env.company
    )
    ticket_ids = fields.Many2many(
        "doorandoor.helpdesk.ticket", string="Tickets reportados",
        compute="_compute_ticket_ids",
    )

    def _utc_day_bounds(self):
        self.ensure_one()
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        local_start = timezone.localize(datetime.combine(self.report_date, time.min))
        local_end = local_start + timedelta(days=1)
        return (
            local_start.astimezone(pytz.UTC).replace(tzinfo=None),
            local_end.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    @api.depends("report_date", "company_id")
    def _compute_ticket_ids(self):
        for wizard in self:
            if not wizard.report_date or not wizard.company_id:
                wizard.ticket_ids = False
                continue
            start, end = wizard._utc_day_bounds()
            wizard.ticket_ids = self.env["doorandoor.helpdesk.ticket"].search(
                [("company_id", "=", wizard.company_id.id),
                 ("create_date", ">=", start), ("create_date", "<", end)],
                order="create_date,name",
            )

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref("doorandoor_helpdesk.action_report_ddhd_daily").report_action(self)
