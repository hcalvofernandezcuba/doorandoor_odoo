import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model_create_multi
    def create(self, vals_list):
        journal_ids = {vals.get("journal_id") for vals in vals_list if vals.get("journal_id")}
        forbidden = self.env["account.journal"].browse(journal_ids).filtered(
            lambda journal: journal.ddc_payment_flow == "authorized_credit"
        )
        if forbidden:
            raise ValidationError(
                _(
                    "El diario Crédito Autorizado no admite pagos manuales de "
                    "Enviar dinero ni Recibir dinero. Asígnele el límite al cliente "
                    "y utilícelo únicamente desde Pagar en una factura confirmada."
                )
            )
        return super().create(vals_list)

    def write(self, vals):
        journal = (
            self.env["account.journal"].browse(vals["journal_id"])
            if vals.get("journal_id")
            else self.env["account.journal"]
        )
        if journal.ddc_payment_flow == "authorized_credit":
            raise ValidationError(
                _(
                    "No se puede asignar el diario Crédito Autorizado a un pago "
                    "manual. El crédito solamente se consume desde una factura."
                )
            )
        return super().write(vals)

    ddc_invoice_id = fields.Many2one(
        "account.move",
        string="Factura asociada",
        copy=False,
        tracking=True,
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('company_id', '=', company_id)]",
        help="Factura de cliente que se comprobara y asociara de forma exclusiva con este pago.",
    )
    ddc_credit_repayment_authorization_id = fields.Many2one(
        "doorandoor.credit.authorization",
        string="Credito autorizado a liquidar",
        copy=False,
        tracking=True,
        check_company=True,
        domain="[('partner_id', '=', partner_id), ('company_id', '=', company_id), ('currency_id', '=', currency_id), ('state', '=', 'used'), ('accounting_state', 'in', ('active', 'partial'))]",
        help=(
            "Deuda financiada del cliente que sera reducida por este cobro real. "
            "Es incompatible con Factura asociada."
        ),
    )
    ddc_credit_repayment_invoice_id = fields.Many2one(
        related="ddc_credit_repayment_authorization_id.invoice_id",
        string="Factura origen del credito",
        readonly=True,
    )
    ddc_credit_repayment_due = fields.Monetary(
        related="ddc_credit_repayment_authorization_id.amount_due",
        string="Saldo financiado pendiente",
        currency_field="company_currency_id",
        readonly=True,
    )
    ddc_credit_authorization_id = fields.Many2one(
        "doorandoor.credit.authorization",
        string="Autorizacion de credito",
        copy=False,
        readonly=True,
        check_company=True,
    )
    ddc_reported_payer_id = fields.Many2one(
        "res.partner",
        string="Pagador informado",
        copy=False,
        readonly=True,
        help="Persona o cliente originalmente informado en el pago cuando difiere del cliente facturado.",
    )
    ddc_invoice_payment_state = fields.Selection(
        related="ddc_invoice_id.payment_state",
        string="Estado de la factura",
        readonly=True,
    )
    ddc_invoice_residual = fields.Monetary(
        related="ddc_invoice_id.amount_residual",
        string="Saldo pendiente por liquidar",
        currency_field="ddc_invoice_currency_id",
        readonly=True,
    )
    ddc_invoice_currency_id = fields.Many2one(
        related="ddc_invoice_id.currency_id",
        string="Moneda de la factura",
        readonly=True,
    )
    ddc_application_type = fields.Selection(
        selection=[
            ("none", "Sin factura"),
            ("partial", "Pago parcial"),
            ("full", "Liquidacion total"),
            ("excess", "Liquidacion total con credito a favor"),
        ],
        string="Aplicacion del pago",
        compute="_compute_ddc_application_type",
    )
    ddc_amount_to_apply = fields.Monetary(
        string="Importe aplicado a la factura",
        currency_field="currency_id",
        compute="_compute_ddc_application_amounts",
    )
    ddc_customer_credit_amount = fields.Monetary(
        string="Credito a favor del cliente",
        currency_field="currency_id",
        compute="_compute_ddc_application_amounts",
    )
    ddc_support_attachment_ids = fields.Many2many(
        "ir.attachment",
        "ddc_payment_support_attachment_rel",
        "payment_id",
        "attachment_id",
        string="Documentos asociados",
        copy=False,
        help="Capturas de pantalla, imagenes, PDF, textos o documentos escaneados que respaldan el pago.",
    )
    ddc_control_id = fields.Many2one(
        "doorandoor.cobro.control",
        string="Control de cobro",
        compute="_compute_ddc_control_id",
        compute_sudo=True,
        search="_search_ddc_control_id",
    )

    @api.model
    def _search_ddc_control_id(self, operator, value):
        """Make the computed control relation usable by dependency recomputation."""
        controls = self.env["doorandoor.cobro.control"].search(
            [("active", "=", True), ("id", operator, value)]
        )
        return [("id", "in", controls.payment_id.ids)]

    @api.depends("ddc_invoice_id")
    def _compute_ddc_control_id(self):
        controls = self.env["doorandoor.cobro.control"].search(
            [
                ("payment_id", "in", self.ids),
                ("active", "=", True),
                ("source_type", "!=", "customer_credit"),
            ],
            order="id desc",
        ) if self.ids else self.env["doorandoor.cobro.control"]
        for payment in self:
            payment_controls = controls.filtered(
                lambda control: control.payment_id == payment
                and (
                    not payment.ddc_invoice_id
                    or control.move_id == payment.ddc_invoice_id
                )
            )
            preferred = payment_controls.filtered(
                lambda control: control.state != "rejected"
            )[:1]
            payment.ddc_control_id = preferred or payment_controls[:1]

    @api.depends(
        "ddc_invoice_id",
        "ddc_invoice_id.amount_residual",
        "ddc_control_id",
        "ddc_control_id.invoice_residual_snapshot",
        "amount",
        "currency_id",
    )
    def _compute_ddc_application_type(self):
        for payment in self:
            invoice = payment.ddc_invoice_id
            if not invoice:
                payment.ddc_application_type = "none"
                continue
            residual_base = (
                payment.ddc_control_id.invoice_residual_snapshot
                if payment.ddc_control_id and payment.ddc_control_id.invoice_residual_snapshot
                else invoice.amount_residual
            )
            comparison = invoice.currency_id.compare_amounts(payment.amount, residual_base)
            if comparison < 0:
                payment.ddc_application_type = "partial"
            elif comparison == 0:
                payment.ddc_application_type = "full"
            else:
                payment.ddc_application_type = "excess"

    @api.depends(
        "ddc_invoice_id",
        "ddc_invoice_id.amount_residual",
        "ddc_control_id",
        "ddc_control_id.invoice_residual_snapshot",
        "amount",
    )
    def _compute_ddc_application_amounts(self):
        for payment in self:
            invoice = payment.ddc_invoice_id
            if not invoice:
                payment.ddc_amount_to_apply = 0.0
                payment.ddc_customer_credit_amount = 0.0
                continue
            residual_base = (
                payment.ddc_control_id.invoice_residual_snapshot
                if payment.ddc_control_id and payment.ddc_control_id.invoice_residual_snapshot
                else invoice.amount_residual
            )
            payment.ddc_amount_to_apply = min(payment.amount, residual_base)
            payment.ddc_customer_credit_amount = max(payment.amount - residual_base, 0.0)

    @api.onchange("partner_id", "payment_type", "partner_type", "company_id")
    def _onchange_ddc_invoice_compatibility(self):
        for payment in self:
            invoice = payment.ddc_invoice_id
            if invoice and not payment._ddc_invoice_is_compatible(invoice):
                payment.ddc_invoice_id = False
            authorization = payment.ddc_credit_repayment_authorization_id
            if authorization and not payment._ddc_credit_repayment_is_compatible(authorization):
                payment.ddc_credit_repayment_authorization_id = False

    @api.onchange("ddc_invoice_id")
    def _onchange_ddc_invoice_excludes_credit_repayment(self):
        if self.ddc_invoice_id:
            self.ddc_credit_repayment_authorization_id = False

    @api.onchange("ddc_credit_repayment_authorization_id")
    def _onchange_ddc_credit_repayment(self):
        authorization = self.ddc_credit_repayment_authorization_id
        if not authorization:
            return
        self.ddc_invoice_id = False
        self.partner_id = authorization.partner_id
        if self.company_currency_id.compare_amounts(self.amount, authorization.amount_due) > 0:
            self.amount = authorization.amount_due

    def _ddc_invoice_is_compatible(self, invoice):
        self.ensure_one()
        return bool(
            invoice
            and self.payment_type == "inbound"
            and self.partner_type == "customer"
            and invoice.move_type == "out_invoice"
            and invoice.state == "posted"
            and invoice.company_id == self.company_id
        )

    def _ddc_credit_repayment_is_compatible(self, authorization):
        self.ensure_one()
        return bool(
            authorization
            and self.payment_type == "inbound"
            and self.partner_type == "customer"
            and authorization.state == "used"
            and authorization.accounting_state in ("active", "partial")
            and authorization.company_id == self.company_id
            and authorization.currency_id == self.currency_id
            and authorization.partner_id == self.partner_id.commercial_partner_id
            and authorization.financing_line_id
            and authorization.amount_due > 0
        )

    @api.constrains(
        "ddc_invoice_id",
        "ddc_credit_repayment_authorization_id",
        "partner_id",
        "payment_type",
        "partner_type",
        "company_id",
        "currency_id",
        "amount",
    )
    def _check_ddc_credit_repayment(self):
        for payment in self.filtered("ddc_credit_repayment_authorization_id"):
            authorization = payment.ddc_credit_repayment_authorization_id
            if payment.ddc_invoice_id:
                raise ValidationError(
                    _("Seleccione una factura o un credito autorizado a liquidar, nunca ambos.")
                )
            if not payment._ddc_credit_repayment_is_compatible(authorization):
                raise ValidationError(
                    _(
                        "El credito seleccionado no corresponde al cliente, compania, "
                        "moneda o ya no conserva saldo financiado."
                    )
                )
            if payment.currency_id.compare_amounts(payment.amount, authorization.amount_due) > 0:
                raise ValidationError(
                    _("El pago no puede superar el saldo financiado pendiente de %s.")
                    % payment.currency_id.format(authorization.amount_due)
                )

    def _ddc_lock_and_validate_credit_repayment(self):
        for payment in self.filtered("ddc_credit_repayment_authorization_id"):
            authorization = payment.ddc_credit_repayment_authorization_id
            self.env.cr.execute(
                "SELECT id FROM doorandoor_credit_authorization WHERE id = %s FOR UPDATE",
                [authorization.id],
            )
            authorization.invalidate_recordset(
                ["state", "accounting_state", "amount_due", "financing_line_id"]
            )
            payment._check_ddc_credit_repayment()

    def _prepare_move_counterpart_lines(self, default_values):
        lines = super()._prepare_move_counterpart_lines(default_values)
        if self.ddc_credit_repayment_authorization_id:
            financing_account = (
                self.ddc_credit_repayment_authorization_id.financing_line_id.account_id
            )
            for line in lines:
                line["account_id"] = financing_account.id
                line["partner_id"] = self.partner_id.commercial_partner_id.id
        return lines

    def _ddc_find_invoice_from_memo(self):
        self.ensure_one()
        reference = " ".join(
            filter(None, [self.memo, self.payment_reference, getattr(self, "ref", False)])
        )
        matches = re.findall(r"\bINV\s*/\s*\d{4}\s*/\s*\d+\b", reference, re.IGNORECASE)
        if not matches:
            return self.env["account.move"]
        invoice_names = {
            re.sub(r"\s*/\s*", "/", match).upper() for match in matches
        }
        invoices = self.env["account.move"].search(
            [
                ("name", "in", list(invoice_names)),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return invoices if len(invoices) == 1 else self.env["account.move"]

    def _ddc_prepare_automatic_invoice_match(self):
        for payment in self.filtered(
            lambda item: item.payment_type == "inbound"
            and item.partner_type == "customer"
            and not item.ddc_credit_repayment_authorization_id
        ):
            invoice = payment.ddc_invoice_id or payment._ddc_find_invoice_from_memo()
            if not invoice:
                continue
            values = {}
            if not payment.ddc_invoice_id:
                values["ddc_invoice_id"] = invoice.id
            if payment.partner_id.commercial_partner_id != invoice.commercial_partner_id:
                values.update(
                    {
                        "ddc_reported_payer_id": payment.partner_id.id,
                        "partner_id": invoice.commercial_partner_id.id,
                    }
                )
            if values:
                payment.with_context(ddc_skip_auto_match=True).write(values)

    def _ddc_validate_invoice_match(self):
        control_model = self.env["doorandoor.cobro.control"]
        for payment in self.filtered("ddc_invoice_id"):
            invoice = payment.ddc_invoice_id
            if not payment._ddc_invoice_is_compatible(invoice):
                raise ValidationError(
                    _("La factura seleccionada no es compatible con el cliente, la compania o el tipo de pago.")
                )
            if payment.currency_id != invoice.currency_id:
                raise ValidationError(
                    _("El pago y la factura deben usar la misma moneda para realizar esta asociacion.")
                )
            other_control_for_payment = control_model.search(
                [
                    ("payment_id", "=", payment.id),
                    ("move_id", "!=", invoice.id),
                    ("active", "=", True),
                    ("state", "!=", "rejected"),
                ],
                limit=1,
            )
            if other_control_for_payment:
                raise ValidationError(
                    _("Este pago ya esta asociado a la factura %s.")
                    % other_control_for_payment.move_id.display_name
                )
            if invoice.payment_state == "paid" and not payment.ddc_control_id:
                raise ValidationError(
                    _("La factura %s ya esta pagada y no puede recibir un nuevo pago.") % invoice.display_name
                )

    @api.constrains(
        "ddc_invoice_id", "partner_id", "payment_type", "partner_type", "company_id", "currency_id", "amount"
    )
    def _check_ddc_invoice_match(self):
        self._ddc_validate_invoice_match()

    def action_post(self):
        forbidden = self.filtered(
            lambda payment: payment.journal_id.ddc_payment_flow == "authorized_credit"
            and not self.env.context.get("ddc_authorized_credit_payment")
        )
        if forbidden:
            raise ValidationError(
                _(
                    "No se puede validar un pago manual con el diario Crédito "
                    "Autorizado. Use el asistente Pagar de la factura y el código "
                    "de autorización del cliente."
                )
            )
        self._ddc_prepare_automatic_invoice_match()
        self._ddc_validate_invoice_match()
        self._ddc_lock_and_validate_credit_repayment()
        result = super().action_post()
        controls = self.filtered("ddc_invoice_id")._ddc_ensure_invoice_control()
        repayment_controls = self.filtered(
            "ddc_credit_repayment_authorization_id"
        )._ddc_ensure_credit_repayment_control()
        if not self.env.context.get("ddc_skip_automatic_policy"):
            controls._ddc_apply_automatic_payment_policy()
        # The control workflow is responsible for the accounting operation.
        # Broadcast again from its final state rather than leaving open forms
        # with the intermediate snapshot emitted while the control was saved.
        invoices = controls.mapped("move_id")
        if invoices:
            invoices.invalidate_recordset()
            invoices._ddsn_broadcast_document_update("payment_post_completed")
        if repayment_controls:
            repayment_controls._ddc_broadcast_operational_update(
                "authorized_credit_repayment_posted"
            )
        return result

    def action_ddc_force_operational_sync(self):
        invoices = self.mapped("ddc_invoice_id")
        return invoices._ddc_force_operational_sync()

    def _ddc_ensure_invoice_control(self):
        control_model = self.env["doorandoor.cobro.control"].sudo()
        result = control_model
        for payment in self:
            invoice = payment.ddc_invoice_id
            if not invoice:
                continue
            
            # Primero verificar si ya existe un control para este pago y factura
            # (esto incluye controles ya vinculados por el flujo de ventas)
            existing_control = control_model.search(
                [("payment_id", "=", payment.id), ("move_id", "=", invoice.id)],
                limit=1,
            )
            if existing_control:
                result |= existing_control
                continue
            
            # Buscar reporte de ventas pendiente para vincular
            pending_domain = [
                ("move_id", "=", invoice.id),
                ("payment_id", "=", False),
                ("source_type", "=", "sales_report"),
                ("state", "in", ["reported", "pending", "review"]),
            ]
            pending_report = control_model.search(
                [
                    *pending_domain,
                    ("journal_id", "=", payment.journal_id.id),
                ],
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
                        "amount_reported": payment.amount,
                        "validated_amount": payment.amount,
                        "payment_date": payment.date,
                        "payment_reference": payment.payment_reference or payment.memo,
                        "notes": _(
                            "El reporte de Ventas fue vinculado al pago oficial %s."
                        ) % (payment.name or payment.display_name),
                    }
                )
                result |= pending_report
                continue
            
            # Si no existe ningún control, crear uno nuevo manual
            result |= control_model.create(
                {
                    "move_id": invoice.id,
                    "partner_id": invoice.partner_id.id,
                    "currency_id": payment.currency_id.id,
                    "company_id": payment.company_id.id,
                    "journal_id": payment.journal_id.id,
                    "payment_id": payment.id,
                    "sale_user_id": self.env.user.id,
                    "payment_date": payment.date,
                    "amount_reported": payment.amount,
                    "validated_amount": payment.amount,
                    "payment_reference": payment.payment_reference or payment.memo,
                    "state": "pending",
                    "source_type": "manual",
                    "notes": _(
                        "Control creado automaticamente desde la factura seleccionada en el pago. "
                        "El resultado sera pago total o parcial segun el saldo conciliado; cualquier "
                        "excedente permanecera como credito a favor del cliente."
                    ),
                }
            )
        return result

    def _ddc_ensure_credit_repayment_control(self):
        control_model = self.env["doorandoor.cobro.control"].sudo()
        result = control_model
        for payment in self.filtered("ddc_credit_repayment_authorization_id"):
            authorization = payment.ddc_credit_repayment_authorization_id
            existing = control_model.search(
                [
                    ("payment_id", "=", payment.id),
                    ("credit_authorization_id", "=", authorization.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if existing:
                result |= existing
                continue
            result |= control_model.create(
                {
                    "credit_authorization_id": authorization.id,
                    "partner_id": authorization.partner_id.id,
                    "currency_id": payment.currency_id.id,
                    "company_id": payment.company_id.id,
                    "journal_id": payment.journal_id.id,
                    "payment_id": payment.id,
                    "sale_user_id": self.env.user.id,
                    "payment_date": payment.date,
                    "amount_reported": payment.amount,
                    "validated_amount": payment.amount,
                    "payment_reference": payment.payment_reference or payment.memo,
                    "state": "pending",
                    "source_type": "authorized_credit_repayment",
                    "authorized_credit_balance_before": authorization.amount_due,
                    "authorized_credit_applied_amount": payment.amount,
                    "authorized_credit_balance_after": max(
                        authorization.amount_due - payment.amount, 0.0
                    ),
                    "notes": _(
                        "Cobro real destinado a reducir la deuda de credito autorizado "
                        "originada por la factura %s. Requiere validacion de Control de Cobros."
                    )
                    % authorization.invoice_id.display_name,
                }
            )
        return result

    def _ddc_transfer_open_credit_to_advance(self, origin_control):
        for payment in self:
            invoice = origin_control.move_id
            if payment.currency_id != payment.company_id.currency_id:
                continue
            credit_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type == "asset_receivable" and line.amount_residual < 0
            )
            if not credit_lines:
                continue
            advance_account = invoice._ddc_get_advance_account()
            for credit_line in credit_lines:
                amount = abs(credit_line.amount_residual)
                transfer = self.env["account.move"].create(
                    {
                        "move_type": "entry", "journal_id": payment.journal_id.id,
                        "date": payment.date, "ref": _("Traslado a pagos anticipados - %s") % payment.display_name,
                        "ddc_credit_origin_payment_id": payment.id,
                        "ddc_credit_origin_control_id": origin_control.id,
                        "line_ids": [
                            fields.Command.create({"name": payment.display_name, "partner_id": invoice.commercial_partner_id.id, "account_id": credit_line.account_id.id, "debit": amount}),
                            fields.Command.create({"name": payment.display_name, "partner_id": invoice.commercial_partner_id.id, "account_id": advance_account.id, "credit": amount}),
                        ],
                    }
                )
                transfer.action_post()
                (credit_line | transfer.line_ids.filtered(lambda line: line.account_id == credit_line.account_id)).reconcile()
