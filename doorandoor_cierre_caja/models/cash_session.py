from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorAndDoorCashDenomination(models.Model):
    _name = "doorandoor.cash.denomination"
    _description = "Denominación de efectivo"
    _order = "value desc, id"

    name = fields.Char(required=True)
    value = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [("ddcc_cash_denomination_value_currency", "unique(value, currency_id)", "La denominación ya existe para esta moneda.")]


class DoorAndDoorCashSession(models.Model):
    _name = "doorandoor.cash.session"
    _description = "Apertura y cierre diario de caja"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False)
    register_id = fields.Many2one("doorandoor.cash.register", required=True, check_company=True)
    company_id = fields.Many2one(related="register_id.company_id", store=True)
    journal_id = fields.Many2one(related="register_id.cash_journal_id", store=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    cashier_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, readonly=True)
    state = fields.Selection([("draft", "Borrador"), ("open", "Abierta"), ("closed", "Cerrada")], default="draft", tracking=True)
    opening_at = fields.Datetime(readonly=True)
    closed_at = fields.Datetime(readonly=True)
    closing_user_id = fields.Many2one("res.users", readonly=True)
    opening_line_ids = fields.One2many("doorandoor.cash.session.line", "session_id", domain=[("kind", "=", "opening")], copy=True)
    closing_line_ids = fields.One2many("doorandoor.cash.session.line", "session_id", domain=[("kind", "=", "closing")], copy=False)
    movement_ids = fields.One2many("doorandoor.cash.movement", "session_id", readonly=True)
    denomination_control_active = fields.Boolean(readonly=True, default=False, copy=False)
    opening_amount = fields.Monetary(compute="_compute_totals", store=True, currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_totals", store=True, currency_field="currency_id")
    cash_sales_amount = fields.Monetary(compute="_compute_cash_activity", currency_field="currency_id")
    cash_out_amount = fields.Monetary(compute="_compute_cash_activity", currency_field="currency_id")
    expected_amount = fields.Monetary(compute="_compute_cash_activity", currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_difference", currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id")
    deposit_reference = fields.Char(string="Referencia de depósito", copy=False)
    note = fields.Text(string="Observaciones de cierre")

    _sql_constraints = [("ddcc_one_register_day", "unique(register_id, date)", "Solo puede existir una sesión por caja y día.")]

    @api.depends("opening_line_ids.subtotal", "closing_line_ids.subtotal")
    def _compute_totals(self):
        for session in self:
            session.opening_amount = sum(session.opening_line_ids.mapped("subtotal"))
            session.counted_amount = sum(session.closing_line_ids.mapped("subtotal"))

    @api.depends("opening_amount", "movement_ids.payment_amount")
    def _compute_cash_activity(self):
        for session in self:
            # Cash movements belong to one explicit session/register. Searching
            # the shared journal duplicated every office's sales in every box.
            session.cash_sales_amount = sum(session.movement_ids.mapped("payment_amount"))
            session.cash_out_amount = 0.0
            session.expected_amount = session.opening_amount + session.cash_sales_amount

    @api.depends("counted_amount", "expected_amount")
    def _compute_difference(self):
        for session in self:
            currency = session.currency_id or self.env.company.currency_id
            difference = session.counted_amount - session.expected_amount
            session.difference_amount = currency.round(difference) if currency else difference

    def action_open(self):
        for session in self:
            if session.state != "draft":
                raise UserError(_("Solo puede abrir una sesión en borrador."))
            if not session.register_id.cash_journal_id:
                raise ValidationError(_("Configure el diario de efectivo de la caja antes de abrirla."))
            if session.name == _("Nuevo"):
                session.name = self.env["ir.sequence"].next_by_code("doorandoor.cash.session") or _("Nuevo")
            session.write({
                "state": "open",
                "opening_at": fields.Datetime.now(),
                "denomination_control_active": True,
            })
            session.message_post(body=_("Caja abierta con fondo de cambio: %s.") % session.currency_id.format(session.opening_amount))

    def action_close(self):
        for session in self:
            if session.state != "open":
                raise UserError(_("Solo puede cerrar una caja abierta."))
            if session.currency_id.compare_amounts(session.counted_amount, session.expected_amount):
                raise ValidationError(_(
                    "El arqueo no coincide. Esperado: %(expected)s; contado: %(counted)s; diferencia: %(difference)s. "
                    "Corrija el conteo o registre la incidencia antes de cerrar."
                ) % {"expected": session.currency_id.format(session.expected_amount), "counted": session.currency_id.format(session.counted_amount), "difference": session.currency_id.format(session.difference_amount)})
            if session.denomination_control_active:
                expected_quantities = session._ddcc_expected_denomination_quantities()
                counted_quantities = {
                    line.denomination_id.id: line.quantity for line in session.closing_line_ids
                }
                differences = []
                for denomination_id, expected_quantity in expected_quantities.items():
                    counted_quantity = counted_quantities.get(denomination_id, 0)
                    if counted_quantity != expected_quantity:
                        denomination = self.env["doorandoor.cash.denomination"].browse(denomination_id)
                        differences.append(
                            _("%(denomination)s: esperado %(expected)s, contado %(counted)s")
                            % {"denomination": denomination.display_name, "expected": expected_quantity, "counted": counted_quantity}
                        )
                if differences:
                    raise ValidationError(_(
                        "El arqueo por denominación no coincide. Corrija el conteo físico: %s"
                    ) % "; ".join(differences))
            session.write({"state": "closed", "closed_at": fields.Datetime.now(), "closing_user_id": self.env.user.id})
            session.message_post(body=_("Cierre validado. Efectivo contado y esperado: %s.") % session.currency_id.format(session.counted_amount))

    def action_print_daily_report(self):
        return self.env.ref("doorandoor_cierre_caja.action_report_cash_daily").report_action(self)

    def action_print_deposit_slip(self):
        return self.env.ref("doorandoor_cierre_caja.action_report_cash_deposit").report_action(self)

    def _ddcc_payment_method_summary(self):
        """Return paid customer collections for this session's office and date."""
        self.ensure_one()
        office = self.register_id.office_id
        if not office or not self.date:
            return []

        summary = {}

        def add(label, amount):
            row = summary.setdefault(label, {"label": label, "count": 0, "amount": 0.0})
            row["count"] += 1
            row["amount"] += amount

        cash_payment_ids = set(self.movement_ids.mapped("payment_id").ids)
        for movement in self.movement_ids:
            add(_("Efectivo"), movement.payment_amount)

        payments = self.env["account.payment"].sudo().search([
            ("id", "not in", list(cash_payment_ids)),
            ("date", "=", self.date),
            ("state", "=", "paid"),
            ("payment_type", "=", "inbound"),
            ("partner_type", "=", "customer"),
        ])
        for payment in payments:
            invoices = payment.reconciled_invoice_ids.filtered(
                lambda move: move.move_type in ("out_invoice", "out_refund")
            )
            invoice_offices = invoices.mapped("ddco_office_id")
            # Do not assign an unlinked or cross-office payment to one box.
            if not invoices or len(invoice_offices) != 1 or invoice_offices != office:
                continue
            source = "%s %s" % (payment.journal_id.name, payment.payment_method_line_id.name)
            normalized = source.lower()
            if "clover" in normalized or "card" in normalized or "tarjeta" in normalized:
                label = _("Clover / Tarjeta")
            elif "zelle" in normalized:
                label = _("Zelle")
            elif "transfer" in normalized:
                label = _("Transferencia")
            elif "check" in normalized or "cheque" in normalized:
                label = _("Cheque")
            else:
                label = payment.journal_id.display_name
            add(label, payment.amount)

        return sorted(summary.values(), key=lambda row: row["label"])

    def _ddcc_expected_denomination_quantities(self):
        """Return the physically expected bill count for a controlled session."""
        self.ensure_one()
        quantities = {
            line.denomination_id.id: line.quantity for line in self.opening_line_ids
        }
        for line in self.movement_ids.mapped("line_ids"):
            quantities[line.denomination_id.id] = quantities.get(line.denomination_id.id, 0) + line.net_quantity
        return quantities


class DoorAndDoorCashSessionLine(models.Model):
    _name = "doorandoor.cash.session.line"
    _description = "Conteo de denominaciones de caja"
    _order = "denomination_id desc"

    session_id = fields.Many2one("doorandoor.cash.session", required=True, ondelete="cascade")
    kind = fields.Selection([("opening", "Apertura"), ("closing", "Cierre")], required=True)
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True)
    quantity = fields.Integer(required=True, default=0)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="session_id.currency_id")

    _sql_constraints = [("ddcc_unique_count_line", "unique(session_id, kind, denomination_id)", "La denominación solo puede registrarse una vez por conteo.")]

    @api.depends("denomination_id.value", "quantity")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.denomination_id.value * line.quantity
