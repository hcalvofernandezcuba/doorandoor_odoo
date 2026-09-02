from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorandoorTelegramLinkWizard(models.TransientModel):
    _name = "doorandoor.telegram.link.wizard"
    _description = "Vincular mi cuenta Telegram"

    user_id = fields.Many2one("res.users", string="Usuario Odoo", required=True, readonly=True)
    bot_id = fields.Many2one(
        "doorandoor.telegram.bot", string="Bot", required=True,
        domain="[('state', '=', 'running'), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(related="user_id.company_id")
    validity_minutes = fields.Integer(string="Validez (minutos)", default=15, readonly=True)
    activation_url = fields.Char(string="Enlace personal", readonly=True, copy=False)
    expires_at = fields.Datetime(string="Expira", readonly=True)
    activation_id = fields.Many2one("doorandoor.telegram.activation", readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        user = self.env.user
        values.setdefault("user_id", user.id)
        bot = self.env["doorandoor.telegram.bot"].search([
            ("company_id", "=", user.company_id.id), ("state", "=", "running"), ("active", "=", True)
        ], limit=1)
        if bot:
            values.setdefault("bot_id", bot.id)
        return values

    def action_generate_link(self):
        self.ensure_one()
        if self.user_id != self.env.user and not self.env.user.has_group(
            "doorandoor_telegram_integration.group_ddtg_manager"
        ):
            raise UserError(_("Solo puede generar un enlace para su propio usuario."))
        activation, raw_token = self.env["doorandoor.telegram.activation"].generate_for_user(
            self.bot_id, self.user_id, self.validity_minutes
        )
        self.write({
            "activation_id": activation.id, "expires_at": activation.expires_at,
            "activation_url": "https://t.me/%s?start=%s" % (
                self.bot_id.username, quote("link_%s" % raw_token, safe="_-"),
            ),
        })
        return {
            "type": "ir.actions.act_window", "res_model": self._name,
            "res_id": self.id, "view_mode": "form", "target": "new",
        }

    def action_open_telegram(self):
        self.ensure_one()
        if not self.activation_url:
            raise UserError(_("Genere primero el enlace personal."))
        return {"type": "ir.actions.act_url", "url": self.activation_url, "target": "new"}
