from markupsafe import Markup

from odoo import _
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        self.ensure_one()
        controlled_journal = self.journal_id.ddc_requires_payment_control
        payments = super(
            AccountPaymentRegister,
            self.with_context(ddc_skip_release_sync=controlled_journal),
        )._create_payments()

        if controlled_journal:
            self._ddc_create_payment_controls(payments)

        return payments

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
        return amount_map
