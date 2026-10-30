import json
import logging
import os
import secrets
from urllib.parse import urljoin

import requests
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"
_logger = logging.getLogger(__name__)


class DoorandoorTelegramBot(models.Model):
    _name = "doorandoor.telegram.bot"
    _description = "Bot Telegram DoorAndDoor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "company_id, name"
    _check_company_auto = True

    name = fields.Char(string="Nombre", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    environment = fields.Selection(
        [("local", "Local"), ("testing", "Pruebas"), ("production", "Producción")],
        string="Instancia", required=True, default="local", tracking=True,
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [("draft", "Borrador"), ("validated", "Validado"),
         ("running", "Activo"), ("stopped", "Detenido"), ("error", "Error")],
        default="draft", required=True, tracking=True,
    )
    delivery_mode = fields.Selection(
        [("webhook", "Webhook HTTPS"), ("polling", "Consulta automática (Local)")],
        string="Recepción", required=True, default="webhook", tracking=True,
    )
    update_offset = fields.Integer(string="Última actualización Telegram", default=0, readonly=True, copy=False)
    token_source = fields.Selection(
        [("environment", "Variable de entorno"), ("database", "Base de datos")],
        string="Origen del token", required=True, default="environment",
    )
    token_env_var = fields.Char(
        string="Variable del token", default="DOORANDOOR_TELEGRAM_BOT_TOKEN",
        help="Nombre de la variable de entorno disponible dentro del contenedor Odoo.",
    )
    token = fields.Char(
        string="Token", copy=False, groups="doorandoor_telegram_integration.group_ddtg_manager",
        help="Solo para desarrollo. Se recomienda usar una variable de entorno.",
    )
    username = fields.Char(string="Usuario del bot", readonly=True, copy=False, tracking=True)
    telegram_bot_id = fields.Char(string="ID Telegram", readonly=True, copy=False)
    public_base_url = fields.Char(
        string="URL HTTPS pública", required=True,
        help="URL externa que Telegram puede alcanzar, sin ruta final. En local debe ser un túnel HTTPS.",
    )
    endpoint_key = fields.Char(
        string="Clave de ruta", required=True, readonly=True, copy=False,
        default=lambda self: secrets.token_urlsafe(24), groups="doorandoor_telegram_integration.group_ddtg_manager",
    )
    webhook_secret = fields.Char(
        string="Secreto webhook", readonly=True, copy=False,
        groups="doorandoor_telegram_integration.group_ddtg_manager",
    )
    webhook_url = fields.Char(string="Webhook", compute="_compute_webhook_url")
    last_error = fields.Text(string="Último error", readonly=True, copy=False)
    last_webhook_at = fields.Datetime(string="Último evento", readonly=True, copy=False)
    link_ids = fields.One2many("doorandoor.telegram.user.link", "bot_id", string="Usuarios vinculados")
    link_count = fields.Integer(compute="_compute_counts", string="Usuarios")
    notification_count = fields.Integer(compute="_compute_counts", string="Notificaciones")
    poll_count = fields.Integer(compute="_compute_counts", string="Encuestas")
    support_channel_id = fields.Many2one(
        "discuss.channel", string="Canal Administración y soporte",
        domain="[('channel_type', '=', 'channel')]", tracking=True,
        help="Bandeja compartida para conversaciones bidireccionales con Telegram.",
    )

    _sql_constraints = [
        ("ddtg_bot_company_name_unique", "unique(company_id, name)", "Ya existe un bot con ese nombre en la compañía."),
        ("ddtg_bot_endpoint_unique", "unique(endpoint_key)", "La clave de ruta del webhook debe ser única."),
    ]

    @api.depends("public_base_url", "endpoint_key")
    def _compute_webhook_url(self):
        for bot in self:
            base = (bot.public_base_url or "").rstrip("/") + "/"
            path = "doorandoor/telegram/webhook/%s" % (bot.endpoint_key or "")
            bot.webhook_url = urljoin(base, path) if bot.public_base_url and bot.endpoint_key else False

    def _compute_counts(self):
        notification_model = self.env["doorandoor.telegram.notification"]
        for bot in self:
            bot.link_count = len(bot.link_ids.filtered(lambda link: link.state == "active"))
            bot.notification_count = notification_model.search_count([("bot_id", "=", bot.id)])
            bot.poll_count = self.env["doorandoor.telegram.poll"].search_count([("bot_id", "=", bot.id)])

    @api.constrains("public_base_url")
    def _check_public_base_url(self):
        for bot in self:
            if bot.public_base_url and not bot.public_base_url.startswith("https://"):
                raise ValidationError(_("La URL pública del webhook debe comenzar con https://"))

    def _get_token(self):
        self.ensure_one()
        token = os.getenv(self.token_env_var or "") if self.token_source == "environment" else self.token
        if not token:
            source = self.token_env_var if self.token_source == "environment" else _("el campo Token")
            raise UserError(_("No se encontró el token de Telegram en %s.") % source)
        return token.strip()

    def _call_api(self, method, data=None, timeout=20):
        self.ensure_one()
        url = TELEGRAM_API_URL.format(token=self._get_token(), method=method)
        try:
            response = requests.post(url, json=data or {}, timeout=timeout)
            result = response.json()
        except (requests.RequestException, ValueError) as error:
            self.sudo().write({"state": "error", "last_error": str(error)})
            raise UserError(_("No fue posible comunicarse con Telegram: %s") % error) from error
        if not result.get("ok"):
            error = result.get("description") or _("Respuesta no válida de Telegram")
            self.sudo().write({"state": "error", "last_error": error})
            raise UserError(_("Telegram rechazó la operación: %s") % error)
        return result.get("result")

    def action_validate_token(self):
        self.ensure_one()
        info = self._call_api("getMe")
        self.write({
            "username": info.get("username"), "telegram_bot_id": str(info.get("id") or ""),
            "state": "validated", "last_error": False,
        })
        return self._notification(_("Bot validado"), _("El bot @%s respondió correctamente.") % self.username)

    def action_register_webhook(self):
        self.ensure_one()
        if not self.username:
            self.action_validate_token()
        secret = secrets.token_urlsafe(32)
        self._call_api("setWebhook", {
            "url": self.webhook_url,
            "secret_token": secret,
            "allowed_updates": ["message", "callback_query", "my_chat_member"],
            "drop_pending_updates": False,
        })
        self.write({"webhook_secret": secret, "delivery_mode": "webhook", "state": "running", "last_error": False})
        return self._notification(_("Webhook registrado"), self.webhook_url)

    def action_remove_webhook(self):
        self.ensure_one()
        self._call_api("deleteWebhook", {"drop_pending_updates": False})
        self.write({"state": "stopped", "webhook_secret": False, "last_error": False})
        return self._notification(_("Webhook retirado"), _("El bot dejó de recibir eventos en esta instancia."))

    def action_start_polling(self):
        self.ensure_one()
        if self.environment != "local":
            raise UserError(_("La consulta automática solo está permitida para el bot Local."))
        if not self.username:
            self.action_validate_token()
        self._call_api("deleteWebhook", {"drop_pending_updates": False})
        self.write({
            "delivery_mode": "polling", "webhook_secret": False,
            "state": "running", "last_error": False,
        })
        return self._notification(
            _("Recepción local activada"),
            _("Odoo consultará automáticamente los mensajes y votos de Telegram."),
        )

    def action_check_webhook(self):
        self.ensure_one()
        info = self._call_api("getWebhookInfo")
        message = _("URL: %(url)s · Pendientes: %(pending)s") % {
            "url": info.get("url") or _("Sin registrar"),
            "pending": info.get("pending_update_count", 0),
        }
        if info.get("last_error_message"):
            message += _(" · Error: %s") % info["last_error_message"]
        return self._notification(_("Estado del webhook"), message, "warning" if info.get("last_error_message") else "info")

    def action_open_polls(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_telegram_integration.action_ddtg_poll").read()[0]
        action["domain"] = [("bot_id", "=", self.id)]
        action["context"] = {"default_bot_id": self.id}
        return action

    def _notification(self, title, message, notification_type="success"):
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": title, "message": message, "type": notification_type, "sticky": False},
        }

    def send_message(self, telegram_chat_id, text, reply_markup=None):
        self.ensure_one()
        if not telegram_chat_id or not text:
            raise ValidationError(_("El chat y el texto son obligatorios."))
        chunks = [text[index:index + 4000] for index in range(0, len(text), 4000)]
        result = False
        for chunk in chunks:
            payload = {"chat_id": telegram_chat_id, "text": chunk}
            if reply_markup and chunk == chunks[-1]:
                payload["reply_markup"] = reply_markup
            result = self._call_api("sendMessage", payload)
        return result

    def send_photo(self, telegram_chat_id, content, filename, caption=None):
        self.ensure_one()
        url = TELEGRAM_API_URL.format(token=self._get_token(), method="sendPhoto")
        try:
            response = requests.post(
                url, data={"chat_id": telegram_chat_id, "caption": caption or ""},
                files={"photo": (filename or "imagen.png", content)}, timeout=30,
            )
            result = response.json()
        except (requests.RequestException, ValueError) as error:
            self.sudo().write({"state": "error", "last_error": str(error)})
            raise UserError(_("No fue posible enviar la imagen a Telegram: %s") % error) from error
        if not result.get("ok"):
            error = result.get("description") or _("Respuesta no válida de Telegram")
            raise UserError(_("Telegram rechazó la imagen: %s") % error)
        return result.get("result")

    @api.model
    def get_company_bot(self, company=None):
        company = company or self.env.company
        return self.search([("company_id", "=", company.id), ("state", "=", "running"), ("active", "=", True)], limit=1)

    def queue_for_user(self, user, message, event_type="general", document=None):
        self.ensure_one()
        link = self.env["doorandoor.telegram.user.link"].search([
            ("bot_id", "=", self.id), ("user_id", "=", user.id), ("state", "=", "active")
        ], limit=1)
        if not link or not link.allows_event(event_type):
            return self.env["doorandoor.telegram.notification"]
        values = {"bot_id": self.id, "link_id": link.id, "message": message, "event_type": event_type}
        if document:
            values.update({"res_model": document._name, "res_id": document.id, "document_name": document.display_name})
        return self.env["doorandoor.telegram.notification"].sudo().create(values)

    def _find_support_link(self, reference):
        self.ensure_one()
        needle = (reference or "").strip().lower().lstrip("@")
        links = self.link_ids.filtered(lambda item: item.state == "active")
        exact = links.filtered(lambda item: needle in {
            (item.user_id.name or "").lower(),
            (item.user_id.login or "").lower(),
            (item.telegram_username or "").lower().lstrip("@"),
        })
        if len(exact) == 1:
            return exact
        partial = links.filtered(lambda item: needle and (
            needle in (item.user_id.name or "").lower()
            or needle in (item.user_id.login or "").lower()
            or needle in (item.telegram_username or "").lower()
        ))
        return partial if len(partial) == 1 else self.env["doorandoor.telegram.user.link"]

    @api.model
    def _cron_poll_updates(self):
        bots = self.sudo().search([
            ("environment", "=", "local"), ("delivery_mode", "=", "polling"),
            ("state", "=", "running"), ("active", "=", True),
        ])
        for bot in bots:
            try:
                bot._poll_one()
            except Exception as error:
                _logger.exception("Error consultando actualizaciones Telegram para bot %s", bot.id)
                bot.last_error = str(error)
        return True

    def _poll_one(self):
        self.ensure_one()
        updates = self._call_api("getUpdates", {
            "offset": self.update_offset or 0, "timeout": 0,
            "allowed_updates": ["message", "callback_query", "my_chat_member"],
        }) or []
        for update in updates:
            self.process_update(update)
            update_id = int(update.get("update_id") or 0)
            if update_id >= self.update_offset:
                self.update_offset = update_id + 1
        return len(updates)

    def action_poll_now(self):
        self.ensure_one()
        if self.delivery_mode != "polling" or self.state != "running":
            raise UserError(_("El bot no está activo en modo de recepción local."))
        count = self._poll_one()
        return self._notification(
            _("Telegram actualizado"), _("Se procesaron %s evento(s).") % count, "info"
        )

    def process_update(self, update):
        self.ensure_one()
        update_id = str(update.get("update_id") or "")
        update_model = self.env["doorandoor.telegram.update"].sudo()
        if update_id and update_model.search_count([
            ("bot_id", "=", self.id), ("telegram_update_id", "=", update_id),
        ]):
            return True
        if update_id:
            update_model.create({"bot_id": self.id, "telegram_update_id": update_id})
        self.last_webhook_at = fields.Datetime.now()
        if update.get("message"):
            self._process_message(update["message"], update)
        elif update.get("my_chat_member"):
            self._process_membership(update["my_chat_member"])
        elif update.get("callback_query"):
            self._process_callback(update["callback_query"])
        return True

    def _process_message(self, message, raw_update):
        chat = message.get("chat") or {}
        telegram_user = message.get("from") or {}
        chat_id = str(chat.get("id") or "")
        text = (message.get("text") or "").strip()
        if not chat_id:
            return
        link_model = self.env["doorandoor.telegram.user.link"].sudo()
        link = link_model.search([
            ("bot_id", "=", self.id), ("telegram_chat_id", "=", chat_id),
        ], limit=1)
        self.env["doorandoor.telegram.message"].sudo().create({
            "bot_id": self.id, "link_id": link.id, "direction": "incoming",
            "telegram_chat_id": chat_id,
            "telegram_message_id": str(message.get("message_id") or ""),
            "text": text, "raw_update": json.dumps(raw_update, ensure_ascii=False),
        })
        if text.startswith("/start link_"):
            token = text.split("/start link_", 1)[1].split()[0]
            try:
                link = self.env["doorandoor.telegram.activation"].sudo().consume(
                    self, token, telegram_user, chat_id
                )
                self.send_message(chat_id, _("Cuenta vinculada correctamente con %s en DoorAndDoor.") % link.user_id.name)
            except ValidationError as error:
                self.send_message(chat_id, str(error))
            return
        if text.startswith("/estado"):
            message_text = _("Vínculo activo con el usuario Odoo: %s") % link.user_id.name if link and link.state == "active" else _("Esta cuenta Telegram no está vinculada con un usuario activo de Odoo.")
            self.send_message(chat_id, message_text)
            return
        if text.startswith("/desvincular"):
            if link and link.state == "active":
                link.write({"state": "revoked", "revoked_at": fields.Datetime.now()})
                self.send_message(chat_id, _("La cuenta Telegram fue desvinculada de DoorAndDoor."))
            else:
                self.send_message(chat_id, _("No existe un vínculo activo para retirar."))
            return
        if link and link.state == "active":
            if self.support_channel_id and text:
                body = Markup(
                    "<p>📥 <strong>Telegram · %s</strong></p><p>%s</p>"
                ) % (escape(link.user_id.name), escape(text).replace("\n", Markup("<br/>")))
                self.support_channel_id.with_context(ddtg_bridge_message=True).message_post(
                    body=body, message_type="comment", subtype_xmlid="mail.mt_comment",
                )
            return
        self.send_message(chat_id, _(
            "Para activar este bot, genere su enlace personal desde Odoo y pulse Iniciar."
        ))

    def _process_membership(self, membership):
        chat_id = str((membership.get("chat") or {}).get("id") or "")
        status = ((membership.get("new_chat_member") or {}).get("status") or "")
        link = self.env["doorandoor.telegram.user.link"].sudo().search([
            ("bot_id", "=", self.id), ("telegram_chat_id", "=", chat_id),
        ], limit=1)
        if link and status in ("kicked", "left"):
            link.state = "blocked"
        elif link and status == "member" and link.state == "blocked":
            link.state = "active"

    def _process_callback(self, callback):
        callback_id = callback.get("id")
        data = callback.get("data") or ""
        answer = _("Acción no reconocida.")
        alert = False
        if data.startswith("ddvote:"):
            try:
                _prefix, poll_id, option_id = data.split(":", 2)
                poll = self.env["doorandoor.telegram.poll"].sudo().browse(int(poll_id)).exists()
                option = self.env["doorandoor.telegram.poll.option"].sudo().browse(int(option_id)).exists()
                if not poll or not option or poll.bot_id != self:
                    raise ValidationError(_("La encuesta o variante ya no existe."))
                vote = poll.register_telegram_vote(option, (callback.get("from") or {}).get("id"))
                answer = _("Voto registrado: %s") % vote.option_id.name
            except (ValueError, ValidationError) as error:
                answer = str(error)
                alert = True
        if callback_id:
            self._call_api("answerCallbackQuery", {
                "callback_query_id": callback_id, "text": answer[:190], "show_alert": alert,
            })
