from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ddc_sales_report_mode = fields.Boolean(
        string="Enviar a espera de pago",
        compute="_compute_ddc_sales_report_mode",
    )
    ddc_report_amount = fields.Monetary(
        string="Monto a reportar",
        currency_field="currency_id",
        compute="_compute_ddc_report_amount",
    )
    ddc_authorized_credit_mode = fields.Boolean(
        string="Pago con credito autorizado",
        compute="_compute_ddc_authorized_credit_mode",
    )
    ddc_credit_authorization_id = fields.Many2one(
        "doorandoor.credit.authorization",
        string="Solicitud de autorizacion",
        readonly=True,
    )
    ddc_credit_authorization_code = fields.Char(
        string="Codigo de autorizacion",
        copy=False,
    )
    ddc_credit_available = fields.Monetary(
        string="Credito disponible",
        currency_field="company_currency_id",
        compute="_compute_ddc_authorized_credit_mode",
    )

    @api.depends(
        "journal_id",
        "journal_id.ddc_payment_flow",
        "partner_id",
        "company_id",
    )
    def _compute_ddc_authorized_credit_mode(self):
        Authorization = self.env["doorandoor.credit.authorization"]
        for wizard in self:
            wizard.ddc_authorized_credit_mode = (
                wizard.journal_id.ddc_payment_flow == "authorized_credit"
            )
            wizard.ddc_credit_available = 0.0
            if wizard.ddc_authorized_credit_mode and wizard.partner_id:
                partner = wizard.partner_id.commercial_partner_id
                used, reserved = Authorization.credit_totals(partner, wizard.company_id)
                limit_amount = partner.with_company(
                    wizard.company_id
                ).ddc_authorized_credit_limit
                wizard.ddc_credit_available = max(limit_amount - used - reserved, 0.0)

    def _ddc_credit_invoice(self):
        self.ensure_one()
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            raise ValidationError(
                _("El credito autorizado solo puede aplicarse a una factura por operacion.")
            )
        return invoices

    def action_send_ddc_credit_code(self):
        self.ensure_one()
        if self.journal_id.ddc_payment_flow != "authorized_credit":
            raise ValidationError(_("Seleccione el diario de credito autorizado."))
        if self.ddc_credit_authorization_id.state == "pending":
            self.ddc_credit_authorization_id.sudo().write({"state": "cancelled"})
        authorization = self.env[
            "doorandoor.credit.authorization"
        ].create_for_wizard(self)
        self.write(
            {
                "ddc_credit_authorization_id": authorization.id,
                "ddc_credit_authorization_code": False,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }

    @api.depends("journal_id", "journal_id.ddc_requires_payment_control")
    def _compute_ddc_sales_report_mode(self):
        for wizard in self:
            # El asistente abierto desde una factura nunca debe crear el pago
            # contable en un diario controlado. Esto aplica tambien a
            # administradores y contadores: el pago oficial debe originarse en
            # Control de Cobros/Pagos, donde existe evidencia bancaria real.
            wizard.ddc_sales_report_mode = bool(
                wizard.journal_id.ddc_requires_payment_control
            )

    @api.depends(
        "journal_id",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.move_id.amount_residual",
        "line_ids.move_id.ddtp_payment_plan",
        "line_ids.move_id.ddtp_payment_due_amount",
        "line_ids.move_id.payment_ids",
    )
    def _compute_ddc_report_amount(self):
        for wizard in self:
            amount_map = wizard._ddc_get_invoice_amount_map()
            wizard.ddc_report_amount = sum(amount_map.values())

    def _create_payments(self):
        self.ensure_one()
        controlled_journal = self.journal_id.ddc_requires_payment_control
        if controlled_journal:
            return self._ddc_create_sales_reports()
        payments = super(
            AccountPaymentRegister,
            self.with_context(ddc_skip_release_sync=controlled_journal),
        )._create_payments()

        if controlled_journal:
            self._ddc_create_payment_controls(payments)

        return payments

    def _ddc_create_sales_reports(self):
        invoices = self.line_ids.move_id.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            raise ValidationError(_("El reporte comercial debe originarse desde una factura de cliente."))
        control_model = self.env["doorandoor.cobro.control"].sudo()
        invoice_amount_map = self._ddc_get_invoice_amount_map()
        controls = control_model
        for invoice in invoices:
            base_amount = invoice_amount_map.get(invoice.id, 0.0)
            amount_reported = base_amount
            if invoice.currency_id.is_zero(amount_reported):
                raise ValidationError(
                    _("La factura %s no tiene saldo pendiente para enviar a espera de pago.")
                    % invoice.display_name
                )
            duplicate = control_model.search(
                [
                    ("move_id", "=", invoice.id),
                    ("payment_id", "=", False),
                    ("source_type", "=", "sales_report"),
                    ("state", "in", ["draft", "reported", "pending", "review"]),
                    ("amount_reported", "=", amount_reported),
                    ("journal_id", "=", self.journal_id.id),
                ],
                limit=1,
            )
            if duplicate:
                controls |= duplicate
                continue
            controls |= control_model.create(
                {
                    "move_id": invoice.id,
                    "partner_id": invoice.partner_id.id,
                    "currency_id": self.currency_id.id or invoice.currency_id.id,
                    "company_id": invoice.company_id.id,
                    "journal_id": self.journal_id.id,
                    "sale_user_id": self.env.user.id,
                    "payment_date": fields.Date.context_today(self),
                    "amount_reported": amount_reported,
                    "validated_amount": 0.0,
                    "payment_reference": invoice.name,
                    "state": "reported",
                    "source_type": "sales_report",
                    "notes": _(
                        "Reporte comercial sin efecto contable. Debe vincularse al pago oficial recibido antes de validar."
                    ),
                }
            )
            invoice.message_post(
                body=Markup(
                    "<p><strong>Pago informado por Ventas</strong></p>"
                    "<p>La factura quedo en espera de un pago real por <strong>%s</strong> "
                    "mediante <strong>%s</strong>. No se creo pago ni asiento contable.</p>"
                ) % (amount_reported, self.journal_id.display_name),
                author_id=self.env.user.partner_id.id,
                email_from=self.env.user.email_formatted or "DoorAndDoor <noreply@doorandoor.com>",
                subtype_xmlid="mail.mt_note",
            )
        return self.env["account.payment"]

    def action_create_payments(self):
        if self.journal_id.ddc_payment_flow == "authorized_credit":
            if not self.ddc_credit_authorization_id or not self.ddc_credit_authorization_code:
                raise ValidationError(
                    _("Debe solicitar e introducir el codigo de autorizacion de 6 digitos.")
                )
            authorization = self.ddc_credit_authorization_id.validate_for_wizard(
                self, self.ddc_credit_authorization_code
            )
            authorization.settle_invoice()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Credito autorizado"),
                    "message": _(
                        "El codigo fue validado. La factura se liquido y la deuda "
                        "quedo abierta en la cuenta por cobrar del cliente."
                    ),
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        if (
            self.journal_id.ddc_requires_payment_control
        ):
            self._ddc_create_sales_reports()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Factura en espera de pago"),
                    "message": _(
                        "Se etiqueto la factura y se envio a Control de Cobros como En espera de pago. "
                        "No se creo un pago contable ni se modifico su saldo."
                    ),
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return super().action_create_payments()

    def _ddc_create_payment_controls(self, payments):
        control_model = self.env["doorandoor.cobro.control"].sudo()
        invoice_amount_map = self._ddc_get_invoice_amount_map()

        for payment in payments:
            invoices = (payment.reconciled_invoice_ids | payment.invoice_ids).filtered(
                lambda move: move.move_type == "out_invoice"
            )
            if not invoices:
                invoices = self.line_ids.move_id.filtered(lambda move: move.move_type == "out_invoice")

            if not invoices:
                continue

            total_base_amount = sum(invoice_amount_map.get(invoice.id, 0.0) for invoice in invoices) or payment.amount or 1.0
            for invoice in invoices:
                existing_control = control_model.search(
                    [
                        ("payment_id", "=", payment.id),
                        ("move_id", "=", invoice.id),
                    ],
                    limit=1,
                )
                if existing_control:
                    continue

                base_amount = invoice_amount_map.get(invoice.id, 0.0)
                amount_reported = payment.amount if len(invoices) == 1 else payment.amount * (base_amount / total_base_amount)
                pending_domain = [
                    ("move_id", "=", invoice.id),
                    ("payment_id", "=", False),
                    ("source_type", "=", "sales_report"),
                    ("state", "in", ["reported", "pending", "review"]),
                ]
                pending_report = control_model.search(
                    [*pending_domain, ("journal_id", "=", payment.journal_id.id)],
                    order="create_date, id",
                    limit=1,
                )
                if not pending_report:
                    pending_report = control_model.search(
                        pending_domain,
                        order="create_date, id",
                        limit=1,
                    )
                if pending_report:
                    pending_report.write(
                        {
                            "payment_id": payment.id,
                            "journal_id": payment.journal_id.id,
                            "payment_date": payment.date,
                            "amount_reported": amount_reported,
                            "validated_amount": amount_reported,
                            "payment_reference": payment.payment_reference
                            or payment.memo
                            or self.communication,
                            "state": "pending",
                            "notes": _(
                                "El reporte En espera de pago fue vinculado al pago oficial %s."
                            )
                            % (payment.name or payment.display_name),
                        }
                    )
                    continue
                control_model.create(
                    {
                        "move_id": invoice.id,
                        "partner_id": invoice.partner_id.id,
                        "currency_id": payment.currency_id.id or invoice.currency_id.id,
                        "company_id": payment.company_id.id or invoice.company_id.id,
                        "journal_id": payment.journal_id.id,
                        "payment_id": payment.id,
                        "sale_user_id": self.env.user.id,
                        "payment_date": payment.date,
                        "amount_reported": amount_reported,
                        "payment_reference": payment.payment_reference or payment.memo or self.communication,
                        "state": "pending",
                        "notes": "Cobro generado automaticamente desde Registrar pago y pendiente de validacion.",
                    }
                )
                invoice.message_post(
                    body=Markup(
                        "<p><strong>Pago reportado para revision</strong></p>"
                        "<p>Se registro un pago por <strong>%s</strong> en el diario <strong>%s</strong>.</p>"
                        "<p>La factura queda en revision hasta que Contabilidad confirme el ingreso.</p>"
                    )
                    % (amount_reported, payment.journal_id.display_name),
                    subtype_xmlid="mail.mt_note",
                )

    def _ddc_get_invoice_amount_map(self):
        amount_map = {}
        for line in self.line_ids.filtered(lambda line: line.move_id.move_type == "out_invoice"):
            amount_map.setdefault(line.move_id.id, 0.0)
            amount_map[line.move_id.id] += abs(line.amount_residual_currency or line.amount_residual)
        for invoice in self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice"
        ):
            residual = amount_map.get(invoice.id, 0.0)
            # The first controlled payment (Zelle, bank transfer, etc.) of a
            # partial-plan invoice must report the agreed deposit, not the
            # complete receivable.  After a real payment is reconciled, Odoo's
            # residual is the authoritative amount for every later payment.
            if (
                invoice.ddtp_payment_plan == "partial"
                and not invoice.payment_ids
                and invoice.ddtp_payment_due_amount > 0
                and invoice.currency_id.compare_amounts(
                    residual, invoice.ddtp_payment_due_amount
                ) >= 0
            ):
                amount_map[invoice.id] = invoice.ddtp_payment_due_amount
        return amount_map
