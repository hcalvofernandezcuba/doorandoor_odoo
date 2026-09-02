from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorandoorTelegramNotification(models.Model):
    _name = "doorandoor.telegram.notification"
    _description = "Notificación Telegram DoorAndDoor"
    _order = "create_date desc"
    _check_company_auto = True

    bot_id = fields.Many2one("doorandoor.telegram.bot", required=True, check_company=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    link_id = fields.Many2one("doorandoor.telegram.user.link", required=True, check_company=True, ondelete="cascade", index=True)
    user_id = fields.Many2one(related="link_id.user_id", store=True, index=True)
    event_type = fields.Selection(
        [("general", "General"), ("manufacturing", "Fabricación"),
         ("warehouse", "Almacén"), ("task", "Tarea")],
        default="general", required=True, index=True,
    )
    message = fields.Text(required=True)
    res_model = fields.Char(string="Modelo")
    res_id = fields.Integer(string="ID registro")
    document_name = fields.Char(string="Documento")
    state = fields.Selection(
        [("pending", "Pendiente"), ("sent", "Enviado"), ("error", "Error"), ("cancel", "Cancelado")],
        default="pending", required=True, index=True,
    )
    attempt_count = fields.Integer(string="Intentos", readonly=True)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True)
    sent_at = fields.Datetime(readonly=True)
    telegram_message_id = fields.Char(readonly=True)
    last_error = fields.Text(readonly=True)

    def action_send_now(self):
        for notification in self:
            notification._send_one()
        return True

    def action_retry(self):
        self.write({"state": "pending", "next_attempt_at": fields.Datetime.now(), "last_error": False})
        return True

    def _send_one(self):
        self.ensure_one()
        if self.state in ("sent", "cancel"):
            return False
        if self.link_id.state != "active":
            self.write({"state": "cancel", "last_error": _("El vínculo Telegram no está activo.")})
            return False
        attempt = self.attempt_count + 1
        try:
            result = self.bot_id.send_message(self.link_id.telegram_chat_id, self.message)
            message_id = str((result or {}).get("message_id") or "")
            self.write({
                "state": "sent", "attempt_count": attempt, "sent_at": fields.Datetime.now(),
                "telegram_message_id": message_id, "last_error": False,
            })
            self.env["doorandoor.telegram.message"].sudo().create({
                "bot_id": self.bot_id.id, "link_id": self.link_id.id,
                "direction": "outgoing", "telegram_chat_id": self.link_id.telegram_chat_id,
                "telegram_message_id": message_id, "text": self.message,
                "notification_id": self.id,
            })
            return True
        except Exception as error:
            next_attempt = fields.Datetime.now() + timedelta(minutes=min(2 ** attempt, 60))
            self.write({
                "state": "error", "attempt_count": attempt,
                "next_attempt_at": next_attempt, "last_error": str(error),
            })
            return False

    @api.model
    def _cron_process_queue(self):
        notifications = self.sudo().search([
            ("state", "in", ("pending", "error")),
            ("attempt_count", "<", 5),
            ("next_attempt_at", "<=", fields.Datetime.now()),
        ], order="create_date", limit=50)
        for notification in notifications:
            notification._send_one()
        return len(notifications)

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id or self.res_model not in self.env:
            raise UserError(_("La notificación no tiene un documento Odoo disponible."))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_("El documento relacionado ya no existe."))
        return record.get_formview_action()


class DoorandoorTelegramMessage(models.Model):
    _name = "doorandoor.telegram.message"
    _description = "Historial de mensajes Telegram"
    _order = "create_date desc"
    _check_company_auto = True

    bot_id = fields.Many2one("doorandoor.telegram.bot", required=True, check_company=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    link_id = fields.Many2one("doorandoor.telegram.user.link", check_company=True, ondelete="set null", index=True)
    user_id = fields.Many2one(related="link_id.user_id", store=True, index=True)
    direction = fields.Selection([("incoming", "Entrante"), ("outgoing", "Saliente")], required=True, index=True)
    telegram_chat_id = fields.Char(required=True, index=True)
    telegram_message_id = fields.Char(index=True)
    text = fields.Text()
    notification_id = fields.Many2one("doorandoor.telegram.notification", ondelete="set null")
    raw_update = fields.Text(groups="doorandoor_telegram_integration.group_ddtg_manager")


class DoorandoorTelegramUpdate(models.Model):
    _name = "doorandoor.telegram.update"
    _description = "Actualización Telegram procesada"
    _order = "create_date desc"
    _check_company_auto = True

    bot_id = fields.Many2one("doorandoor.telegram.bot", required=True, check_company=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    telegram_update_id = fields.Char(required=True, index=True)

    _sql_constraints = [
        ("ddtg_update_unique", "unique(bot_id, telegram_update_id)", "La actualización de Telegram ya fue procesada."),
    ]
