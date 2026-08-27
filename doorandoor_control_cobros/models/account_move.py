from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    ddc_credit_origin_payment_id = fields.Many2one(
        "account.payment", string="Pago origen del anticipo", copy=False, readonly=True
    )
    ddc_credit_origin_control_id = fields.Many2one(
        "doorandoor.cobro.control", string="Control origen del anticipo", copy=False, readonly=True
    )
    ddc_last_manual_sync_at = fields.Datetime(
        string="Ultima sincronizacion operativa",
        copy=False,
        readonly=True,
    )

    ddc_control_ids = fields.One2many(
        "doorandoor.cobro.control",
        "move_id",
        string="Controles de cobro",
        copy=False,
    )
    ddc_control_count = fields.Integer(
        string="Controles de cobro",
        compute="_compute_ddc_control_count",
    )
    ddc_collection_state = fields.Selection(
        selection=[
            ("not_applicable", "No aplica"),
            ("pending", "Pendiente revision"),
            ("validated", "Validado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado de control de cobro",
        compute="_compute_ddc_collection_state",
        store=True,
    )
    ddc_payment_review_state = fields.Selection(
        selection=[
            ("no_control", "Sin control"),
            ("reviewing", "Revisando pago"),
            ("partial", "Pago parcial validado"),
            ("validated", "Pago validado"),
            ("rejected", "Pago rechazado"),
        ],
        string="Estado funcional del pago",
        compute="_compute_ddc_payment_review_state",
        store=True,
    )
    ddc_total_reported = fields.Monetary(
        string="Total reportado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_validated = fields.Monetary(
        string="Total validado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_rejected = fields.Monetary(
        string="Total rechazado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_pending = fields.Monetary(
        string="Total pendiente",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_balance_pending = fields.Monetary(
        string="Saldo pendiente por validar",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_customer_credit_available = fields.Monetary(
        string="Crédito disponible del cliente",
        compute="_compute_ddc_customer_credit_available",
        currency_field="currency_id",
        help="Saldo contable disponible en anticipos del cliente, expresado en la moneda de la factura.",
    )

    @api.depends("partner_id", "company_id", "currency_id", "invoice_date", "date")
    def _compute_ddc_customer_credit_available(self):
        Credit = self.env["doorandoor.customer.credit"]
        for move in self:
            move.ddc_customer_credit_available = 0.0
            if move.move_type != "out_invoice" or not move.partner_id or not move.company_id:
                continue

            commercial_partner = move.partner_id.commercial_partner_id
            credits = Credit.search(
                [
                    ("partner_id", "child_of", commercial_partner.id),
                    ("company_id", "=", move.company_id.id),
                    ("available_amount", ">", 0),
                ]
            )
            conversion_date = move.invoice_date or move.date or fields.Date.context_today(move)
            move.ddc_customer_credit_available = sum(
                credit.currency_id._convert(
                    credit.available_amount,
                    move.currency_id,
                    move.company_id,
                    conversion_date,
                )
                for credit in credits
            )

    def _compute_ddc_control_count(self):
        for move in self:
            move.ddc_control_count = len(move.ddc_control_ids)

    @api.depends(
        "move_type",
        "amount_total",
        "ddc_control_ids",
        "ddc_control_ids.state",
        "ddc_control_ids.amount_reported",
        "ddc_control_ids.validated_amount",
        "ddc_control_ids.active",
        "ddc_control_ids.payment_id",
    )
    def _compute_ddc_control_totals(self):
        for move in self:
            if move.move_type != "out_invoice":
                move.ddc_total_reported = 0.0
                move.ddc_total_validated = 0.0
                move.ddc_total_rejected = 0.0
                move.ddc_total_pending = 0.0
                move.ddc_balance_pending = 0.0
                continue

            controls = move.ddc_control_ids.filtered(lambda control: control.active)
            
            # Filtrar para contar solo pagos únicos y evitar duplicación cuando
            # el control de ventas se vincula al pago oficial de contabilidad
            controls_with_payment = controls.filtered(lambda control: control.payment_id)
            unique_payment_controls = self.env["doorandoor.cobro.control"]
            seen_payments = set()
            
            for control in controls_with_payment:
                if control.payment_id.id not in seen_payments:
                    seen_payments.add(control.payment_id.id)
                    unique_payment_controls |= control
            
            # Controles sin pago (reportes de ventas pendientes de vincular)
            controls_without_payment = controls.filtered(lambda control: not control.payment_id)
            
            # Combinar ambos grupos para el cálculo usando operador de recordset
            all_unique_controls = controls_without_payment | unique_payment_controls
            
            move.ddc_total_reported = sum(
                all_unique_controls.filtered(lambda control: control.state != "rejected").mapped("amount_reported")
            )
            move.ddc_total_validated = sum(
                all_unique_controls.filtered(lambda control: control.state == "validated").mapped("validated_amount")
            )
            move.ddc_total_rejected = sum(
                all_unique_controls.filtered(lambda control: control.state == "rejected").mapped("amount_reported")
            )
            move.ddc_total_pending = sum(
                all_unique_controls.filtered(lambda control: control.state in ("draft", "reported", "pending", "review")).mapped("amount_reported")
            )
            move.ddc_balance_pending = max(move.amount_total - move.ddc_total_validated, 0.0)

    @api.depends("ddc_control_ids", "ddc_control_ids.state", "payment_state", "move_type", "ddc_total_validated", "amount_total")
    def _compute_ddc_collection_state(self):
        for move in self:
            if move.move_type != "out_invoice":
                move.ddc_collection_state = "not_applicable"
                continue
            if not move.ddc_control_ids:
                move.ddc_collection_state = "not_applicable"
                continue
            states = set(move.ddc_control_ids.mapped("state"))
            if states & {"pending", "reported", "review"}:
                move.ddc_collection_state = "pending"
            elif move.ddc_total_validated and move.currency_id.compare_amounts(move.ddc_total_validated, move.amount_total) < 0:
                move.ddc_collection_state = "validated"
            elif states == {"rejected"}:
                move.ddc_collection_state = "rejected"
            elif states and states.issubset({"validated"}):
                move.ddc_collection_state = "validated"
            else:
                move.ddc_collection_state = "pending"

    @api.depends(
        "move_type",
        "ddc_collection_state",
        "ddc_control_ids",
        "ddc_control_ids.state",
        "ddc_total_validated",
        "amount_total",
        "amount_residual",
    )
    def _compute_ddc_payment_review_state(self):
        for move in self:
            if move.move_type != "out_invoice" or not move.ddc_control_ids:
                move.ddc_payment_review_state = "no_control"
                continue
            if move.ddc_collection_state == "rejected":
                move.ddc_payment_review_state = "rejected"
                continue
            # Solo mostrar "validated" si hay pagos validados, no solo por residual cero
            if move.currency_id.is_zero(move.amount_residual) and move.ddc_total_validated > 0:
                move.ddc_payment_review_state = "validated"
                continue
            if move.ddc_collection_state == "validated":
                if move.currency_id.compare_amounts(move.ddc_total_validated, move.amount_total) < 0:
                    move.ddc_payment_review_state = "partial"
                else:
                    move.ddc_payment_review_state = "validated"
            else:
                move.ddc_payment_review_state = "reviewing"

    def action_view_ddc_controls(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_control_cobros.action_ddc_cobro_control").read()[0]
        action["domain"] = [("move_id", "=", self.id)]
        action["context"] = {
            "default_move_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_currency_id": self.currency_id.id,
            "default_amount_reported": self.amount_residual,
        }
        return action

    def action_post(self):
        result = super().action_post()
        self.filtered(lambda move: move.move_type == "out_invoice")._ddc_apply_customer_advances()
        return result

    def _ddc_is_us_accounting_company(self):
        self.ensure_one()
        fiscal_country = getattr(self.company_id, "account_fiscal_country_id", False)
        return getattr(fiscal_country or self.company_id.country_id, "code", False) == "US"

    def _ddc_get_advance_parent_account(self, required=True):
        self.ensure_one()
        account_model = self.env["account.account"].sudo()
        account = account_model.with_company(self.company_id).search(
            [("code", "=", "120000"), ("company_ids", "in", self.company_id.id)], limit=1
        )
        if not account and self._ddc_is_us_accounting_company():
            account = account_model.with_company(self.company_id).create(
                {
                    "name": "Pagos Anticipados",
                    "code": "120000",
                    "account_type": "liability_current",
                    "reconcile": True,
                    "company_ids": [fields.Command.set(self.company_id.ids)],
                }
            )
        if not account and required:
            raise ValidationError(
                _("No existe la cuenta madre 120000 Pagos Anticipados para la compania %s.")
                % self.company_id.display_name
            )
        return account

    def _ddc_get_advance_account(self, required=True, create=True):
        self.ensure_one()
        partner = self.commercial_partner_id.with_company(self.company_id)
        if partner.ddc_advance_account_id:
            return partner.ddc_advance_account_id
        if not create:
            return self.env["account.account"]
        parent_account = self._ddc_get_advance_parent_account(required=required)
        if not parent_account:
            return parent_account
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", (120000, self.company_id.id))
        partner.invalidate_recordset(["ddc_advance_account_id"])
        if partner.ddc_advance_account_id:
            return partner.ddc_advance_account_id
        accounts = self.env["account.account"].sudo().with_company(self.company_id).search(
            [("code", "=like", "1200__"), ("company_ids", "in", self.company_id.id)]
        )
        used_codes = {account.code for account in accounts if (account.code or "").isdigit()}
        next_number = max([int(code) for code in used_codes] + [120000]) + 1
        while str(next_number) in used_codes:
            next_number += 1
        account = self.env["account.account"].sudo().with_company(self.company_id).create(
            {
                "name": _("Pagos Anticipados - %s") % partner.display_name,
                "code": str(next_number),
                "account_type": "liability_current",
                "reconcile": True,
                "company_ids": [fields.Command.set(self.company_id.ids)],
            }
        )
        partner.sudo().ddc_advance_account_id = account
        return account

    def _ddc_apply_customer_advances(self):
        for invoice in self:
            if invoice.state != "posted" or invoice.currency_id != invoice.company_currency_id:
                continue
            advance_account = invoice._ddc_get_advance_account(required=False, create=False)
            if not advance_account:
                continue
            partner = invoice.commercial_partner_id
            advance_lines = self.env["account.move.line"].search(
                [
                    ("account_id", "=", advance_account.id),
                    ("partner_id", "child_of", partner.id),
                    ("parent_state", "=", "posted"),
                    ("amount_residual", "<", 0),
                    ("reconciled", "=", False),
                ],
                order="date, id",
            )
            for advance_line in advance_lines:
                if invoice.currency_id.is_zero(invoice.amount_residual):
                    break
                amount = min(invoice.amount_residual, abs(advance_line.amount_residual))
                origin_payment = advance_line.move_id.ddc_credit_origin_payment_id
                origin_control = advance_line.move_id.ddc_credit_origin_control_id
                if not origin_payment or not origin_control:
                    continue
                receivable_line = invoice.line_ids.filtered(
                    lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
                )[:1]
                transfer = self.env["account.move"].create(
                    {
                        "move_type": "entry",
                        "journal_id": origin_payment.journal_id.id,
                        "date": fields.Date.context_today(invoice),
                        "ref": _("Aplicacion anticipo a %s") % invoice.name,
                        "ddc_credit_origin_payment_id": origin_payment.id,
                        "ddc_credit_origin_control_id": origin_control.id,
                        "line_ids": [
                            fields.Command.create({"name": invoice.name, "partner_id": invoice.partner_id.id, "account_id": advance_account.id, "debit": amount}),
                            fields.Command.create({"name": invoice.name, "partner_id": invoice.partner_id.id, "account_id": receivable_line.account_id.id, "credit": amount}),
                        ],
                    }
                )
                transfer.action_post()
                (advance_line | transfer.line_ids.filtered(lambda line: line.account_id == advance_account)).reconcile()
                (receivable_line | transfer.line_ids.filtered(lambda line: line.account_id == receivable_line.account_id)).reconcile()
                invoice.invalidate_recordset(["amount_residual", "payment_state"])
                applied_control = self.env["doorandoor.cobro.control"].sudo().create(
                    {
                        "move_id": invoice.id, "partner_id": invoice.partner_id.id,
                        "currency_id": invoice.currency_id.id, "company_id": invoice.company_id.id,
                        "journal_id": origin_payment.journal_id.id, "payment_id": origin_payment.id,
                        "amount_reported": amount, "validated_amount": amount, "state": "validated",
                        "source_type": "customer_credit", "credit_origin_control_id": origin_control.id,
                        "credit_balance_before": abs(advance_line.amount_residual) + amount,
                        "credit_applied_amount": amount, "credit_balance_after": abs(advance_line.amount_residual),
                        "invoice_residual_snapshot": invoice.amount_residual + amount,
                        "accountant_user_id": self.env.user.id, "review_date": fields.Datetime.now(),
                        "notes": _("Aplicacion automatica desde la cuenta 120000 Pagos Anticipados."),
                    }
                )
                invoice.message_post(body=_("Se aplico un anticipo de %s mediante el control %s.") % (amount, applied_control.name))
            invoice._ddc_refresh_control_status()

    def js_assign_outstanding_line(self, line_id):
        """Registra el consumo de un credito ya validado al conciliarlo."""
        self.ensure_one()
        payment_line = self.env["account.move.line"].browse(line_id).exists()
        payment = payment_line.payment_id
        residual_before = self.amount_residual
        credit_before = abs(payment_line.amount_residual_currency or payment_line.amount_residual)

        result = super().js_assign_outstanding_line(line_id)

        self.invalidate_recordset(["amount_residual", "payment_state"])
        payment_line.invalidate_recordset(["amount_residual", "amount_residual_currency"])
        applied_amount = max(residual_before - self.amount_residual, 0.0)
        if not payment or self.currency_id.is_zero(applied_amount):
            return result

        control_model = self.env["doorandoor.cobro.control"].sudo()
        # Si ya existe un control de esta factura para el pago, se trata del
        # flujo normal de validacion y no de una aplicacion posterior de credito.
        if control_model.search_count(
            [
                ("payment_id", "=", payment.id),
                ("move_id", "=", self.id),
                ("active", "=", True),
                ("state", "!=", "rejected"),
            ]
        ):
            return result

        origin_control = control_model.search(
            [
                ("payment_id", "=", payment.id),
                ("state", "=", "validated"),
                ("active", "=", True),
                ("move_id", "!=", self.id),
            ],
            order="id asc",
            limit=1,
        )
        if not origin_control:
            return result

        credit_after = abs(payment_line.amount_residual_currency or payment_line.amount_residual)
        control = control_model.create(
            {
                "move_id": self.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "journal_id": payment.journal_id.id,
                "payment_id": payment.id,
                "sale_user_id": self.env.user.id,
                "accountant_user_id": self.env.user.id,
                "payment_date": fields.Date.context_today(self),
                "amount_reported": applied_amount,
                "validated_amount": applied_amount,
                "payment_reference": payment.payment_reference or payment.memo,
                "state": "validated",
                "source_type": "customer_credit",
                "invoice_residual_snapshot": residual_before,
                "review_date": fields.Datetime.now(),
                "credit_origin_control_id": origin_control.id,
                "credit_balance_before": credit_before,
                "credit_applied_amount": applied_amount,
                "credit_balance_after": credit_after,
                "notes": _(
                    "Aplicacion de credito validado procedente del control %(control)s. "
                    "Credito anterior: %(before)s; aplicado: %(applied)s; restante: %(after)s."
                )
                % {
                    "control": origin_control.name,
                    "before": credit_before,
                    "applied": applied_amount,
                    "after": credit_after,
                },
            }
        )
        self._ddc_refresh_control_status()
        self.message_post(
            body=Markup(
                "<p><strong>Factura liquidada con credito a favor</strong></p>"
                "<p>Origen: %(origin)s. Credito anterior: %(before)s; "
                "aplicado: %(applied)s; saldo restante: %(after)s.</p>"
                "<p><strong>Control:</strong> %(control)s</p>"
            )
            % {
                "origin": origin_control.name,
                "before": credit_before,
                "applied": applied_amount,
                "after": credit_after,
                "control": control.name,
            },
            subtype_xmlid="mail.mt_note",
        )
        return result

    def _ddc_has_pending_controls(self):
        self.ensure_one()
        return bool(self.ddc_control_ids.filtered(lambda control: control.state in ("draft", "reported", "pending", "review")))

    def _ddc_refresh_control_status(self):
        for move in self:
            move._compute_ddc_control_totals()
            move._compute_ddc_collection_state()
            move._compute_ddc_payment_review_state()
            move._compute_payment_state()
            move._ddsn_sync_release_from_payments()

    def _ddc_force_operational_sync(self):
        """Recompute and rebroadcast an invoice without creating accounting data."""
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Solo un administrador con acceso a Ajustes puede forzar la sincronizacion."))
        invoices = self.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            raise ValidationError(_("No existe una factura asociada para sincronizar."))
        invoices.invalidate_recordset()
        invoices._ddc_refresh_control_status()
        sync_time = fields.Datetime.now()
        invoices.write({"ddc_last_manual_sync_at": sync_time})
        for invoice in invoices:
            invoice.message_post(
                body=_("%s forzo la sincronizacion operativa del pago y la factura.") % self.env.user.display_name,
                subtype_xmlid="mail.mt_note",
            )
        invoices._ddsn_broadcast_document_update("manual_payment_sync")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sincronizacion enviada"),
                "message": _("Se recalcularon los estados y se notificaron las pantallas abiertas."),
                "type": "success",
                "sticky": False,
            },
        }

    def _ddc_post_control_message(self, body):
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            move.message_post(body=body, subtype_xmlid="mail.mt_note")

    def _ddsn_sync_release_from_payments(self):
        if self.env.context.get("ddc_skip_release_sync"):
            for move in self:
                move._ddsn_set_release_state()
            return

        blocked_moves = self.filtered(lambda move: move._ddc_has_pending_controls())
        for move in blocked_moves:
            move._ddsn_set_release_state()

        return super(AccountMove, self - blocked_moves)._ddsn_sync_release_from_payments()

    def _ddc_has_manufacturing_lines(self):
        self.ensure_one()
        return bool(
            self.fulfillment_line_ids.filtered(
                lambda line: self._ddsn_get_line_route(line, 1.0) == "ready_mrp"
            )
        )

    def _ddc_auto_payment_threshold(self):
        self.ensure_one()
        return 0.50 if self._ddc_has_manufacturing_lines() else 1.0

    def _ddc_release_manufacturing_at_threshold(self):
        for invoice in self:
            manufacturing_lines = invoice.fulfillment_line_ids.filtered(
                lambda line: invoice._ddsn_get_line_route(line, 1.0) == "ready_mrp"
                and line.qty_sent_mrp < line.qty_invoiced
            )
            for line in manufacturing_lines:
                line.write(
                    {
                        "qty_released": line.qty_invoiced,
                        "qty_pending_payment": 0.0,
                        "amount_released": line.amount_total,
                        "state": "ready_mrp",
                    }
                )
            invoice._ddsn_sync_mrp_fulfillment_documents()
            invoice._ddsn_set_release_state()

    def _ddsn_is_fully_paid(self):
        self.ensure_one()
        if self._ddc_has_pending_controls():
            return False
        return super()._ddsn_is_fully_paid()

    @api.depends_context("lang")
    @api.depends(
        "payment_state",
        "amount_residual",
        "move_type",
        "state",
        "ddc_collection_state",
        "ddc_control_ids.state",
    )
    def _compute_payment_state(self):
        super()._compute_payment_state()
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.ddc_collection_state == "rejected":
                move.payment_state = "not_paid"
                continue
            if move.ddc_collection_state == "pending":
                move.payment_state = "in_payment"
                continue
            if move.ddc_payment_review_state == "partial":
                if move.currency_id.is_zero(move.amount_residual):
                    move.payment_state = "paid"
                    continue
                move.payment_state = "partial"
                continue
            if move.state != "posted":
                continue
            if move.ddc_collection_state != "validated":
                continue
            if move._ddc_has_pending_controls():
                continue
            if not move.currency_id.is_zero(move.amount_residual):
                continue
            move.payment_state = "paid"
