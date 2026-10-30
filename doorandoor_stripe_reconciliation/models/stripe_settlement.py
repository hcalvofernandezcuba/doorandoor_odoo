from datetime import datetime, timezone

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorandoorStripeSettlement(models.Model):
    _name = "doorandoor.stripe.settlement"
    _description = "Liquidación bancaria de Stripe"
    _order = "arrival_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True)
    provider_id = fields.Many2one(
        "payment.provider", required=True, readonly=True, ondelete="cascade", check_company=True
    )
    company_id = fields.Many2one(related="provider_id.company_id", store=True, readonly=True)
    journal_id = fields.Many2one(
        related="provider_id.ddsr_bank_journal_id", store=True, readonly=True
    )
    stripe_payout_id = fields.Char(required=True, readonly=True, copy=False, index=True)
    stripe_status = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("in_transit", "En tránsito"),
            ("paid", "Pagada"),
            ("failed", "Fallida"),
            ("canceled", "Cancelada"),
        ],
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    arrival_date = fields.Date(readonly=True)
    stripe_created_at = fields.Datetime(readonly=True)
    description = fields.Char(readonly=True)
    gross_amount = fields.Monetary(compute="_compute_totals", store=True)
    fee_amount = fields.Monetary(compute="_compute_totals", store=True)
    net_amount = fields.Monetary(compute="_compute_totals", store=True)
    payout_amount = fields.Monetary(required=True, readonly=True)
    difference_amount = fields.Monetary(compute="_compute_totals", store=True)
    line_ids = fields.One2many(
        "doorandoor.stripe.settlement.line", "settlement_id", string="Movimientos Stripe", readonly=True
    )
    statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Movimiento bancario propuesto",
        check_company=True,
        copy=False,
    )
    match_state = fields.Selection(
        [("pending", "Pendiente"), ("proposed", "Propuesta"), ("confirmed", "Confirmada")],
        default="pending",
        required=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "stripe_payout_company_unique",
            "UNIQUE(stripe_payout_id, company_id)",
            "La liquidación Stripe ya existe para esta compañía.",
        )
    ]

    @api.depends("line_ids.amount", "line_ids.fee", "line_ids.net", "payout_amount")
    def _compute_totals(self):
        for settlement in self:
            settlement.gross_amount = sum(settlement.line_ids.mapped("amount"))
            settlement.fee_amount = sum(settlement.line_ids.mapped("fee"))
            settlement.net_amount = sum(settlement.line_ids.mapped("net"))
            settlement.difference_amount = settlement.payout_amount - settlement.net_amount

    @api.model
    def _ddsr_upsert_from_stripe(self, provider, data):
        currency = self.env["res.currency"].search(
            [("name", "=", (data.get("currency") or "").upper())], limit=1
        )
        if not currency:
            raise ValidationError(_("Stripe devolvió una moneda desconocida: %s") % data.get("currency"))
        divisor = 10 ** currency.decimal_places
        created = data.get("created")
        values = {
            "name": data["id"],
            "provider_id": provider.id,
            "stripe_payout_id": data["id"],
            "stripe_status": data.get("status", "pending"),
            "currency_id": currency.id,
            "arrival_date": data.get("arrival_date")
            and datetime.fromtimestamp(data["arrival_date"], tz=timezone.utc).date(),
            "stripe_created_at": created
            and datetime.fromtimestamp(created, tz=timezone.utc).replace(tzinfo=None),
            "description": data.get("description"),
            "payout_amount": data.get("amount", 0) / divisor,
        }
        settlement = self.search(
            [("stripe_payout_id", "=", data["id"]), ("company_id", "=", provider.company_id.id)],
            limit=1,
        )
        if settlement:
            settlement.write(values)
        else:
            settlement = self.create(values)
        return settlement

    def _ddsr_refresh_balance_transactions(self):
        line_model = self.env["doorandoor.stripe.settlement.line"]
        for settlement in self:
            starting_after = None
            while True:
                payload = {"payout": settlement.stripe_payout_id, "limit": 100}
                if starting_after:
                    payload["starting_after"] = starting_after
                response = settlement.provider_id._stripe_make_request(
                    "balance_transactions", payload=payload, method="GET"
                )
                items = response.get("data", [])
                for item in items:
                    line_model._ddsr_upsert_from_stripe(settlement, item)
                if not response.get("has_more") or not items:
                    break
                starting_after = items[-1]["id"]
            settlement.action_ddsr_propose_bank_line()

    def action_ddsr_propose_bank_line(self):
        for settlement in self.filtered(lambda record: record.journal_id and not record.statement_line_id):
            date_from = fields.Date.subtract(settlement.arrival_date, days=3)
            date_to = fields.Date.add(settlement.arrival_date, days=3)
            candidates = self.env["account.bank.statement.line"].search(
                [
                    ("journal_id", "=", settlement.journal_id.id),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                    ("amount", ">=", settlement.payout_amount - 0.01),
                    ("amount", "<=", settlement.payout_amount + 0.01),
                ],
                order="date asc, id asc",
                limit=2,
            )
            if len(candidates) == 1:
                settlement.write({"statement_line_id": candidates.id, "match_state": "proposed"})
        return True

    def action_ddsr_confirm_proposal(self):
        for settlement in self:
            if not settlement.statement_line_id:
                raise ValidationError(_("Seleccione primero el movimiento bancario del depósito."))
            settlement.match_state = "confirmed"
        return True


class DoorandoorStripeSettlementLine(models.Model):
    _name = "doorandoor.stripe.settlement.line"
    _description = "Movimiento de una liquidación Stripe"
    _order = "available_date, id"
    _check_company_auto = True

    settlement_id = fields.Many2one(
        "doorandoor.stripe.settlement", required=True, ondelete="cascade", check_company=True
    )
    company_id = fields.Many2one(related="settlement_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="settlement_id.currency_id", store=True, readonly=True)
    stripe_balance_transaction_id = fields.Char(required=True, readonly=True, index=True)
    source_reference = fields.Char(readonly=True, index=True)
    transaction_type = fields.Char(readonly=True)
    description = fields.Char(readonly=True)
    available_date = fields.Date(readonly=True)
    amount = fields.Monetary(readonly=True)
    fee = fields.Monetary(readonly=True)
    net = fields.Monetary(readonly=True)
    payment_transaction_id = fields.Many2one("payment.transaction", readonly=True, copy=False)

    _sql_constraints = [
        (
            "stripe_balance_transaction_company_unique",
            "UNIQUE(stripe_balance_transaction_id, company_id)",
            "El movimiento de saldo Stripe ya fue importado para esta compañía.",
        )
    ]

    @api.model
    def _ddsr_upsert_from_stripe(self, settlement, data):
        divisor = 10 ** settlement.currency_id.decimal_places
        source = data.get("source")
        transaction = self.env["payment.transaction"].search(
            [
                ("provider_id", "=", settlement.provider_id.id),
                ("provider_reference", "=", source),
            ],
            limit=1,
        )
        values = {
            "settlement_id": settlement.id,
            "stripe_balance_transaction_id": data["id"],
            "source_reference": source,
            "transaction_type": data.get("type"),
            "description": data.get("description"),
            "available_date": data.get("available_on")
            and datetime.fromtimestamp(data["available_on"], tz=timezone.utc).date(),
            "amount": data.get("amount", 0) / divisor,
            "fee": data.get("fee", 0) / divisor,
            "net": data.get("net", 0) / divisor,
            "payment_transaction_id": transaction.id,
        }
        line = self.search(
            [
                ("stripe_balance_transaction_id", "=", data["id"]),
                ("company_id", "=", settlement.company_id.id),
            ],
            limit=1,
        )
        if line:
            line.write(values)
        else:
            line = self.create(values)
        return line
