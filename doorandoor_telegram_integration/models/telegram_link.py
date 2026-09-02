import hashlib
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorandoorTelegramUserLink(models.Model):
    _name = "doorandoor.telegram.user.link"
    _description = "Vínculo de usuario con Telegram"
    _inherit = ["mail.thread"]
    _order = "user_id"
    _check_company_auto = True

    bot_id = fields.Many2one(
        "doorandoor.telegram.bot", string="Bot", required=True, index=True,
        check_company=True, ondelete="cascade", tracking=True,
    )
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    user_id = fields.Many2one(
        "res.users", string="Usuario Odoo", required=True, index=True,
        domain="[('share', '=', False)]", ondelete="cascade", tracking=True,
    )
    telegram_user_id = fields.Char(string="ID usuario Telegram", required=True, index=True, readonly=True)
    telegram_chat_id = fields.Char(string="ID chat Telegram", required=True, index=True, readonly=True)
    telegram_username = fields.Char(string="Usuario Telegram", readonly=True)
    telegram_first_name = fields.Char(string="Nombre Telegram", readonly=True)
    telegram_last_name = fields.Char(string="Apellidos Telegram", readonly=True)
    language_code = fields.Char(string="Idioma", readonly=True)
    state = fields.Selection(
        [("active", "Activo"), ("blocked", "Bot bloqueado"), ("revoked", "Desvinculado")],
        default="active", required=True, tracking=True, index=True,
    )
    verified_at = fields.Datetime(string="Verificado", readonly=True, tracking=True)
    revoked_at = fields.Datetime(string="Desvinculado", readonly=True)
    notify_general = fields.Boolean(string="Avisos generales", default=True)
    notify_manufacturing = fields.Boolean(string="Fabricación", default=True)
    notify_warehouse = fields.Boolean(string="Almacén y traslados", default=True)
    notify_tasks = fields.Boolean(string="Tareas y actividades", default=True)
    message_ids = fields.One2many("doorandoor.telegram.message", "link_id", string="Mensajes")

    _sql_constraints = [
        ("ddtg_link_bot_user_unique", "unique(bot_id, user_id)", "El usuario ya tiene un vínculo con este bot."),
        ("ddtg_link_bot_chat_unique", "unique(bot_id, telegram_chat_id)", "El chat ya está vinculado con otro usuario."),
        ("ddtg_link_bot_tg_user_unique", "unique(bot_id, telegram_user_id)", "La cuenta Telegram ya está vinculada."),
    ]

    def name_get(self):
        return [(link.id, "%s · @%s" % (link.user_id.name, link.telegram_username or link.telegram_chat_id)) for link in self]

    def allows_event(self, event_type):
        self.ensure_one()
        mapping = {
            "general": self.notify_general, "manufacturing": self.notify_manufacturing,
            "warehouse": self.notify_warehouse, "task": self.notify_tasks,
        }
        return self.state == "active" and mapping.get(event_type, self.notify_general)

    def action_revoke(self):
        own_links = self.filtered(lambda link: link.user_id == self.env.user or self.env.user.has_group("doorandoor_telegram_integration.group_ddtg_manager"))
        if own_links != self:
            raise UserError(_("Solo puede desvincular su propia cuenta de Telegram."))
        own_links.write({"state": "revoked", "revoked_at": fields.Datetime.now()})
        return True


class DoorandoorTelegramActivation(models.Model):
    _name = "doorandoor.telegram.activation"
    _description = "Activación temporal de Telegram"
    _order = "create_date desc"
    _check_company_auto = True

    bot_id = fields.Many2one("doorandoor.telegram.bot", required=True, check_company=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    token_digest = fields.Char(required=True, copy=False, index=True, readonly=True)
    expires_at = fields.Datetime(required=True, index=True, readonly=True)
    state = fields.Selection(
        [("pending", "Pendiente"), ("used", "Utilizado"), ("expired", "Expirado"), ("revoked", "Revocado")],
        default="pending", required=True, index=True, readonly=True,
    )
    used_at = fields.Datetime(readonly=True)
    telegram_chat_id = fields.Char(readonly=True)

    _sql_constraints = [
        ("ddtg_activation_digest_unique", "unique(token_digest)", "El token de activación debe ser único."),
    ]

    @api.model
    def generate_for_user(self, bot, user, validity_minutes=15):
        if bot.state != "running" or not bot.username:
            raise UserError(_("El bot debe estar validado y con el webhook activo antes de vincular usuarios."))
        if user.share or not user.active:
            raise UserError(_("Solo se pueden vincular usuarios internos activos."))
        self.sudo().search([
            ("bot_id", "=", bot.id), ("user_id", "=", user.id), ("state", "=", "pending")
        ]).write({"state": "revoked"})
        raw_token = secrets.token_urlsafe(24)
        activation = self.sudo().create({
            "bot_id": bot.id, "user_id": user.id,
            "token_digest": self._digest(raw_token),
            "expires_at": fields.Datetime.now() + timedelta(minutes=validity_minutes),
        })
        return activation, raw_token

    @api.model
    def consume(self, bot, raw_token, telegram_user, telegram_chat_id):
        digest = self._digest(raw_token)
        activation = self.sudo().search([
            ("bot_id", "=", bot.id), ("token_digest", "=", digest), ("state", "=", "pending")
        ], limit=1)
        if not activation:
            raise ValidationError(_("El enlace de activación no existe, ya fue usado o fue revocado."))
        if activation.expires_at < fields.Datetime.now():
            activation.write({"state": "expired"})
            raise ValidationError(_("El enlace de activación expiró. Genere uno nuevo desde Odoo."))
        telegram_user_id = str(telegram_user.get("id") or "")
        telegram_chat_id = str(telegram_chat_id or "")
        if not telegram_user_id or not telegram_chat_id:
            raise ValidationError(_("Telegram no proporcionó una identidad válida."))
        link_model = self.env["doorandoor.telegram.user.link"].sudo()
        chat_link = link_model.search([
            ("bot_id", "=", bot.id), "|",
            ("telegram_chat_id", "=", telegram_chat_id),
            ("telegram_user_id", "=", telegram_user_id),
        ], limit=1)
        if chat_link and chat_link.user_id != activation.user_id:
            raise ValidationError(_("Esta cuenta Telegram ya está vinculada con otro usuario Odoo."))
        user_link = link_model.search([
            ("bot_id", "=", bot.id), ("user_id", "=", activation.user_id.id)
        ], limit=1)
        values = {
            "telegram_user_id": telegram_user_id,
            "telegram_chat_id": telegram_chat_id,
            "telegram_username": telegram_user.get("username"),
            "telegram_first_name": telegram_user.get("first_name"),
            "telegram_last_name": telegram_user.get("last_name"),
            "language_code": telegram_user.get("language_code"),
            "state": "active", "verified_at": fields.Datetime.now(), "revoked_at": False,
        }
        if user_link:
            user_link.write(values)
            link = user_link
        else:
            values.update({"bot_id": bot.id, "user_id": activation.user_id.id})
            link = link_model.create(values)
        activation.write({"state": "used", "used_at": fields.Datetime.now(), "telegram_chat_id": telegram_chat_id})
        return link

    @staticmethod
    def _digest(raw_token):
        return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()

    @api.model
    def _cron_expire_activations(self):
        self.sudo().search([
            ("state", "=", "pending"), ("expires_at", "<", fields.Datetime.now())
        ]).write({"state": "expired"})
        return True
