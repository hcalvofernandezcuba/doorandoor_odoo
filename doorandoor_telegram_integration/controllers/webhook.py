import json
import logging
import secrets

from odoo import _, fields, http
from odoo.exceptions import ValidationError
from odoo.http import Response, request


_logger = logging.getLogger(__name__)


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
        update_id = str(update.get("update_id") or "")
        update_model = request.env["doorandoor.telegram.update"].sudo()
        if update_id and update_model.search_count([
            ("bot_id", "=", bot.id), ("telegram_update_id", "=", update_id)
        ]):
            return self._response({"ok": True})
        if update_id:
            update_model.create({"bot_id": bot.id, "telegram_update_id": update_id})
        bot.last_webhook_at = fields.Datetime.now()
        try:
            if update.get("message"):
                self._handle_message(bot, update["message"], update)
            elif update.get("my_chat_member"):
                self._handle_membership(bot, update["my_chat_member"])
            elif update.get("callback_query"):
                self._handle_callback(bot, update["callback_query"])
        except Exception as error:
            _logger.exception("Error procesando evento Telegram para bot %s", bot.id)
            bot.last_error = str(error)
        return self._response({"ok": True})

    def _handle_message(self, bot, message, raw_update):
        chat = message.get("chat") or {}
        telegram_user = message.get("from") or {}
        chat_id = str(chat.get("id") or "")
        text = (message.get("text") or "").strip()
        if not chat_id:
            return
        link_model = request.env["doorandoor.telegram.user.link"].sudo()
        link = link_model.search([
            ("bot_id", "=", bot.id), ("telegram_chat_id", "=", chat_id)
        ], limit=1)
        request.env["doorandoor.telegram.message"].sudo().create({
            "bot_id": bot.id, "link_id": link.id,
            "direction": "incoming", "telegram_chat_id": chat_id,
            "telegram_message_id": str(message.get("message_id") or ""),
            "text": text, "raw_update": json.dumps(raw_update, ensure_ascii=False),
        })
        if text.startswith("/start link_"):
            token = text.split("/start link_", 1)[1].split()[0]
            try:
                link = request.env["doorandoor.telegram.activation"].sudo().consume(
                    bot, token, telegram_user, chat_id
                )
                bot.send_message(chat_id, _(
                    "Cuenta vinculada correctamente con %(user)s en DoorAndDoor. "
                    "Use /estado para comprobarla o /desvincular para retirarla."
                ) % {"user": link.user_id.name})
            except ValidationError as error:
                bot.send_message(chat_id, str(error))
            return
        if text.startswith("/estado"):
            if link and link.state == "active":
                bot.send_message(chat_id, _("Vínculo activo con el usuario Odoo: %s") % link.user_id.name)
            else:
                bot.send_message(chat_id, _("Esta cuenta Telegram no está vinculada con un usuario activo de Odoo."))
            return
        if text.startswith("/desvincular"):
            if link and link.state == "active":
                link.write({"state": "revoked", "revoked_at": fields.Datetime.now()})
                bot.send_message(chat_id, _("La cuenta Telegram fue desvinculada de DoorAndDoor."))
            else:
                bot.send_message(chat_id, _("No existe un vínculo activo para retirar."))
            return
        if not link or link.state != "active":
            bot.send_message(chat_id, _(
                "Para activar este bot, genere su enlace personal desde Odoo y pulse Iniciar."
            ))
        else:
            bot.send_message(chat_id, _(
                "Bot operativo de DoorAndDoor. Su cuenta está vinculada. Use /estado para consultar el vínculo."
            ))

    def _handle_membership(self, bot, membership):
        chat_id = str((membership.get("chat") or {}).get("id") or "")
        status = ((membership.get("new_chat_member") or {}).get("status") or "")
        link = request.env["doorandoor.telegram.user.link"].sudo().search([
            ("bot_id", "=", bot.id), ("telegram_chat_id", "=", chat_id)
        ], limit=1)
        if link and status in ("kicked", "left"):
            link.state = "blocked"
        elif link and status == "member" and link.state == "blocked":
            link.state = "active"

    def _handle_callback(self, bot, callback):
        callback_id = callback.get("id")
        if callback_id:
            bot._call_api("answerCallbackQuery", {
                "callback_query_id": callback_id,
                "text": _("Acción recibida. Esta primera versión solo admite consultas."),
            })

    @staticmethod
    def _response(payload, status=200):
        return Response(
            json.dumps(payload), status=status,
            headers=[("Content-Type", "application/json; charset=utf-8")],
        )
