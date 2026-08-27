from odoo import SUPERUSER_ID, api, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    control_model = env["doorandoor.cobro.control"].sudo()
    invoices = env["account.move"].sudo().search(
        [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "in_payment"),
            ("amount_residual", "=", 0.0),
            ("ddc_control_ids", "=", False),
        ]
    )

    for invoice in invoices:
        applied_by_line = {}
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        for invoice_line in receivable_lines:
            for partial in invoice_line.matched_credit_ids:
                payment_line = partial.credit_move_id
                if payment_line.payment_id:
                    applied_by_line[payment_line] = applied_by_line.get(payment_line, 0.0) + partial.amount
            for partial in invoice_line.matched_debit_ids:
                payment_line = partial.debit_move_id
                if payment_line.payment_id:
                    applied_by_line[payment_line] = applied_by_line.get(payment_line, 0.0) + partial.amount

        for payment_line, applied_amount in applied_by_line.items():
            payment = payment_line.payment_id
            if control_model.search_count(
                [
                    ("payment_id", "=", payment.id),
                    ("move_id", "=", invoice.id),
                    ("active", "=", True),
                    ("state", "!=", "rejected"),
                ]
            ):
                continue
            origin_control = control_model.search(
                [
                    ("payment_id", "=", payment.id),
                    ("state", "=", "validated"),
                    ("active", "=", True),
                    ("move_id", "!=", invoice.id),
                ],
                order="id asc",
                limit=1,
            )
            if not origin_control or invoice.currency_id.is_zero(applied_amount):
                continue

            credit_after = abs(payment_line.amount_residual_currency or payment_line.amount_residual)
            credit_before = credit_after + applied_amount
            control_model.create(
                {
                    "move_id": invoice.id,
                    "partner_id": invoice.partner_id.id,
                    "currency_id": invoice.currency_id.id,
                    "company_id": invoice.company_id.id,
                    "journal_id": payment.journal_id.id,
                    "payment_id": payment.id,
                    "sale_user_id": env.user.id,
                    "accountant_user_id": env.user.id,
                    "payment_date": fields.Date.context_today(invoice),
                    "amount_reported": applied_amount,
                    "validated_amount": applied_amount,
                    "payment_reference": payment.payment_reference or payment.memo,
                    "state": "validated",
                    "source_type": "customer_credit",
                    "invoice_residual_snapshot": applied_amount,
                    "review_date": fields.Datetime.now(),
                    "credit_origin_control_id": origin_control.id,
                    "credit_balance_before": credit_before,
                    "credit_applied_amount": applied_amount,
                    "credit_balance_after": credit_after,
                    "notes": (
                        "Control reconstruido al actualizar el modulo para documentar "
                        f"la aplicacion de credito procedente de {origin_control.name}."
                    ),
                }
            )
        if applied_by_line:
            invoice._ddc_refresh_control_status()
