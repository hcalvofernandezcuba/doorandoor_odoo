from odoo import _, fields, models
from odoo.exceptions import ValidationError


class CloverCheckoutWizard(models.TransientModel):
    _name = "doorandoor.clover.checkout.wizard"
    _description = "Simulador seguro Clover Ecommerce"

    operation_id = fields.Many2one("doorandoor.clover.operation", required=True, readonly=True)
    payment_register_id = fields.Many2one("account.payment.register", required=True, readonly=True)
    invoice_id = fields.Many2one(related="operation_id.invoice_id", readonly=True)
    partner_id = fields.Many2one(related="operation_id.partner_id", readonly=True)
    currency_id = fields.Many2one(related="operation_id.currency_id", readonly=True)
    amount = fields.Monetary(related="operation_id.amount", readonly=True, currency_field="currency_id")
    cardholder_name = fields.Char(string="Titular de tarjeta (simulado)", required=True)
    card_number = fields.Char(string="Número de tarjeta", default="4111 1111 1111 1111")
    expiry = fields.Char(string="Vencimiento", default="12/30")
    cvc = fields.Char(string="CVC", default="123")
    otp_code = fields.Char(string="Código OTP")
    otp_sent_at = fields.Datetime(related="operation_id.otp_sent_at", readonly=True)
    otp_verified_at = fields.Datetime(related="operation_id.otp_verified_at", readonly=True)

    def action_send_training_otp(self):
        self.ensure_one()
        if not self.operation_id.provider_id.sudo().ddcl_mock_mode:
            raise ValidationError(_("El OTP de capacitación solo está permitido en desarrollo local."))
        self.operation_id._ddcl_validate_cardholder(self.cardholder_name)
        self.operation_id._ddcl_send_otp(delivery="telegram")
        return {
            "type": "ir.actions.act_window",
            "name": _("Pago con tarjeta - Clover (simulación)"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_simulate_approved(self):
        self.ensure_one()
        if not self.operation_id.provider_id.sudo().ddcl_mock_mode:
            raise ValidationError(_("El simulador solo está permitido en desarrollo local."))
        if not self.operation_id.otp_sent_at:
            raise ValidationError(_("Envíe primero el OTP de capacitación por Telegram."))
        if not self.operation_id.otp_verified_at:
            if not self.otp_code:
                raise ValidationError(_("Introduzca el código OTP recibido por Telegram."))
            self.operation_id._ddcl_verify_otp(self.otp_code)
        payment = self.operation_id._ddcl_register_approved_payment()
        payment_result = {"type": "ir.actions.act_window_close"}
        self.operation_id.write({
            "state": "approved",
            "payment_id": payment.id,
            "provider_reference": "LOCAL-MOCK-%s" % self.operation_id.id,
            "state_message": _("Pago aprobado mediante simulación local; no se transmitieron datos de tarjeta."),
        })
        return payment_result

    def action_simulate_declined(self):
        self.operation_id.action_mark_declined()
        return {"type": "ir.actions.act_window_close"}
