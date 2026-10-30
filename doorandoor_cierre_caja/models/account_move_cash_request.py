from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ddcc_cash_collection_amount(self):
        """Return the cash amount needed for the invoice's current stage.

        A partial plan is a business milestone: fifty percent of the untaxed
        amount plus all taxes.  Until that milestone is reached, cash must
        collect only the missing validated amount, not the whole accounting
        residual.  Once reached, later collections use the normal residual.
        """
        self.ensure_one()
        residual = max(self.amount_residual, 0.0)
        if getattr(self, "ddtp_payment_plan", False) != "partial":
            return residual
        required = getattr(self, "ddtp_payment_due_amount", 0.0) or 0.0
        validated = getattr(self, "ddc_total_validated", 0.0) or 0.0
        missing = self.currency_id.round(max(required - validated, 0.0))
        return min(residual, missing) if missing else residual

    def action_ddcc_pay_selected_method(self):
        """Open the normal payment selector for every financial method.

        Clover keeps taking control of invoices explicitly prepared for card
        payment through its payment-register extension.  Cash is deliberately
        excluded from this generic action and has its own auditable button,
        so Zelle, transfer and cheque can never be mistaken for cash merely
        because the invoice was not marked as a card payment.
        """
        self.ensure_one()
        return self.action_register_payment()

    def action_ddcc_request_cash_collection(self):
        self.ensure_one()
        if self.move_type != "out_invoice" or self.state != "posted" or self.amount_residual <= 0:
            raise ValidationError(_("Solo puede solicitarse efectivo para una factura publicada con saldo pendiente."))
        Request = self.env["doorandoor.cash.collection.request"]
        previous = Request.search([("invoice_id", "=", self.id), ("state", "in", ("pending", "waiting_archeo"))], limit=1)
        if previous:
            return {"type": "ir.actions.act_window", "res_model": Request._name, "res_id": previous.id, "view_mode": "form", "target": "current"}
        city = self.ddts_tax_city_rule_id if "ddts_tax_city_rule_id" in self._fields else False
        # The seller may create a request but must not need access to cash
        # configuration records.  The request itself remains owned by seller.
        Register = self.env["doorandoor.cash.register"].sudo()
        register = Register.search([("company_id", "=", self.company_id.id), ("city_rule_id", "=", city.id), ("active", "=", True)], limit=1) if city else Register.browse()
        if not register:
            register = Register.search([("company_id", "=", self.company_id.id), ("city_rule_id", "=", False), ("active", "=", True)], limit=1)
        if not register:
            raise ValidationError(_("No hay una caja de ventas configurada para la ciudad de esta factura."))
        blocked = self.env["doorandoor.cash.audit"].sudo().search_count([("session_id.register_id", "=", register.id), ("state", "=", "prepared"), ("cash_blocked", "=", True)])
        request = Request.create({"invoice_id": self.id, "register_id": register.id, "salesperson_id": self.invoice_user_id.id or self.env.user.id, "state": "waiting_archeo" if blocked else "pending"})
        request._notify_cashiers(_("Nuevo cobro en efectivo %(request)s: factura %(invoice)s, vendedor %(seller)s, importe %(amount)s.") % {"request": request.name, "invoice": self.name, "seller": request.salesperson_id.display_name, "amount": self.currency_id.format(self.amount_residual)})
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "title": _("Solicitud enviada a caja"),
            "message": _("La solicitud %(request)s fue enviada a %(register)s. El cajero confirmará el efectivo y el vuelto.") % {"request": request.name, "register": register.display_name},
            "type": "success", "sticky": False,
        }}
