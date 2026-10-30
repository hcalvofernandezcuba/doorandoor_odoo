from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelpdeskRequiredAction(TransactionCase):
    def setUp(self):
        super().setUp()
        self.requester = self.env["res.users"].create({
            "name": "Usuario solicitante",
            "login": "helpdesk.requester@example.test",
        })
        self.ticket = self.env["doorandoor.helpdesk.ticket"].create({
            "title": "Cambio de ubicación en conteo inicial",
            "description": "El lote requiere confirmación física.",
            "requester_id": self.requester.id,
            "assigned_user_id": self.env.user.id,
            "affected_area": "inventory",
        })
        self.ticket.action_start_analysis()

    def test_waiting_requires_explicit_user_action(self):
        with self.assertRaises(UserError):
            self.ticket.action_waiting()

    def test_required_action_is_notified_and_cleared_when_resolved(self):
        instruction = (
            "Escanee nuevamente el lote y confirme la ubicación física 15A1."
        )
        self.ticket.write({"required_action": instruction})
        self.ticket.action_waiting()

        self.assertEqual(self.ticket.state, "waiting")
        self.assertTrue(self.ticket.user_action_required)
        notification = self.ticket.message_ids.filtered(
            lambda message: instruction in (message.body or "")
        )
        self.assertTrue(notification)
        self.assertIn(
            self.requester.partner_id,
            notification[:1].notified_partner_ids,
        )

        self.ticket.action_resolve()
        self.assertEqual(self.ticket.state, "resolved")
        self.assertFalse(self.ticket.user_action_required)
        self.assertEqual(self.ticket.required_action, instruction)
