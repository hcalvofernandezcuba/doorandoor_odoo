import base64

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError


class DoorandoorPaymentReceipt(models.Model):
    _name = "doorandoor.payment.receipt"
    _description = "Recibo de cobro auditable"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="Nuevo", readonly=True, copy=False, tracking=True)
    receipt_type = fields.Selection(
        [("invoice", "Recibo por factura"), ("customer", "Estado de pagos del cliente")],
        required=True, readonly=True, tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Cliente", required=True, readonly=True,
        tracking=True, index=True,
    )
    invoice_id = fields.Many2one(
        "account.move", string="Factura", readonly=True, tracking=True,
        domain="[('move_type','=','out_invoice'),('state','=','posted')]",
    )
    date_from = fields.Date(string="Desde", readonly=True)
    date_to = fields.Date(string="Hasta", readonly=True)
    generated_at = fields.Datetime(
        string="Generado el", required=True, readonly=True,
        default=fields.Datetime.now,
    )
    generated_by_id = fields.Many2one(
        "res.users", string="Generado por", required=True, readonly=True,
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", required=True, readonly=True,
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "doorandoor.payment.receipt.line", "receipt_id",
        string="Aplicaciones contables", readonly=True,
    )
    invoice_line_ids = fields.One2many(
        "doorandoor.payment.receipt.invoice.line", "receipt_id",
        string="Detalle de factura", readonly=True,
    )
    tax_line_ids = fields.One2many(
        "doorandoor.payment.receipt.tax.line", "receipt_id",
        string="Desglose de impuestos", readonly=True,
    )
    invoice_untaxed = fields.Monetary(string="Subtotal sin impuestos", readonly=True)
    invoice_tax = fields.Monetary(string="Total impuestos", readonly=True)
    invoice_total = fields.Monetary(string="Total factura", readonly=True)
    invoice_fees = fields.Monetary(string="Cargos/fees", readonly=True)
    invoice_accounting_total = fields.Monetary(
        string="Total contable a cobrar", readonly=True,
    )
    invoice_residual = fields.Monetary(string="Saldo factura al emitir", readonly=True)
    total_received = fields.Monetary(string="Pagos recibidos", readonly=True)
    total_applied = fields.Monetary(string="Pagos aplicados", readonly=True)
    total_credit_notes = fields.Monetary(string="Créditos aplicados", readonly=True)
    total_unapplied = fields.Monetary(string="Saldo sin aplicar", readonly=True)
    notes = fields.Text(string="Observaciones", readonly=True)
    state = fields.Selection(
        [("generated", "Generado"), ("cancelled", "Anulado")],
        default="generated", required=True, readonly=True, tracking=True,
    )

    _sql_constraints = [
        ("invoice_required_for_invoice_receipt",
         "CHECK(receipt_type != 'invoice' OR invoice_id IS NOT NULL)",
         "El recibo por factura requiere una factura."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("ddc_generate_payment_receipt"):
            raise UserError(_(
                "Los recibos se generan únicamente desde el asistente o desde una factura."
            ))
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "doorandoor.payment.receipt"
                ) or "Nuevo"
        return super().create(vals_list)

    def write(self, vals):
        protected = set(vals) - {"state"}
        if protected:
            raise UserError(_(
                "Un recibo emitido es una fotografía contable y no puede modificarse. "
                "Genere uno nuevo si necesita otro período o contenido."
            ))
        return super().write(vals)

    @api.model
    def _invoice_allocation_values(self, invoice, target_currency,
                                   date_from=False, date_to=False):
        values = []
        for item in invoice._get_all_reconciled_invoice_partials():
            if item.get("is_exchange"):
                continue
            partial = self.env["account.partial.reconcile"].browse(item["partial_id"])
            application_date = partial.max_date
            if date_from and application_date < date_from:
                continue
            if date_to and application_date > date_to:
                continue
            counterpart_line = item["aml"]
            counterpart_move = counterpart_line.move_id
            payment = counterpart_move.origin_payment_id
            if payment:
                line_type = "payment"
                reference = payment.memo or payment.name
                journal = payment.journal_id
                payment_amount = payment.currency_id._convert(
                    payment.amount, target_currency, payment.company_id, payment.date
                )
            elif counterpart_move.move_type == "out_refund":
                line_type = "credit_note"
                reference = counterpart_move.ref or counterpart_move.name
                journal = counterpart_move.journal_id
                payment_amount = 0.0
            else:
                line_type = "journal_entry"
                reference = counterpart_move.ref or counterpart_move.name
                journal = counterpart_move.journal_id
                payment_amount = 0.0
            values.append({
                "line_type": line_type,
                "application_date": application_date,
                "invoice_id": invoice.id,
                "payment_id": payment.id or False,
                "counterpart_move_id": counterpart_move.id,
                "journal_id": journal.id,
                "reference": reference,
                "payment_amount": payment_amount,
                "applied_amount": invoice.currency_id._convert(
                    abs(item["amount"]), target_currency, invoice.company_id,
                    application_date,
                ),
                "unapplied_amount": 0.0,
            })
        return values

    @api.model
    def _unapplied_payment_values(self, partner, target_currency, date_from,
                                  date_to, excluded_payment_ids):
        domain = [
            ("partner_id", "child_of", partner.commercial_partner_id.id),
            ("partner_type", "=", "customer"),
            ("payment_type", "=", "inbound"),
            ("state", "in", ("in_process", "paid")),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        values = []
        for payment in self.env["account.payment"].search(domain, order="date, id"):
            receivable_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_type == "asset_receivable"
            )
            residual = sum(abs(line.amount_residual_currency) for line in receivable_lines)
            if payment.id in excluded_payment_ids or payment.currency_id.is_zero(residual):
                continue
            values.append({
                "line_type": "unapplied",
                "application_date": payment.date,
                "payment_id": payment.id,
                "counterpart_move_id": payment.move_id.id,
                "journal_id": payment.journal_id.id,
                "reference": payment.memo or payment.name,
                "payment_amount": payment.currency_id._convert(
                    payment.amount, target_currency, payment.company_id, payment.date
                ),
                "applied_amount": 0.0,
                "unapplied_amount": payment.currency_id._convert(
                    residual, target_currency, payment.company_id, payment.date
                ),
            })
        return values

    @api.model
    def generate_receipt(self, receipt_type, partner, invoice=False,
                         date_from=False, date_to=False, include_unapplied=True,
                         notes=False):
        partner = partner.commercial_partner_id
        target_currency = invoice.currency_id if invoice else self.env.company.currency_id
        if receipt_type == "invoice":
            if not invoice or invoice.move_type != "out_invoice" or invoice.state != "posted":
                raise UserError(_("Seleccione una factura de cliente confirmada."))
            if invoice.commercial_partner_id != partner:
                raise UserError(_("La factura no pertenece al cliente seleccionado."))
            invoices = invoice
            allocation_from = allocation_to = False
        else:
            invoices = self.env["account.move"].search([
                ("commercial_partner_id", "=", partner.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
            ], order="invoice_date, id")
            allocation_from, allocation_to = date_from, date_to

        line_values = []
        for customer_invoice in invoices.filtered(lambda move: move.move_type == "out_invoice"):
            line_values += self._invoice_allocation_values(
                customer_invoice, target_currency, allocation_from, allocation_to
            )
        payment_ids = {
            values["payment_id"] for values in line_values if values.get("payment_id")
        }
        if receipt_type == "customer" and include_unapplied:
            line_values += self._unapplied_payment_values(
                partner, target_currency, date_from, date_to, payment_ids
            )
        if not line_values:
            raise UserError(_(
                "No existen pagos conciliados ni saldos sin aplicar para los filtros seleccionados."
            ))

        payment_amounts = {}
        for value in line_values:
            if value.get("payment_id"):
                payment_amounts.setdefault(value["payment_id"], value["payment_amount"])
        receivable_total = 0.0
        if invoice:
            receivable_total = sum(
                abs(line.amount_currency)
                for line in invoice.line_ids
                if line.account_type == "asset_receivable"
            )
        invoice_line_values = []
        tax_line_values = []
        if invoice:
            for sequence, invoice_line in enumerate(
                invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product"),
                start=1,
            ):
                invoice_line_values.append({
                    "sequence": sequence,
                    "product_id": invoice_line.product_id.id,
                    "description": invoice_line.name,
                    "quantity": invoice_line.quantity,
                    "product_uom_id": invoice_line.product_uom_id.id,
                    "price_unit": invoice_line.price_unit,
                    "discount": invoice_line.discount,
                    "tax_names": ", ".join(invoice_line.tax_ids.mapped("name")),
                    "price_subtotal": invoice_line.price_subtotal,
                    "price_total": invoice_line.price_total,
                })
            tax_totals = invoice.tax_totals or {}
            sequence = 1
            for subtotal in tax_totals.get("subtotals", []):
                for tax_group in subtotal.get("tax_groups", []):
                    tax_line_values.append({
                        "sequence": sequence,
                        "name": tax_group.get("group_name") or _("Impuesto"),
                        "base_amount": tax_group.get("base_amount_currency", 0.0),
                        "tax_amount": tax_group.get("tax_amount_currency", 0.0),
                    })
                    sequence += 1

        receipt = self.with_context(ddc_generate_payment_receipt=True).create({
            "receipt_type": receipt_type,
            "partner_id": partner.id,
            "invoice_id": invoice.id if invoice else False,
            "date_from": date_from if receipt_type == "customer" else False,
            "date_to": date_to if receipt_type == "customer" else False,
            "company_id": (invoice.company_id.id if invoice else self.env.company.id),
            "currency_id": target_currency.id,
            "invoice_untaxed": invoice.amount_untaxed if invoice else 0.0,
            "invoice_tax": invoice.amount_tax if invoice else 0.0,
            "invoice_total": invoice.amount_total if invoice else 0.0,
            "invoice_fees": max(receivable_total - invoice.amount_total, 0.0) if invoice else 0.0,
            "invoice_accounting_total": receivable_total if invoice else 0.0,
            "invoice_residual": invoice.amount_residual if invoice else 0.0,
            "total_received": sum(payment_amounts.values()),
            "total_applied": sum(
                value["applied_amount"] for value in line_values
                if value["line_type"] == "payment"
            ),
            "total_credit_notes": sum(
                value["applied_amount"] for value in line_values
                if value["line_type"] == "credit_note"
            ),
            "total_unapplied": sum(value["unapplied_amount"] for value in line_values),
            "notes": notes,
            "line_ids": [Command.create(value) for value in line_values],
            "invoice_line_ids": [Command.create(value) for value in invoice_line_values],
            "tax_line_ids": [Command.create(value) for value in tax_line_values],
        })
        receipt.message_post(body=_(
            "Recibo %(receipt)s generado por %(user)s con %(count)s aplicaciones contables."
        ) % {
            "receipt": receipt.name,
            "user": self.env.user.display_name,
            "count": len(line_values),
        })
        if invoice:
            invoice.message_post(body=_(
                "Recibo de cobro %(receipt)s generado por %(user)s."
            ) % {"receipt": receipt.name, "user": self.env.user.display_name})
        return receipt

    def action_print_receipt(self):
        self.ensure_one()
        self.message_post(body=_("Recibo impreso por %s.") % self.env.user.display_name)
        return self.env.ref(
            "doorandoor_control_cobros.action_report_ddc_payment_receipt"
        ).report_action(self)

    def action_send_email(self):
        self.ensure_one()
        pdf, __format = self.env["ir.actions.report"]._render_qweb_pdf(
            "doorandoor_control_cobros.action_report_ddc_payment_receipt", self.ids
        )
        attachment = self.env["ir.attachment"].create({
            "name": "%s.pdf" % self.name.replace("/", "-"),
            "type": "binary",
            "datas": base64.b64encode(pdf),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/pdf",
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar recibo de cobro"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_partner_ids": [self.partner_id.id],
                "default_attachment_ids": [attachment.id],
                "default_subject": _("Recibo de cobro %s") % self.name,
            },
        }


class DoorandoorPaymentReceiptLine(models.Model):
    _name = "doorandoor.payment.receipt.line"
    _description = "Aplicación incluida en recibo de cobro"
    _order = "application_date, id"

    receipt_id = fields.Many2one(
        "doorandoor.payment.receipt", required=True, ondelete="cascade", index=True,
    )
    currency_id = fields.Many2one(related="receipt_id.currency_id", store=True)
    line_type = fields.Selection(
        [("payment", "Pago"), ("credit_note", "Nota de crédito"),
         ("journal_entry", "Asiento/ajuste"), ("unapplied", "Saldo sin aplicar")],
        required=True, readonly=True,
    )
    application_date = fields.Date(string="Fecha", required=True, readonly=True)
    invoice_id = fields.Many2one("account.move", string="Factura", readonly=True)
    payment_id = fields.Many2one("account.payment", string="Pago", readonly=True)
    counterpart_move_id = fields.Many2one("account.move", string="Asiento", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Diario", readonly=True)
    reference = fields.Char(string="Referencia", readonly=True)
    payment_amount = fields.Monetary(string="Importe original", readonly=True)
    applied_amount = fields.Monetary(string="Aplicado", readonly=True)
    unapplied_amount = fields.Monetary(string="Sin aplicar", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("ddc_generate_payment_receipt"):
            raise UserError(_("Las líneas del recibo no admiten creación manual."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("Las aplicaciones de un recibo emitido son inmutables."))

    def unlink(self):
        raise UserError(_("Las aplicaciones de un recibo emitido no pueden eliminarse."))


class DoorandoorPaymentReceiptInvoiceLine(models.Model):
    _name = "doorandoor.payment.receipt.invoice.line"
    _description = "Detalle comercial incluido en recibo de cobro"
    _order = "sequence, id"

    receipt_id = fields.Many2one(
        "doorandoor.payment.receipt", required=True, ondelete="cascade", index=True,
    )
    currency_id = fields.Many2one(related="receipt_id.currency_id", store=True)
    sequence = fields.Integer(readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    description = fields.Text(string="Descripción", readonly=True)
    quantity = fields.Float(string="Cantidad", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    price_unit = fields.Monetary(string="Precio unitario", readonly=True)
    discount = fields.Float(string="Descuento (%)", readonly=True)
    tax_names = fields.Char(string="Impuestos", readonly=True)
    price_subtotal = fields.Monetary(string="Subtotal", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("ddc_generate_payment_receipt"):
            raise UserError(_("El detalle comercial del recibo no admite creación manual."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("El detalle comercial de un recibo emitido es inmutable."))

    def unlink(self):
        raise UserError(_("El detalle comercial de un recibo emitido no puede eliminarse."))


class DoorandoorPaymentReceiptTaxLine(models.Model):
    _name = "doorandoor.payment.receipt.tax.line"
    _description = "Impuesto incluido en recibo de cobro"
    _order = "sequence, id"

    receipt_id = fields.Many2one(
        "doorandoor.payment.receipt", required=True, ondelete="cascade", index=True,
    )
    currency_id = fields.Many2one(related="receipt_id.currency_id", store=True)
    sequence = fields.Integer(readonly=True)
    name = fields.Char(string="Impuesto", required=True, readonly=True)
    base_amount = fields.Monetary(string="Base imponible", readonly=True)
    tax_amount = fields.Monetary(string="Importe", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("ddc_generate_payment_receipt"):
            raise UserError(_("El desglose fiscal del recibo no admite creación manual."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("El desglose fiscal de un recibo emitido es inmutable."))

    def unlink(self):
        raise UserError(_("El desglose fiscal de un recibo emitido no puede eliminarse."))


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_ddc_create_payment_receipt(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Generar recibo de cobro"),
            "res_model": "doorandoor.payment.receipt.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_receipt_type": "invoice",
                "default_partner_id": self.commercial_partner_id.id,
                "default_invoice_id": self.id,
            },
        }


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_ddc_create_payment_statement(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Generar estado de pagos"),
            "res_model": "doorandoor.payment.receipt.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_receipt_type": "customer",
                "default_partner_id": self.commercial_partner_id.id,
            },
        }
