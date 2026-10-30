from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    ddsr_operational_state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("in_process", "En proceso"),
            ("paid", "Pagado"),
            ("canceled", "Cancelado"),
            ("rejected", "Rechazado"),
            ("credit_available", "Crédito disponible"),
            ("credit_partial", "Crédito parcialmente usado"),
            ("credit_consumed", "Crédito consumido"),
        ],
        string="Estado",
        compute="_compute_ddsr_operational_state",
    )

    @api.depends("state", "move_id.line_ids.amount_residual")
    def _compute_ddsr_operational_state(self):
        """Show the business outcome without changing Odoo's payment lifecycle."""
        transfer_model = self.env["account.move"].sudo()
        for payment in self:
            display_state = payment.state
            transfers = transfer_model.search(
                [
                    ("ddc_credit_origin_payment_id", "=", payment.id),
                    ("state", "=", "posted"),
                ]
            )
            credit_lines = transfers.line_ids.filtered(
                lambda line: line.credit > 0
                and line.account_id.code
                and line.account_id.code.startswith("1200")
                and line.account_id.code != "120000"
            )
            if credit_lines:
                original_amount = sum(credit_lines.mapped("credit"))
                available_amount = max(-sum(credit_lines.mapped("amount_residual")), 0.0)
                if payment.currency_id.is_zero(available_amount):
                    display_state = "credit_consumed"
                elif payment.currency_id.compare_amounts(
                    available_amount, original_amount
                ) < 0:
                    display_state = "credit_partial"
                else:
                    display_state = "credit_available"
            payment.ddsr_operational_state = display_state
