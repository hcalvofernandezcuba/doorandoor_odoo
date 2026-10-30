from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddsr_stripe_payment_status = fields.Selection(
        selection=[
            ("waiting", "En proceso - esperando Stripe"),
            ("confirmed", "Confirmado por Stripe - contabilizando"),
            ("error", "Error o cancelación en Stripe"),
        ],
        string="Estado Stripe",
        compute="_compute_ddsr_stripe_payment_status",
    )

    @api.depends("transaction_ids.state", "payment_state")
    def _compute_ddsr_stripe_payment_status(self):
        for move in self:
            status = False
            transactions = move.transaction_ids.filtered(
                lambda tx: tx.provider_code == "stripe"
            )
            if move.payment_state not in ("paid", "in_payment") and transactions:
                if any(tx.state == "done" for tx in transactions):
                    status = "confirmed"
                elif any(tx.state in ("draft", "pending", "authorized") for tx in transactions):
                    status = "waiting"
                elif all(tx.state in ("cancel", "error") for tx in transactions):
                    status = "error"
            move.ddsr_stripe_payment_status = status
