from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashOpenWizard(models.TransientModel):
    _name = "doorandoor.cash.open.wizard"
    _description = "Apertura de caja"

    register_id = fields.Many2one(
        "doorandoor.cash.register",
        required=True,
        domain=lambda self: self._ddcc_allowed_register_domain(),
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("doorandoor.cash.open.wizard.line", "wizard_id", string="Fondo de cambio")
    currency_id = fields.Many2one(related="register_id.company_id.currency_id")
    amount = fields.Monetary(compute="_compute_amount", currency_field="currency_id")

    def _ddcc_allowed_register_domain(self):
        if self.env.user.has_group("base.group_system"):
            return [("active", "=", True)]
        return [
            ("active", "=", True),
            "|",
            ("cashier_ids", "in", [self.env.user.id]),
            ("manager_ids", "in", [self.env.user.id]),
        ]

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        denoms = self.env["doorandoor.cash.denomination"].search([
            ("active", "=", True), ("currency_id", "=", self.env.company.currency_id.id),
        ])
        values["line_ids"] = [(0, 0, {"denomination_id": denom.id, "quantity": 0}) for denom in denoms]
        return values

    @api.depends("line_ids.subtotal")
    def _compute_amount(self):
        for wizard in self:
            wizard.amount = sum(wizard.line_ids.mapped("subtotal"))

    def action_open_cash(self):
        self.ensure_one()
        allowed = self.env["doorandoor.cash.register"].search(
            self._ddcc_allowed_register_domain() + [("id", "=", self.register_id.id)],
            limit=1,
        )
        if not allowed:
            raise ValidationError(_("No está autorizado para abrir esta caja."))
        existing = self.env["doorandoor.cash.session"].search([
            ("register_id", "=", self.register_id.id), ("date", "=", self.date),
        ], limit=1)
        if existing:
            raise ValidationError(_("La caja %(register)s ya tiene la sesión %(session)s para esta fecha.") % {"register": self.register_id.display_name, "session": existing.name})
        session = self.env["doorandoor.cash.session"].create({
            "register_id": self.register_id.id, "date": self.date,
            "opening_line_ids": [(0, 0, {"kind": "opening", "denomination_id": line.denomination_id.id, "quantity": line.quantity}) for line in self.line_ids],
        })
        session.action_open()
        return {"type": "ir.actions.act_window", "res_model": "doorandoor.cash.session", "res_id": session.id, "view_mode": "form", "target": "current"}


class DoorAndDoorCashOpenWizardLine(models.TransientModel):
    _name = "doorandoor.cash.open.wizard.line"
    _description = "Denominación de apertura de caja"

    wizard_id = fields.Many2one("doorandoor.cash.open.wizard", required=True, ondelete="cascade")
    denomination_id = fields.Many2one("doorandoor.cash.denomination", required=True)
    quantity = fields.Integer(default=0, required=True)
    subtotal = fields.Monetary(compute="_compute_subtotal", currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id")

    @api.depends("denomination_id.value", "quantity")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.denomination_id.value * line.quantity
