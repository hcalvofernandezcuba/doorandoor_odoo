from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ddpa_customer_display_policy_payload(self):
        self.ensure_one()
        acceptance = self._ddpa_resolve_acceptance()
        if acceptance:
            return {"accepted": True}
        pending = self._ddpa_get_or_create_request("email" if self.partner_id.email else "present")
        return {
            "accepted": False,
            "url": pending._get_public_url(),
            "customer": self.partner_id.display_name,
            "email": self.partner_id.email or "",
        }

    def _ddpc_customer_display_payload(self):
        payload = super()._ddpc_customer_display_payload()
        if payload.get("mode") == "document" and self.partner_id:
            payload["policy_acceptance"] = self._ddpa_customer_display_policy_payload()
        return payload


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ddpa_customer_display_policy_payload(self):
        self.ensure_one()
        acceptance = self._ddpa_resolve_acceptance()
        if acceptance:
            return {"accepted": True}
        pending = self._ddpa_get_or_create_request("email" if self.partner_id.email else "present")
        return {
            "accepted": False,
            "url": pending._get_public_url(),
            "customer": self.partner_id.display_name,
            "email": self.partner_id.email or "",
        }

    def _ddpc_customer_display_payload(self):
        payload = super()._ddpc_customer_display_payload()
        if payload.get("mode") == "document" and self.partner_id:
            payload["policy_acceptance"] = self._ddpa_customer_display_policy_payload()
        return payload
