from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoorandoorHelpdeskSummaryReport(models.TransientModel):
    _name = "doorandoor.helpdesk.summary.report"
    _description = "Reporte resumido de soporte técnico"

    date_from = fields.Date(
        string="Desde", required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Hasta", required=True, default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True,
        default=lambda self: self.env.company,
    )
    date_basis = fields.Selection(
        [
            ("create", "Fecha de creación"),
            ("resolved", "Fecha de solución"),
            ("closed", "Fecha de cierre"),
        ],
        string="Analizar por", required=True, default="create",
    )
    state_filter = fields.Selection(
        [
            ("all", "Todos los estados"),
            ("open", "Todos los abiertos"),
            ("solved", "Resueltos y cerrados"),
            ("new", "Nuevo"),
            ("analysis", "En análisis"),
            ("waiting", "Esperando al usuario"),
            ("resolved", "Resuelto"),
            ("closed", "Cerrado"),
            ("cancel", "Cancelado"),
        ],
        string="Estado", required=True, default="all",
    )
    assigned_user_ids = fields.Many2many(
        "res.users", "ddhd_summary_assigned_user_rel", "report_id", "user_id",
        string="Técnicos",
        domain=[("share", "=", False)],
    )
    requester_ids = fields.Many2many(
        "res.users", "ddhd_summary_requester_user_rel", "report_id", "user_id",
        string="Solicitantes",
    )
    affected_area_filter = fields.Selection(
        selection=lambda self: self.env["doorandoor.helpdesk.ticket"]
        ._fields["affected_area"]._description_selection(self.env),
        string="Área",
    )
    ticket_ids = fields.Many2many(
        "doorandoor.helpdesk.ticket", string="Tickets del período",
        compute="_compute_summary",
    )
    total_count = fields.Integer(string="Total", compute="_compute_summary")
    new_count = fields.Integer(string="Nuevos", compute="_compute_summary")
    analysis_count = fields.Integer(string="En análisis", compute="_compute_summary")
    waiting_count = fields.Integer(string="En espera", compute="_compute_summary")
    resolved_count = fields.Integer(string="Resueltos", compute="_compute_summary")
    closed_count = fields.Integer(string="Cerrados", compute="_compute_summary")
    cancelled_count = fields.Integer(string="Cancelados", compute="_compute_summary")

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for report in self:
            if report.date_from and report.date_to and report.date_from > report.date_to:
                raise ValidationError(_("La fecha inicial no puede ser posterior a la final."))

    def _utc_bounds(self):
        self.ensure_one()
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        local_start = timezone.localize(datetime.combine(self.date_from, time.min))
        local_end = timezone.localize(datetime.combine(self.date_to, time.min)) + timedelta(days=1)
        return (
            local_start.astimezone(pytz.UTC).replace(tzinfo=None),
            local_end.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def _ticket_domain(self):
        self.ensure_one()
        start, end = self._utc_bounds()
        date_field = {
            "create": "create_date",
            "resolved": "resolved_at",
            "closed": "closed_at",
        }[self.date_basis]
        domain = [
            ("company_id", "=", self.company_id.id),
            (date_field, ">=", start),
            (date_field, "<", end),
        ]
        if self.state_filter == "open":
            domain.append(("state", "in", ("new", "analysis", "waiting")))
        elif self.state_filter == "solved":
            domain.append(("state", "in", ("resolved", "closed")))
        elif self.state_filter != "all":
            domain.append(("state", "=", self.state_filter))
        if self.assigned_user_ids:
            domain.append(("assigned_user_id", "in", self.assigned_user_ids.ids))
        if self.requester_ids:
            domain.append(("requester_id", "in", self.requester_ids.ids))
        if self.affected_area_filter:
            domain.append(("affected_area", "=", self.affected_area_filter))
        return domain

    @api.depends(
        "date_from", "date_to", "company_id", "date_basis", "state_filter",
        "assigned_user_ids", "requester_ids", "affected_area_filter",
    )
    def _compute_summary(self):
        Ticket = self.env["doorandoor.helpdesk.ticket"]
        for report in self:
            tickets = Ticket
            if report.date_from and report.date_to and report.company_id:
                tickets = Ticket.search(
                    report._ticket_domain(), order="create_date, name"
                )
            report.ticket_ids = tickets
            report.total_count = len(tickets)
            counts = {state: len(tickets.filtered(lambda ticket, key=state: ticket.state == key))
                      for state in ("new", "analysis", "waiting", "resolved", "closed", "cancel")}
            report.new_count = counts["new"]
            report.analysis_count = counts["analysis"]
            report.waiting_count = counts["waiting"]
            report.resolved_count = counts["resolved"]
            report.closed_count = counts["closed"]
            report.cancelled_count = counts["cancel"]

    def _technician_summary(self):
        self.ensure_one()
        rows = {}
        for ticket in self.ticket_ids:
            key = ticket.assigned_user_id.id or 0
            row = rows.setdefault(key, {
                "name": ticket.assigned_user_id.display_name or _("Sin asignar"),
                "total": 0, "resolved": 0, "closed": 0, "open": 0,
            })
            row["total"] += 1
            if ticket.state == "resolved":
                row["resolved"] += 1
            elif ticket.state == "closed":
                row["closed"] += 1
            elif ticket.state != "cancel":
                row["open"] += 1
        return sorted(rows.values(), key=lambda row: (-row["resolved"] - row["closed"], row["name"]))

    @api.model
    def _resolution_hours(self, ticket):
        return ticket.solution_hours if ticket.resolved_at else False

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            "doorandoor_helpdesk.action_report_ddhd_summary"
        ).report_action(self)

    def _filter_label(self, field_name):
        self.ensure_one()
        value = self[field_name]
        if not value:
            return _("Todos")
        return dict(self._fields[field_name]._description_selection(self.env)).get(
            value, value
        )
