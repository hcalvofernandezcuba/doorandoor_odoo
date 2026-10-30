import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class DoorAndDoorAuditLog(models.Model):
    _name = "doorandoor.audit.log"
    _description = "DoorAndDoor General Audit Log"
    _order = "event_date desc, id desc"
    _rec_name = "display_reference"

    event_date = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    user_id = fields.Many2one("res.users", required=True, index=True, readonly=True)
    company_id = fields.Many2one("res.company", index=True, readonly=True)
    operation = fields.Selection(
        [("create", "Creación"), ("write", "Modificación"), ("unlink", "Eliminación")],
        required=True,
        index=True,
        readonly=True,
    )
    model_name = fields.Char(required=True, index=True, readonly=True)
    model_label = fields.Char(readonly=True)
    record_id = fields.Integer(required=True, index=True, readonly=True)
    record_name = fields.Char(index=True, readonly=True)
    display_reference = fields.Char(compute="_compute_display_reference", store=True)
    field_name = fields.Char(index=True, readonly=True)
    field_label = fields.Char(readonly=True)
    old_value = fields.Text(readonly=True)
    new_value = fields.Text(readonly=True)
    source = fields.Selection(
        [("web", "Interfaz web"), ("rpc", "RPC/Integración"), ("cron", "Tarea automática"), ("server", "Servidor")],
        required=True,
        default="server",
        index=True,
        readonly=True,
    )
    remote_ip = fields.Char(readonly=True)
    request_path = fields.Char(readonly=True)
    session_sid = fields.Char(readonly=True)
    context_note = fields.Char(readonly=True)

    @api.depends("model_label", "record_name", "record_id", "field_label")
    def _compute_display_reference(self):
        for log in self:
            document = log.record_name or "#%s" % log.record_id
            log.display_reference = "%s · %s · %s" % (
                log.model_label or log.model_name,
                document,
                log.field_label or _("Registro"),
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("doorandoor_audit_internal"):
            raise AccessError(_("Las trazas de auditoría solo pueden ser creadas por el sistema."))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Las trazas de auditoría son inmutables."))

    def unlink(self):
        raise AccessError(_("Las trazas de auditoría no pueden eliminarse."))

    @api.model
    def _serialize_value(self, model, field_name, value):
        field = model._fields.get(field_name)
        if not field:
            return ""
        if field.type == "many2one":
            record = value if hasattr(value, "id") else self.env[field.comodel_name].sudo().browse(value)
            return json.dumps({"id": record.id, "name": record.display_name}, ensure_ascii=False)
        if field.type in ("many2many", "one2many"):
            records = value if hasattr(value, "ids") else self.env[field.comodel_name].sudo().browse(value or [])
            return json.dumps(
                [{"id": record.id, "name": record.display_name} for record in records],
                ensure_ascii=False,
            )
        if field.type in ("date", "datetime") and value:
            return str(value)
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return "" if value is False or value is None else str(value)

    @api.model
    def _request_metadata(self):
        metadata = {"source": "server"}
        try:
            from odoo.http import request

            if request and request.httprequest:
                metadata.update({
                    "source": "web",
                    "remote_ip": request.httprequest.remote_addr,
                    "request_path": request.httprequest.path,
                    "session_sid": getattr(request.session, "sid", False),
                })
        except (RuntimeError, AttributeError):
            pass
        if self.env.context.get("cron_id"):
            metadata["source"] = "cron"
        return metadata

    @api.model
    def log_changes(self, records, operation, before=None, tracked_fields=None):
        if self.env.context.get("doorandoor_audit_skip") or not records:
            return
        before = before or {}
        tracked_fields = set(tracked_fields or [])
        metadata = self._request_metadata()
        values = []
        for record in records.sudo():
            model_label = record._description or record._name
            record_name = record.display_name
            field_names = tracked_fields if operation != "unlink" else set(before.get(record.id, {}))
            if operation == "create":
                field_names = tracked_fields
            for field_name in sorted(field_names):
                field = record._fields.get(field_name)
                if not field:
                    continue
                old_raw = before.get(record.id, {}).get(field_name)
                new_raw = False if operation == "unlink" else record[field_name]
                old_value = self._serialize_value(record, field_name, old_raw)
                new_value = self._serialize_value(record, field_name, new_raw)
                if operation == "write" and old_value == new_value:
                    continue
                values.append({
                    "event_date": fields.Datetime.now(),
                    "user_id": self.env.user.id,
                    "company_id": self.env.company.id,
                    "operation": operation,
                    "model_name": record._name,
                    "model_label": model_label,
                    "record_id": record.id,
                    "record_name": record_name,
                    "field_name": field_name,
                    "field_label": field.string,
                    "old_value": old_value,
                    "new_value": new_value,
                    "context_note": self.env.context.get("doorandoor_audit_note"),
                    **metadata,
                })
        if values:
            self.sudo().with_context(doorandoor_audit_internal=True, doorandoor_audit_skip=True).create(values)


def audit_snapshot(records, field_names):
    snapshot = {}
    for record in records.sudo():
        snapshot[record.id] = {name: record[name] for name in field_names if name in record._fields}
    return snapshot
