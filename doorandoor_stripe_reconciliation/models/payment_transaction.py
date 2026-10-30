from odoo import _, fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _create_payment(self, **extra_create_values):
        self.ensure_one()
        paid_invoices = self.invoice_ids.filtered(
            lambda invoice: invoice.state == "posted"
            and invoice.payment_state in ("paid", "in_payment")
        )
        if (
            self.provider_code == "stripe"
            and self.amount > 0
            and self.invoice_ids
            and paid_invoices == self.invoice_ids
        ):
            payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids.filtered(
                lambda line: line.payment_provider_id == self.provider_id
            )[:1]
            receivable_lines = self.invoice_ids.line_ids.filtered(
                lambda line: line.display_type == "payment_term"
            )
            if not payment_method_line or not receivable_lines:
                return super()._create_payment(**extra_create_values)
            payment = self.env["account.payment"].create({
                "amount": abs(self.amount),
                "payment_type": "inbound",
                "currency_id": self.currency_id.id,
                "partner_id": self.partner_id.commercial_partner_id.id,
                "partner_type": "customer",
                "journal_id": self.provider_id.journal_id.id,
                "company_id": self.provider_id.company_id.id,
                "payment_method_line_id": payment_method_line.id,
                "payment_transaction_id": self.id,
                "memo": _("Crédito por cobro Stripe duplicado - %(provider)s") % {
                    "provider": self.provider_reference or "sin referencia",
                },
                "destination_account_id": receivable_lines[0].account_id.id,
                "invoice_ids": [(5, 0, 0)],
                **extra_create_values,
            })
            payment.action_post()
            self.payment_id = payment
            control = self.env["doorandoor.cobro.control"].sudo().create({
                "move_id": paid_invoices[0].id,
                "partner_id": self.partner_id.commercial_partner_id.id,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "journal_id": self.provider_id.journal_id.id,
                "payment_id": payment.id,
                "payment_date": fields.Date.context_today(self),
                "amount_reported": self.amount,
                "validated_amount": self.amount,
                "payment_reference": self.provider_reference or self.reference,
                "source_type": "accounting_detected",
                "state": "validated",
                "accountant_user_id": self.env.user.id,
                "review_date": fields.Datetime.now(),
                "notes": _(
                    "Cobro Stripe duplicado convertido automáticamente en crédito disponible."
                ),
            })
            payment._ddc_transfer_open_credit_to_advance(control)
            self.invoice_ids.message_post(
                body=_(
                    "Stripe confirmó un cobro adicional de %(amount)s. Como la factura ya "
                    "estaba pagada, se registró como crédito disponible del cliente (%(payment)s)."
                ) % {
                    "amount": self.currency_id.format(self.amount),
                    "payment": payment.display_name,
                }
            )
            return payment
        return super()._create_payment(**extra_create_values)

    def _post_process(self):
        result = super()._post_process()
        self._ddsr_validate_stripe_po_payments()
        return result

    def _ddsr_validate_stripe_po_payments(self):
        """Turn a confirmed Stripe payment for one PO into validated control."""
        if "ddsn_po_first_flow" not in self.env["sale.order"]._fields:
            return True

        controls = self.env["doorandoor.cobro.control"]
        for transaction in self.filtered(
            lambda tx: tx.provider_code == "stripe"
            and tx.state == "done"
            and tx.payment_id
        ):
            orders = transaction.sale_order_ids.filtered("ddsn_po_first_flow")
            if not orders:
                continue
            if len(orders) != 1:
                transaction._log_message_on_linked_documents(
                    _(
                        "El cobro Stripe no se validó automáticamente porque "
                        "incluye más de un PO."
                    )
                )
                continue

            order = orders.ensure_one()
            existing = controls.search(
                [
                    ("payment_id", "=", transaction.payment_id.id),
                    ("sale_order_id", "=", order.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if existing:
                continue

            control = controls.sudo().create(
                {
                    "sale_order_id": order.id,
                    "partner_id": order.partner_id.commercial_partner_id.id,
                    "currency_id": transaction.currency_id.id,
                    "company_id": transaction.company_id.id,
                    "journal_id": transaction.provider_id.journal_id.id,
                    "payment_id": transaction.payment_id.id,
                    "payment_date": fields.Date.context_today(transaction),
                    "amount_reported": transaction.amount,
                    "validated_amount": transaction.amount,
                    "payment_reference": transaction.reference,
                    "source_type": "accounting_detected",
                    "state": "validated",
                    "accountant_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                    "notes": _(
                        "Validado automáticamente por webhook Stripe; "
                        "el diario está configurado como vía inmediata."
                    ),
                }
            )
            order.invalidate_recordset(
                ["ddc_po_amount_validated", "ddc_po_control_count"]
            )
            if order.currency_id.compare_amounts(
                order.ddc_po_amount_validated, order.amount_total
            ) >= 0:
                preinvoice = order.ddsn_preinvoice_move_id
                if preinvoice:
                    preinvoice.sudo()._ddsn_create_supply_transfers_from_preinvoice(
                        preinvoice
                    )
            order.message_post(
                body=_(
                    "Cobro Stripe %(reference)s validado automáticamente por %(amount)s."
                )
                % {
                    "reference": transaction.reference,
                    "amount": transaction.currency_id.format(transaction.amount),
                }
            )
        return True
