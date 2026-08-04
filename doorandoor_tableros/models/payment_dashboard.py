from datetime import timedelta

from odoo import _, api, fields, models


class DoorAndDoorPaymentDashboard(models.TransientModel):
    _name = "doorandoor.payment.dashboard"
    _description = "Tablero de Pagos DoorAndDoor"

    name = fields.Char(default="Tablero de Pagos", readonly=True)
    period_mode = fields.Selection(
        selection=[
            ("manual", "Rango manual"),
            ("today", "Hoy"),
            ("this_week", "Esta semana"),
            ("this_month", "Este mes"),
            ("last_month", "Mes anterior"),
        ],
        string="Periodo",
        default="manual",
        required=True,
    )
    date_filter_type = fields.Selection(
        selection=[
            ("payment_date", "Fecha reportada"),
            ("review_date", "Fecha de revision"),
            ("validated_date", "Fecha de validacion"),
            ("payment_accounting_date", "Fecha del pago contable"),
        ],
        string="Analizar por",
        default="payment_date",
        required=True,
    )
    date_from = fields.Date(
        string="Desde",
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        required=True,
    )
    date_to = fields.Date(
        string="Hasta",
        default=fields.Date.context_today,
        required=True,
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios",
        domain=[("type", "in", ("bank", "cash"))],
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        domain=[("customer_rank", ">", 0)],
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Vendedores",
        domain=[("share", "=", False)],
    )
    total_controls = fields.Integer(
        string="Controles",
        compute="_compute_kpis",
    )
    total_payments_linked = fields.Integer(
        string="Pagos enlazados",
        compute="_compute_kpis",
    )
    total_invoices_linked = fields.Integer(
        string="Facturas vinculadas",
        compute="_compute_kpis",
    )
    total_pending_controls = fields.Integer(
        string="Pendientes",
        compute="_compute_kpis",
    )
    total_validated_controls = fields.Integer(
        string="Validados",
        compute="_compute_kpis",
    )
    total_rejected_controls = fields.Integer(
        string="Rechazados",
        compute="_compute_kpis",
    )
    total_unidentified_controls = fields.Integer(
        string="Por identificar",
        compute="_compute_kpis",
    )
    total_partial_controls = fields.Integer(
        string="Pagos parciales",
        compute="_compute_kpis",
    )
    total_review_controls = fields.Integer(
        string="En revision",
        compute="_compute_kpis",
    )
    total_reported_controls = fields.Integer(
        string="Reportados",
        compute="_compute_kpis",
    )
    total_amount_reported = fields.Monetary(
        string="Monto reportado",
        currency_field="currency_id",
        compute="_compute_kpis",
    )
    total_amount_validated = fields.Monetary(
        string="Monto validado",
        currency_field="currency_id",
        compute="_compute_kpis",
    )
    total_amount_rejected = fields.Monetary(
        string="Monto rechazado",
        currency_field="currency_id",
        compute="_compute_kpis",
    )
    total_amount_pending = fields.Monetary(
        string="Monto pendiente",
        currency_field="currency_id",
        compute="_compute_kpis",
    )
    total_amount_linked_payments = fields.Monetary(
        string="Monto en pagos enlazados",
        currency_field="currency_id",
        compute="_compute_kpis",
    )
    average_validation_hours = fields.Float(
        string="Horas promedio a validacion",
        compute="_compute_kpis",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id.id,
    )
    top_customer_count_id = fields.Many2one(
        "res.partner",
        string="Cliente con mas pagos",
        compute="_compute_rankings",
    )
    top_customer_count_value = fields.Integer(
        string="Cantidad de pagos",
        compute="_compute_rankings",
    )
    top_customer_amount_id = fields.Many2one(
        "res.partner",
        string="Cliente con mayor monto",
        compute="_compute_rankings",
    )
    top_customer_amount_value = fields.Monetary(
        string="Monto acumulado",
        currency_field="currency_id",
        compute="_compute_rankings",
    )
    top_journal_count_id = fields.Many2one(
        "account.journal",
        string="Diario con mas pagos",
        compute="_compute_rankings",
    )
    top_journal_count_value = fields.Integer(
        string="Cantidad en diario",
        compute="_compute_rankings",
    )
    top_journal_amount_id = fields.Many2one(
        "account.journal",
        string="Diario con mayor monto",
        compute="_compute_rankings",
    )
    top_journal_amount_value = fields.Monetary(
        string="Monto en diario",
        currency_field="currency_id",
        compute="_compute_rankings",
    )
    notes = fields.Text(
        string="Notas de evolucion",
        help="Usa este espacio para registrar futuras solicitudes del tablero.",
    )
    control_ids = fields.Many2many(
        "doorandoor.cobro.control",
        string="Controles del tablero",
        compute="_compute_detail_records",
    )
    payment_ids = fields.Many2many(
        "account.payment",
        string="Pagos del tablero",
        compute="_compute_detail_records",
    )
    move_ids = fields.Many2many(
        "account.move",
        string="Facturas del tablero",
        compute="_compute_detail_records",
    )

    def _get_control_domain(self):
        self.ensure_one()
        self._ddt_apply_period_mode()
        domain = [("active", "=", True)]
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        if self.user_ids:
            domain.append(("sale_user_id", "in", self.user_ids.ids))
        if self.date_from:
            if self.date_filter_type == "review_date":
                domain.append(("review_date", ">=", fields.Datetime.to_datetime(self.date_from)))
            elif self.date_filter_type == "validated_date":
                domain.append(("state", "=", "validated"))
                domain.append(("review_date", ">=", fields.Datetime.to_datetime(self.date_from)))
            elif self.date_filter_type == "payment_accounting_date":
                domain.append(("payment_id.date", ">=", self.date_from))
            else:
                domain.append(("payment_date", ">=", self.date_from))
        if self.date_to:
            if self.date_filter_type == "review_date":
                domain.append(("review_date", "<=", fields.Datetime.to_datetime(self.date_to)))
            elif self.date_filter_type == "validated_date":
                domain.append(("state", "=", "validated"))
                domain.append(("review_date", "<=", fields.Datetime.to_datetime(self.date_to)))
            elif self.date_filter_type == "payment_accounting_date":
                domain.append(("payment_id.date", "<=", self.date_to))
            else:
                domain.append(("payment_date", "<=", self.date_to))
        return domain

    def _ddt_apply_period_mode(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.period_mode == "manual":
            return
        if self.period_mode == "today":
            self.date_from = today
            self.date_to = today
            return
        if self.period_mode == "this_week":
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = today
            return
        if self.period_mode == "this_month":
            self.date_from = today.replace(day=1)
            self.date_to = today
            return
        if self.period_mode == "last_month":
            first_this_month = today.replace(day=1)
            last_prev_month = first_this_month - timedelta(days=1)
            self.date_from = last_prev_month.replace(day=1)
            self.date_to = last_prev_month

    @api.onchange("period_mode")
    def _onchange_period_mode(self):
        for dashboard in self:
            dashboard._ddt_apply_period_mode()

    def _get_controls(self):
        self.ensure_one()
        return self.env["doorandoor.cobro.control"].search(self._get_control_domain())

    @api.depends("date_filter_type", "date_from", "date_to", "journal_ids", "partner_ids", "user_ids")
    def _compute_kpis(self):
        for dashboard in self:
            controls = dashboard._get_controls()
            dashboard.total_controls = len(controls)
            dashboard.total_payments_linked = len(controls.filtered("payment_id"))
            dashboard.total_invoices_linked = len(controls.filtered("move_id"))
            dashboard.total_pending_controls = len(controls.filtered(lambda c: c.state in ("reported", "pending", "review")))
            dashboard.total_validated_controls = len(controls.filtered(lambda c: c.state == "validated"))
            dashboard.total_rejected_controls = len(controls.filtered(lambda c: c.state == "rejected"))
            dashboard.total_unidentified_controls = len(controls.filtered(lambda c: not c.move_id))
            dashboard.total_partial_controls = len(controls.filtered(lambda c: c.is_partial))
            dashboard.total_review_controls = len(controls.filtered(lambda c: c.state == "review"))
            dashboard.total_reported_controls = len(controls.filtered(lambda c: c.state == "reported"))
            dashboard.total_amount_reported = sum(controls.mapped("amount_reported"))
            dashboard.total_amount_validated = sum(controls.filtered(lambda c: c.state == "validated").mapped("validated_amount"))
            dashboard.total_amount_rejected = sum(controls.filtered(lambda c: c.state == "rejected").mapped("amount_reported"))
            dashboard.total_amount_pending = sum(
                controls.filtered(lambda c: c.state in ("reported", "pending", "review")).mapped("amount_reported")
            )
            dashboard.total_amount_linked_payments = sum(
                controls.filtered("payment_id").mapped("amount_reported")
            )
            validated_with_review = controls.filtered(lambda c: c.state == "validated" and c.review_date and c.create_date)
            if validated_with_review:
                total_hours = 0.0
                for control in validated_with_review:
                    delta = control.review_date - control.create_date
                    total_hours += delta.total_seconds() / 3600.0
                dashboard.average_validation_hours = total_hours / len(validated_with_review)
            else:
                dashboard.average_validation_hours = 0.0

    @api.depends("date_filter_type", "date_from", "date_to", "journal_ids", "partner_ids", "user_ids")
    def _compute_rankings(self):
        for dashboard in self:
            controls = dashboard._get_controls()
            customer_count_map = {}
            customer_amount_map = {}
            journal_count_map = {}
            journal_amount_map = {}
            for control in controls:
                if control.partner_id:
                    customer_count_map[control.partner_id.id] = customer_count_map.get(control.partner_id.id, 0) + 1
                    customer_amount_map[control.partner_id.id] = customer_amount_map.get(control.partner_id.id, 0.0) + (control.amount_reported or 0.0)
                if control.journal_id:
                    journal_count_map[control.journal_id.id] = journal_count_map.get(control.journal_id.id, 0) + 1
                    journal_amount_map[control.journal_id.id] = journal_amount_map.get(control.journal_id.id, 0.0) + (control.amount_reported or 0.0)

            top_customer_count = max(customer_count_map.items(), key=lambda item: item[1], default=(False, 0))
            top_customer_amount = max(customer_amount_map.items(), key=lambda item: item[1], default=(False, 0.0))
            top_journal_count = max(journal_count_map.items(), key=lambda item: item[1], default=(False, 0))
            top_journal_amount = max(journal_amount_map.items(), key=lambda item: item[1], default=(False, 0.0))

            dashboard.top_customer_count_id = top_customer_count[0]
            dashboard.top_customer_count_value = top_customer_count[1]
            dashboard.top_customer_amount_id = top_customer_amount[0]
            dashboard.top_customer_amount_value = top_customer_amount[1]
            dashboard.top_journal_count_id = top_journal_count[0]
            dashboard.top_journal_count_value = top_journal_count[1]
            dashboard.top_journal_amount_id = top_journal_amount[0]
            dashboard.top_journal_amount_value = top_journal_amount[1]

    @api.depends("date_filter_type", "date_from", "date_to", "journal_ids", "partner_ids", "user_ids")
    def _compute_detail_records(self):
        for dashboard in self:
            controls = dashboard._get_controls()
            dashboard.control_ids = [(6, 0, controls.ids)]
            dashboard.payment_ids = [(6, 0, controls.filtered("payment_id").mapped("payment_id").ids)]
            dashboard.move_ids = [(6, 0, controls.filtered("move_id").mapped("move_id").ids)]

    def action_refresh(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.payment.dashboard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_controls(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_control_cobros.action_ddc_cobro_control").read()[0]
        action["domain"] = self._get_control_domain()
        return action

    def action_view_payments(self):
        self.ensure_one()
        control_ids = self._get_controls().filtered("payment_id").mapped("payment_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Pagos del tablero"),
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", control_ids)],
            "context": {"default_partner_type": "customer"},
        }

    def action_view_report(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_control_cobros.action_ddc_cobro_report").read()[0]
        action["domain"] = self._get_control_domain()
        return action
