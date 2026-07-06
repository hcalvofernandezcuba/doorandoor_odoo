from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from .main import ServerMonitorBase


class ServerMonitorWireGuardController(http.Controller, ServerMonitorBase):
    @http.route("/server_monitor/wireguard", type="json", auth="user")
    def get_wireguard_metrics(self):
        if not request.env.user.has_group("server_monitor.group_server_monitor_user"):
            raise AccessError(_("You do not have access to Server Monitor."))

        config = self._get_config()
        return self._get_wireguard_payload(config)
