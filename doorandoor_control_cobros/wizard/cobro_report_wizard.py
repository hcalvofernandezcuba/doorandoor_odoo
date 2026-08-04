from odoo import _, fields, models


class DoorAndDoorCobroReportWizard(models.TransientModel):
    _name = "doorandoor.cobro.report.wizard"
    _description = "Asistente de Reporte de Cobros"

    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        domain=[("customer_rank", ">", 0)],
        help="Permite preparar futuras variantes del PDF filtradas por uno o varios clientes.",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Vendedores",
        domain=[("share", "=", False)],
        help="Permite definir variantes del PDF filtradas por uno o varios vendedores.",
    )
    control_id = fields.Many2one(
        "doorandoor.cobro.control",
        string="Control de cobro",
        help="Permite imprimir un control especifico mientras se define el formato final del reporte.",
    )
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")
    journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios",
        domain=[("type", "in", ("bank", "cash"))],
    )
    state_filter = fields.Selection(
        selection=[
            ("all", "Todos"),
            ("pending", "Pendientes de revision"),
            ("validated", "Validados"),
            ("rejected", "Rechazados"),
        ],
        string="Estado del control",
        default="all",
        required=True,
    )
    include_reference = fields.Boolean(string="Incluir referencia", default=True)
    include_notes = fields.Boolean(string="Incluir notas", default=True)
    include_rejection_reason = fields.Boolean(string="Incluir motivo de rechazo", default=True)
    include_signatures = fields.Boolean(string="Incluir firmas", default=True)
    layout_variant = fields.Selection(
        selection=[
            ("standard", "Estandar"),
            ("compact", "Compacto"),
            ("audit", "Auditoria"),
        ],
        string="Variante de formato",
        default="standard",
        required=True,
    )
    notes = fields.Text(
        string="Observaciones para diseno",
        help="Espacio para documentar decisiones o solicitudes futuras sobre el PDF.",
    )

    def _get_control_domain(self):
        self.ensure_one()
        domain = [("active", "=", True)]
        if self.control_id:
            domain.append(("id", "=", self.control_id.id))
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        if self.user_ids:
            domain.append(("sale_user_id", "in", self.user_ids.ids))
        if self.date_from:
            domain.append(("payment_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("payment_date", "<=", self.date_to))
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))
        if self.state_filter == "pending":
            domain.append(("state", "in", ["reported", "pending", "review"]))
        elif self.state_filter == "validated":
            domain.append(("state", "=", "validated"))
        elif self.state_filter == "rejected":
            domain.append(("state", "=", "rejected"))
        return domain

    def _get_controls(self):
        self.ensure_one()
        return self.env["doorandoor.cobro.control"].search(
            self._get_control_domain(),
            order="payment_date desc, create_date desc, id desc",
        )

    def _get_report_payload(self):
        self.ensure_one()
        controls = self._get_controls()
        rejected_controls = controls.filtered(lambda c: c.state == "rejected")
        pending_controls = controls.filtered(lambda c: c.state in ("reported", "pending", "review"))
        validated_controls = controls.filtered(lambda c: c.state == "validated")
        return {
            "controls": controls,
            "rejected_controls": rejected_controls,
            "total_amount": sum(controls.mapped("amount_reported")),
            "count_controls": len(controls),
            "count_validated": len(validated_controls),
            "count_rejected": len(rejected_controls),
            "count_pending": len(pending_controls),
        }

    def action_print_pdf(self):
        self.ensure_one()
        controls = self._get_controls()
        if not controls:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Asistente de PDF"),
                    "message": _(
                        "No se encontraron controles con los filtros seleccionados. "
                        "Ajusta clientes, vendedores, fechas o estados para generar el PDF."
                    ),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return self.env.ref("doorandoor_control_cobros.action_report_ddc_cobro_wizard_pdf").report_action(self)


class DoorAndDoorCobroWizardReport(models.AbstractModel):
    _name = "report.doorandoor_control_cobros.cobro_wizard_pdf"
    _description = "Reporte PDF de Cobros desde Wizard"

    def _get_report_values(self, docids, data=None):
        docs = self.env["doorandoor.cobro.report.wizard"].browse(docids)
        wizard = docs[:1]
        payload = wizard._get_report_payload() if wizard else {}
        return {
            "doc_ids": docs.ids,
            "doc_model": "doorandoor.cobro.report.wizard",
            "docs": docs,
            "wizard": wizard,
            **payload,
        }
