# -*- coding: utf-8 -*-

import secrets

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    ddpc_customer_display_active = fields.Boolean(
        string="Pantalla de cliente activa", copy=False, readonly=True,
    )
    ddpc_customer_display_mode = fields.Selection([("document", "Documento"), ("promotion", "Promociones")], default="document", copy=False, readonly=True)
    ddpc_customer_display_token = fields.Char(
        string="Token de pantalla de cliente", copy=False, readonly=True, index=True,
    )
    ddpc_customer_display_expires_at = fields.Datetime(
        string="Vence pantalla de cliente", copy=False, readonly=True,
    )
    ddpc_customer_display_opened_by = fields.Many2one(
        "res.users", string="Abierta por", copy=False, readonly=True,
    )

    def _ddpc_check_customer_display_manager(self):
        if not (
            self.env.user.has_group("sales_team.group_sale_salesman")
            or
            self.env.user.has_group("sales_team.group_sale_manager")
            or self.env.user.has_group("base.group_system")
        ):
            raise AccessError(_("Solo un usuario autorizado de Ventas puede abrir la pantalla de cliente."))

    def _ddpc_customer_display_is_valid(self, token):
        self.ensure_one()
        return bool(
            self.ddpc_customer_display_active
            and self.ddpc_customer_display_token
            and token
            and secrets.compare_digest(self.ddpc_customer_display_token, token)
            and self.ddpc_customer_display_expires_at
            and self.ddpc_customer_display_expires_at >= fields.Datetime.now()
        )

    def action_ddpc_open_customer_display(self):
        self.ensure_one()
        self._ddpc_check_customer_display_manager()
        if self.move_type != "out_invoice":
            raise UserError(_("La pantalla de cliente solo está disponible para facturas de cliente."))
        session = self.env["doorandoor.customer.display.session"]._ddpc_start_for_user(
            self.env, self.env.user, self.company_id,
        )
        session._ddpc_set_document(self)
        return {
            "type": "ir.actions.act_url",
            "url": "/pantalla-cliente/s/%s" % session.token,
            "target": "new",
        }

    def action_ddpc_close_customer_display(self):
        self.ensure_one()
        self._ddpc_check_customer_display_manager()
        session = self.env["doorandoor.customer.display.session"]._ddpc_for_user(
            self.env, self.env.user, self.company_id,
        )
        if session:
            session.sudo().write({"active": False, "expires_at": fields.Datetime.now()})
        return True

    def _ddpc_customer_display_payload(self):
        self.ensure_one()
        if self.ddpc_customer_display_mode == "promotion" and not self.env.context.get("ddpc_session_display"):
            city = self.ddts_tax_city_rule_id if "ddts_tax_city_rule_id" in self._fields else self.env["doorandoor.tax.state.rule"]
            promotions = self.env["doorandoor.customer.display.promotion"]._ddpc_active_for_city(self.company_id, city)
            return {"mode": "promotion", "city": city.county_name or "Door&Door", "promotions": [p._ddpc_as_payload() for p in promotions]}
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        currency = self.currency_id
        fee_amount = self.ddtp_card_fee_preview if "ddtp_card_fee_preview" in self._fields else 0.0
        fee_rate = self.ddtp_card_fee_rate if "ddtp_card_fee_rate" in self._fields else 0.0
        card_total = self.ddtp_card_total_preview if "ddtp_card_total_preview" in self._fields else self.amount_total
        payment_plan = self.ddtp_payment_plan if "ddtp_payment_plan" in self._fields else "full"
        payment_due = self.ddtp_payment_due_amount if "ddtp_payment_due_amount" in self._fields else self.amount_total
        payment_pending = self.ddtp_payment_pending_amount if "ddtp_payment_pending_amount" in self._fields else 0.0
        tax_rate = self.ddts_tax_city_rate if "ddts_tax_city_rate" in self._fields else 0.0
        if self.payment_state == "paid":
            payment_state = {"code": "paid", "label": _("Pago confirmado"), "detail": _("La factura fue pagada correctamente.")}
        elif self.payment_state == "partial":
            payment_state = {"code": "partial", "label": _("Pago parcial registrado"), "detail": _("Queda un saldo pendiente por cobrar.")}
        elif self.payment_state == "in_payment":
            payment_state = {"code": "processing", "label": _("Pago en proceso"), "detail": _("Estamos confirmando el pago.")}
        else:
            payment_state = {"code": "pending", "label": _("Pendiente de pago"), "detail": _("Puede continuar cuando esté listo.")}

        operation = self.env["doorandoor.clover.operation"].search(
            [("invoice_id", "=", self.id)], order="id desc", limit=1,
        )
        if operation and self.payment_state != "paid":
            if operation.state == "declined":
                payment_state = {"code": "declined", "label": _("Pago rechazado"), "detail": _("No se realizó ningún cargo. Puede intentar otro medio de pago.")}
            elif operation.state == "unknown":
                payment_state = {"code": "review", "label": _("Pago en revisión"), "detail": _("No vuelva a intentar el cobro hasta recibir confirmación.")}
            elif operation.state == "approved":
                payment_state = {"code": "processing", "label": _("Pago aprobado"), "detail": _("Estamos registrando la confirmación del pago.")}
            elif operation.state == "pending":
                if operation.cardholder_match != "matched":
                    payment_state = {"code": "authorization", "label": _("Validando autorización"), "detail": _("Se está verificando el titular de la tarjeta.")}
                elif operation.otp_sent_at and not operation.otp_verified_at:
                    payment_state = {"code": "authorization", "label": _("Autorización pendiente"), "detail": _("Revise y confirme el código de autorización para continuar.")}
                elif operation.otp_verified_at:
                    payment_state = {"code": "processing", "label": _("Pago en proceso"), "detail": _("Autorización recibida. Estamos procesando el cobro.")}

        def image_as_text(image):
            return image.decode() if isinstance(image, bytes) else (image or "")

        return {
            "mode": "document",
            "invoice": self.name or _("Factura en borrador"),
            "currency": {"name": currency.name, "symbol": currency.symbol, "position": currency.position},
            "payment_state": payment_state,
            "lines": [
                {
                    "name": line.name,
                    "quantity": line.quantity,
                    "unit_price": line.price_unit,
                    "subtotal": line.price_subtotal,
                    "image": image_as_text(line.product_id.image_128),
                }
                for line in lines
            ],
            "last_product": {
                "name": lines[-1:].product_id.display_name if lines else "",
                "image": image_as_text(lines[-1:].product_id.image_512),
            },
            "totals": {
                "untaxed": self.amount_untaxed,
                "tax": self.amount_tax,
                "tax_rate": tax_rate,
                "fee": fee_amount,
                "fee_rate": fee_rate,
                "total": self.amount_total,
                "payment_plan": payment_plan,
                "payment_due": payment_due,
                "payment_pending": payment_pending,
                "card_total": card_total,
            },
        }
