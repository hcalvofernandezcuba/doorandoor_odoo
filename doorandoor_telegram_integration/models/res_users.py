from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    doorandoor_telegram_link_ids = fields.One2many(
        "doorandoor.telegram.user.link", "user_id", string="Vínculos Telegram"
    )
    doorandoor_telegram_link_count = fields.Integer(
        compute="_compute_doorandoor_telegram_link_count", string="Telegram"
    )

    def _compute_doorandoor_telegram_link_count(self):
        for user in self:
            user.doorandoor_telegram_link_count = len(user.doorandoor_telegram_link_ids.filtered(
                lambda link: link.state == "active"
            ))

    def action_open_doorandoor_telegram_links(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_telegram_integration.action_ddtg_user_link").read()[0]
        action["domain"] = [("user_id", "=", self.id)]
        action["context"] = {"default_user_id": self.id}
        return action
