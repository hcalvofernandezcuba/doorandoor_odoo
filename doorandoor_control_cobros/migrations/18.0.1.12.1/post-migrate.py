from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].sudo().search([], order="id")
    mother_account = env["account.account"]
    for source_company in companies:
        mother_account = env["account.account"].sudo().with_company(source_company).search(
            [("code", "=", "120000"), ("company_ids", "in", source_company.id)],
            order="id",
            limit=1,
        )
        if mother_account:
            break
    if not mother_account:
        return

    for company in companies:
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
        if not env["account.move"].search_count(
            [("ddc_credit_origin_payment_id", "=", payment.id), ("state", "!=", "cancel")]
        ):
            payment._ddc_transfer_open_credit_to_advance(control)
        processed_payments |= payment
