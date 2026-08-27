from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    mother_account = env["account.account"]
    for source_company in env["res.company"].sudo().search([], order="id"):
        mother_account = env["account.account"].sudo().with_company(source_company).search(
            [("code", "=", "120000"), ("company_ids", "in", source_company.id)],
            order="id",
            limit=1,
        )
        if mother_account:
            break
    if mother_account:
        for company in env["res.company"].sudo().search([]):
            if company not in mother_account.company_ids:
                mother_account.write({"company_ids": [(4, company.id)]})
            mother_account.with_company(company).code = "120000"
    controls = env["doorandoor.cobro.control"].sudo().search(
        [
            ("state", "=", "validated"),
            ("payment_id", "!=", False),
            ("source_type", "!=", "customer_credit"),
            ("active", "=", True),
        ],
        order="id",
    )
    processed_payments = env["account.payment"]
    for control in controls:
        payment = control.payment_id
        if payment in processed_payments or not payment.move_id:
            continue
        advance_account = env["account.account"].sudo().with_company(payment.company_id).search(
            [("code", "=", "120000"), ("company_ids", "in", payment.company_id.id)], limit=1
        )
        if not advance_account:
            continue
        already_transferred = env["account.move"].search_count(
            [("ddc_credit_origin_payment_id", "=", payment.id), ("state", "!=", "cancel")]
        )
        if already_transferred:
            processed_payments |= payment
            continue
        payment._ddc_transfer_open_credit_to_advance(control)
        processed_payments |= payment
