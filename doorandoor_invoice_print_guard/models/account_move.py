from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ddipg_check_printable_invoice(self):
        # Keep every PDF/report entry point under the same business rule as
        # the invoice buttons.  This also preserves the Administrator/Ajustes
        # exception and the validated partial-payment threshold.
        return self._ddsn_check_printable_invoice()

    def action_print_pdf(self):
        self._ddipg_check_printable_invoice()
        return super().action_print_pdf()

    def action_invoice_sent(self):
        self._ddipg_check_printable_invoice()
        return super().action_invoice_sent()

    def action_send_and_print(self):
        self._ddipg_check_printable_invoice()
        return super().action_send_and_print()

    def _generate_and_send(self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings):
        self._ddipg_check_printable_invoice()
        return super()._generate_and_send(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
            **custom_settings,
        )
