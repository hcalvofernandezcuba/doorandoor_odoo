from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddc_control_ids = fields.One2many(
        "doorandoor.cobro.control",
        "move_id",
        string="Controles de cobro",
        copy=False,
    )
    ddc_control_count = fields.Integer(
        string="Controles de cobro",
        compute="_compute_ddc_control_count",
    )
    ddc_collection_state = fields.Selection(
        selection=[
            ("not_applicable", "No aplica"),
            ("pending", "Pendiente revision"),
            ("validated", "Validado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado de control de cobro",
        compute="_compute_ddc_collection_state",
        store=True,
    )

    def _compute_ddc_control_count(self):
        for move in self:
            move.ddc_control_count = len(move.ddc_control_ids)

    @api.depends("ddc_control_ids", "ddc_control_ids.state", "payment_state", "move_type")
    def _compute_ddc_collection_state(self):
        for move in self:
            if move.move_type != "out_invoice":
                move.ddc_collection_state = "not_applicable"
                continue
            if not move.ddc_control_ids:
                move.ddc_collection_state = "not_applicable"
                continue
            states = set(move.ddc_control_ids.mapped("state"))
            if states & {"pending", "reported", "review"}:
                move.ddc_collection_state = "pending"
            elif states == {"rejected"}:
                move.ddc_collection_state = "rejected"
            elif states and states.issubset({"validated"}):
                move.ddc_collection_state = "validated"
            else:
                move.ddc_collection_state = "pending"

    def action_view_ddc_controls(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_control_cobros.action_ddc_cobro_control").read()[0]
        action["domain"] = [("move_id", "=", self.id)]
        action["context"] = {
            "default_move_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_currency_id": self.currency_id.id,
            "default_amount_reported": self.amount_residual,
        }
        return action

    def _ddc_has_pending_controls(self):
        self.ensure_one()
        return bool(self.ddc_control_ids.filtered(lambda control: control.state in ("draft", "reported", "pending", "review")))

    def _ddsn_sync_release_from_payments(self):
        if self.env.context.get("ddc_skip_release_sync"):
            for move in self:
                move._ddsn_set_release_state()
            return

        blocked_moves = self.filtered(lambda move: move._ddc_has_pending_controls())
        for move in blocked_moves:
            move._ddsn_set_release_state()

        return super(AccountMove, self - blocked_moves)._ddsn_sync_release_from_payments()

    def _ddsn_is_fully_paid(self):
        self.ensure_one()
        if self._ddc_has_pending_controls():
            return False
        return super()._ddsn_is_fully_paid()

    @api.depends_context("lang")
    @api.depends(
        "payment_state",
        "amount_residual",
        "move_type",
        "state",
        "ddc_collection_state",
        "ddc_control_ids.state",
    )
    def _compute_payment_state(self):
        super()._compute_payment_state()
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.state != "posted":
                continue
            if move.ddc_collection_state != "validated":
                continue
            if move._ddc_has_pending_controls():
                continue
            if not move.currency_id.is_zero(move.amount_residual):
                continue
            move.payment_state = "paid"
