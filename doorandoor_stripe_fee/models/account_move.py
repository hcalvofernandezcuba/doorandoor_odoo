from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    ddtp_payment_plan = fields.Selection([
        ("full", "Pago total"),
        ("partial", "Pago parcial: 50% + impuestos"),
    ], string="Tipo de pago", default="full", copy=False)
    ddtp_payment_due_amount = fields.Monetary(
        string="Importe a cobrar", compute="_compute_ddtp_payment_due_amount",
        currency_field="currency_id", readonly=True,
    )
    ddtp_payment_pending_amount = fields.Monetary(
        string="Saldo pendiente", compute="_compute_ddtp_payment_pending_amount",
        currency_field="currency_id", readonly=True,
    )

    ddtp_card_fee_invoice_ids = fields.One2many(
        "account.move", "ddtp_origin_invoice_id", string="Cargos por tarjeta"
    )
    ddtp_origin_invoice_id = fields.Many2one(
        "account.move", string="Factura de origen", copy=False, index=True
    )
    ddtp_is_card_fee_invoice = fields.Boolean(
        string="Cargo por pago con tarjeta", copy=False, index=True
    )
    ddtp_card_payment_enabled = fields.Boolean(
        string="Pago con tarjeta", copy=False,
        help="Añade el cargo de procesamiento a esta factura antes de publicarla.",
    )
    ddtp_card_payment_amount = fields.Monetary(
        string="Importe a cobrar con tarjeta", copy=False, currency_field="currency_id",
        help="Importe de la factura que se cobrará en la primera operación con tarjeta, sin el cargo.",
    )
    ddtp_card_fee_line_id = fields.Many2one(
        "account.move.line", string="Línea de cargo por tarjeta", copy=False, readonly=True
    )
    ddtp_card_fee_amount = fields.Monetary(
        string="Cargo por procesamiento", compute="_compute_ddtp_card_fee_amount",
        currency_field="currency_id", store=True,
    )
    ddtp_card_fee_preview = fields.Monetary(
        string="Cargo por procesamiento", compute="_compute_ddtp_card_payment_preview",
        currency_field="currency_id", readonly=True,
    )
    ddtp_card_fee_rate = fields.Float(
        string="Porcentaje de cargo por tarjeta", compute="_compute_ddtp_card_payment_preview",
        readonly=True,
    )
    ddtp_card_fee_rate_display = fields.Char(
        string="Porcentaje de cargo por tarjeta visible",
        compute="_compute_ddtp_card_fee_rate_display",
        readonly=True,
    )
    ddtp_card_total_preview = fields.Monetary(
        string="Total con tarjeta", compute="_compute_ddtp_card_payment_preview",
        currency_field="currency_id", readonly=True,
    )

    @api.depends("ddtp_payment_plan", "amount_untaxed", "amount_tax")
    def _compute_ddtp_payment_due_amount(self):
        for move in self:
            if move.ddtp_payment_plan == "partial":
                move.ddtp_payment_due_amount = move.currency_id.round(
                    move.amount_untaxed * 0.5 + move.amount_tax
                )
            else:
                move.ddtp_payment_due_amount = move.amount_total

    @api.depends(
        "ddtp_payment_plan", "ddtp_payment_due_amount", "ddtp_card_payment_amount",
        "amount_total", "ddtp_card_fee_amount",
    )
    def _compute_ddtp_payment_pending_amount(self):
        for move in self:
            # The processing fee is not part of the commercial balance.  In a
            # partial card collection the customer pays the deposit plus its
            # fee, while the pending amount is the remaining sale amount.
            # The technical ``cogs`` fee line increases receivables but is
            # deliberately excluded from Odoo's commercial ``amount_total``.
            # Therefore do not subtract it here a second time.
            base_total = move.amount_total
            commercial_payment = (
                move.ddtp_card_payment_amount or move.ddtp_payment_due_amount
            )
            move.ddtp_payment_pending_amount = move.currency_id.round(
                max(base_total - commercial_payment, 0.0)
            ) if move.ddtp_payment_plan == "partial" else 0.0

    @api.depends(
        "ddtp_card_fee_line_id.price_total",
        "ddtp_card_fee_line_id.amount_currency",
        "ddtp_card_fee_line_id.balance",
    )
    def _compute_ddtp_card_fee_amount(self):
        for move in self:
            fee_line = move.ddtp_card_fee_line_id
            move.ddtp_card_fee_amount = abs(fee_line.amount_currency) if fee_line else 0.0

    @api.depends(
        "ddtp_card_payment_enabled", "ddtp_card_payment_amount", "ddtp_card_fee_amount",
        "amount_total", "company_id",
    )
    def _compute_ddtp_card_payment_preview(self):
        for move in self:
            provider = self.env["payment.provider"]._ddtp_get_active_card_provider(move.company_id)
            move.ddtp_card_fee_rate = provider.ddtp_card_fee_rate if provider else 0.0
            base_amount = move._ddtp_get_planned_card_amount()
            fee_amount = move.ddtp_card_fee_amount
            if move.ddtp_card_payment_enabled and not fee_amount and provider:
                fee_amount = move.currency_id.round(base_amount * provider.ddtp_card_fee_rate / 100.0)
            move.ddtp_card_fee_preview = fee_amount if move.ddtp_card_payment_enabled else 0.0
            move.ddtp_card_total_preview = base_amount + fee_amount if move.ddtp_card_payment_enabled else 0.0

    @api.depends("ddtp_card_fee_rate")
    def _compute_ddtp_card_fee_rate_display(self):
        for move in self:
            move.ddtp_card_fee_rate_display = move._ddtp_format_percent(
                move.ddtp_card_fee_rate
            )

    @api.model
    def _ddtp_format_percent(self, rate):
        """Compact visual percentage; the stored charge rate is unchanged."""
        text = ("%.10f" % (rate or 0.0)).rstrip("0").rstrip(".")
        return text.replace(".", ",")

    @api.onchange("ddtp_card_payment_enabled")
    def _onchange_ddtp_card_payment_enabled(self):
        for move in self:
            if move.ddtp_card_payment_enabled and not move.ddtp_card_fee_line_id:
                move.ddtp_card_payment_amount = move.ddtp_payment_due_amount

    @api.onchange("ddtp_payment_plan", "amount_untaxed", "amount_tax")
    def _onchange_ddtp_payment_plan(self):
        for move in self:
            if not move.ddtp_card_payment_enabled:
                continue
            if move.ddtp_card_fee_line_id:
                move._ddtp_refresh_card_fee_after_tax_change()
            else:
                move.ddtp_card_payment_amount = move.ddtp_payment_due_amount

    def _ddtp_refresh_card_fee_after_tax_change(self):
        """Rebase a prepared card surcharge after a draft tax change.

        A city change updates commercial taxes, but an already-created
        technical fee line has a fixed amount.  Refresh it before posting so
        the visible tax, card fee and receivable always describe the same
        draft invoice.
        """
        for move in self:
            if (
                move.move_type != "out_invoice"
                or move.state != "draft"
                or not move.ddtp_card_payment_enabled
                or not move.ddtp_card_fee_line_id
            ):
                continue
            provider = self.env["payment.provider"]._ddtp_get_active_card_provider(move.company_id)
            if not provider:
                continue
            base_amount = move._ddtp_get_planned_card_amount()
            new_fee = move.currency_id.round(base_amount * provider.ddtp_card_fee_rate / 100.0)
            fee_line = move.ddtp_card_fee_line_id
            move.with_context(check_move_validity=False).ddtp_card_payment_amount = base_amount
            fee_line.with_context(check_move_validity=False, ddtp_card_fee_line=True).write({
                "amount_currency": -new_fee,
                "balance": -move.currency_id._convert(
                    new_fee,
                    move.company_currency_id,
                    move.company_id,
                    move.invoice_date or move.date or fields.Date.context_today(move),
                ),
            })
            payment_term_line = move.line_ids.filtered(
                lambda item: item.display_type == "payment_term"
            )[-1:]
            if payment_term_line:
                # A tax recomputation can rebuild the receivable without the
                # technical cogs line. Derive the exact balancing amount from
                # every other line instead of assuming the old fee remains.
                payment_term_lines = move.line_ids.filtered(
                    lambda item: item.display_type == "payment_term"
                )
                other_lines = move.line_ids - payment_term_lines
                desired_balance = -sum(other_lines.mapped("balance"))
                desired_amount_currency = -sum(other_lines.mapped("amount_currency"))
                payment_term_line.with_context(check_move_validity=False).write({
                    "balance": payment_term_line.balance + desired_balance - sum(payment_term_lines.mapped("balance")),
                    "amount_currency": payment_term_line.amount_currency + desired_amount_currency - sum(payment_term_lines.mapped("amount_currency")),
                })

    def _ddtp_get_card_provider(self):
        self.ensure_one()
        provider = self.env["payment.provider"]._ddtp_get_active_card_provider(self.company_id)
        if not provider:
            raise ValidationError(_("No hay un proveedor de pagos con tarjeta activo para esta compañía."))
        provider._ddtp_validate_card_fee_configuration()
        return provider

    def _ddtp_get_planned_card_amount(self):
        """Compute the card principal from the invoice's current totals."""
        self.ensure_one()
        if self.ddtp_payment_plan == "partial":
            return self.ddtp_payment_due_amount
        return self.amount_total

    def action_ddtp_apply_card_fee(self):
        for move in self:
            if move.move_type != "out_invoice" or move.state != "draft":
                raise ValidationError(_("El cargo por tarjeta solo se prepara en facturas de cliente en borrador."))
            if not move.ddtp_card_payment_enabled:
                raise ValidationError(_("Active Pago con tarjeta antes de aplicar el cargo."))
            if move.ddtp_card_fee_line_id:
                continue
            base_amount = move._ddtp_get_planned_card_amount()
            move.ddtp_card_payment_amount = base_amount
            if base_amount <= 0 or move.currency_id.compare_amounts(base_amount, move.amount_total) > 0:
                raise ValidationError(_("El importe de tarjeta debe ser mayor que cero y no superar el total actual."))
            provider = move._ddtp_get_card_provider()
            fee_amount = move.currency_id.round(base_amount * provider.ddtp_card_fee_rate / 100.0)
            fee_product = provider.ddtp_card_fee_product_id
            income_account = (
                fee_product.property_account_income_id
                or fee_product.categ_id.property_account_income_categ_id
            )
            if not income_account:
                raise ValidationError(_(
                    "Configure una cuenta de ingresos para el cargo por pago con tarjeta."
                ))
            line = self.env["account.move.line"].with_company(move.company_id).with_context(
                check_move_validity=False, ddtp_card_fee_line=True
            ).create({
                "move_id": move.id,
                "name": _("Cargo por procesamiento de pago con tarjeta - %(rate)s%%") % {
                    "rate": provider.ddtp_card_fee_rate,
                },
                # A technical accounting line: it increases the receivable and
                # credits income, but is intentionally excluded from invoice
                # products. The customer sees it only in the totals block.
                "display_type": "cogs",
                "account_id": income_account.id,
                "partner_id": move.partner_id.id,
                "currency_id": move.currency_id.id,
                "amount_currency": -fee_amount,
                "balance": -move.currency_id._convert(
                    fee_amount,
                    move.company_currency_id,
                    move.company_id,
                    move.invoice_date or move.date or fields.Date.context_today(move),
                ),
            })
            move.with_context(check_move_validity=False).ddtp_card_fee_line_id = line
            # The receivable is already present on a draft invoice. Increase
            # its last due installment by the surcharge so the move remains
            # balanced without inserting a commercial invoice line.
            payment_term_lines = move.line_ids.filtered(
                lambda item: item.display_type == "payment_term"
            )
            if not payment_term_lines:
                raise ValidationError(_(
                    "No se encontró la cuenta por cobrar de la factura para aplicar el cargo de tarjeta."
                ))
            payment_term_line = payment_term_lines[-1]
            converted_fee = move.currency_id._convert(
                fee_amount,
                move.company_currency_id,
                move.company_id,
                move.invoice_date or move.date or fields.Date.context_today(move),
            )
            payment_term_line.with_context(check_move_validity=False).write({
                "balance": payment_term_line.balance + converted_fee,
                "amount_currency": payment_term_line.amount_currency + fee_amount,
            })
        return True

    def action_ddsn_create_invoice_from_preinvoice(self):
        """Carry the selected card payment from prefactura to its invoice."""
        self.ensure_one()
        action = super().action_ddsn_create_invoice_from_preinvoice()
        invoice = self.ddsn_created_invoice_id
        if self.ddtp_card_payment_enabled and invoice and not invoice.ddtp_card_payment_enabled:
            invoice.write({
                "ddtp_card_payment_enabled": True,
                "ddtp_card_payment_amount": self._ddtp_get_planned_card_amount(),
                "ddtp_payment_plan": self.ddtp_payment_plan,
            })
        return action

    def action_post(self):
        for move in self.filtered(lambda item: item.move_type == "out_invoice" and item.ddtp_card_payment_enabled):
            if move.ddtp_card_fee_line_id:
                move._ddtp_refresh_card_fee_after_tax_change()
            else:
                move.action_ddtp_apply_card_fee()
        return super().action_post()

    def button_draft(self):
        """Return a prepared card invoice to its commercial draft safely.

        Odoo removes ``cogs`` lines while resetting an invoice to draft.  The
        card surcharge is intentionally such a technical line, so the native
        reset removes its credit but leaves the extra amount in receivables.
        Capture the surcharge first, let Odoo rebuild the draft without the
        intermediate balance check, and remove the same amount from the due
        line before validating the resulting commercial draft.
        """
        fee_amounts = {
            move.id: abs(move.ddtp_card_fee_line_id.amount_currency)
            for move in self.filtered(
                lambda item: item.move_type == "out_invoice" and item.ddtp_card_fee_line_id
            )
        }
        result = super(AccountMove, self.with_context(check_move_validity=False)).button_draft()
        for move in self.filtered(lambda item: item.id in fee_amounts and item.state == "draft"):
            fee_amount = fee_amounts[move.id]
            if not fee_amount:
                continue
            converted_fee = move.currency_id._convert(
                fee_amount,
                move.company_currency_id,
                move.company_id,
                move.invoice_date or move.date or fields.Date.context_today(move),
            )
            payment_term_line = move.line_ids.filtered(
                lambda item: item.display_type == "payment_term"
            )[-1:]
            if not payment_term_line:
                raise ValidationError(_(
                    "No se encontró la cuenta por cobrar al devolver la factura a borrador."
                ))
            payment_term_line.with_context(check_move_validity=False).write({
                "balance": payment_term_line.balance - converted_fee,
                "amount_currency": payment_term_line.amount_currency - fee_amount,
            })
            move.with_context(check_move_validity=False).ddtp_card_fee_line_id = False
            imbalance = sum(move.line_ids.mapped("balance"))
            if not move.company_currency_id.is_zero(imbalance):
                raise ValidationError(_(
                    "La factura no quedó balanceada al devolverla a borrador. Diferencia: %(amount)s."
                ) % {"amount": move.company_currency_id.format(imbalance)})
        return result
