from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from markupsafe import Markup, escape

from ..hooks import ensure_administration_channel


class DoorAndDoorStripeRefundRequest(models.Model):
    _name = "doorandoor.stripe.refund.request"
    _description = "Solicitud de devolución Stripe"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="Nuevo", readonly=True, copy=False, tracking=True)
    invoice_id = fields.Many2one(
        "account.move", required=True, readonly=True, ondelete="restrict", tracking=True
    )
    partner_id = fields.Many2one(related="invoice_id.commercial_partner_id", store=True)
    company_id = fields.Many2one(related="invoice_id.company_id", store=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", store=True)
    original_transaction_id = fields.Many2one(
        "payment.transaction", required=True, readonly=True, ondelete="restrict", tracking=True
    )
    refund_transaction_id = fields.Many2one(
        "payment.transaction", readonly=True, copy=False, tracking=True
    )
    credit_note_id = fields.Many2one("account.move", readonly=True, copy=False, tracking=True)
    refund_payment_id = fields.Many2one(
        related="refund_transaction_id.payment_id", string="Pago de devolución", readonly=True
    )
    requested_by_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user, readonly=True
    )
    requested_at = fields.Datetime(readonly=True, copy=False)
    reviewed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    reviewed_at = fields.Datetime(readonly=True, copy=False)
    reason_id = fields.Many2one(
        "doorandoor.stripe.refund.reason",
        string="Causa",
        tracking=True,
        ondelete="restrict",
    )
    reason = fields.Text(string="Detalle adicional", tracking=True)
    review_note = fields.Text(string="Nota de Control de Cobros", tracking=True)
    line_ids = fields.One2many(
        "doorandoor.stripe.refund.request.line", "request_id", string="Productos a devolver", copy=True
    )
    amount = fields.Monetary(compute="_compute_amount", store=True, tracking=True)
    maximum_refundable_amount = fields.Monetary(
        compute="_compute_maximum_refundable_amount", string="Máximo reembolsable"
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending", "Pendiente de autorización"),
            ("processing", "Enviado a Stripe"),
            ("done", "Reembolso completado"),
            ("error", "Reembolso fallido"),
            ("rejected", "Rechazado"),
        ],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
    )
    provider_reference = fields.Char(
        related="refund_transaction_id.provider_reference", string="Referencia Stripe", readonly=True
    )
    transaction_state_message = fields.Text(
        related="refund_transaction_id.state_message", string="Respuesta de Stripe", readonly=True
    )
    admin_notified_state = fields.Char(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("name", "Nuevo") == "Nuevo":
                values["name"] = self.env["ir.sequence"].next_by_code(
                    "doorandoor.stripe.refund.request"
                ) or "Nuevo"
        return super().create(vals_list)

    def write(self, values):
        if not self.env.user.has_group("doorandoor_control_cobros.group_ddc_manager"):
            protected = {
                "state", "invoice_id", "original_transaction_id",
                "refund_transaction_id", "credit_note_id", "reviewed_by_id",
                "reviewed_at", "requested_by_id", "requested_at",
            }
            if protected.intersection(values) and not self.env.context.get(
                "ddsr_state_transition"
            ):
                raise AccessError(_("El estado y los documentos de la devolución solo cambian mediante el flujo autorizado."))
            if any(request.state != "draft" for request in self) and not self.env.context.get(
                "ddsr_state_transition"
            ):
                raise AccessError(_("Una solicitud enviada ya no puede ser modificada por Ventas."))
        return super().write(values)

    @api.model
    def create_from_invoice(self, invoice):
        transaction = invoice.transaction_ids.filtered(
            lambda tx: tx.provider_code == "stripe"
            and tx.state == "done"
            and tx.amount > 0
            and tx.operation != "refund"
        ).sorted("id", reverse=True)[:1]
        if not transaction:
            raise UserError(_("La factura no tiene un cobro Stripe confirmado que pueda reembolsarse."))
        request = self.create(
            {
                "invoice_id": invoice.id,
                "original_transaction_id": transaction.id,
                "reason_id": self.env.ref(
                    "doorandoor_stripe_refund.reason_product_out_of_stock"
                ).id,
                "line_ids": [
                    fields.Command.create(
                        {
                            "invoice_line_id": line.id,
                            "quantity": 0.0,
                        }
                    )
                    for line in invoice.invoice_line_ids.filtered(
                        lambda item: item.display_type == "product" and item.quantity > 0
                    )
                ],
            }
        )
        return request

    @api.depends("line_ids.amount")
    def _compute_amount(self):
        for request in self:
            request.amount = sum(request.line_ids.mapped("amount"))

    @api.depends("original_transaction_id.child_transaction_ids.state")
    def _compute_maximum_refundable_amount(self):
        for request in self:
            transaction = request.original_transaction_id
            refunded = sum(
                abs(child.amount)
                for child in transaction.child_transaction_ids
                if child.operation == "refund" and child.state not in ("cancel", "error")
                and child != request.refund_transaction_id
            )
            request.maximum_refundable_amount = max(transaction.amount - refunded, 0.0)

    @api.constrains("invoice_id", "original_transaction_id")
    def _check_source_transaction(self):
        for request in self:
            tx = request.original_transaction_id
            if request.invoice_id not in tx.invoice_ids or tx.provider_code != "stripe" or tx.state != "done":
                raise ValidationError(_("La transacción debe ser un cobro Stripe confirmado de esta factura."))

    def _check_manager(self):
        if not self.env.user.has_group("doorandoor_control_cobros.group_ddc_manager"):
            raise AccessError(_("Solo un administrador de Control de Cobros puede autorizar o rechazar devoluciones."))

    def action_submit(self):
        for request in self:
            if request.state != "draft":
                raise UserError(_("Solo se puede enviar una solicitud en borrador."))
            selected = request.line_ids.filtered(lambda line: line.quantity > 0)
            if not selected or request.currency_id.is_zero(request.amount):
                raise ValidationError(_("Seleccione al menos una cantidad mayor que cero."))
            if not request.reason_id:
                raise ValidationError(_("Seleccione la causa de la devolución."))
            if request.reason_id.requires_details and not (request.reason or "").strip():
                raise ValidationError(
                    _("La causa seleccionada requiere escribir un detalle adicional.")
                )
            request.line_ids._validate_refundable_quantities()
            if request.currency_id.compare_amounts(request.amount, request.maximum_refundable_amount) > 0:
                raise ValidationError(_("El importe supera el saldo reembolsable del cobro Stripe."))
            request.with_context(ddsr_state_transition=True).write(
                {"state": "pending", "requested_at": fields.Datetime.now()}
            )
            request.message_post(body=_("Solicitud enviada a Control de Cobros por %s.") % self.env.user.display_name)
            request._notify_administration("pending", create_activities=True)
        return True

    def action_reject(self):
        self._check_manager()
        for request in self:
            if request.state != "pending":
                raise UserError(_("Solo se puede rechazar una solicitud pendiente."))
            request.write(
                {
                    "state": "rejected",
                    "reviewed_by_id": self.env.user.id,
                    "reviewed_at": fields.Datetime.now(),
                }
            )
            request.message_post(body=_("Devolución rechazada por Control de Cobros."))
            request._complete_administration_activities(_("Solicitud rechazada."))
            request._notify_administration("rejected")
        return True

    def action_approve_and_refund(self):
        self._check_manager()
        for request in self:
            if request.state != "pending":
                raise UserError(_("Solo se puede autorizar una solicitud pendiente."))
            request.line_ids._validate_refundable_quantities()
            if request.currency_id.compare_amounts(request.amount, request.maximum_refundable_amount) > 0:
                raise ValidationError(_("El importe supera el saldo reembolsable disponible en Stripe."))
            credit_note = request._create_credit_note()
            refund_transaction = request.original_transaction_id.with_context(
                ddsr_refund_request=request
            )._send_refund_request(request.amount)
            refund_transaction.write(
                {
                    "ddsr_refund_request_id": request.id,
                    "invoice_ids": [fields.Command.set(credit_note.ids)],
                }
            )
            request.write(
                {
                    "credit_note_id": credit_note.id,
                    "refund_transaction_id": refund_transaction.id,
                    "reviewed_by_id": self.env.user.id,
                    "reviewed_at": fields.Datetime.now(),
                    "state": "processing",
                }
            )
            request._complete_administration_activities(_("Solicitud aprobada."))
            request._notify_administration("approved")
            if refund_transaction.state == "done":
                refund_transaction._post_process()
            request._sync_from_transaction()
            request.invoice_id.message_post(
                body=_("%(request)s autorizada por %(user)s: reembolso Stripe por %(amount)s.")
                % {
                    "request": request.name,
                    "user": self.env.user.display_name,
                    "amount": request.currency_id.format(request.amount),
                }
            )
        return True

    def _administration_users(self):
        system_users = self.env.ref("base.group_system").users
        collection_managers = self.env.ref(
            "doorandoor_control_cobros.group_ddc_manager"
        ).users
        return (system_users | collection_managers).filtered(
            lambda user: user.active and not user.share
        )

    def _administration_channel(self):
        return ensure_administration_channel(self.env)

    def _administration_message(self, event):
        self.ensure_one()
        labels = {
            "pending": ("Nueva devolución pendiente", "warning"),
            "approved": ("Devolución aprobada por Control de Cobros", "info"),
            "rejected": ("Devolución rechazada", "danger"),
            "processing": ("Devolución enviada a Stripe", "info"),
            "done": ("Devolución completada", "success"),
            "error": ("Devolución Stripe fallida", "danger"),
        }
        title, color = labels[event]
        reviewer = self.reviewed_by_id.display_name or "Pendiente"
        stripe_reference = self.provider_reference or "Pendiente"
        product_details = Markup("<br/>").join(
            Markup("%s × %s = %s")
            % (
                escape(line.product_id.display_name),
                escape(line.quantity),
                escape(self.currency_id.format(line.amount)),
            )
            for line in self.line_ids.filtered(lambda item: item.quantity > 0)
        ) or Markup("Sin productos seleccionados")
        return Markup(
            '<div class="alert alert-%s mb-0">'
            '<strong>%s — %s</strong><br/>'
            'Factura: %s<br/>Cliente: %s<br/>Importe: %s<br/>Causa: %s<br/>'
            'Solicitante: %s<br/>Responsable: %s<br/>'
            'Productos:<br/>%s<br/>Detalle: %s<br/>Nota administrativa: %s<br/>'
            'Referencia Stripe: %s'
            '</div>'
        ) % (
            color,
            escape(title),
            escape(self.name),
            escape(self.invoice_id.display_name),
            escape(self.partner_id.display_name),
            escape(self.currency_id.format(self.amount)),
            escape(self.reason_id.display_name or "Sin especificar"),
            escape(self.requested_by_id.display_name),
            escape(reviewer),
            product_details,
            escape(self.reason or "Sin detalle adicional"),
            escape(self.review_note or "Sin nota"),
            escape(stripe_reference),
        )

    def _notify_administration(self, event, create_activities=False):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get_id(self._name)
        for request in self:
            if request.admin_notified_state == event:
                continue
            channel = request._administration_channel()
            if channel:
                channel.message_post(
                    body=request._administration_message(event),
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
            if create_activities:
                existing_users = request.activity_ids.filtered(
                    lambda activity: activity.activity_type_id == activity_type
                ).user_id
                for user in request._administration_users() - existing_users:
                    self.env["mail.activity"].sudo().create(
                        {
                            "activity_type_id": activity_type.id,
                            "res_model_id": model_id,
                            "res_id": request.id,
                            "user_id": user.id,
                            "summary": _("Autorizar devolución Stripe %s") % request.name,
                            "note": request._administration_message("pending"),
                            "date_deadline": fields.Date.context_today(request),
                        }
                    )
            request.sudo().with_context(ddsr_state_transition=True).admin_notified_state = event

    def _complete_administration_activities(self, feedback):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for request in self:
            request.activity_ids.filtered(
                lambda activity: activity.activity_type_id == activity_type
                and activity.user_id in request._administration_users()
            ).sudo().action_feedback(feedback=feedback)

    def _create_credit_note(self):
        self.ensure_one()
        selected = self.line_ids.filtered(lambda line: line.quantity > 0)
        commands = []
        for request_line in selected:
            source = request_line.invoice_line_id
            commands.append(
                fields.Command.create(
                    {
                        "product_id": source.product_id.id,
                        "name": source.name,
                        "quantity": request_line.quantity,
                        "product_uom_id": source.product_uom_id.id,
                        "price_unit": source.price_unit,
                        "discount": source.discount,
                        "tax_ids": [fields.Command.set(source.tax_ids.ids)],
                        "account_id": source.account_id.id,
                        "analytic_distribution": source.analytic_distribution,
                    }
                )
            )
        credit_note = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.invoice_id.partner_id.id,
                "currency_id": self.invoice_id.currency_id.id,
                "company_id": self.invoice_id.company_id.id,
                "journal_id": self.invoice_id.journal_id.id,
                "invoice_date": fields.Date.context_today(self),
                "reversed_entry_id": self.invoice_id.id,
                "invoice_origin": self.invoice_id.name,
                "ref": self.name,
                "invoice_line_ids": commands,
            }
        )
        if self.currency_id.compare_amounts(credit_note.amount_total, self.amount) != 0:
            raise ValidationError(
                _("La nota de crédito calculada (%(credit)s) no coincide con la solicitud (%(request)s).")
                % {
                    "credit": self.currency_id.format(credit_note.amount_total),
                    "request": self.currency_id.format(self.amount),
                }
            )
        credit_note.action_post()
        return credit_note

    def _sync_from_transaction(self):
        for request in self.filtered("refund_transaction_id"):
            state = request.refund_transaction_id.state
            previous_state = request.state
            if state == "done":
                request.sudo().with_context(ddsr_state_transition=True).state = "done"
            elif state in ("error", "cancel"):
                request.sudo().with_context(ddsr_state_transition=True).state = "error"
            else:
                request.sudo().with_context(ddsr_state_transition=True).state = "processing"
            if request.state != previous_state or request.admin_notified_state != request.state:
                if request.state in ("done", "error"):
                    request._complete_administration_activities(
                        _("Resultado Stripe: %s") % dict(request._fields["state"].selection).get(request.state)
                    )
                request._notify_administration(request.state)

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Solicitud de devolución Stripe"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class DoorAndDoorStripeRefundRequestLine(models.Model):
    _name = "doorandoor.stripe.refund.request.line"
    _description = "Línea de solicitud de devolución Stripe"
    _order = "id"

    request_id = fields.Many2one(
        "doorandoor.stripe.refund.request", required=True, ondelete="cascade"
    )
    invoice_line_id = fields.Many2one("account.move.line", required=True, readonly=True)
    product_id = fields.Many2one(related="invoice_line_id.product_id", readonly=True)
    description = fields.Char(related="invoice_line_id.name", readonly=True)
    invoiced_quantity = fields.Float(related="invoice_line_id.quantity", readonly=True)
    already_requested_quantity = fields.Float(compute="_compute_already_requested_quantity")
    available_quantity = fields.Float(compute="_compute_already_requested_quantity")
    quantity = fields.Float(string="Cantidad a devolver", digits="Product Unit of Measure")
    price_unit = fields.Float(related="invoice_line_id.price_unit", readonly=True)
    tax_ids = fields.Many2many(related="invoice_line_id.tax_ids", readonly=True)
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount = fields.Monetary(compute="_compute_amount", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env["doorandoor.stripe.refund.request"].browse(
            [values.get("request_id") for values in vals_list if values.get("request_id")]
        )
        if any(request.state != "draft" for request in requests):
            raise AccessError(_("No se pueden agregar productos a una solicitud ya enviada."))
        return super().create(vals_list)

    def write(self, values):
        if any(line.request_id.state != "draft" for line in self):
            raise AccessError(_("No se pueden modificar cantidades de una solicitud ya enviada."))
        return super().write(values)

    def unlink(self):
        if any(line.request_id.state != "draft" for line in self):
            raise AccessError(_("No se pueden eliminar productos de una solicitud ya enviada."))
        return super().unlink()

    @api.depends(
        "invoice_line_id",
        "invoice_line_id.fulfillment_line_id.qty_delivered",
        "request_id.invoice_id.ddsr_refund_request_ids.state",
    )
    def _compute_already_requested_quantity(self):
        for line in self:
            prior_lines = self.search(
                [
                    ("invoice_line_id", "=", line.invoice_line_id.id),
                    ("request_id", "!=", line.request_id.id),
                    ("request_id.state", "in", ("pending", "processing", "done")),
                ]
            )
            line.already_requested_quantity = sum(prior_lines.mapped("quantity"))
            delivered = line.invoice_line_id.fulfillment_line_id.qty_delivered
            line.available_quantity = max(
                line.invoiced_quantity - line.already_requested_quantity - delivered,
                0.0,
            )

    @api.depends("quantity", "invoice_line_id.price_unit", "invoice_line_id.discount", "tax_ids")
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.invoice_line_id.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.request_id.partner_id,
                is_refund=True,
            )
            line.amount = taxes["total_included"]

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_("La cantidad a devolver no puede ser negativa."))

    def _validate_refundable_quantities(self):
        for line in self.filtered(lambda item: item.quantity > 0):
            if line.quantity > line.available_quantity:
                raise ValidationError(
                    _(
                        "%(product)s: solo quedan %(quantity)s unidades sin entregar disponibles "
                        "para devolver. Las unidades ya entregadas no pueden reducirse mediante "
                        "este flujo."
                    )
                    % {
                        "product": line.product_id.display_name,
                        "quantity": line.available_quantity,
                    }
                )
