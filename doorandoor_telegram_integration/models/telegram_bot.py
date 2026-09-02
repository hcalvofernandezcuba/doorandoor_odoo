import os
import secrets
from urllib.parse import urljoin

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"


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
        self.write({"webhook_secret": secret, "state": "running", "last_error": False})
        return self._notification(_("Webhook registrado"), self.webhook_url)

    def action_remove_webhook(self):
        self.ensure_one()
        self._call_api("deleteWebhook", {"drop_pending_updates": False})
        self.write({"state": "stopped", "webhook_secret": False, "last_error": False})
        return self._notification(_("Webhook retirado"), _("El bot dejó de recibir eventos en esta instancia."))

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

    def _notification(self, title, message, notification_type="success"):
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": title, "message": message, "type": notification_type, "sticky": False},
        }

    def send_message(self, telegram_chat_id, text):
        self.ensure_one()
        if not telegram_chat_id or not text:
            raise ValidationError(_("El chat y el texto son obligatorios."))
        chunks = [text[index:index + 4000] for index in range(0, len(text), 4000)]
        result = False
        for chunk in chunks:
            result = self._call_api("sendMessage", {"chat_id": telegram_chat_id, "text": chunk})
        return result

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
