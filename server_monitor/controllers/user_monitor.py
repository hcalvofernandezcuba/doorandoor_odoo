from datetime import timedelta

from odoo import fields, http
from odoo.http import request


def _device_from_agent(agent):
    value = (agent or "").lower()
    if "android" in value:
        return "android"
    if "macintosh" in value or "mac os" in value:
        return "mac"
    if "windows" in value or "linux" in value:
        return "pc"
    return "other"


class ServerMonitorUsers(http.Controller):

    def _check_access(self):
        return request.env.user.has_group("server_monitor.group_server_monitor_user")

    @http.route("/server_monitor/users/heartbeat", type="json", auth="user", csrf=False)
    def heartbeat(self, session_key=None, tab_key=None, path=None):
        if not session_key or not tab_key:
            return {"ok": False}
        model = request.env["server.monitor.user.session"].sudo()
        domain = [
            ("user_id", "=", request.env.user.id),
            ("session_key", "=", str(session_key)[:80]),
            ("tab_key", "=", str(tab_key)[:80]),
        ]
        record = model.search(domain, limit=1)
        current_path = str(path or "")[:500]
        now = fields.Datetime.now()
        values = {
            "last_seen": now,
            "user_agent": request.httprequest.headers.get("User-Agent", "")[:1000],
            "device": _device_from_agent(request.httprequest.headers.get("User-Agent")),
            "heartbeat_count": (record.heartbeat_count if record else 0) + 1,
        }
        if not record or record.current_path != current_path:
            values.update({"current_path": current_path, "navigation_count": (record.navigation_count if record else 0) + 1})
        if record:
            record.write(values)
        else:
            values.update({"user_id": request.env.user.id, "session_key": session_key, "tab_key": tab_key})
            model.create(values)
        return {"ok": True}

    @http.route("/server_monitor/users/data", type="json", auth="user")
    def user_data(self):
        if not self._check_access():
            return {"error": "Access denied"}
        cutoff = fields.Datetime.now() - timedelta(seconds=90)
        records = request.env["server.monitor.user.session"].sudo().search(
            [("last_seen", ">=", cutoff)], order="user_id, last_seen desc"
        )
        users = {}
        for record in records:
            row = users.setdefault(record.user_id.id, {
                "id": record.user_id.id,
                "name": record.user_id.name,
                "tabs": 0,
                "devices": set(),
                "last_seen": record.last_seen,
                "heartbeats": 0,
                "navigations": 0,
                "paths": [],
            })
            row["tabs"] += 1
            row["devices"].add(dict(record._fields["device"].selection).get(record.device, record.device))
            row["heartbeats"] += record.heartbeat_count
            row["navigations"] += record.navigation_count
            if record.current_path and record.current_path not in row["paths"]:
                row["paths"].append(record.current_path)
            if record.last_seen > row["last_seen"]:
                row["last_seen"] = record.last_seen
        result = []
        for row in users.values():
            row["devices"] = sorted(row["devices"])
            row["last_seen"] = fields.Datetime.to_string(row["last_seen"])
            result.append(row)
        result.sort(key=lambda row: (row["heartbeats"] + row["navigations"], row["tabs"]), reverse=True)
        devices = {label: 0 for _key, label in request.env["server.monitor.user.session"]._fields["device"].selection}
        for record in records:
            label = dict(record._fields["device"].selection).get(record.device, record.device)
            devices[label] = devices.get(label, 0) + 1
        return {
            "users": result,
            "active_users": len(result),
            "active_tabs": len(records),
            "total_heartbeats": sum(row["heartbeats"] for row in result),
            "total_navigations": sum(row["navigations"] for row in result),
            "devices": [{"name": name, "value": value} for name, value in devices.items() if value],
        }

    @http.route("/usuarios/", type="http", auth="user", website=False)
    def users_page(self, **kwargs):
        if not self._check_access():
            return request.not_found()
        return request.render("server_monitor.user_monitor_page", {})
