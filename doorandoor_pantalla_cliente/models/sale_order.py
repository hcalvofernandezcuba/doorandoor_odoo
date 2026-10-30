# -*- coding: utf-8 -*-

import secrets

from odoo import _, fields, models
from odoo.exceptions import AccessError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddpc_customer_display_active = fields.Boolean(copy=False, readonly=True)
    ddpc_customer_display_mode = fields.Selection([("document", "Documento"), ("promotion", "Promociones")], default="document", copy=False, readonly=True)
    ddpc_customer_display_token = fields.Char(copy=False, readonly=True, index=True)
    ddpc_customer_display_expires_at = fields.Datetime(copy=False, readonly=True)

    def _ddpc_check_customer_display_manager(self):
        if not (
            self.env.user.has_group("sales_team.group_sale_salesman")
            or self.env.user.has_group("sales_team.group_sale_manager")
            or self.env.user.has_group("base.group_system")
        ):
            raise AccessError(_("Solo un usuario autorizado de Ventas puede abrir la pantalla de cliente."))

    def _ddpc_customer_display_is_valid(self, token):
        self.ensure_one()
        return bool(self.ddpc_customer_display_active and self.ddpc_customer_display_token and token
                    and secrets.compare_digest(self.ddpc_customer_display_token, token)
                    and self.ddpc_customer_display_expires_at and self.ddpc_customer_display_expires_at >= fields.Datetime.now())

    def action_ddpc_open_customer_display(self):
        self.ensure_one()
        self._ddpc_check_customer_display_manager()
        session = self.env["doorandoor.customer.display.session"]._ddpc_start_for_user(
            self.env, self.env.user, self.company_id,
        )
        session._ddpc_set_document(self)
        return {"type": "ir.actions.act_url", "url": "/pantalla-cliente/s/%s" % session.token, "target": "new"}

    def _ddpc_customer_display_payload(self):
        self.ensure_one()
        if self.ddpc_customer_display_mode == "promotion" and not self.env.context.get("ddpc_session_display"):
            city = self.ddts_tax_city_rule_id if "ddts_tax_city_rule_id" in self._fields else self.env["doorandoor.tax.state.rule"]
            promotions = self.env["doorandoor.customer.display.promotion"]._ddpc_active_for_city(self.company_id, city)
            return {"mode": "promotion", "city": city.county_name or "Door&Door", "promotions": [p._ddpc_as_payload() for p in promotions]}
        lines = self.order_line.filtered(lambda line: not line.display_type)
        currency = self.currency_id
        tax_rate = self.ddts_tax_city_rule_id.sale_tax_id.amount if "ddts_tax_city_rule_id" in self._fields and self.ddts_tax_city_rule_id else 0.0
        fee_amount = self.ddtp_card_fee_preview if "ddtp_card_fee_preview" in self._fields else 0.0
        fee_rate = self.ddtp_card_fee_rate if "ddtp_card_fee_rate" in self._fields else 0.0
        card_total = self.ddtp_card_total_preview if "ddtp_card_total_preview" in self._fields else self.amount_total
        payment_plan = self.ddtp_payment_plan if "ddtp_payment_plan" in self._fields else "full"
        payment_due = self.ddtp_payment_due_amount if "ddtp_payment_due_amount" in self._fields else self.amount_total
        payment_pending = self.ddtp_payment_pending_amount if "ddtp_payment_pending_amount" in self._fields else 0.0
        image = lambda value: value.decode() if isinstance(value, bytes) else (value or "")
        return {"mode": "document", "invoice": self.name or _("Cotización"), "currency": {"name": currency.name, "symbol": currency.symbol, "position": currency.position},
                "payment_state": {"code": "pending", "label": _("Cotización en preparación"), "detail": _("Los productos y totales se actualizan en tiempo real.")},
                "lines": [{"name": line.name, "quantity": line.product_uom_qty, "unit_price": line.price_unit, "subtotal": line.price_subtotal, "image": image(line.product_id.image_128)} for line in lines],
                "last_product": {"name": lines[-1:].product_id.display_name if lines else "", "image": image(lines[-1:].product_id.image_512)},
                "totals": {"untaxed": self.amount_untaxed, "tax": self.amount_tax, "tax_rate": tax_rate,
                           "fee": fee_amount, "fee_rate": fee_rate,
                           "total": self.amount_total,
                           "payment_plan": payment_plan,
                           "payment_due": payment_due,
                           "payment_pending": payment_pending,
                           "card_total": card_total}}
