from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashCollectionRequest(models.Model):
    _name = "doorandoor.cash.collection.request"
    _description = "Solicitud de cobro en efectivo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date, id"

    name = fields.Char(default=lambda self: self.env["ir.sequence"].next_by_code("doorandoor.cash.collection.request") or _("Nuevo"), readonly=True)
    invoice_id = fields.Many2one("account.move", required=True, readonly=True, ondelete="restrict", index=True)
    register_id = fields.Many2one("doorandoor.cash.register", required=True, readonly=True, ondelete="restrict")
    city_rule_id = fields.Many2one(related="invoice_id.ddts_tax_city_rule_id", readonly=True)
    salesperson_id = fields.Many2one("res.users", required=True, readonly=True)
    cashier_id = fields.Many2one("res.users", readonly=True)
    payment_id = fields.Many2one("account.payment", readonly=True, ondelete="restrict")
    currency_id = fields.Many2one(related="invoice_id.currency_id", readonly=True)
    amount = fields.Monetary(
        string="Importe a cobrar",
        compute="_compute_amount",
        readonly=True,
        currency_field="currency_id",
    )
    state = fields.Selection([
        ("pending", "Pendiente de cobro"),
        ("waiting_archeo", "En espera de arqueo"),
        ("paid", "Cobrado"),
        ("cancelled", "Cancelado"),
    ], default="pending", required=True, readonly=True, tracking=True)

    @api.depends(
        "invoice_id.amount_residual",
        "invoice_id.ddc_total_validated",
        "payment_id.amount",
        "state",
    )
    def _compute_amount(self):
        for request in self:
            if request.payment_id:
                request.amount = request.payment_id.amount
            elif request.invoice_id:
                request.amount = request.invoice_id._ddcc_cash_collection_amount()
            else:
                request.amount = 0.0

    def _notify_cashiers(self, body):
        for request in self:
            # The salesperson owns the request but must not receive direct
            # access to cash-register configuration.  Read only the routing
            # data with elevated privileges and post the notification on the
            # request with the original user/environment.
            routing_request = request.sudo()
            register = routing_request.register_id
            users = register.cashier_ids | register.manager_ids
            if not register.city_rule_id:
                users = self.env.ref("base.group_system").users
            if not users:
                session = self.env["doorandoor.cash.session"].sudo().search([
                    ("register_id", "=", register.id), ("state", "=", "open"),
                ], limit=1)
                users = session.cashier_id
            request.message_post(body=body, partner_ids=users.mapped("partner_id").ids,
                                 message_type="notification", subtype_xmlid="mail.mt_note")

    def action_open_invoice(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "account.move", "res_id": self.invoice_id.id, "view_mode": "form", "target": "current"}

    def action_open_cash_payment(self):
        self.ensure_one()
        if self.state != "pending":
            raise ValidationError(_("Esta solicitud no está disponible para cobro."))
        if self.invoice_id.amount_residual <= 0:
            raise ValidationError(_("La factura ya no tiene saldo pendiente."))
        if not self.register_id.city_rule_id:
            if not self.env.user.has_group("base.group_system"):
                raise ValidationError(_(
                    "La caja general, sin ciudad asignada, solo puede ser operada por Administración general."
                ))
        elif (
            self.env.user not in (self.register_id.cashier_ids | self.register_id.manager_ids)
            and not self.env.user.has_group("base.group_system")
        ):
            raise ValidationError(_("Solo los operadores o responsables asignados a esta caja pueden confirmar el cobro."))
        action = self.invoice_id.action_register_payment()
        context = dict(action.get("context", {}), default_journal_id=self.register_id.cash_journal_id.id,
                       default_amount=self.amount, default_custom_user_amount=self.amount,
                       ddcc_cash_request_id=self.id)
        action["context"] = context
        return action

    def action_cancel(self):
        self.filtered(lambda r: r.state in ("pending", "waiting_archeo")).write({"state": "cancelled"})

    @classmethod
    def _ddcc_set_waiting_for_register(cls, env, register):
        env["doorandoor.cash.collection.request"].search([
            ("register_id", "=", register.id), ("state", "=", "pending"),
        ]).write({"state": "waiting_archeo"})

    @classmethod
    def _ddcc_release_for_register(cls, env, register):
        env["doorandoor.cash.collection.request"].search([
            ("register_id", "=", register.id), ("state", "=", "waiting_archeo"),
        ]).write({"state": "pending"})
