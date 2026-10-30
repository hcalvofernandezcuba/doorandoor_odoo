import json
import secrets

from odoo import http
from odoo.http import Response, request


class DoorandoorTelegramWebhookController(http.Controller):

    @http.route(
        "/doorandoor/telegram/webhook/<string:endpoint_key>",
        type="http", auth="none", methods=["POST"], csrf=False, save_session=False,
    )
    def telegram_webhook(self, endpoint_key, **kwargs):
        bot = request.env["doorandoor.telegram.bot"].sudo().search([
            ("endpoint_key", "=", endpoint_key), ("state", "=", "running"), ("active", "=", True)
        ], limit=1)
        if not bot:
            return self._response({"ok": False}, status=404)
        received_secret = request.httprequest.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not bot.webhook_secret or not secrets.compare_digest(received_secret, bot.webhook_secret):
            return self._response({"ok": False}, status=403)
        try:
            update = json.loads(request.httprequest.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._response({"ok": False}, status=400)
        try:
            bot.process_update(update)
        except Exception as error:  # Telegram debe recibir 200 para no repetir indefinidamente.
            bot.last_error = str(error)
        return self._response({"ok": True})

    @staticmethod
    def _response(payload, status=200):
        return Response(
            json.dumps(payload), status=status,
            headers=[("Content-Type", "application/json; charset=utf-8")],
        )
