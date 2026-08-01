from odoo import _, api, fields, models


class DoorAndDoorCobroControl(models.Model):
    _name = "doorandoor.cobro.control"
    _description = "Control de Cobro"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Numero",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
    )
    active = fields.Boolean(default=True)
    move_id = fields.Many2one(
        "account.move",
        string="Factura",
        required=True,
        domain=[("move_type", "=", "out_invoice")],
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        required=True,
        default=lambda self: self.env.company.id,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario reportado",
        domain="[('type', 'in', ('bank', 'cash'))]",
        tracking=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        copy=False,
        readonly=True,
    )
    payment_state = fields.Selection(
        related="payment_id.state",
        string="Estado del pago",
        store=True,
        readonly=True,
    )
    invoice_payment_state = fields.Selection(
        related="move_id.payment_state",
        string="Estado de la factura",
        store=True,
        readonly=True,
    )
    sale_user_id = fields.Many2one(
        "res.users",
        string="Reportado por",
        default=lambda self: self.env.user,
        tracking=True,
    )
    accountant_user_id = fields.Many2one(
        "res.users",
        string="Validado por",
        tracking=True,
        copy=False,
    )
    payment_date = fields.Date(
        string="Fecha reportada",
        default=fields.Date.context_today,
        tracking=True,
    )
    amount_reported = fields.Monetary(
        string="Monto reportado",
        required=True,
        tracking=True,
    )
    payment_reference = fields.Char(
        string="Referencia",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("reported", "Reportado"),
            ("pending", "Pendiente"),
            ("review", "En revision"),
            ("validated", "Validado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    review_date = fields.Datetime(
        string="Fecha de revision",
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string="Motivo de rechazo",
        copy=False,
    )
    notes = fields.Text(string="Notas")

    _sql_constraints = [
        ("amount_reported_positive", "CHECK(amount_reported > 0)", "El monto reportado debe ser mayor que cero."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("doorandoor.cobro.control") or _("Nuevo")
            if vals.get("move_id") and not vals.get("partner_id"):
                move = self.env["account.move"].browse(vals["move_id"])
                vals["partner_id"] = move.partner_id.id
                vals.setdefault("currency_id", move.currency_id.id)
                vals.setdefault("company_id", move.company_id.id)
        return super().create(vals_list)

    def action_report(self):
        for record in self:
            record.state = "reported"

    def action_mark_pending(self):
        for record in self:
            record.state = "pending"

    def action_review(self):
        for record in self:
            record.state = "review"
            record.review_date = fields.Datetime.now()

    def action_validate(self):
        for record in self:
            payment = record.payment_id
            if payment and payment.state in ("draft", "in_process"):
                if not payment.outstanding_account_id:
                    payment.outstanding_account_id = payment._get_outstanding_account(payment.payment_type)
                if not payment.move_id:
                    payment._generate_journal_entry()
                    payment.move_id.filtered(lambda move: move.state == "draft").action_post()
                record._ddc_reconcile_payment_with_invoice(payment)
                payment.action_post()
                payment.action_validate()
            record.state = "validated"
            record.accountant_user_id = self.env.user
            record.review_date = fields.Datetime.now()
            record.move_id._compute_ddc_collection_state()
            record.move_id._compute_payment_state()
            record.move_id._ddsn_sync_release_from_payments()

    def _ddc_reconcile_payment_with_invoice(self, payment):
        self.ensure_one()
        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == payment.destination_account_id
                and not line.reconciled
                and line.partner_id == payment.partner_id
            )
        )
        invoice_lines = self.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == payment.destination_account_id
                and not line.reconciled
                and line.partner_id == payment.partner_id
            )
        )
        if payment_lines and invoice_lines:
            (payment_lines | invoice_lines).reconcile()

    def action_reject(self):
        for record in self:
            record.state = "rejected"
            record.accountant_user_id = self.env.user
            record.review_date = fields.Datetime.now()
