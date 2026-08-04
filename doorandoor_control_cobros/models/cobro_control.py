from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCobroControl(models.Model):
    _name = "doorandoor.cobro.control"
    _description = "Control de Cobro"
    _inherit = ["mail.thread", "mail.activity.mixin", "doorandoor.document.barcode.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Numero",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
    )
    active = fields.Boolean(default=True)
    move_id = fields.Many2one(
        "account.move",
        string="Factura",
        domain=[("move_type", "=", "out_invoice")],
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        required=True,
        default=lambda self: self.env.company.id,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario reportado",
        domain="[('type', 'in', ('bank', 'cash'))]",
        tracking=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        copy=False,
    )
    payment_state = fields.Selection(
        related="payment_id.state",
        string="Estado del pago",
        store=True,
        readonly=True,
    )
    invoice_payment_state = fields.Selection(
        related="move_id.payment_state",
        string="Estado de la factura",
        store=True,
        readonly=True,
    )
    sale_user_id = fields.Many2one(
        "res.users",
        string="Reportado por",
        default=lambda self: self.env.user,
        tracking=True,
    )
    accountant_user_id = fields.Many2one(
        "res.users",
        string="Validado por",
        tracking=True,
        copy=False,
    )
    payment_date = fields.Date(
        string="Fecha reportada",
        default=fields.Date.context_today,
        tracking=True,
    )
    amount_reported = fields.Monetary(
        string="Monto reportado",
        required=True,
        tracking=True,
    )
    validated_amount = fields.Monetary(
        string="Monto validado",
        tracking=True,
        copy=False,
    )
    payment_reference = fields.Char(
        string="Referencia",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("reported", "Reportado"),
            ("pending", "Pendiente"),
            ("review", "En revision"),
            ("validated", "Validado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    source_type = fields.Selection(
        selection=[
            ("sales_report", "Reportado por ventas"),
            ("accounting_detected", "Detectado por contabilidad"),
            ("manual", "Manual"),
        ],
        string="Origen del control",
        default="manual",
        required=True,
        tracking=True,
    )
    matching_status = fields.Selection(
        selection=[
            ("unidentified", "Sin factura"),
            ("identified", "Cliente identificado"),
            ("invoice_linked", "Factura vinculada"),
            ("payment_linked", "Pago vinculado"),
            ("ready_to_validate", "Listo para validar"),
            ("validated", "Validado"),
        ],
        string="Estado de asociacion",
        compute="_compute_matching_status",
        store=True,
    )
    is_unidentified = fields.Boolean(
        string="Pago por identificar",
        compute="_compute_matching_flags",
        store=True,
    )
    is_partial = fields.Boolean(
        string="Pago parcial",
        compute="_compute_matching_flags",
        store=True,
    )
    invoice_residual_snapshot = fields.Monetary(
        string="Residual observado",
        copy=False,
    )
    review_date = fields.Datetime(
        string="Fecha de revision",
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string="Motivo de rechazo",
        copy=False,
    )
    notes = fields.Text(string="Notas")
    identification_notes = fields.Text(string="Notas de identificacion")

    _sql_constraints = [
        ("amount_reported_positive", "CHECK(amount_reported > 0)", "El monto reportado debe ser mayor que cero."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("doorandoor.cobro.control") or _("Nuevo")
            if vals.get("move_id") and not vals.get("partner_id"):
                move = self.env["account.move"].browse(vals["move_id"])
                vals["partner_id"] = move.partner_id.id
                vals.setdefault("currency_id", move.currency_id.id)
                vals.setdefault("company_id", move.company_id.id)
                vals.setdefault("invoice_residual_snapshot", move.amount_residual)
            vals.setdefault("validated_amount", vals.get("amount_reported", 0.0))
        records = super().create(vals_list)
        records.mapped("move_id")._ddc_refresh_control_status()
        return records

    def write(self, vals):
        tracked_fields = {"state", "move_id", "payment_id", "amount_reported", "validated_amount", "active"}
        moves_before = self.mapped("move_id")
        if "move_id" in vals and vals["move_id"]:
            move = self.env["account.move"].browse(vals["move_id"])
            vals.setdefault("invoice_residual_snapshot", move.amount_residual)
            vals.setdefault("partner_id", move.partner_id.id)
            vals.setdefault("currency_id", move.currency_id.id)
            vals.setdefault("company_id", move.company_id.id)
        if "amount_reported" in vals and "validated_amount" not in vals:
            vals["validated_amount"] = vals["amount_reported"]
        result = super().write(vals)
        if tracked_fields.intersection(vals):
            (moves_before | self.mapped("move_id"))._ddc_refresh_control_status()
        return result

    def unlink(self):
        moves = self.mapped("move_id")
        result = super().unlink()
        moves._ddc_refresh_control_status()
        return result

    def action_report(self):
        already_reported = self.filtered(lambda record: record.state != "draft")
        if already_reported:
            return self._ddc_notification_action(
                _("Accion ya aplicada"),
                _("Este cobro ya fue enviado a contabilidad o ya avanzo a otro estado. No se puede reportar de nuevo."),
                "warning",
            )
        self.write({"state": "reported"})
        for record in self:
            record._ddc_notify_transition(
                _("Pago reportado para validacion"),
                _(
                    "Ventas reporto el pago %s por %s y la factura queda en revision hasta confirmacion de contabilidad."
                )
                % (record.name, record.amount_reported),
                "info",
            )
        return self._ddc_notification_action(
            _("Pago reportado"),
            _("El cobro fue enviado a revision contable y la factura quedo en proceso de validacion."),
            "success",
        )

    def action_create_payment_entry(self):
        for record in self:
            if record.payment_id:
                return self._ddc_notification_action(
                    _("Pago ya asociado"),
                    _("Este control ya tiene un pago contable enlazado. No es necesario crearlo nuevamente."),
                    "warning",
                )
            if not record.partner_id:
                raise ValidationError(_("Primero debes identificar el cliente antes de crear el pago contable."))
            if not record.journal_id:
                raise ValidationError(_("Debes indicar el diario o via de pago antes de crear el pago contable."))
            payment_method_line = record.journal_id.inbound_payment_method_line_ids[:1]
            if not payment_method_line:
                raise ValidationError(_("El diario seleccionado no tiene un metodo de pago de entrada configurado."))
            payment = self.env["account.payment"].create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": record.partner_id.id,
                    "amount": record.validated_amount or record.amount_reported,
                    "currency_id": record.currency_id.id,
                    "date": record.payment_date or fields.Date.context_today(self),
                    "journal_id": record.journal_id.id,
                    "payment_method_line_id": payment_method_line.id,
                    "memo": record.payment_reference or record.name,
                }
            )
            record.write({"payment_id": payment.id})
            record._ddc_notify_transition(
                _("Pago contable creado"),
                _(
                    "Se creo el pago contable %s para este control. Ahora puede mantenerse por identificar o asociarse despues a la factura correcta."
                )
                % (payment.name or payment.display_name),
                "info",
            )
        return self._ddc_notification_action(
            _("Pago creado"),
            _("El pago contable fue creado y enlazado al control correctamente."),
            "success",
        )

    def action_open_match_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Asociar control detectado"),
            "res_model": "doorandoor.cobro.match.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_control_id": self.id,
            },
        }

    def action_print_control_report(self):
        self.ensure_one()
        return self.env.ref("doorandoor_control_cobros.action_report_ddc_cobro_control").report_action(self)

    def action_mark_pending(self):
        already_pending = self.filtered(lambda record: record.state == "pending")
        if already_pending:
            return self._ddc_notification_action(
                _("Control ya pendiente"),
                _("Este control ya estaba marcado como pendiente de revision."),
                "warning",
            )
        self.write({"state": "pending"})
        for record in self:
            record._ddc_notify_transition(
                _("Cobro pendiente de revision"),
                _("El control %s quedo marcado como pendiente para continuar la revision del pago.") % record.name,
                "info",
            )
        return self._ddc_notification_action(
            _("Cobro pendiente"),
            _("El control quedo pendiente para continuar el proceso de revision."),
            "warning",
        )

    def action_review(self):
        already_in_review = self.filtered(lambda record: record.state == "review")
        if already_in_review:
            return self._ddc_notification_action(
                _("Revision ya iniciada"),
                _("Este control ya se encuentra en revision contable."),
                "warning",
            )
        already_validated = self.filtered(lambda record: record.state == "validated")
        if already_validated:
            return self._ddc_notification_action(
                _("Cobro ya validado"),
                _("Este control ya fue validado y no puede volver a pasar a revision."),
                "warning",
            )
        self.write(
            {
                "state": "review",
                "review_date": fields.Datetime.now(),
            }
        )
        for record in self:
            record._ddc_notify_transition(
                _("Contabilidad inicio la revision"),
                _(
                    "Contabilidad inicio la revision bancaria del control %s. La factura permanece en proceso de pago."
                )
                % record.name,
                "info",
            )
        return self._ddc_notification_action(
            _("Revision iniciada"),
            _("El cobro ya esta siendo revisado por contabilidad."),
            "success",
        )

    def action_validate(self):
        for record in self:
            if record.state == "validated":
                return self._ddc_notification_action(
                    _("Cobro ya validado"),
                    _("Este control ya estaba validado. No es necesario validarlo nuevamente."),
                    "warning",
                )
            if not record.move_id:
                raise ValidationError(_("No puedes validar un control sin factura asociada."))
            payment = record.payment_id
            if not payment:
                raise ValidationError(_("No puedes validar un control sin un pago contable asociado."))
            if payment and payment.state in ("draft", "in_process"):
                if not payment.outstanding_account_id:
                    payment.outstanding_account_id = payment._get_outstanding_account(payment.payment_type)
                payment.action_post()
                payment.move_id.filtered(lambda move: move.state == "draft").action_post()
                record._ddc_reconcile_payment_with_invoice(payment)
                payment.action_validate()
                record.move_id._compute_amount()
                record.move_id._compute_payment_state()
            elif payment and payment.state == "posted":
                record._ddc_reconcile_payment_with_invoice(payment)
                payment.action_validate()
                record.move_id._compute_amount()
                record.move_id._compute_payment_state()
            record.write(
                {
                    "state": "validated",
                    "accountant_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                }
            )
            record._ddc_notify_transition(
                _("Pago validado por contabilidad"),
                _(
                    "Contabilidad valido el control %s. La factura puede avanzar a pagada o pagada parcialmente segun la conciliacion."
                )
                % record.name,
                "success",
            )
        return self._ddc_notification_action(
            _("Pago validado"),
            _("El pago fue validado correctamente y la factura se sincronizo con el resultado contable."),
            "success",
        )

    def _ddc_reconcile_payment_with_invoice(self, payment):
        self.ensure_one()
        if not payment.move_id:
            return
        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id.reconcile
                and not line.reconciled
                and line.partner_id == payment.partner_id
                and line.account_id.account_type in ("asset_receivable", "liability_payable")
            )
        )
        invoice_lines = self.move_id.line_ids.filtered(
            lambda line: (
                line.account_id.reconcile
                and not line.reconciled
                and line.partner_id == payment.partner_id
                and line.account_id.account_type in ("asset_receivable", "liability_payable")
            )
        )
        if payment_lines and invoice_lines:
            common_accounts = payment_lines.mapped("account_id") & invoice_lines.mapped("account_id")
            for account in common_accounts:
                (payment_lines.filtered(lambda line: line.account_id == account) | invoice_lines.filtered(lambda line: line.account_id == account)).reconcile()

    def action_reject(self):
        self.write(
            {
                "state": "rejected",
                "accountant_user_id": self.env.user.id,
                "review_date": fields.Datetime.now(),
            }
        )
        for record in self:
            record._ddc_notify_transition(
                _("Pago rechazado por contabilidad"),
                _(
                    "Contabilidad rechazo el control %s. La factura queda marcada como rechazada hasta corregir o volver a reportar el pago."
                )
                % record.name,
                "danger",
            )
        return self._ddc_notification_action(
            _("Pago rechazado"),
            _("El pago fue rechazado y la factura quedo marcada como rechazada."),
            "danger",
        )

    def _ddc_notify_transition(self, title, message, level):
        self.ensure_one()
        body = Markup(
            "<p><strong>%s</strong></p>"
            "<p>%s</p>"
            "<p><strong>Control:</strong> %s</p>"
            "<p><strong>Factura:</strong> %s</p>"
        ) % (
            title,
            message,
            self.name or "-",
            self.move_id.name or "-",
        )
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        if self.move_id:
            self.move_id._ddc_post_control_message(body)

    def _ddc_notification_action(self, title, message, level):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": level,
                "sticky": False,
            },
        }

    def _ddsn_get_barcode_document_name(self):
        self.ensure_one()
        return self.name or self.move_id.name or super()._ddsn_get_barcode_document_name()

    @api.depends("move_id", "payment_id", "state")
    def _compute_matching_status(self):
        for record in self:
            if record.state == "validated":
                record.matching_status = "validated"
            elif not record.move_id:
                if record.payment_id:
                    record.matching_status = "payment_linked"
                elif record.partner_id:
                    record.matching_status = "identified"
                else:
                    record.matching_status = "unidentified"
            elif record.move_id and record.payment_id:
                record.matching_status = "ready_to_validate"
            elif record.move_id:
                record.matching_status = "invoice_linked"
            else:
                record.matching_status = "payment_linked"

    @api.depends("move_id", "amount_reported", "invoice_residual_snapshot")
    def _compute_matching_flags(self):
        for record in self:
            record.is_unidentified = not bool(record.move_id)
            residual_base = record.move_id.amount_residual if record.move_id else record.invoice_residual_snapshot
            record.is_partial = bool(residual_base and record.amount_reported and record.amount_reported < residual_base)
