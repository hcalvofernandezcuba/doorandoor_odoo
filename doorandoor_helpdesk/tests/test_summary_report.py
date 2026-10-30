from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelpdeskSummaryReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        common = {
            "description": "Caso para validar el reporte resumido.",
            "requester_id": cls.env.user.id,
            "received_by_id": cls.env.user.id,
            "request_channel": "system",
            "affected_area": "inventory",
            "company_id": cls.env.company.id,
            "assigned_user_id": cls.env.user.id,
        }
        cls.tickets = cls.env["doorandoor.helpdesk.ticket"]
        for index, state in enumerate(
            ("new", "analysis", "waiting", "resolved", "closed", "cancel"), 1
        ):
            cls.tickets |= cls.env["doorandoor.helpdesk.ticket"].create({
                **common, "title": "Resumen %s" % index, "state": state,
            })

    def _report(self, **extra):
        return self.env["doorandoor.helpdesk.summary.report"].create({
            "date_from": self.today,
            "date_to": self.today,
            "company_id": self.env.company.id,
            **extra,
        })

    def test_summary_has_lines_totals_and_technician_results(self):
        report = self._report()
        self.assertTrue(self.tickets <= report.ticket_ids)
        self.assertGreaterEqual(report.total_count, 6)
        for field_name in (
            "new_count", "analysis_count", "waiting_count", "resolved_count",
            "closed_count", "cancelled_count",
        ):
            self.assertGreaterEqual(report[field_name], 1)
        technician = next(
            row for row in report._technician_summary()
            if row["name"] == self.env.user.display_name
        )
        self.assertGreaterEqual(technician["total"], 6)
        self.assertGreaterEqual(technician["resolved"], 1)
        self.assertGreaterEqual(technician["closed"], 1)

    def test_analysis_filters_control_lines_and_pdf_source(self):
        report = self._report(
            state_filter="solved",
            assigned_user_ids=[(6, 0, self.env.user.ids)],
            affected_area_filter="inventory",
        )
        self.assertTrue(report.ticket_ids)
        self.assertFalse(report.ticket_ids.filtered(
            lambda ticket: ticket.state not in ("resolved", "closed")
        ))
        self.assertEqual(report.total_count, report.resolved_count + report.closed_count)
        self.assertEqual(report._filter_label("state_filter"), "Resueltos y cerrados")

    def test_summary_rejects_inverted_date_range(self):
        with self.assertRaises(ValidationError):
            self._report(date_to=self.today - timedelta(days=1))

    def test_solution_efficiency_uses_analysis_to_resolution_hours(self):
        ticket = self.tickets.filtered(lambda item: item.state == "resolved")[:1]
        resolved_at = fields.Datetime.now()
        ticket.write({
            "analysis_started_at": resolved_at - timedelta(hours=5),
            "resolved_at": resolved_at,
        })
        self.assertAlmostEqual(ticket.solution_hours, 5.0, places=2)
        self.assertEqual(ticket.solution_efficiency, "good")
