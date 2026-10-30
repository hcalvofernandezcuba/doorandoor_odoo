from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ddcl_clover_ecommerce_mode = fields.Boolean(compute="_compute_ddcl_clover_ecommerce_mode")
    ddcl_clover_provider_id = fields.Integer(
        string="Identificador técnico del proveedor Clover",
        compute="_compute_ddcl_clover_ecommerce_mode",
        compute_sudo=True,
    )
    ddcl_clover_required = fields.Boolean(
        string="Clover obligatorio", compute="_compute_ddcl_clover_ecommerce_mode"
    )
    ddcl_collection_base_amount = fields.Monetary(
        string="Saldo a liquidar", compute="_compute_ddcl_collection_amounts",
        currency_field="currency_id", readonly=True,
    )
    ddcl_collection_fee_amount = fields.Monetary(
        string="Cargo Clover", compute="_compute_ddcl_collection_amounts",
        currency_field="currency_id", readonly=True,
    )
    ddcl_collection_total_amount = fields.Monetary(
        string="Total a cobrar por Clover", compute="_compute_ddcl_collection_amounts",
        currency_field="currency_id", readonly=True,
    )
    ddcl_collection_fee_rate_display = fields.Char(
        string="Porcentaje Clover", compute="_compute_ddcl_collection_amounts", readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        """Render a planned card collection as Clover from the first frame.

        The server already enforced Clover at payment creation, but the base
        wizard selected its first manual journal (normally Zelle) before the
        readonly protection was evaluated.  Set the provider journal and its
        online line in defaults so the visible form matches the protected
        transaction from the start.
        """
        values = super().default_get(fields_list)
        invoices = self._ddcl_get_context_invoices()
        if len(invoices) != 1:
            return values
        invoice = invoices.ensure_one()
        if not invoice.ddtp_card_payment_enabled:
            return values
        expected_amount = self._ddcl_expected_amount(invoice)
        if not expected_amount:
            return values
        provider = self.env["payment.provider"].sudo().search([
            ("code", "=", "clover"),
            ("state", "in", ("test", "enabled")),
            ("company_id", "=", invoice.company_id.id),
        ], limit=1)
        if not provider:
            return values
        provider_line = self._ddcl_get_provider_payment_line(provider)
        values.update({
            "journal_id": provider.journal_id.id,
            "payment_method_line_id": provider_line.id,
            "amount": expected_amount,
        })
        return values

    @api.model
    def _ddcl_get_context_invoices(self):
        """Resolve invoices from both standard payment-register entry points.

        ``account.move.action_register_payment`` delegates to receivable
        lines, so the normal Pagar button provides ``account.move.line`` ids.
        Treating those ids as invoice ids made the browser fall back to the
        first manual journal (Zelle) even for a Clover card collection.
        """
        active_ids = self.env.context.get("active_ids", [])
        if self.env.context.get("active_model") == "account.move.line":
            invoices = self.env["account.move.line"].browse(active_ids).exists().move_id
        else:
            invoices = self.env["account.move"].browse(active_ids).exists()
        return invoices.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )

    @api.depends(
        "journal_id", "line_ids.move_id.ddtp_card_payment_enabled",
        "line_ids.move_id.ddtp_card_fee_line_id", "line_ids.move_id.amount_residual",
    )
    def _compute_ddcl_clover_ecommerce_mode(self):
        for wizard in self:
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            invoice = invoices[:1] if len(invoices) == 1 else self.env["account.move"]
            required = bool(
                invoice
                and invoice.ddtp_card_payment_enabled
                and wizard._ddcl_expected_amount(invoice)
            )
            providers = self.env["payment.provider"].sudo().search([
                ("code", "=", "clover"),
                ("state", "in", ("test", "enabled")),
                ("company_id", "=", invoice.company_id.id if invoice else wizard.company_id.id),
            ])
            provider = (
                providers[:1]
                if required
                else providers.filtered(lambda item: item.journal_id == wizard.journal_id)[:1]
            )
            # Keep only the technical id in the transient wizard. Exposing a
            # Many2one makes the web client call name_get on payment.provider,
            # whose configuration is intentionally restricted to Ajustes.
            wizard.ddcl_clover_provider_id = provider.id
            wizard.ddcl_clover_required = required
            wizard.ddcl_clover_ecommerce_mode = bool(
                provider and (required or provider.journal_id == wizard.journal_id)
            )

    def _ddcl_get_selected_card_invoice(self):
        """Return the initial Clover collection selected on a single invoice."""
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            return self.env["account.move"]
        invoice = invoices.ensure_one()
        if invoice.ddtp_card_payment_enabled and self._ddcl_expected_amount(invoice):
            return invoice
        return self.env["account.move"]

    def _ddcl_get_clover_invoice(self):
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            raise ValidationError(_("Clover requiere una sola factura publicada por operación."))
        invoice = invoices.ensure_one()
        expected_amount = self._ddcl_expected_amount(invoice)
        if expected_amount <= 0:
            raise ValidationError(_("La factura no tiene saldo disponible para cobrar por Clover."))
        if self.currency_id.compare_amounts(self.amount, expected_amount) != 0:
            raise ValidationError(
                _("Clover solo puede cobrar el saldo calculado de la factura: %(amount)s. "
                  "El importe no se puede modificar.")
                % {"amount": self.currency_id.format(expected_amount)}
            )
        return invoice

    def _ddcl_expected_amount(self, invoice):
        """Return the only amount permitted for a Clover collection.

        The shared card-fee module may prepare a first collection amount that
        already includes the applicable fee.  In every other case Clover must
        collect precisely the current receivable residual.  The value is
        derived server-side, never trusted from the browser wizard.
        """
        invoice.ensure_one()
        expected = None
        helper = getattr(self, "_ddtp_expected_card_amount", None)
        if helper:
            expected = helper(invoice)
        return expected if expected is not None else invoice.amount_residual

    def _ddcl_get_provider_payment_line(self, provider):
        line = provider.journal_id.inbound_payment_method_line_ids.filtered(
            lambda item: item.payment_provider_id == provider
        )[:1]
        if not line:
            raise ValidationError(_("El diario Clover no tiene una línea de pago online válida."))
        return line

    def _ddcl_get_collection_amounts(self, invoice, provider):
        """Split a later Clover liquidation into receivable, fee and charge.

        A fee already planned on the original invoice remains governed by
        ``doorandoor_stripe_fee``.  This additional fee applies only when a
        previous payment exists and Clover is used to liquidate the current
        residual, so earlier Zelle/cash/check payments are never surcharged.
        """
        invoice.ensure_one()
        planned_amount = self._ddtp_expected_card_amount(invoice)
        base_amount = planned_amount if planned_amount is not None else invoice.amount_residual
        # Reconciliations imported from another system do not always expose an
        # ``account.payment`` through ``payment_ids``.  A reduced residual is
        # the accounting fact that proves an earlier collection exists.
        has_previous_payment = (
            invoice.currency_id.compare_amounts(
                invoice.amount_residual, invoice.amount_total
            ) < 0
        )
        rate = provider.ddtp_card_fee_rate if has_previous_payment and planned_amount is None else 0.0
        fee_amount = invoice.currency_id.round(base_amount * rate / 100.0)
        return base_amount, fee_amount, base_amount + fee_amount, rate

    @api.depends(
        "amount", "currency_id", "journal_id", "ddcl_clover_ecommerce_mode",
        "line_ids.move_id.amount_residual", "line_ids.move_id.payment_ids",
    )
    def _compute_ddcl_collection_amounts(self):
        for wizard in self:
            base_amount = wizard.amount
            fee_amount = rate = 0.0
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            provider = self.env["payment.provider"].sudo().search([
                ("code", "=", "clover"),
                ("state", "in", ("test", "enabled")),
                ("company_id", "=", wizard.company_id.id),
                ("journal_id", "=", wizard.journal_id.id),
            ], limit=1)
            if wizard.ddcl_clover_ecommerce_mode and len(invoices) == 1 and provider:
                base_amount, fee_amount, _total, rate = wizard._ddcl_get_collection_amounts(
                    invoices.ensure_one(), provider
                )
            wizard.ddcl_collection_base_amount = base_amount
            wizard.ddcl_collection_fee_amount = fee_amount
            wizard.ddcl_collection_total_amount = base_amount + fee_amount
            wizard.ddcl_collection_fee_rate_display = wizard._ddtp_format_percent(rate)

    def action_create_payments(self):
        self.ensure_one()
        selected_card_invoice = self._ddcl_get_selected_card_invoice()
        if selected_card_invoice:
            # The card choice belongs to the invoice, not to the default
            # journal of the payment wizard. This blocks the old path that
            # recorded a Manual Payment in cash after Clover was selected.
            provider = self.env["payment.provider"].sudo().search([
                ("code", "=", "clover"),
                ("state", "in", ("test", "enabled")),
                ("company_id", "=", selected_card_invoice.company_id.id),
            ], limit=1)
            if not provider:
                raise ValidationError(_(
                    "La factura fue preparada para Clover. Configure Clover o anule "
                    "el plan de tarjeta antes de intentar un pago manual."
                ))
            provider_line = self._ddcl_get_provider_payment_line(provider)
            self.write({
                "journal_id": provider.journal_id.id,
                "payment_method_line_id": provider_line.id,
                "amount": self._ddcl_expected_amount(selected_card_invoice),
            })
        if not self.ddcl_clover_ecommerce_mode:
            return super().action_create_payments()
        invoice = self._ddcl_get_clover_invoice()
        provider = self.env["payment.provider"].sudo().browse(
            self.ddcl_clover_provider_id
        ).exists()
        if not provider:
            raise ValidationError(_("Clover no está configurado para esta compañía."))
        provider._ddcl_validate_ecommerce_configuration()
        # A journal can contain a similarly named manual line.  Force the
        # provider line in both the initial and post-approval paths so an
        # approved Clover operation always creates a normal posted payment.
        provider_line = self._ddcl_get_provider_payment_line(provider)
        if self.payment_method_line_id != provider_line:
            self.write({"payment_method_line_id": provider_line.id})
        if self.env.context.get("ddcl_bypass_checkout"):
            return super().action_create_payments()
        operation = self.env["doorandoor.clover.operation"].create({
            "reference": "%s-CLOVER-%s" % (invoice.name, self.env["ir.sequence"].next_by_code("doorandoor.clover.operation") or "NEW"),
            "invoice_id": invoice.id,
            "provider_id": provider.id,
            "amount": self.ddcl_collection_total_amount,
            "collection_base_amount": self.ddcl_collection_base_amount,
            "collection_fee_amount": self.ddcl_collection_fee_amount,
            "state": "pending",
            "is_mock": provider.ddcl_mock_mode,
            "payment_register_id": self.id,
            "idempotency_key": self.env["doorandoor.clover.operation"]._ddcl_new_idempotency_key(),
            "state_message": _("Operación creada; pendiente de formulario Clover."),
        })
        if provider.ddcl_mock_mode:
            return {
                "type": "ir.actions.act_window",
                "name": _("Pago con tarjeta - Clover (simulación)"),
                "res_model": "doorandoor.clover.checkout.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_operation_id": operation.id, "default_payment_register_id": self.id},
            }
        return {"type": "ir.actions.act_url", "url": "/payment/clover/verify/%s" % operation.id, "target": "self"}
