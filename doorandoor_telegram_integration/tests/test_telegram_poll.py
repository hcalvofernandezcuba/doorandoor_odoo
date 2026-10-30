import base64
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDoorandoorTelegramPoll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bot = cls.env["doorandoor.telegram.bot"].create({
            "name": "Bot local de aprobaciones",
            "environment": "local",
            "company_id": cls.env.company.id,
            "public_base_url": "https://local-tunnel.example",
            "username": "doorandoor_local_bot",
            "state": "running",
        })
        cls.link = cls.env["doorandoor.telegram.user.link"].create({
            "bot_id": cls.bot.id,
            "user_id": cls.env.user.id,
            "telegram_user_id": "123456",
            "telegram_chat_id": "123456",
            "telegram_username": "direccion",
            "state": "active",
        })
        pixel = base64.b64encode(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        cls.poll = cls.env["doorandoor.telegram.poll"].create({
            "name": "Logo maestro",
            "description": "Seleccione la identidad visual oficial.",
            "bot_id": cls.bot.id,
            "voter_ids": [(6, 0, cls.env.user.ids)],
            "option_ids": [
                (0, 0, {"name": "Variante 1", "image": pixel}),
                (0, 0, {"name": "Variante 2", "image": pixel}),
            ],
        })

    def test_send_and_change_vote(self):
        with patch.object(type(self.bot), "send_message", return_value={"message_id": 1}), \
             patch.object(type(self.bot), "send_photo", return_value={"message_id": 2}):
            self.poll.action_open_and_send()
        self.assertEqual(self.poll.state, "open")
        first, second = self.poll.option_ids
        self.poll.register_telegram_vote(first, "123456")
        self.assertEqual(self.poll.vote_count, 1)
        self.poll.register_telegram_vote(second, "123456")
        self.assertEqual(len(self.poll.vote_ids), 1)
        self.assertEqual(self.poll.vote_ids.option_id, second)

    def test_rejects_unauthorized_telegram_user(self):
        self.poll.state = "open"
        with self.assertRaises(ValidationError):
            self.poll.register_telegram_vote(self.poll.option_ids[0], "999999")
