from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashCloseWizard(models.TransientModel):
    _name = "doorandoor.cash.close.wizard"
    _description = "Cierre y arqueo de caja"

    session_id = fields.Many2one("doorandoor.cash.session", required=True, domain=[("state", "=", "open")])
    line_ids = fields.One2many("doorandoor.cash.close.wizard.line", "wizard_id", string="Efectivo contado")
    currency_id = fields.Many2one(related="session_id.currency_id")
    expected_amount = fields.Monetary(related="session_id.expected_amount", currency_field="currency_id")
    counted_amount = fields.Monetary(compute="_compute_counted", currency_field="currency_id")
    difference_amount = fields.Monetary(compute="_compute_counted", currency_field="currency_id")
    deposit_reference = fields.Char(string="Referencia de depósito")
    note = fields.Text(string="Observaciones")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        session = self.env["doorandoor.cash.session"].browse(self.env.context.get("active_id")).exists()
        if session and session.state == "open":
            values["session_id"] = session.id
        denoms = self.env["doorandoor.cash.denomination"].search([
            ("active", "=", True), ("currency_id", "=", self.env.company.currency_id.id),
        ])
        values["line_ids"] = [(0, 0, {"denomination_id": denom.id, "quantity": 0}) for denom in denoms]
        return values

    @api.depends("line_ids.subtotal", "expected_amount")
    def _compute_counted(self):
        for wizard in self:
            wizard.counted_amount = sum(wizard.line_ids.mapped("subtotal"))
            wizard.difference_amount = wizard.currency_id.round(wizard.counted_amount - wizard.expected_amount)

    def action_close_cash(self):
        self.ensure_one()
        if self.currency_id.compare_amounts(self.counted_amount, self.expected_amount):
            raise ValidationError(_("El efectivo contado no coincide con el esperado. Esperado: %(expected)s; contado: %(counted)s; diferencia: %(difference)s.") % {"expected": self.currency_id.format(self.expected_amount), "counted": self.currency_id.format(self.counted_amount), "difference": self.currency_id.format(self.difference_amount)})
        self.session_id.closing_line_ids.unlink()
        self.session_id.write({
            "closing_line_ids": [(0, 0, {"kind": "closing", "denomination_id": line.denomination_id.id, "quantity": line.quantity}) for line in self.line_ids],
            "deposit_reference": self.deposit_reference,
            "note": self.note,
        })
        self.session_id.action_close()
        return {"type": "ir.actions.act_window", "res_model": "doorandoor.cash.session", "res_id": self.session_id.id, "view_mode": "form", "target": "current"}


class DoorAndDoorCashCloseWizardLine(models.TransientModel):
    _name = "doorandoor.cash.close.wizard.line"
    _description = "Denominación de cierre de caja"

    wizard_id = fields.Many2one("doorandoor.cash.close.wizard", required=True, ondelete="cascade")
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True)
    quantity = fields.Integer(default=0, required=True)
    subtotal = fields.Monetary(compute="_compute_subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id")

    @api.depends("denomination_id.value", "quantity")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.denomination_id.value * line.quantity
