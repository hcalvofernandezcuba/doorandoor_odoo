from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


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
    credit_authorization_id = fields.Many2one(
        "doorandoor.credit.authorization",
        string="Credito autorizado a liquidar",
        copy=False,
        tracking=True,
        check_company=True,
    )
    credit_origin_invoice_id = fields.Many2one(
        related="credit_authorization_id.invoice_id",
        string="Factura origen del credito",
        readonly=True,
    )
    authorized_credit_balance_before = fields.Monetary(
        string="Deuda antes del cobro",
        currency_field="currency_id",
        copy=False,
        readonly=True,
    )
    authorized_credit_applied_amount = fields.Monetary(
        string="Pago aplicado al credito",
        currency_field="currency_id",
        copy=False,
        readonly=True,
    )
    authorized_credit_balance_after = fields.Monetary(
        string="Deuda restante",
        currency_field="currency_id",
        copy=False,
        readonly=True,
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
    payment_support_attachment_ids = fields.Many2many(
        related="payment_id.ddc_support_attachment_ids",
        string="Documentos asociados al pago",
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
            ("customer_credit", "Credito a favor del cliente"),
            ("authorized_credit_repayment", "Cobro de credito autorizado"),
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
    needs_reconciliation_repair = fields.Boolean(
        string="Requiere reparar conciliacion",
        compute="_compute_needs_reconciliation_repair",
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
    credit_origin_control_id = fields.Many2one(
        "doorandoor.cobro.control",
        string="Control origen del credito",
        copy=False,
        readonly=True,
    )
    credit_balance_before = fields.Monetary(
        string="Credito disponible antes",
        currency_field="currency_id",
        copy=False,
        readonly=True,
    )
    credit_applied_amount = fields.Monetary(
        string="Credito aplicado",
        currency_field="currency_id",
        copy=False,
        readonly=True,
    )
    credit_balance_after = fields.Monetary(
        string="Credito restante",
        currency_field="currency_id",
        copy=False,
        readonly=True,
    )

    _sql_constraints = [
        ("amount_reported_positive", "CHECK(amount_reported > 0)", "El monto reportado debe ser mayor que cero."),
    ]

    def _ddc_check_official_payment_permission(self):
        if not (
            self.env.user.has_group(
                "doorandoor_control_cobros.group_ddc_official_payment"
            )
            or self.env.user.has_group("base.group_system")
            or self.env.is_superuser()
        ):
            raise AccessError(
                _(
                    "Solo el personal autorizado de Control de Cobros puede "
                    "asociar, validar, revisar o rechazar pagos oficiales."
                )
            )

    def _ddc_validate_official_payment_link(self):
        """Keep one official payment attached to one primary control/invoice.

        Controls generated when consuming a previously recognized customer
        advance are intentionally excluded: they reference the origin payment
        for audit purposes but do not represent a second bank payment.
        """
        for record in self.filtered(
            lambda control: control.payment_id
            and control.source_type != "customer_credit"
            and control.active
            and control.state != "rejected"
        ):
            payment = record.payment_id
            # Serialize checks for the same payment so two concurrent users
            # cannot both pass the duplicate search before either commits.
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)", (77001, payment.id)
            )
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("payment_id", "=", payment.id),
                    ("active", "=", True),
                    ("state", "!=", "rejected"),
                    ("source_type", "!=", "customer_credit"),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "El pago oficial %(payment)s ya pertenece al control "
                        "%(control)s de la factura %(invoice)s. No puede "
                        "asociarse nuevamente."
                    )
                    % {
                        "payment": payment.display_name,
                        "control": duplicate.name,
                        "invoice": duplicate.move_id.display_name or _("Sin factura"),
                    }
                )
            if record.move_id and payment.ddc_invoice_id and payment.ddc_invoice_id != record.move_id:
                raise ValidationError(
                    _(
                        "El pago %(payment)s esta asociado a %(payment_invoice)s "
                        "y no puede utilizarse en el control de %(control_invoice)s."
                    )
                    % {
                        "payment": payment.display_name,
                        "payment_invoice": payment.ddc_invoice_id.display_name,
                        "control_invoice": record.move_id.display_name,
                    }
                )
            if record.source_type == "authorized_credit_repayment":
                if not record.credit_authorization_id:
                    raise ValidationError(
                        _("El control debe indicar el credito autorizado que se liquidara.")
                    )
                if (
                    payment.ddc_credit_repayment_authorization_id
                    != record.credit_authorization_id
                ):
                    raise ValidationError(
                        _(
                            "El pago %(payment)s no corresponde al credito autorizado "
                            "seleccionado en el control %(control)s."
                        )
                        % {"payment": payment.display_name, "control": record.name}
                    )
            reconciled_invoices = payment.reconciled_invoice_ids
            if record.move_id and reconciled_invoices and record.move_id not in reconciled_invoices:
                raise ValidationError(
                    _(
                        "El pago %(payment)s ya esta conciliado con %(invoices)s "
                        "y no puede vincularse a %(invoice)s."
                    )
                    % {
                        "payment": payment.display_name,
                        "invoices": ", ".join(reconciled_invoices.mapped("display_name")),
                        "invoice": record.move_id.display_name,
                    }
                )

    @api.constrains(
        "payment_id", "move_id", "credit_authorization_id", "state", "active", "source_type"
    )
    def _check_ddc_official_payment_link(self):
        self._ddc_validate_official_payment_link()

    def _ddc_broadcast_operational_update(self, reason="updated"):
        """Notify open operational forms after the current transaction commits."""
        for record in self:
            partner = record.partner_id.commercial_partner_id
            self.env["bus.bus"]._sendone(
                "doorandoor.payment.operations",
                "doorandoor_payment_update",
                {
                    "reason": reason,
                    "invoice_ids": record.move_id.ids,
                    "payment_ids": record.payment_id.ids,
                    "control_ids": record.ids,
                    "partner_ids": partner.ids,
                    "title": _("Información de cobro actualizada"),
                    "message": _("La factura, el pago o el crédito abierto recibió información nueva."),
                },
            )

    def action_ddc_force_operational_sync(self):
        return self.mapped("move_id")._ddc_force_operational_sync()

    @api.model_create_multi
    def create(self, vals_list):
        if any(
            vals.get("payment_id")
            and vals.get("source_type", "manual") != "customer_credit"
            for vals in vals_list
        ):
            self._ddc_check_official_payment_permission()
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
        records._ddc_broadcast_operational_update("created")
        return records

    def write(self, vals):
        changes_official_link = "payment_id" in vals or (
            "move_id" in vals and any(self.mapped("payment_id"))
        )
        normal_controls = self.filtered(
            lambda record: vals.get("source_type", record.source_type)
            != "customer_credit"
        )
        if changes_official_link and normal_controls:
            self._ddc_check_official_payment_permission()
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
            self._ddc_broadcast_operational_update("updated")
        return result

    def unlink(self):
        moves = self.mapped("move_id")
        payload_records = self
        payload_records._ddc_broadcast_operational_update("deleted")
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
        self._ddc_check_official_payment_permission()
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
        if self.filtered("payment_id"):
            self._ddc_check_official_payment_permission()
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
        self._ddc_check_official_payment_permission()
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
        self._ddc_check_official_payment_permission()
        self._ddc_validate_official_payment_link()
        for record in self:
            if record.state == "validated":
                if record.source_type == "authorized_credit_repayment":
                    return self._ddc_notification_action(
                        _("Cobro ya validado"),
                        _(
                            "Este pago ya fue aplicado a la deuda de credito autorizado. "
                            "No es necesario validarlo nuevamente."
                        ),
                        "warning",
                    )
                payment = record.payment_id
                if payment and record.move_id in payment.reconciled_invoice_ids:
                    return self._ddc_notification_action(
                        _("Cobro ya validado"),
                        _("Este control ya estaba validado y conciliado. No es necesario validarlo nuevamente."),
                        "warning",
                    )
            if record.source_type == "authorized_credit_repayment":
                record._ddc_validate_credit_repayment()
                continue
            if not record.move_id:
                raise ValidationError(_("No puedes validar un control sin factura asociada."))
            payment = record.payment_id
            if not payment:
                raise ValidationError(_("No puedes validar un control sin un pago contable asociado."))
            other_validated = self.search(
                [
                    ("id", "!=", record.id),
                    ("payment_id", "=", payment.id),
                    ("state", "=", "validated"),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if other_validated:
                raise ValidationError(
                    _("El pago oficial %s ya fue validado mediante el control %s.")
                    % (payment.display_name, other_validated.name)
                )
            if payment.state in ("draft", "in_process", "posted", "paid"):
                record._ddc_prepare_payment_entry(payment)
                record._ddc_reconcile_payment_with_invoice(payment)
                payment.action_validate()
            else:
                raise ValidationError(
                    _("El pago %s no se encuentra en un estado que permita conciliarlo.")
                    % payment.display_name
                )
            record.write(
                {
                    "state": "validated",
                    "accountant_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                }
            )
            payment._ddc_transfer_open_credit_to_advance(record)
            # ``write(state=validated)`` emits an operational event, but that
            # event can be queued while Odoo is still finishing the payment
            # and invoice recomputations.  Emit one authoritative event only
            # after the accounting result is final, so an invoice form never
            # reloads the intermediate "en revision" snapshot and then stays
            # stale until a manual refresh.
            invoice = record.move_id
            invoice.invalidate_recordset()
            invoice._ddc_refresh_control_status()
            invoice._ddsn_broadcast_document_update("payment_reconciled")
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

    def _ddc_validate_credit_repayment(self):
        self.ensure_one()
        authorization = self.credit_authorization_id
        payment = self.payment_id
        if not authorization:
            raise ValidationError(_("Seleccione el credito autorizado que se liquidara."))
        if not payment:
            raise ValidationError(_("El control no tiene un pago real asociado."))
        self.env.cr.execute(
            "SELECT id FROM doorandoor_credit_authorization WHERE id = %s FOR UPDATE",
            [authorization.id],
        )
        authorization.invalidate_recordset(
            ["amount_due", "accounting_state", "financing_line_id"]
        )
        due_before = authorization.amount_due
        amount = self.validated_amount or self.amount_reported
        if authorization.currency_id.compare_amounts(amount, due_before) > 0:
            raise ValidationError(
                _("El cobro no puede superar la deuda financiada pendiente de %s.")
                % authorization.currency_id.format(due_before)
            )
        if payment.currency_id.compare_amounts(payment.amount, amount) != 0:
            raise ValidationError(
                _("El monto validado debe coincidir con el importe del pago contable.")
            )
        self._ddc_prepare_payment_entry(payment)
        payment.move_id.invalidate_recordset(["line_ids"])
        financing_line = authorization.financing_line_id
        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == financing_line.account_id
            and line.partner_id.commercial_partner_id == authorization.partner_id
            and not line.reconciled
            and line.amount_residual < 0
        )
        if not payment_lines:
            raise ValidationError(
                _(
                    "El asiento del pago no contiene la contrapartida en la "
                    "subcuenta de credito autorizado del cliente."
                )
            )
        (financing_line | payment_lines).reconcile()
        payment.action_validate()
        authorization.invalidate_recordset(
            ["amount_due", "amount_repaid", "accounting_state"]
        )
        due_after = authorization.amount_due
        if authorization.currency_id.compare_amounts(due_after, due_before) >= 0:
            raise ValidationError(
                _("La conciliacion no redujo el saldo del credito autorizado.")
            )
        self.write(
            {
                "state": "validated",
                "accountant_user_id": self.env.user.id,
                "review_date": fields.Datetime.now(),
                "authorized_credit_balance_before": due_before,
                "authorized_credit_applied_amount": due_before - due_after,
                "authorized_credit_balance_after": due_after,
            }
        )
        if authorization.invoice_id:
            authorization.invoice_id.message_post(
                body=_(
                    "Se registro un pago de la deuda de credito autorizado por %(amount)s. "
                    "La factura original permanece liquidada; deuda financiada restante: %(due)s."
                )
                % {
                    "amount": authorization.currency_id.format(due_before - due_after),
                    "due": authorization.currency_id.format(due_after),
                },
                subtype_xmlid="mail.mt_note",
            )
        self._ddc_broadcast_operational_update("authorized_credit_repayment_validated")

    def _ddc_apply_automatic_payment_policy(self):
        for record in self.filtered(lambda control: control.move_id and control.payment_id):
            invoice = record.move_id
            active_controls = invoice.ddc_control_ids.filtered(
                lambda control: control.active and control.payment_id and control.state != "rejected"
            )
            unique_payments = active_controls.mapped("payment_id")
            accumulated = sum(unique_payments.mapped("amount"))
            threshold_amount = abs(invoice.amount_total) * invoice._ddc_auto_payment_threshold()
            if invoice.currency_id.compare_amounts(accumulated, threshold_amount) < 0:
                record.write(
                    {
                        "state": "review",
                        "review_date": fields.Datetime.now(),
                        "notes": _(
                            "Pago asociado automaticamente por referencia de factura. "
                            "El acumulado es menor al umbral automatico y queda para seguimiento contable."
                        ),
                    }
                )
                continue
            pending_controls = active_controls.filtered(
                lambda control: control.state in ("draft", "reported", "pending", "review")
                and control.payment_id
            ).sorted("id")
            for pending_control in pending_controls:
                pending_control.action_validate()
            invoice._ddc_refresh_control_status()
            if invoice._ddc_has_manufacturing_lines() and invoice.currency_id.compare_amounts(
                accumulated, abs(invoice.amount_total) * 0.50
            ) >= 0:
                invoice._ddc_release_manufacturing_at_threshold()
            invoice.message_post(
                body=_(
                    "Los pagos asociados alcanzaron %.2f%% del total de la factura. "
                    "El control se valido automaticamente y se sincronizo la fabricacion."
                )
                % (invoice._ddc_auto_payment_threshold() * 100.0),
                subtype_xmlid="mail.mt_note",
            )

    def _ddc_prepare_payment_entry(self, payment):
        self.ensure_one()
        if not payment.outstanding_account_id:
            payment.outstanding_account_id = payment._get_outstanding_account(payment.payment_type)
        if not payment.outstanding_account_id:
            raise ValidationError(
                _("No existe una cuenta transitoria configurada para generar el asiento del pago %s.")
                % payment.display_name
            )
        if not payment.move_id:
            existing_moves = self.env["account.move"].search(
                [("origin_payment_id", "=", payment.id), ("state", "!=", "cancel")]
            )
            if len(existing_moves) > 1:
                raise ValidationError(
                    _("El pago %s tiene mas de un asiento activo y requiere revision contable.")
                    % payment.display_name
                )
            if existing_moves:
                payment.move_id = existing_moves.id
            else:
                payment._generate_journal_entry()
        if not payment.move_id:
            raise ValidationError(_("No se pudo generar el asiento contable del pago %s.") % payment.display_name)
        payment.move_id.filtered(lambda move: move.state == "draft").action_post()
        payment.with_context(ddc_skip_automatic_policy=True).action_post()

    def _ddc_reconcile_payment_with_invoice(self, payment):
        self.ensure_one()
        if not payment.move_id:
            raise ValidationError(_("El pago seleccionado no tiene un asiento contable para conciliar."))
        invoice = self.move_id
        residual_before = invoice.amount_residual
        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id.reconcile
                and not line.reconciled
                and line.partner_id.commercial_partner_id == invoice.partner_id.commercial_partner_id
                and line.account_id.account_type in ("asset_receivable", "liability_payable")
                and not line.currency_id.is_zero(line.amount_residual_currency)
            )
        )
        invoice_lines = invoice.line_ids.filtered(
            lambda line: (
                line.account_id.reconcile
                and not line.reconciled
                and line.partner_id.commercial_partner_id == invoice.partner_id.commercial_partner_id
                and line.account_id.account_type in ("asset_receivable", "liability_payable")
            )
        )
        common_accounts = payment_lines.mapped("account_id") & invoice_lines.mapped("account_id")
        candidate_lines = payment_lines.filtered(lambda line: line.account_id in common_accounts)
        for payment_line in candidate_lines:
            invoice.js_assign_outstanding_line(payment_line.id)

        invoice.invalidate_recordset(["amount_residual", "payment_state"])
        if invoice.currency_id.compare_amounts(invoice.amount_residual, residual_before) >= 0:
            raise ValidationError(
                _(
                    "No se pudo aplicar contablemente el pago %s a la factura %s. "
                    "El control no sera validado hasta que disminuya el saldo pendiente."
                )
                % (payment.display_name, invoice.display_name)
            )

    def action_reject(self):
        self._ddc_check_official_payment_permission()
        reconciled = self.filtered(
            lambda record: record.payment_id
            and record.move_id
            and record.move_id in record.payment_id.reconciled_invoice_ids
        )
        if reconciled:
            details = ", ".join(
                "%s / %s" % (record.name, record.payment_id.display_name)
                for record in reconciled
            )
            raise ValidationError(
                _(
                    "No se puede rechazar un control cuyo pago ya fue aplicado "
                    "contablemente (%s). Primero debe ejecutarse una correccion "
                    "contable autorizada que revierta la conciliacion."
                )
                % details
            )
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

    @api.depends("move_id", "credit_authorization_id", "payment_id", "state")
    def _compute_matching_status(self):
        for record in self:
            if record.state == "validated":
                record.matching_status = "validated"
            elif record.credit_authorization_id and record.payment_id:
                record.matching_status = "ready_to_validate"
            elif record.credit_authorization_id:
                record.matching_status = "invoice_linked"
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

    @api.depends(
        "move_id",
        "credit_authorization_id",
        "amount_reported",
        "invoice_residual_snapshot",
    )
    def _compute_matching_flags(self):
        for record in self:
            record.is_unidentified = not bool(
                record.move_id or record.credit_authorization_id
            )
            residual_base = record.move_id.amount_residual if record.move_id else record.invoice_residual_snapshot
            record.is_partial = bool(residual_base and record.amount_reported and record.amount_reported < residual_base)

    @api.depends("state", "move_id", "move_id.amount_residual", "payment_id", "payment_id.reconciled_invoice_ids")
    def _compute_needs_reconciliation_repair(self):
        for record in self:
            record.needs_reconciliation_repair = bool(
                record.state == "validated"
                and record.move_id
                and record.payment_id
                and not record.move_id.currency_id.is_zero(record.move_id.amount_residual)
                and record.move_id not in record.payment_id.reconciled_invoice_ids
            )
