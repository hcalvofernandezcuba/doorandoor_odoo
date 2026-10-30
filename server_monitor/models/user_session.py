from odoo import fields, models


class ServerMonitorUserSession(models.Model):
    _name = "server.monitor.user.session"
    _description = "Odoo active browser tab"
    _order = "last_seen desc"

    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    session_key = fields.Char(required=True, index=True)
    tab_key = fields.Char(required=True, index=True)
    device = fields.Selection(
        [("pc", "PC"), ("mac", "Mac"), ("android", "Hanger / Android"), ("other", "Other")],
        required=True,
    )
    user_agent = fields.Char()
    current_path = fields.Char()
    first_seen = fields.Datetime(default=fields.Datetime.now, required=True)
    last_seen = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    heartbeat_count = fields.Integer(default=0)
    navigation_count = fields.Integer(default=0)

    _sql_constraints = [
        ("user_session_tab_unique", "unique(user_id, session_key, tab_key)", "Browser tab must be unique."),
    ]
