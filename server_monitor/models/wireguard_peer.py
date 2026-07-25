from odoo import fields, models


class ServerMonitorWireGuardPeer(models.Model):
    _name = "server.monitor.wireguard.peer"
    _description = "Server Monitor WireGuard Peer"
    _order = "name, id"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    public_key = fields.Char(index=True)
    allowed_ip = fields.Char(string="Allowed IP", index=True)
    note = fields.Char()

    _sql_constraints = [
        (
            "server_monitor_wireguard_peer_public_key_unique",
            "unique(public_key)",
            "Public key must be unique.",
        ),
    ]
