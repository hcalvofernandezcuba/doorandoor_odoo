from datetime import datetime, timezone

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    ddsr_bank_journal_id = fields.Many2one(
        "account.journal",
        string="Diario de depósito Stripe",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        check_company=True,
        help="Diario de City National donde se reciben las liquidaciones de Stripe.",
    )
    ddsr_auto_sync = fields.Boolean(
        string="Sincronizar liquidaciones automáticamente",
        help="Consulta periódicamente los payouts de Stripe. Viene desactivado para permitir pruebas controladas.",
    )
    ddsr_last_sync_at = fields.Datetime(
        string="Última sincronización de liquidaciones", readonly=True, copy=False
    )

    @api.constrains("code", "journal_id")
    def _check_ddsr_stripe_journal_is_immediate(self):
        for provider in self.filtered(lambda item: item.code == "stripe" and item.journal_id):
            if provider.journal_id.ddc_payment_flow != "immediate":
                raise ValidationError(
                    _(
                        "El diario del proveedor Stripe debe usar Validación inmediata; "
                        "los pagos confirmados por webhook no requieren revisión humana."
                    )
                )

    def action_ddsr_set_journal_immediate(self):
        for provider in self.filtered(lambda item: item.code == "stripe" and item.journal_id):
            provider.journal_id.write(
                {"ddc_payment_flow": "immediate", "ddc_requires_payment_control": False}
            )
        return True

    def action_ddsr_prepare_payment_journal(self):
        """Prepare the Stripe clearing journal without enabling live payments."""
        self.ensure_one()
        if self.code != "stripe":
            raise UserError(_("Esta acción solo está disponible para proveedores Stripe."))

        account = self.env["account.account"].search(
            [
                ("company_ids", "in", self.company_id.id),
                ("name", "=", "Stripe - Fondos por liquidar"),
            ],
            limit=1,
        )
        if not account:
            used_codes = set(
                self.env["account.account"].search(
                    [("company_ids", "in", self.company_id.id)]
                ).mapped("code")
            )
            account_code = next(
                (str(candidate) for candidate in range(101406, 101500) if str(candidate) not in used_codes),
                False,
            )
            if not account_code:
                raise UserError(_("No hay un código contable disponible entre 101406 y 101499."))
            account = self.env["account.account"].create(
                {
                    "name": "Stripe - Fondos por liquidar",
                    "code": account_code,
                    "account_type": "asset_current",
                    "reconcile": True,
                    "company_ids": [Command.set(self.company_id.ids)],
                }
            )

        journal = self.journal_id.filtered(
            lambda item: item.code == "STRP" and item.type == "bank"
        ) or self.env["account.journal"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("code", "=", "STRP"),
                ("type", "=", "bank"),
            ],
            limit=1,
        )
        if not journal:
            journal = self.env["account.journal"].create(
                {
                    "name": "Stripe",
                    "code": "STRP",
                    "type": "bank",
                    "company_id": self.company_id.id,
                    "currency_id": self.company_id.currency_id.id,
                    "default_account_id": account.id,
                    "ddc_payment_flow": "immediate",
                    "ddc_requires_payment_control": False,
                }
            )
        else:
            journal.write(
                {
                    "default_account_id": account.id,
                    "ddc_payment_flow": "immediate",
                    "ddc_requires_payment_control": False,
                }
            )

        self.write({"journal_id": journal.id})
        stripe_lines = journal.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id.code == "stripe"
        )
        stripe_lines.write({"payment_account_id": account.id})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Stripe preparado"),
                "message": _(
                    "El diario Stripe quedó configurado como vía inmediata. "
                    "Las tarjetas se activarán al configurar Stripe en modo sandbox."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_ddsr_sync_settlements(self):
        self.ensure_one()
        if self.code != "stripe":
            raise UserError(_("Esta acción solo está disponible para proveedores Stripe."))
        if not self.stripe_secret_key:
            raise UserError(_("Configure primero la clave secreta de Stripe."))

        settlements = self.env["doorandoor.stripe.settlement"]
        starting_after = None
        while True:
            payload = {"limit": 100}
            if starting_after:
                payload["starting_after"] = starting_after
            response = self._stripe_make_request("payouts", payload=payload, method="GET")
            payouts = response.get("data", [])
            for payout_data in payouts:
                settlements |= self.env["doorandoor.stripe.settlement"]._ddsr_upsert_from_stripe(
                    self, payout_data
                )
            if not response.get("has_more") or not payouts:
                break
            starting_after = payouts[-1]["id"]

        self.ddsr_last_sync_at = fields.Datetime.now()
        settlements._ddsr_refresh_balance_transactions()
        return {
            "type": "ir.actions.act_window",
            "name": _("Liquidaciones Stripe"),
            "res_model": "doorandoor.stripe.settlement",
            "view_mode": "list,form",
            "domain": [("provider_id", "=", self.id)],
        }

    @api.model
    def _cron_ddsr_sync_settlements(self):
        providers = self.search(
            [("code", "=", "stripe"), ("state", "in", ("test", "enabled")), ("ddsr_auto_sync", "=", True)]
        )
        for provider in providers:
            provider.action_ddsr_sync_settlements()

    @api.model
    def _ddsr_stripe_timestamp_to_datetime(self, value):
        if not value:
            return False
        return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
