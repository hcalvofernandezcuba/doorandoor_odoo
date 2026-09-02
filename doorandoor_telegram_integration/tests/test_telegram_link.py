from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDoorandoorTelegramLink(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bot = cls.env["doorandoor.telegram.bot"].create({
            "name": "DoorAndDoor Operaciones Local",
            "environment": "local",
            "company_id": cls.env.company.id,
            "public_base_url": "https://local-tunnel.example",
            "username": "doorandoor_operaciones_local_bot",
            "state": "running",
        })

    def test_one_time_activation_links_odoo_user(self):
        activation, raw_token = self.env["doorandoor.telegram.activation"].generate_for_user(
            self.bot, self.env.user
        )
        self.assertNotEqual(activation.token_digest, raw_token)
        self.assertNotIn(raw_token, activation.token_digest)
        link = self.env["doorandoor.telegram.activation"].consume(
            self.bot, raw_token,
            {"id": 123456, "username": "usuario_prueba", "first_name": "Usuario", "language_code": "es"},
            123456,
        )
        self.assertEqual(link.user_id, self.env.user)
        self.assertEqual(link.state, "active")
        self.assertEqual(activation.state, "used")
        with self.assertRaises(ValidationError):
            self.env["doorandoor.telegram.activation"].consume(
                self.bot, raw_token, {"id": 123456}, 123456
            )

    def test_notification_queue_logs_delivery(self):
        _activation, raw_token = self.env["doorandoor.telegram.activation"].generate_for_user(
            self.bot, self.env.user
        )
        link = self.env["doorandoor.telegram.activation"].consume(
            self.bot, raw_token, {"id": 987654, "username": "cola_prueba"}, 987654
        )
        notification = self.env["doorandoor.telegram.notification"].create({
            "bot_id": self.bot.id, "link_id": link.id,
            "event_type": "manufacturing", "message": "OF lista para revisión",
        })
        with patch.object(type(self.bot), "send_message", return_value={"message_id": 42}):
            notification._send_one()
        self.assertEqual(notification.state, "sent")
        self.assertEqual(notification.telegram_message_id, "42")
        self.assertTrue(notification.env["doorandoor.telegram.message"].search([
            ("notification_id", "=", notification.id), ("direction", "=", "outgoing")
        ]))
