from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorandoorPaymentReceiptWizard(models.TransientModel):
    _name = "doorandoor.payment.receipt.wizard"
    _description = "Generar recibo o estado de pagos"

    receipt_type = fields.Selection(
        [("invoice", "Recibo por factura"), ("customer", "Estado de pagos del cliente")],
        required=True, default="customer",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Cliente", required=True,
        domain=[("customer_rank", ">", 0)],
    )
    invoice_id = fields.Many2one(
        "account.move", string="Factura",
        domain="[('commercial_partner_id','=',partner_id),('move_type','=','out_invoice'),('state','=','posted')]",
    )
    date_from = fields.Date(
        string="Desde",
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(string="Hasta", default=fields.Date.context_today)
    include_unapplied = fields.Boolean(string="Incluir saldos sin aplicar", default=True)
    notes = fields.Text(string="Observaciones para el cliente")

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.partner_id = self.invoice_id.commercial_partner_id

    @api.onchange("receipt_type")
    def _onchange_receipt_type(self):
        if self.receipt_type == "customer":
            self.invoice_id = False

    def _generate_receipt(self):
        self.ensure_one()
        if self.receipt_type == "invoice" and not self.invoice_id:
            raise UserError(_("Seleccione la factura para generar su recibo."))
        if self.receipt_type == "customer" and self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_("La fecha Desde no puede ser posterior a Hasta."))
        return self.env["doorandoor.payment.receipt"].generate_receipt(
            self.receipt_type,
            self.partner_id,
            invoice=self.invoice_id,
            date_from=self.date_from,
            date_to=self.date_to,
            include_unapplied=self.include_unapplied,
            notes=self.notes,
        )
    def action_generate(self):
        receipt = self._generate_receipt()
        return {
            "type": "ir.actions.act_window",
            "name": receipt.name,
            "res_model": receipt._name,
            "res_id": receipt.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_generate_pdf(self):
        receipt = self._generate_receipt()
        return receipt.action_print_receipt()
