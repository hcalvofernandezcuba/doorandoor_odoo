from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ddcc_cash_mode = fields.Boolean(compute="_compute_ddcc_cash_mode")
    ddcc_cash_session_id = fields.Many2one(
        "doorandoor.cash.session", compute="_compute_ddcc_cash_mode", string="Caja abierta"
    )
    ddcc_tender_line_ids = fields.One2many(
        "doorandoor.cash.tender.line", "wizard_id", string="Billetes recibidos"
    )
    ddcc_change_line_ids = fields.One2many(
        "doorandoor.cash.change.line", "wizard_id", string="Billetes entregados como vuelto"
    )
    ddcc_tender_amount = fields.Monetary(
        string="Efectivo recibido", compute="_compute_ddcc_cash_totals", currency_field="currency_id"
    )
    ddcc_change_amount = fields.Monetary(
        string="Vuelto a entregar", compute="_compute_ddcc_cash_totals", currency_field="currency_id"
    )

    @api.depends("journal_id", "payment_date", "company_id")
    def _compute_ddcc_cash_mode(self):
        # The register/session lookup only classifies the selected journal.
        # Salespeople must be able to open the payment wizard for Zelle,
        # Clover and other non-cash methods without becoming cash operators.
        Register = self.env["doorandoor.cash.register"].sudo()
        Session = self.env["doorandoor.cash.session"].sudo()
        for wizard in self:
            request = self.env["doorandoor.cash.collection.request"].sudo().browse(
                self.env.context.get("ddcc_cash_request_id")
            ).exists()
            register = request.register_id if (
                request
                and request.register_id.company_id == wizard.company_id
                and request.register_id.cash_journal_id == wizard.journal_id
                and request.register_id.active
            ) else Register.search([
                ("company_id", "=", wizard.company_id.id),
                ("cash_journal_id", "=", wizard.journal_id.id),
                ("active", "=", True),
                "|",
                ("cashier_ids", "in", self.env.user.id),
                ("manager_ids", "in", self.env.user.id),
            ], limit=1)
            if not register:
                register = Register.search([
                    ("company_id", "=", wizard.company_id.id),
                    ("cash_journal_id", "=", wizard.journal_id.id),
                    ("active", "=", True),
                ], limit=1)
            wizard.ddcc_cash_mode = bool(register)
            wizard.ddcc_cash_session_id = Session.search([
                ("register_id", "=", register.id),
                ("date", "=", wizard.payment_date),
                ("state", "=", "open"),
            ], limit=1) if register else False

    @api.depends("ddcc_tender_line_ids.subtotal", "ddcc_change_line_ids.subtotal")
    def _compute_ddcc_cash_totals(self):
        for wizard in self:
            wizard.ddcc_tender_amount = sum(wizard.ddcc_tender_line_ids.mapped("subtotal"))
            wizard.ddcc_change_amount = sum(wizard.ddcc_change_line_ids.mapped("subtotal"))

    @api.depends(
        "can_edit_wizard", "source_amount", "source_amount_currency",
        "source_currency_id", "company_id", "currency_id", "payment_date",
        "installments_mode", "line_ids",
    )
    def _compute_amount(self):
        super()._compute_amount()
        request = self.env["doorandoor.cash.collection.request"].sudo().browse(
            self.env.context.get("ddcc_cash_request_id")
        ).exists()
        if not request:
            return
        for wizard in self:
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            if len(invoices) == 1 and request.invoice_id == invoices:
                wizard.amount = min(request.amount, invoices.amount_residual)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        # Do not create cash denomination lines for non-cash collections.
        # Payment-register defaults are also used by Clover and other online
        # providers.  Creating those one2many records unconditionally made a
        # card collection require access to the cash-count transient models.
        journal_id = values.get("journal_id")
        register = self.env["doorandoor.cash.register"].sudo().search([
            ("company_id", "=", self.env.company.id),
            ("cash_journal_id", "=", journal_id),
            ("active", "=", True),
        ], limit=1)
        if not register:
            return values
        denoms = self.env["doorandoor.cash.denomination"].sudo().search([
            ("active", "=", True),
            ("currency_id", "=", self.env.company.currency_id.id),
        ])
        values.update({
            "ddcc_tender_line_ids": [(0, 0, {"denomination_id": denom.id, "quantity": 0}) for denom in denoms],
            "ddcc_change_line_ids": [(0, 0, {"denomination_id": denom.id, "quantity": 0}) for denom in denoms],
        })
        return values

    @api.onchange("journal_id")
    def _onchange_ddcc_cash_journal(self):
        """Prepare the cash count when, and only when, the sales cash drawer is chosen.

        ``journal_id`` is populated by Odoo after ``default_get`` in the normal
        payment dialog, so seeding the denomination lines solely from defaults
        left a selected cash drawer with an empty grid.  The onchange keeps the
        financial methods untouched and never replaces quantities already typed
        by the cashier.
        """
        Register = self.env["doorandoor.cash.register"].sudo()
        Denomination = self.env["doorandoor.cash.denomination"].sudo()
        for wizard in self:
            register = Register.search([
                ("company_id", "=", wizard.company_id.id),
                ("cash_journal_id", "=", wizard.journal_id.id),
                ("active", "=", True),
            ], limit=1)
            if not register:
                wizard.ddcc_tender_line_ids = [(5, 0, 0)]
                wizard.ddcc_change_line_ids = [(5, 0, 0)]
                continue
            currency = wizard.currency_id or wizard.company_id.currency_id
            denominations = Denomination.search([
                ("active", "=", True),
                ("currency_id", "=", currency.id),
            ], order="value desc")
            if not wizard.ddcc_tender_line_ids:
                wizard.ddcc_tender_line_ids = [
                    (0, 0, {"denomination_id": denomination.id, "quantity": 0})
                    for denomination in denominations
                ]
            if not wizard.ddcc_change_line_ids:
                wizard.ddcc_change_line_ids = [
                    (0, 0, {"denomination_id": denomination.id, "quantity": 0})
                    for denomination in denominations
                ]

    def _ddcc_cash_invoice(self):
        self.ensure_one()
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            raise ValidationError(_(
                "Un cobro en efectivo debe aplicarse a una sola factura para conservar el detalle de billetes y vuelto."
            ))
        return invoices

    def _ddcc_get_cash_specification(self):
        """Validate tender/change before Odoo creates the accounting payment."""
        self.ensure_one()
        if not self.ddcc_cash_mode:
            return False
        session = self.ddcc_cash_session_id
        if not session:
            raise ValidationError(_(
                "No hay una caja abierta para la fecha del pago. Abra la venta del día antes de cobrar efectivo."
            ))
        if not session.denomination_control_active:
            raise ValidationError(_(
                "Esta caja fue abierta antes del control por denominación. Ciérrela y abra una nueva caja para cobrar efectivo."
            ))
        self._ddcc_validate_no_active_archeo(session)
        request = self.env["doorandoor.cash.collection.request"].browse(self.env.context.get("ddcc_cash_request_id"))
        if not request or request.state != "pending" or request.invoice_id != self._ddcc_cash_invoice() or request.register_id != session.register_id:
            raise ValidationError(_("El efectivo debe cobrarse desde una solicitud pendiente de la cola de caja."))
        invoice = self._ddcc_cash_invoice()
        if self.amount <= 0 or self.currency_id.compare_amounts(self.amount, invoice.amount_residual) > 0:
            raise ValidationError(_("El importe en efectivo debe ser mayor que cero y no puede superar el saldo de la factura."))
        if (
            getattr(invoice, "ddtp_payment_plan", False) == "partial"
            and self.currency_id.compare_amounts(
                getattr(invoice, "ddc_total_validated", 0.0) or 0.0,
                getattr(invoice, "ddtp_payment_due_amount", 0.0) or 0.0,
            ) < 0
            and self.currency_id.compare_amounts(self.amount, request.amount) != 0
        ):
            raise ValidationError(_(
                "Para completar el pago parcial, este cobro en efectivo debe ser exactamente %(amount)s."
            ) % {"amount": self.currency_id.format(request.amount)})
        denominations = self.env["doorandoor.cash.denomination"].search([
            ("active", "=", True), ("currency_id", "=", self.currency_id.id),
        ])
        tender = {line.denomination_id.id: line.quantity for line in self.ddcc_tender_line_ids}
        change = {line.denomination_id.id: line.quantity for line in self.ddcc_change_line_ids}
        required_ids = set(denominations.ids)
        if set(tender) != required_ids or set(change) != required_ids:
            raise ValidationError(_(
                "Complete el conteo de todas las denominaciones, incluso cuando una cantidad sea cero."
            ))
        tender_amount = sum(denom.value * tender[denom.id] for denom in denominations)
        change_amount = sum(denom.value * change[denom.id] for denom in denominations)
        expected_change = self.currency_id.round(tender_amount - self.amount)
        if self.currency_id.compare_amounts(tender_amount, self.amount) < 0:
            raise ValidationError(_(
                "El efectivo recibido (%(received)s) no cubre el cobro de %(payment)s."
            ) % {"received": self.currency_id.format(tender_amount), "payment": self.currency_id.format(self.amount)})
        if self.currency_id.compare_amounts(change_amount, expected_change):
            raise ValidationError(_(
                "El vuelto declarado debe ser exactamente %(expected)s; se registró %(declared)s."
            ) % {"expected": self.currency_id.format(expected_change), "declared": self.currency_id.format(change_amount)})
        return {
            "session": session,
            "invoice": invoice,
            "denominations": denominations,
            "tender": tender,
            "change": change,
            "tender_amount": tender_amount,
            "change_amount": change_amount,
            "request": request,
        }

    def _ddcc_validate_no_active_archeo(self, session):
        # Cashiers must not receive direct access to surprise audits.  This is
        # an internal safety check only: use a privileged read to determine
        # whether the drawer is blocked, while keeping the audit model and its
        # contents restricted to cash managers and system administrators.
        audit = self.env["doorandoor.cash.audit"].sudo().search([
            ("session_id", "=", session.id), ("state", "=", "prepared"), ("cash_blocked", "=", True),
        ], limit=1)
        if audit:
            raise ValidationError(_(
                "La caja %(register)s está en proceso de arqueo desde %(started)s. "
                "El cobro en efectivo queda en espera hasta que el supervisor registre el conteo."
            ) % {
                "register": session.register_id.display_name,
                "started": fields.Datetime.to_string(audit.audit_at),
            })

    def _ddcc_lock_and_validate_cash_stock(self, spec):
        """Serialize cash drawer changes and prevent a non-existent change bill."""
        session = spec["session"]
        self.env.cr.execute("SELECT id FROM doorandoor_cash_session WHERE id = %s FOR UPDATE", [session.id])
        self._ddcc_validate_no_active_archeo(session)
        expected = session._ddcc_expected_denomination_quantities()
        shortages = []
        for denomination in spec["denominations"]:
            remaining = expected.get(denomination.id, 0) + spec["tender"][denomination.id] - spec["change"][denomination.id]
            if remaining < 0:
                shortages.append(_("%(denomination)s: disponibles %(available)s, vuelto solicitado %(change)s") % {
                    "denomination": denomination.display_name,
                    "available": expected.get(denomination.id, 0) + spec["tender"][denomination.id],
                    "change": spec["change"][denomination.id],
                })
        if shortages:
            raise ValidationError(_(
                "No hay billetes suficientes para entregar ese vuelto: %s"
            ) % "; ".join(shortages))

    def _create_payments(self):
        self.ensure_one()
        spec = self._ddcc_get_cash_specification()
        if spec:
            self._ddcc_lock_and_validate_cash_stock(spec)
        # Cash collection and logistics are two separate operational stages.
        # Creating/reconciling the accounting payment fires Odoo's partial
        # reconcile hooks while the invoice cache is still being finalized.
        # If fulfillment runs inside that hook it can try to create/confirm a
        # delivery before the payment is complete and roll back the cash
        # collection with a delivery authorization error.  Preserve the cash
        # payment, denomination movement and receipt first; logistics can be
        # released afterwards from the paid invoice through its own action.
        payment_wizard = self.with_context(ddc_skip_release_sync=True) if spec else self
        payments = super(AccountPaymentRegister, payment_wizard)._create_payments()
        if spec:
            payment = payments[:1]
            if not payment:
                raise ValidationError(_("No se creó el pago en efectivo; no se registró ningún movimiento de caja."))
            cashier = self.env.user
            self.env["doorandoor.cash.movement"].sudo().create({
                "name": _("Cobro %(payment)s - %(invoice)s") % {
                    "payment": payment.display_name, "invoice": spec["invoice"].display_name,
                },
                "session_id": spec["session"].id,
                "payment_id": payment.id,
                "move_id": spec["invoice"].id,
                "user_id": cashier.id,
                "tender_amount": spec["tender_amount"],
                "payment_amount": self.amount,
                "change_amount": spec["change_amount"],
                "line_ids": [(0, 0, {
                    "denomination_id": denomination.id,
                    "received_quantity": spec["tender"][denomination.id],
                    "change_quantity": spec["change"][denomination.id],
                }) for denomination in spec["denominations"]],
            })
            spec["request"].write({"state": "paid", "payment_id": payment.id, "cashier_id": cashier.id})
        return payments

    @api.depends("payment_type", "company_id", "can_edit_wizard", "line_ids.move_id")
    def _compute_available_journal_ids(self):
        """Keep the bank/deposit journal out of direct customer-sale payments.

        Bank deposits settle cash or credit operations afterwards; they are not
        a counter payment method at the sales desk.  This affects only posted
        customer invoices, never accounting's bank/deposit workflows.
        """
        super()._compute_available_journal_ids()
        Journal = self.env["account.journal"]
        for wizard in self:
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice"
            )
            if not invoices:
                continue
            deposit_journals = Journal.search([
                ("company_id", "=", wizard.company_id.id),
                ("code", "=", "BNK1"),
            ])
            cash_register_journal_ids = set(self.env["doorandoor.cash.register"].sudo().search([
                ("company_id", "=", wizard.company_id.id),
                ("active", "=", True),
            ]).mapped("cash_journal_id").ids)
            non_sales_cash_journals = wizard.available_journal_ids.filtered(
                lambda journal: journal.type == "cash"
                and journal._origin.id not in cash_register_journal_ids
            )
            request = self.env["doorandoor.cash.collection.request"].sudo().browse(
                self.env.context.get("ddcc_cash_request_id")
            ).exists()
            configured_cash = wizard.available_journal_ids.filtered(
                lambda journal: journal._origin.id in cash_register_journal_ids
            )
            if request and request.invoice_id in invoices:
                configured_cash -= request.register_id.cash_journal_id
            allowed = (
                wizard.available_journal_ids
                - deposit_journals
                - non_sales_cash_journals
                - configured_cash
            )
            if request and request.invoice_id in invoices:
                # Some payment extensions build their own journal subset and
                # may omit cash before this compute runs.  The queue is the
                # sole authorized cash entry point, so add back exactly the
                # journal of its assigned register and no other cash journal.
                allowed |= request.register_id.cash_journal_id
            wizard.available_journal_ids = allowed

    @api.model
    def _get_batch_available_journals(self, batch_result):
        """Filter BNK1 before Odoo assigns journals to the wizard field."""
        journals = super()._get_batch_available_journals(batch_result)
        moves = batch_result["lines"].move_id
        invoices = moves.filtered(lambda move: move.move_type == "out_invoice")
        if invoices:
            company = invoices[:1].company_id or self.env.company
            cash_register_journal_ids = set(self.env["doorandoor.cash.register"].sudo().search([
                ("company_id", "=", company.id),
                ("active", "=", True),
            ]).mapped("cash_journal_id").ids)
            request = self.env["doorandoor.cash.collection.request"].sudo().browse(
                self.env.context.get("ddcc_cash_request_id")
            ).exists()
            allowed_cash_id = request.register_id.cash_journal_id.id if (
                request and request.invoice_id in invoices
            ) else False
            if allowed_cash_id:
                journals |= request.register_id.cash_journal_id
            journals = journals.filtered(
                lambda journal: journal.code != "BNK1" and (
                    journal.type != "cash" or journal._origin.id == allowed_cash_id
                )
            )
        return journals


class DoorAndDoorCashTenderLine(models.TransientModel):
    _name = "doorandoor.cash.tender.line"
    _description = "Billete recibido en cobro de efectivo"

    wizard_id = fields.Many2one("account.payment.register", required=True, ondelete="cascade")
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True)
    quantity = fields.Integer(string="Cantidad", required=True, default=0)
    subtotal = fields.Monetary(compute="_compute_subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id")

    _sql_constraints = [
        ("ddcc_tender_one_denomination", "unique(wizard_id, denomination_id)", "La denominación solo puede aparecer una vez."),
        ("ddcc_tender_non_negative", "CHECK(quantity >= 0)", "La cantidad no puede ser negativa."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Ignore a browser-created empty transient row; denominations are seeded by the wizard."""
        values = [vals for vals in vals_list if vals.get("denomination_id")]
        return super().create(values) if values else self.browse()

    @api.depends("denomination_id.value", "quantity")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.denomination_id.value * line.quantity


class DoorAndDoorCashChangeLine(models.TransientModel):
    _name = "doorandoor.cash.change.line"
    _description = "Billete entregado como vuelto"

    wizard_id = fields.Many2one("account.payment.register", required=True, ondelete="cascade")
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True)
    quantity = fields.Integer(string="Cantidad", required=True, default=0)
    subtotal = fields.Monetary(compute="_compute_subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id")

    _sql_constraints = [
        ("ddcc_change_one_denomination", "unique(wizard_id, denomination_id)", "La denominación solo puede aparecer una vez."),
        ("ddcc_change_non_negative", "CHECK(quantity >= 0)", "La cantidad no puede ser negativa."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Ignore a browser-created empty transient row; denominations are seeded by the wizard."""
        values = [vals for vals in vals_list if vals.get("denomination_id")]
        return super().create(values) if values else self.browse()

    @api.depends("denomination_id.value", "quantity")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.denomination_id.value * line.quantity
