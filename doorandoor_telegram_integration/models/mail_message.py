import re

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


TELEGRAM_COMMAND = re.compile(r"^/tg\s+([^:]+):\s*(.+)$", re.IGNORECASE | re.DOTALL)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        if self.env.context.get("ddtg_bridge_message"):
            return messages
        for message in messages:
            message._ddtg_route_channel_command()
        return messages

    def _ddtg_route_channel_command(self):
        self.ensure_one()
        if self.model != "discuss.channel" or not self.res_id or self.message_type != "comment":
            return False
        bot = self.env["doorandoor.telegram.bot"].sudo().search([
            ("support_channel_id", "=", self.res_id),
            ("state", "=", "running"), ("active", "=", True),
        ], limit=1)
        if not bot:
            return False
        text = (html2plaintext(self.body or "") or "").strip()
        match = TELEGRAM_COMMAND.match(text)
        if not match:
            return False
        recipient, outgoing_text = match.groups()
        link = bot._find_support_link(recipient)
        if not link:
            raise UserError(_(
                "No existe un vínculo Telegram activo y único para '%s'. "
                "Revise Administración → Usuarios vinculados."
            ) % recipient.strip())
        result = bot.send_message(link.telegram_chat_id, outgoing_text.strip())
        self.env["doorandoor.telegram.message"].sudo().create({
            "bot_id": bot.id, "link_id": link.id, "direction": "outgoing",
            "telegram_chat_id": link.telegram_chat_id,
            "telegram_message_id": str((result or {}).get("message_id") or ""),
            "text": outgoing_text.strip(),
        })
        return True
