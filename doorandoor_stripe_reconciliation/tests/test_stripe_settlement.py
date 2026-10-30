from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestStripeSettlement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.ref("base.USD")
        cls.company = cls.env.company
        cls.company.currency_id = cls.currency
        cls.provider = cls.env["payment.provider"].search([("code", "=", "stripe")], limit=1)
        cls.provider.write(
            {
                "company_id": cls.company.id,
                "state": "disabled",
                "stripe_secret_key": "sk_test_fake",
                "stripe_publishable_key": "pk_test_fake",
            }
        )

    def test_sync_is_idempotent_and_computes_totals(self):
        responses = {
            "payouts": {
                "data": [
                    {
                        "id": "po_test_1",
                        "amount": 9700,
                        "currency": "usd",
                        "status": "paid",
                        "created": 1704067200,
                        "arrival_date": 1704153600,
                        "description": "TEST PAYOUT",
                    }
                ],
                "has_more": False,
            },
            "balance_transactions": {
                "data": [
                    {
                        "id": "txn_test_1",
                        "source": "pi_test_1",
                        "type": "charge",
                        "description": "Test charge",
                        "available_on": 1704153600,
                        "amount": 10000,
                        "fee": 300,
                        "net": 9700,
                    }
                ],
                "has_more": False,
            },
        }

        def fake_request(record, endpoint, **kwargs):
            return responses[endpoint]

        with patch.object(type(self.provider), "_stripe_make_request", autospec=True, side_effect=fake_request):
            self.provider.action_ddsr_sync_settlements()
            self.provider.action_ddsr_sync_settlements()

        settlement = self.env["doorandoor.stripe.settlement"].search(
            [("stripe_payout_id", "=", "po_test_1")]
        )
        self.assertEqual(len(settlement), 1)
        self.assertEqual(len(settlement.line_ids), 1)
        self.assertEqual(settlement.gross_amount, 100)
        self.assertEqual(settlement.fee_amount, 3)
        self.assertEqual(settlement.net_amount, 97)
        self.assertEqual(settlement.difference_amount, 0)

    def test_prepare_journal_is_idempotent_and_keeps_provider_disabled(self):
        original_account = self.env["account.account"].search(
            [("company_ids", "in", self.company.id)], limit=1
        )
        generic_journal = self.env["account.journal"].create(
            {
                "name": "Generic Bank Test",
                "code": "GBT1",
                "type": "bank",
                "company_id": self.company.id,
                "default_account_id": original_account.id,
                "ddc_payment_flow": "immediate",
            }
        )
        self.provider.journal_id = generic_journal
        self.provider.action_ddsr_prepare_payment_journal()
        journal = self.provider.journal_id
        account = journal.default_account_id
        self.provider.action_ddsr_prepare_payment_journal()

        self.assertEqual(self.provider.state, "disabled")
        self.assertEqual(self.provider.journal_id, journal)
        self.assertEqual(journal.code, "STRP")
        self.assertEqual(journal.ddc_payment_flow, "immediate")
        self.assertFalse(journal.ddc_requires_payment_control)
        self.assertTrue(account.reconcile)
        stripe_line = journal.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id.code == "stripe"
        )
        self.assertTrue(stripe_line)
        self.assertEqual(stripe_line.payment_account_id, account)
        self.assertEqual(generic_journal.default_account_id, original_account)
