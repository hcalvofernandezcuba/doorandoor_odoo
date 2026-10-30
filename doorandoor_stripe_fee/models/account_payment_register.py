from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ddtp_card_fee_rate = fields.Float(
        string="Cargo por procesamiento (%)", compute="_compute_ddtp_card_fee", readonly=True
    )
    ddtp_card_fee_rate_display = fields.Char(
        string="Cargo por procesamiento visible", compute="_compute_ddtp_card_fee", readonly=True
    )
    ddtp_card_fee_amount = fields.Monetary(
        string="Cargo por procesamiento", compute="_compute_ddtp_card_fee", currency_field="currency_id", readonly=True
    )
    ddtp_card_total_amount = fields.Monetary(
        string="Total a cobrar con tarjeta", compute="_compute_ddtp_card_fee", currency_field="currency_id", readonly=True
    )

    @api.model
    def _ddtp_format_percent(self, rate):
        text = ("%.10f" % (rate or 0.0)).rstrip("0").rstrip(".")
        return text.replace(".", ",")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        invoice_ids = self.env.context.get("active_ids", [])
        # A browser can retain an obsolete active id after an invoice was
        # deleted in a previous tab.  Ignore it instead of blocking every
        # subsequent payment-register action with a MissingError.
        invoices = self.env["account.move"].browse(invoice_ids).exists().filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) == 1:
            amount = self._ddtp_expected_card_amount(invoices)
            if amount is not None:
                # ``amount`` is a computed standard field.  Supplying the
                # same value here also prevents the wizard from briefly
                # rendering the entire invoice residual while it loads.
                values["amount"] = amount
                values["custom_user_amount"] = amount
        return values

    @api.model
    def _ddtp_expected_card_amount(self, invoice):
        """Return the amount for the current card collection, if planned.

        The fee technical line is already included in the invoice receivable.
        Before its first collection we must therefore charge only the agreed
        deposit plus its fee, never the full invoice residual.  Once that
        collection has been reconciled, the normal outstanding balance remains
        editable for the next payment.
        """
        invoice.ensure_one()
        if not invoice.ddtp_card_fee_line_id:
            return None
        first_total = invoice.currency_id.round(
            invoice.ddtp_card_payment_amount + invoice.ddtp_card_fee_amount
        )
        # The original receivable contains the commercial total plus the fee.
        # For a full collection it equals ``first_total`` exactly; this is
        # still the first card payment and must not fall back to a manual
        # journal. A later installment already has a registered payment.
        is_first_collection = not invoice.payment_ids
        if (
            invoice.currency_id.compare_amounts(invoice.amount_residual, first_total) > 0
            or (
                is_first_collection
                and invoice.currency_id.compare_amounts(invoice.amount_residual, first_total) == 0
            )
        ):
            return first_total
        return None

    @api.depends(
        "can_edit_wizard", "source_amount", "source_amount_currency",
        "source_currency_id", "company_id", "currency_id", "payment_date",
        "installments_mode", "line_ids",
    )
    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self:
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            if len(invoices) == 1:
                amount = wizard._ddtp_expected_card_amount(invoices)
                if amount is not None:
                    wizard.amount = amount

    @api.depends("amount", "currency_id", "ddsr_stripe_checkout_mode", "journal_id")
    def _compute_ddtp_card_fee(self):
        providers = self.env["payment.provider"].sudo().search([
            ("code", "=", "stripe"), ("state", "in", ("test", "enabled")),
        ])
        for wizard in self:
            invoices = wizard.line_ids.move_id.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            planned_invoice = invoices[:1] if len(invoices) == 1 else self.env["account.move"]
            planned_amount = (
                wizard._ddtp_expected_card_amount(planned_invoice)
                if planned_invoice else None
            )
            if planned_amount is not None:
                wizard.ddtp_card_fee_rate = provider_rate = 0.0
                wizard.ddtp_card_fee_rate_display = wizard._ddtp_format_percent(provider_rate)
                wizard.ddtp_card_fee_amount = planned_invoice.ddtp_card_fee_amount
                wizard.ddtp_card_total_amount = planned_amount
                continue
            provider = providers.filtered(lambda item: item.journal_id == wizard.journal_id)[:1]
            rate = provider.ddtp_card_fee_rate if wizard.ddsr_stripe_checkout_mode and provider else 0.0
            wizard.ddtp_card_fee_rate = rate
            wizard.ddtp_card_fee_rate_display = wizard._ddtp_format_percent(rate)
            wizard.ddtp_card_fee_amount = wizard.currency_id.round(wizard.amount * rate / 100.0)
            wizard.ddtp_card_total_amount = wizard.amount + wizard.ddtp_card_fee_amount

    def action_create_payments(self):
        self.ensure_one()
        if not self.ddsr_stripe_checkout_mode:
            return super().action_create_payments()
        return self._ddtp_open_card_checkout()

    def _ddtp_get_provider_and_invoice(self):
        invoices = self.line_ids.move_id.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        if len(invoices) != 1:
            raise ValidationError(_("El pago con tarjeta requiere seleccionar una sola factura publicada."))
        invoice = invoices.ensure_one()
        provider = self.env["payment.provider"].sudo().search([
            ("code", "=", "stripe"),
            ("state", "in", ("test", "enabled")),
            ("company_id", "=", invoice.company_id.id),
        ]).filtered(lambda item: item.journal_id == self.journal_id)[:1]
        if not provider:
            raise ValidationError(_("El diario seleccionado no tiene pagos con tarjeta activos."))
        provider._ddtp_validate_card_fee_configuration()
        if self.amount <= 0 or self.currency_id.compare_amounts(self.amount, invoice.amount_residual) > 0:
            raise ValidationError(_("El importe debe ser mayor que cero y no puede superar el saldo pendiente."))
        expected = self._ddtp_expected_card_amount(invoice)
        if expected is not None:
            if self.currency_id.compare_amounts(self.amount, expected) != 0:
                raise ValidationError(
                    _("Esta factura fue preparada para un cobro con tarjeta de %(amount)s, incluido su cargo.")
                    % {"amount": self.currency_id.format(expected)}
                )
        return provider, invoice

    def _ddtp_create_fee_invoice(self, invoice, provider):
        fee_amount = self.currency_id.round(self.amount * provider.ddtp_card_fee_rate / 100.0)
        if not fee_amount:
            return self.env["account.move"]
        product = provider.ddtp_card_fee_product_id
        fee_invoice = self.env["account.move"].with_company(invoice.company_id).create({
            "move_type": "out_invoice",
            "partner_id": invoice.partner_id.id,
            "invoice_user_id": invoice.invoice_user_id.id,
            "currency_id": invoice.currency_id.id,
            "invoice_origin": invoice.name,
            "ref": _("Pago con tarjeta - %(invoice)s") % {"invoice": invoice.name},
            "ddtp_origin_invoice_id": invoice.id,
            "ddtp_is_card_fee_invoice": True,
            "invoice_line_ids": [(0, 0, {
                "product_id": product.id,
                "name": _("Cargo por procesamiento de pago con tarjeta - %(rate)s%%") % {
                    "rate": provider.ddtp_card_fee_rate,
                },
                "quantity": 1,
                # The surcharge is calculated over an amount that already
                # includes the sale taxes. It must remain exactly the agreed
                # percentage and cannot inherit product taxes by accident.
                "tax_ids": [(5, 0, 0)],
            })],
        })
        # Some product customizations restore the standard product price while
        # creating invoice lines.  Set the computed surcharge only after the
        # line exists so that the posted document always matches the checkout.
        fee_invoice.invoice_line_ids.write({
            "price_unit": fee_amount,
            "tax_ids": [(5, 0, 0)],
        })
        fee_invoice.action_post()
        fee_invoice.message_post(
            body=_("Documento complementario creado para el cobro con tarjeta de %(amount)s sobre %(invoice)s.")
            % {"amount": self.currency_id.format(self.amount), "invoice": invoice.name}
        )
        return fee_invoice

    def _ddtp_open_card_checkout(self):
        provider, invoice = self._ddtp_get_provider_and_invoice()
        card = provider.payment_method_ids.filtered(lambda method: method.code == "card")[:1]
        if not card:
            raise ValidationError(_("El proveedor no tiene habilitado el método Tarjeta."))

        linked_invoices = invoice
        first_collection_amount = self._ddtp_expected_card_amount(invoice)
        # The first fee was inserted in the draft invoice as a technical
        # receivable line.  Any later card collection has to recover its own
        # fee in the payment journal, otherwise Odoo would treat it as a
        # customer credit when reconciling the remaining invoice balance.
        subsequent_fee = (
            self.ddtp_card_fee_amount if first_collection_amount is None else 0.0
        )
        fee_account = self.env["account.account"]
        if subsequent_fee:
            fee_product = provider.ddtp_card_fee_product_id
            fee_account = (
                fee_product.property_account_income_id
                or fee_product.categ_id.property_account_income_categ_id
            )
            if not fee_account:
                raise ValidationError(_(
                    "Configure una cuenta de ingresos para el cargo por pago con tarjeta."
                ))
        transaction = self.env["payment.transaction"].sudo().create({
            "provider_id": provider.id,
            "payment_method_id": card.id,
            "reference": self.env["payment.transaction"]._compute_reference(
                "stripe", prefix=invoice.name
            ),
            "amount": self.ddtp_card_total_amount,
            "currency_id": self.currency_id.id,
            "partner_id": invoice.commercial_partner_id.id,
            "operation": "online_direct",
            "invoice_ids": [(6, 0, linked_invoices.ids)],
            "landing_route": f"/web#id={invoice.id}&model=account.move&view_type=form",
            "ddtp_origin_invoice_id": invoice.id,
            "ddtp_fee_invoice_id": False,
            "ddtp_collection_base_amount": self.amount,
            "ddtp_collection_fee_amount": subsequent_fee,
            "ddtp_collection_fee_account_id": fee_account.id,
        })
        base_url = provider.get_base_url().rstrip("/") + "/"
        invoice_url = urljoin(base_url, f"web#id={invoice.id}&model=account.move&view_type=form")
        payload = {
            "mode": "payment",
            "success_url": invoice_url,
            "cancel_url": invoice_url,
            "line_items[0][price_data][currency]": self.currency_id.name.lower(),
            "line_items[0][price_data][unit_amount]": int(round(self.ddtp_card_total_amount * 100)),
            "line_items[0][price_data][product_data][name]": _("Pago con tarjeta"),
            "line_items[0][quantity]": 1,
            "payment_intent_data[description]": _("Pago con tarjeta - %(invoice)s") % {"invoice": invoice.name},
            "metadata[odoo_reference]": transaction.reference,
            "payment_intent_data[metadata][odoo_reference]": transaction.reference,
        }
        if invoice.partner_id.email:
            payload["customer_email"] = invoice.partner_id.email
        try:
            session = provider._stripe_make_request("checkout/sessions", payload=payload)
        except Exception:
            raise
        checkout_url = session.get("url")
        if not checkout_url:
            raise ValidationError(_("El proveedor no devolvió la URL del formulario de pago."))
        transaction._set_pending(state_message=_("Esperando que el cliente complete el pago con tarjeta."))
        transaction._log_sent_message()
        return {"type": "ir.actions.act_url", "url": checkout_url, "target": "self"}
