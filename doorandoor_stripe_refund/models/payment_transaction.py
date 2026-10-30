from odoo import fields, models
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe.controllers.main import StripeController


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    ddsr_refund_request_id = fields.Many2one(
        "doorandoor.stripe.refund.request",
        string="Solicitud de devolución",
        readonly=True,
        copy=False,
        index=True,
    )

    def _send_refund_request(self, amount_to_refund=None):
        request = self.env.context.get("ddsr_refund_request")
        if self.provider_code != "stripe" or not request:
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        self.ensure_one()
        amount = amount_to_refund or self.amount
        refund_tx = self._create_child_transaction(amount, is_refund=True)
        refund_tx._log_sent_message()
        data = self.provider_id._stripe_make_request(
            "refunds",
            payload={
                "payment_intent": self.provider_reference,
                "amount": payment_utils.to_minor_currency_units(
                    amount,
                    refund_tx.currency_id,
                    arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(
                        refund_tx.currency_id.name
                    ),
                ),
                "metadata[doorandoor_refund_request]": request.name,
            },
            idempotency_key="doorandoor-refund-%s" % request.id,
        )
        notification_data = {}
        StripeController._include_refund_in_notification_data(data, notification_data)
        refund_tx._handle_notification_data("stripe", notification_data)
        return refund_tx

    def _post_process(self):
        result = super()._post_process()
        for transaction in self.filtered("ddsr_refund_request_id"):
            transaction.ddsr_refund_request_id._sync_from_transaction()
        return result
