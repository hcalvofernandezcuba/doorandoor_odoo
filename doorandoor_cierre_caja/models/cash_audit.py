from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashAudit(models.Model):
    _name = "doorandoor.cash.audit"
    _description = "Auditoría sorpresa de existencias de caja"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "audit_at desc, id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False)
    session_id = fields.Many2one("doorandoor.cash.session", required=True, readonly=True, ondelete="restrict", index=True)
    register_id = fields.Many2one(related="session_id.register_id", store=True, readonly=True)
    company_id = fields.Many2one(related="session_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="session_id.currency_id", readonly=True)
    state = fields.Selection([
        ("prepared", "Pendiente de conteo"),
        ("counted", "Conteo registrado"),
    ], required=True, default="prepared", readonly=True, tracking=True)
    audit_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True,
                               string="Inicio del arqueo")
    printed_at = fields.Datetime(readonly=True, string="Hoja impresa")
    counted_at = fields.Datetime(readonly=True, string="Conteo registrado")
    cash_blocked = fields.Boolean(readonly=True, default=False, tracking=True, string="Caja bloqueada")
    blocked_at = fields.Datetime(readonly=True, string="Bloqueada desde")
    auditor_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, readonly=True)
    expected_amount = fields.Monetary(compute="_compute_totals", store=True, readonly=True, currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_totals", store=True, readonly=True, currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_totals", store=True, readonly=True, currency_field="currency_id")
    note = fields.Text()
    line_ids = fields.One2many("doorandoor.cash.audit.line", "audit_id")
    movement_snapshot_ids = fields.One2many("doorandoor.cash.audit.movement", "audit_id", readonly=True)

    def action_open_session(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.cash.session",
            "res_id": self.session_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("line_ids.expected_amount", "line_ids.counted_amount")
    def _compute_totals(self):
        for audit in self:
            audit.expected_amount = sum(audit.line_ids.mapped("expected_amount"))
            audit.counted_amount = sum(audit.line_ids.mapped("counted_amount"))
            audit.difference_amount = audit.currency_id.round(
                audit.counted_amount - audit.expected_amount
            ) if audit.currency_id else 0.0

    def action_print_worksheet(self):
        self.ensure_one()
        if not self.printed_at:
            self.write({"printed_at": fields.Datetime.now()})
            self.message_post(body=_("Se emitió la hoja de arqueo para conteo físico."))
        return self.env.ref("doorandoor_cierre_caja.action_report_cash_audit_worksheet").report_action(self)

    def _ddcc_notify_cashiers(self, body):
        """Leave an in-Odoo notification for the cashier(s) of this drawer."""
        for audit in self:
            users = audit.session_id.cashier_id | audit.register_id.cashier_ids | audit.register_id.manager_ids
            partners = users.mapped("partner_id")
            audit.message_post(
                body=body,
                partner_ids=partners.ids,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def action_block_cash(self):
        for audit in self:
            if audit.state != "prepared" or audit.cash_blocked:
                continue
            audit.write({"cash_blocked": True, "blocked_at": fields.Datetime.now()})
            self.env["doorandoor.cash.collection.request"]._ddcc_set_waiting_for_register(self.env, audit.register_id)
            audit._ddcc_notify_cashiers(_(
                "La caja %(register)s está en proceso de arqueo desde %(started)s. "
                "Los cobros en efectivo quedan temporalmente en espera hasta que se registre el conteo."
            ) % {
                "register": audit.register_id.display_name,
                "started": fields.Datetime.to_string(audit.blocked_at),
            })

    def action_confirm_count(self):
        for audit in self:
            if audit.state != "prepared":
                continue
            audit.write({"state": "counted", "counted_at": fields.Datetime.now()})
            if audit.cash_blocked:
                audit.write({"cash_blocked": False})
                self.env["doorandoor.cash.collection.request"]._ddcc_release_for_register(self.env, audit.register_id)
            audit.message_post(body=_(
                "Conteo físico registrado. Esperado: %(expected)s; contado: %(counted)s; diferencia: %(difference)s."
            ) % {
                "expected": audit.currency_id.format(audit.expected_amount),
                "counted": audit.currency_id.format(audit.counted_amount),
                "difference": audit.currency_id.format(audit.difference_amount),
            })
            audit._ddcc_notify_cashiers(_(
                "El arqueo %(audit)s de %(register)s finalizó. La caja vuelve a estar disponible para cobros en efectivo."
            ) % {"audit": audit.display_name, "register": audit.register_id.display_name})

    def write(self, vals):
        if any(key in vals for key in ("line_ids", "session_id", "expected_amount")):
            locked = self.filtered(lambda a: a.state == "counted")
            if locked:
                raise ValidationError(_("Un arqueo registrado no puede modificarse."))
        return super().write(vals)

    @classmethod
    def _next_name(cls, env):
        return env["ir.sequence"].next_by_code("doorandoor.cash.audit") or _("Nuevo")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("name", _("Nuevo")) == _("Nuevo"):
                values["name"] = self._next_name(self.env)
        return super().create(vals_list)


class DoorAndDoorCashAuditLine(models.Model):
    _name = "doorandoor.cash.audit.line"
    _description = "Detalle de auditoría sorpresa de caja"
    _order = "denomination_id desc, id"

    audit_id = fields.Many2one("doorandoor.cash.audit", required=True, ondelete="cascade", index=True)
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True, readonly=True)
    currency_id = fields.Many2one(related="audit_id.currency_id", readonly=True)
    expected_quantity = fields.Integer(required=True, readonly=True)
    counted_quantity = fields.Integer(required=True, default=0)
    difference_quantity = fields.Integer(compute="_compute_amounts", store=True, readonly=True)
    expected_amount = fields.Monetary(compute="_compute_amounts", store=True, readonly=True, currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_amounts", store=True, readonly=True, currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_amounts", store=True, readonly=True, currency_field="currency_id")

    @api.depends("denomination_id.value", "expected_quantity", "counted_quantity")
    def _compute_amounts(self):
        for line in self:
            value = line.denomination_id.value
            line.difference_quantity = line.counted_quantity - line.expected_quantity
            line.expected_amount = value * line.expected_quantity
            line.counted_amount = value * line.counted_quantity
            line.difference_amount = line.counted_amount - line.expected_amount


class DoorAndDoorCashAuditMovement(models.Model):
    _name = "doorandoor.cash.audit.movement"
    _description = "Movimiento congelado para arqueo de caja"
    _order = "payment_date, id"

    audit_id = fields.Many2one("doorandoor.cash.audit", required=True, ondelete="cascade", index=True)
    payment_id = fields.Many2one("account.payment", readonly=True, ondelete="restrict")
    move_id = fields.Many2one("account.move", readonly=True, ondelete="restrict", string="Factura")
    payment_date = fields.Date(readonly=True)
    cashier_id = fields.Many2one("res.users", readonly=True)
    tender_amount = fields.Monetary(readonly=True, currency_field="currency_id")
    payment_amount = fields.Monetary(readonly=True, currency_field="currency_id")
    change_amount = fields.Monetary(readonly=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="audit_id.currency_id", readonly=True)
    line_ids = fields.One2many("doorandoor.cash.audit.movement.line", "snapshot_id", readonly=True)


class DoorAndDoorCashAuditMovementLine(models.Model):
    _name = "doorandoor.cash.audit.movement.line"
    _description = "Denominación congelada para arqueo de caja"
    _order = "denomination_id desc, id"

    snapshot_id = fields.Many2one("doorandoor.cash.audit.movement", required=True, ondelete="cascade", index=True)
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True, readonly=True)
    received_quantity = fields.Integer(readonly=True)
    change_quantity = fields.Integer(readonly=True)
    currency_id = fields.Many2one(related="snapshot_id.currency_id", readonly=True)
