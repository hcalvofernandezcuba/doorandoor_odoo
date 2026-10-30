from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashAuditWizard(models.TransientModel):
    _name = "doorandoor.cash.audit.wizard"
    _description = "Conteo sorpresa de caja"

    register_id = fields.Many2one("doorandoor.cash.register", required=True, domain=[("active", "=", True)])
    session_id = fields.Many2one("doorandoor.cash.session", readonly=True)
    currency_id = fields.Many2one(related="session_id.currency_id", readonly=True)
    expected_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    note = fields.Text(string="Observaciones de auditoría")
    line_ids = fields.One2many("doorandoor.cash.audit.wizard.line", "wizard_id", string="Conteo físico")

    def _get_open_session(self):
        self.ensure_one()
        return self.env["doorandoor.cash.session"].search([
            ("register_id", "=", self.register_id.id),
            ("state", "=", "open"),
        ], order="opening_at desc, id desc", limit=1)

    def _load_expected_stock(self):
        for wizard in self:
            wizard.line_ids = [(5, 0, 0)]
            session = wizard._get_open_session() if wizard.register_id else self.env["doorandoor.cash.session"]
            wizard.session_id = session
            if not session:
                continue
            expected_quantities = session._ddcc_expected_denomination_quantities()
            denominations = self.env["doorandoor.cash.denomination"].search([
                ("active", "=", True), ("currency_id", "=", session.currency_id.id),
            ], order="value desc")
            wizard.line_ids = [(0, 0, {
                "denomination_id": denomination.id,
                "expected_quantity": expected_quantities.get(denomination.id, 0),
                "counted_quantity": 0,
            }) for denomination in denominations]

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        registers = self.env["doorandoor.cash.register"].search([
            ("company_id", "=", self.env.company.id), ("active", "=", True),
        ], limit=2)
        if len(registers) == 1:
            values["register_id"] = registers.id
            session = self.env["doorandoor.cash.session"].search([
                ("register_id", "=", registers.id), ("state", "=", "open"),
            ], order="opening_at desc, id desc", limit=1)
            if session:
                quantities = session._ddcc_expected_denomination_quantities()
                denominations = self.env["doorandoor.cash.denomination"].search([
                    ("active", "=", True), ("currency_id", "=", session.currency_id.id),
                ], order="value desc")
                values.update({
                    "session_id": session.id,
                    "line_ids": [(0, 0, {
                        "denomination_id": denomination.id,
                        "expected_quantity": quantities.get(denomination.id, 0),
                        "counted_quantity": 0,
                    }) for denomination in denominations],
                })
        return values

    @api.onchange("register_id")
    def _onchange_register_id(self):
        self._load_expected_stock()
        if self.register_id and not self.session_id:
            return {"warning": {
                "title": _("Caja sin sesión abierta"),
                "message": _("Esta caja no tiene una sesión abierta para auditar."),
            }}

    @api.depends("line_ids.expected_amount", "line_ids.counted_amount")
    def _compute_totals(self):
        for wizard in self:
            wizard.expected_amount = sum(wizard.line_ids.mapped("expected_amount"))
            wizard.counted_amount = sum(wizard.line_ids.mapped("counted_amount"))
            wizard.difference_amount = wizard.currency_id.round(
                wizard.counted_amount - wizard.expected_amount
            ) if wizard.currency_id else 0.0

    def action_record_audit(self):
        self.ensure_one()
        if not self.session_id or self.session_id.state != "open":
            raise ValidationError(_("Seleccione una caja con una sesión abierta antes de registrar el conteo."))
        if not self.line_ids:
            raise ValidationError(_("No hay denominaciones disponibles para el conteo."))
        audit = self.env["doorandoor.cash.audit"].search([
            ("session_id", "=", self.session_id.id), ("state", "=", "prepared"),
        ], limit=1)
        if not audit:
            audit = self.env["doorandoor.cash.audit"].create({
                "session_id": self.session_id.id,
                "line_ids": [(0, 0, {
                    "denomination_id": line.denomination_id.id,
                    "expected_quantity": line.expected_quantity,
                    "counted_quantity": 0,
                }) for line in self.line_ids],
            })
        snapshots = []
        for movement in self.session_id.movement_ids:
            snapshots.append((0, 0, {
                "payment_id": movement.payment_id.id,
                "move_id": movement.move_id.id,
                "payment_date": movement.payment_id.date,
                "cashier_id": movement.user_id.id,
                "tender_amount": movement.tender_amount,
                "payment_amount": movement.payment_amount,
                "change_amount": movement.change_amount,
                "line_ids": [(0, 0, {
                    "denomination_id": line.denomination_id.id,
                    "received_quantity": line.received_quantity,
                    "change_quantity": line.change_quantity,
                }) for line in movement.line_ids if line.received_quantity or line.change_quantity],
            }))
        if not audit.movement_snapshot_ids:
            audit.write({"movement_snapshot_ids": snapshots})
            self.session_id.message_post(body=_(
                "Arqueo %(audit)s iniciado por %(auditor)s. Efectivo esperado al emitir la hoja: %(expected)s."
            ) % {
                "audit": audit.display_name,
                "auditor": self.env.user.display_name,
                "expected": self.currency_id.format(self.expected_amount),
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.cash.audit",
            "res_id": audit.id,
            "view_mode": "form",
            "target": "current",
        }


class DoorAndDoorCashAuditWizardLine(models.TransientModel):
    _name = "doorandoor.cash.audit.wizard.line"
    _description = "Denominación contada en auditoría sorpresa"

    wizard_id = fields.Many2one("doorandoor.cash.audit.wizard", required=True, ondelete="cascade")
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True, readonly=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)
    expected_quantity = fields.Integer(required=True, readonly=True, default=0)
    counted_quantity = fields.Integer(required=True, default=0)
    expected_amount = fields.Monetary(compute="_compute_amounts", currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_amounts", currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_amounts", currency_field="currency_id")

    @api.depends("denomination_id.value", "expected_quantity", "counted_quantity")
    def _compute_amounts(self):
        for line in self:
            value = line.denomination_id.value
            line.expected_amount = value * line.expected_quantity
            line.counted_amount = value * line.counted_quantity
            line.difference_amount = line.counted_amount - line.expected_amount
