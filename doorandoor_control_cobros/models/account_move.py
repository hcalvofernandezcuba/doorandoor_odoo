from odoo import _, api, fields, models


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
    ddc_payment_review_state = fields.Selection(
        selection=[
            ("no_control", "Sin control"),
            ("reviewing", "Revisando pago"),
            ("partial", "Pago parcial validado"),
            ("validated", "Pago validado"),
            ("rejected", "Pago rechazado"),
        ],
        string="Estado funcional del pago",
        compute="_compute_ddc_payment_review_state",
        store=True,
    )
    ddc_total_reported = fields.Monetary(
        string="Total reportado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_validated = fields.Monetary(
        string="Total validado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_rejected = fields.Monetary(
        string="Total rechazado",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_total_pending = fields.Monetary(
        string="Total pendiente",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )
    ddc_balance_pending = fields.Monetary(
        string="Saldo pendiente por validar",
        compute="_compute_ddc_control_totals",
        currency_field="currency_id",
        store=True,
    )

    def _compute_ddc_control_count(self):
        for move in self:
            move.ddc_control_count = len(move.ddc_control_ids)

    @api.depends(
        "move_type",
        "amount_total",
        "ddc_control_ids",
        "ddc_control_ids.state",
        "ddc_control_ids.amount_reported",
        "ddc_control_ids.validated_amount",
        "ddc_control_ids.active",
    )
    def _compute_ddc_control_totals(self):
        for move in self:
            if move.move_type != "out_invoice":
                move.ddc_total_reported = 0.0
                move.ddc_total_validated = 0.0
                move.ddc_total_rejected = 0.0
                move.ddc_total_pending = 0.0
                move.ddc_balance_pending = 0.0
                continue

            controls = move.ddc_control_ids.filtered(lambda control: control.active)
            move.ddc_total_reported = sum(
                controls.filtered(lambda control: control.state != "rejected").mapped("amount_reported")
            )
            move.ddc_total_validated = sum(
                controls.filtered(lambda control: control.state == "validated").mapped("validated_amount")
            )
            move.ddc_total_rejected = sum(
                controls.filtered(lambda control: control.state == "rejected").mapped("amount_reported")
            )
            move.ddc_total_pending = sum(
                controls.filtered(lambda control: control.state in ("draft", "reported", "pending", "review")).mapped("amount_reported")
            )
            move.ddc_balance_pending = max(move.amount_total - move.ddc_total_validated, 0.0)

    @api.depends("ddc_control_ids", "ddc_control_ids.state", "payment_state", "move_type", "ddc_total_validated", "amount_total")
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
            elif move.ddc_total_validated and move.currency_id.compare_amounts(move.ddc_total_validated, move.amount_total) < 0:
                move.ddc_collection_state = "validated"
            elif states == {"rejected"}:
                move.ddc_collection_state = "rejected"
            elif states and states.issubset({"validated"}):
                move.ddc_collection_state = "validated"
            else:
                move.ddc_collection_state = "pending"

    @api.depends("move_type", "ddc_collection_state", "ddc_control_ids", "ddc_control_ids.state", "ddc_total_validated", "amount_total")
    def _compute_ddc_payment_review_state(self):
        for move in self:
            if move.move_type != "out_invoice" or not move.ddc_control_ids:
                move.ddc_payment_review_state = "no_control"
                continue
            if move.ddc_collection_state == "validated":
                if move.currency_id.compare_amounts(move.ddc_total_validated, move.amount_total) < 0:
                    move.ddc_payment_review_state = "partial"
                else:
                    move.ddc_payment_review_state = "validated"
            elif move.ddc_collection_state == "rejected":
                move.ddc_payment_review_state = "rejected"
            else:
                move.ddc_payment_review_state = "reviewing"

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

    def _ddc_refresh_control_status(self):
        for move in self:
            move._compute_ddc_control_totals()
            move._compute_ddc_collection_state()
            move._compute_ddc_payment_review_state()
            move._compute_payment_state()
            move._ddsn_sync_release_from_payments()

    def _ddc_post_control_message(self, body):
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            move.message_post(body=body, subtype_xmlid="mail.mt_note")

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
            if move.ddc_collection_state == "rejected":
                move.payment_state = "not_paid"
                continue
            if move.ddc_collection_state == "pending":
                move.payment_state = "in_payment"
                continue
            if move.ddc_payment_review_state == "partial":
                move.payment_state = "partial"
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
