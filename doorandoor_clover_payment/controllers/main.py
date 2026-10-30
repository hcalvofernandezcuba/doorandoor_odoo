import logging
import secrets

import requests

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from werkzeug.exceptions import NotFound


_logger = logging.getLogger(__name__)


class CloverEcommerceController(http.Controller):
    @staticmethod
    def _ddcl_portal_operation(operation_id, portal_token):
        operation = request.env["doorandoor.clover.operation"].sudo().browse(operation_id).exists()
        if not operation or operation.payment_channel != "portal" or not portal_token:
            raise NotFound()
        if not secrets.compare_digest(operation.portal_token or "", portal_token):
            raise NotFound()
        return operation

    @staticmethod
    def _ddcl_portal_invoice(invoice_id, access_token):
        try:
            invoice = CustomerPortal()._document_check_access("account.move", invoice_id, access_token)
        except (AccessError, MissingError):
            raise NotFound()
        if invoice.move_type != "out_invoice" or invoice.state != "posted" or invoice.currency_id.is_zero(invoice.amount_residual):
            raise NotFound()
        return invoice.sudo()

    @staticmethod
    def _ddcl_portal_return_url(operation):
        return "/my/invoices/%s?access_token=%s" % (
            operation.invoice_id.id, operation.invoice_id._portal_ensure_token(),
        )

    def _ddcl_create_portal_operation(self, invoice):
        provider = request.env["payment.provider"].sudo().search([
            ("code", "=", "clover"), ("state", "in", ("test", "enabled")),
            ("company_id", "=", invoice.company_id.id),
        ], limit=1)
        if not provider:
            raise ValidationError(_("Clover no está disponible para esta factura."))
        provider._ddcl_validate_ecommerce_configuration()
        wizard_model = request.env["account.payment.register"].sudo().with_context(
            active_model="account.move", active_ids=invoice.ids,
        )
        payment_register = wizard_model.create(wizard_model.default_get(list(wizard_model._fields)))
        clover_method_line = provider.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_provider_id == provider
        )[:1]
        if not clover_method_line:
            payment_register.unlink()
            raise ValidationError(_("El diario Clover no tiene una línea de pago online válida."))
        # The standard wizard defaults to the generic manual line when a
        # journal contains both entries.  Select Clover explicitly so the
        # portal never falls back to a non-online payment method.
        payment_register.write({
            "journal_id": provider.journal_id.id,
            "payment_method_line_id": clover_method_line.id,
        })
        if payment_register.payment_method_line_id.payment_provider_id != provider:
            payment_register.unlink()
            raise ValidationError(_("El diario Clover no tiene una línea de pago online válida."))
        return request.env["doorandoor.clover.operation"].sudo().create({
            "reference": "%s-CLOVER-%s" % (
                invoice.name,
                request.env["ir.sequence"].sudo().next_by_code("doorandoor.clover.operation") or "NEW",
            ),
            "invoice_id": invoice.id,
            "provider_id": provider.id,
            "amount": payment_register.ddcl_collection_total_amount,
            "collection_base_amount": payment_register.ddcl_collection_base_amount,
            "collection_fee_amount": payment_register.ddcl_collection_fee_amount,
            "state": "pending",
            "is_mock": provider.ddcl_mock_mode,
            "payment_register_id": payment_register.id,
            "idempotency_key": request.env["doorandoor.clover.operation"]._ddcl_new_idempotency_key(),
            "portal_token": secrets.token_urlsafe(32),
            "payment_channel": "portal",
            "state_message": _("Operación portal creada; pendiente de autorización del titular."),
        })

    @http.route("/payment/clover/portal/invoice/<int:invoice_id>", type="http", auth="public", website=True)
    def clover_portal_start(self, invoice_id, access_token=None, **kwargs):
        invoice = self._ddcl_portal_invoice(invoice_id, access_token)
        try:
            operation = self._ddcl_create_portal_operation(invoice)
        except ValidationError as exc:
            return request.render("http_routing.404", {"message": exc.args[0]})
        return request.redirect("/payment/clover/portal/verify/%s/%s" % (operation.id, operation.portal_token))

    @http.route("/payment/clover/portal/verify/<int:operation_id>/<string:portal_token>", type="http", auth="public", methods=["GET", "POST"], website=True)
    def clover_portal_verify(self, operation_id, portal_token, code=None, cardholder_name=None, resend=False, send_otp=False, **kwargs):
        operation = self._ddcl_portal_operation(operation_id, portal_token)
        error = notice = False
        if request.httprequest.method == "POST":
            try:
                if send_otp:
                    operation._ddcl_validate_cardholder(cardholder_name)
                    operation._ddcl_send_otp()
                    notice = _("Enviamos el código de autorización por el canal configurado.")
                elif resend:
                    operation._ddcl_send_otp()
                    notice = _("Enviamos un código nuevo por el canal configurado.")
                else:
                    operation._ddcl_verify_otp(code)
                    return request.redirect("/payment/clover/portal/checkout/%s/%s" % (operation.id, portal_token))
            except ValidationError as exc:
                error = exc.args[0]
            except Exception:
                _logger.exception("Unexpected portal Clover OTP error for operation %s", operation.id)
                error = _("No se pudo validar el código. No se realizó ningún cargo; solicite uno nuevo.")
        return request.render("doorandoor_clover_payment.otp_verification_page", {
            "operation": operation, "error": error, "notice": notice,
            "csrf_token": request.csrf_token(),
            "checkout_url": "/payment/clover/portal/checkout/%s/%s" % (operation.id, portal_token),
        })

    @http.route("/payment/clover/portal/checkout/<int:operation_id>/<string:portal_token>", type="http", auth="public", website=True)
    def clover_portal_checkout(self, operation_id, portal_token, **kwargs):
        operation = self._ddcl_portal_operation(operation_id, portal_token)
        if operation.state != "pending":
            return request.redirect(self._ddcl_portal_return_url(operation))
        if not operation.otp_verified_at:
            return request.redirect("/payment/clover/portal/verify/%s/%s" % (operation.id, portal_token))
        provider = operation.provider_id.sudo()
        provider._ddcl_validate_ecommerce_configuration()
        return request.render("doorandoor_clover_payment.checkout_page", {
            "operation": operation, "provider": provider,
            "sdk_url": "https://checkout.sandbox.dev.clover.com/sdk.js" if provider.ddcl_environment == "sandbox" else "https://checkout.clover.com/sdk.js",
            "return_url": self._ddcl_portal_return_url(operation),
            "charge_url": "/payment/clover/portal/charge/%s/%s" % (operation.id, portal_token),
            "csrf_token": request.csrf_token(),
        })
    @staticmethod
    def _ddcl_decline_message(response, payload):
        """Return a customer-safe decline message without exposing HTTP details."""
        if response.status_code == 402:
            return _("La tarjeta fue rechazada por Clover. No se realizó ningún cargo.")
        return payload.get("message") or payload.get("error") or _(
            "Clover rechazó el cobro. No se realizó ningún cargo."
        )

    @http.route("/payment/clover/checkout/<int:operation_id>", type="http", auth="user", website=False)
    def clover_checkout(self, operation_id, **kwargs):
        operation = request.env["doorandoor.clover.operation"].browse(operation_id).exists()
        if not operation or operation.create_uid != request.env.user:
            raise AccessError(_("No tiene acceso a esta operación Clover."))
        if operation.state != "pending":
            return request.redirect("/web#id=%s&model=account.move&view_type=form" % operation.invoice_id.id)
        if not operation.otp_verified_at:
            return request.redirect("/payment/clover/verify/%s" % operation.id)
        provider = operation.provider_id.sudo()
        provider._ddcl_validate_ecommerce_configuration()
        if provider.ddcl_mock_mode:
            raise ValidationError(_("La operación está configurada para simulación local."))
        return request.render("doorandoor_clover_payment.checkout_page", {
            "operation": operation, "provider": provider,
            "sdk_url": "https://checkout.sandbox.dev.clover.com/sdk.js" if provider.ddcl_environment == "sandbox" else "https://checkout.clover.com/sdk.js",
            "return_url": "/web#id=%s&model=account.move&view_type=form" % operation.invoice_id.id,
            "charge_url": "/payment/clover/charge",
            "csrf_token": request.csrf_token(),
        })

    @http.route("/payment/clover/verify/<int:operation_id>", type="http", auth="user", methods=["GET", "POST"], website=False)
    def clover_verify(self, operation_id, code=None, cardholder_name=None, resend=False, send_otp=False, **kwargs):
        operation = request.env["doorandoor.clover.operation"].browse(operation_id).exists()
        if not operation or operation.create_uid != request.env.user:
            raise AccessError(_("No tiene acceso a esta operación Clover."))
        error = False
        notice = False
        if request.httprequest.method == "POST":
            try:
                if send_otp:
                    operation._ddcl_validate_cardholder(cardholder_name)
                    operation._ddcl_send_otp()
                    notice = _("Enviamos un código nuevo al correo registrado del cliente.")
                elif resend:
                    operation._ddcl_send_otp()
                    notice = _("Enviamos un código nuevo al correo registrado del cliente.")
                else:
                    operation._ddcl_verify_otp(code)
                    return request.redirect("/payment/clover/checkout/%s" % operation.id)
            except ValidationError as exc:
                error = exc.args[0]
            except Exception:
                # A bad or expired code is never allowed to expose Odoo's
                # technical error page to the commercial user.  Keep the
                # operation pending and provide a safe recovery path instead.
                _logger.exception("Unexpected error validating Clover OTP for operation %s", operation.id)
                error = _(
                    "No se pudo validar el código en este momento. No se realizó ningún cargo. "
                    "Solicite un código nuevo o contacte al administrador si el problema continúa."
                )
        return request.render("doorandoor_clover_payment.otp_verification_page", {
            "operation": operation, "error": error, "notice": notice,
            "csrf_token": request.csrf_token(),
            "checkout_url": "/payment/clover/checkout/%s" % operation.id,
        })

    @http.route("/payment/clover/charge", type="http", auth="user", methods=["POST"], csrf=False, website=False)
    def clover_charge(self, operation_id=None, source=None, portal_token=None, **kwargs):
        operation = request.env["doorandoor.clover.operation"].browse(int(operation_id or 0)).exists()
        is_portal = bool(operation and operation.payment_channel == "portal" and portal_token and secrets.compare_digest(operation.portal_token or "", portal_token))
        if not operation or (not is_portal and operation.create_uid != request.env.user):
            return request.make_json_response({"ok": False, "error": _("Operación Clover no disponible.")}, status=404)
        redirect_url = self._ddcl_portal_return_url(operation) if is_portal else "/web#id=%s&model=account.move&view_type=form" % operation.invoice_id.id
        if operation.state == "approved":
            return request.make_json_response({"ok": True, "redirect_url": redirect_url})
        if operation.state != "pending":
            return request.make_json_response({"ok": False, "error": operation.state_message or _("La operación no puede procesarse.")}, status=409)
        if not source or not source.startswith("clv_"):
            return request.make_json_response({"ok": False, "error": _("Clover no devolvió un token de tarjeta válido.")}, status=400)
        provider = operation.provider_id.sudo()
        try:
            provider._ddcl_validate_ecommerce_configuration()
            base_url = "https://scl-sandbox.dev.clover.com" if provider.ddcl_environment == "sandbox" else "https://scl.clover.com"
            response = requests.post("%s/v1/charges" % base_url, headers={
                "Accept": "application/json", "Authorization": "Bearer %s" % provider.ddcl_private_token,
                "Content-Type": "application/json", "Idempotency-Key": operation.idempotency_key,
                "User-Agent": "DoorAndDoor-Odoo/18 Clover-Ecommerce",
                "X-Forwarded-For": request.httprequest.remote_addr or "127.0.0.1",
            }, json={"amount": int(round(operation.amount * 100)), "currency": operation.currency_id.name.lower(), "source": source}, timeout=30)
            payload = response.json() if response.content else {}
        except (requests.RequestException, ValueError):
            operation.write({"state": "unknown", "state_message": _("No fue posible confirmar la respuesta de Clover. No reintente el cobro: revíselo en Clover antes de continuar.")})
            return request.make_json_response({"ok": False, "error": _("Respuesta de Clover no confirmada; la operación quedó en revisión.")}, status=502)
        if not response.ok:
            # Keep only provider diagnostics that cannot identify a card or
            # reproduce a token.  The commercial user receives the concise
            # decline message while support can distinguish Sandbox causes.
            diagnostic = {
                key: payload.get(key)
                for key in ("id", "status", "code", "type", "message", "error", "decline_code")
                if payload.get(key) not in (None, "")
            }
            _logger.warning(
                "Clover charge declined: operation=%s http_status=%s diagnostic=%s",
                operation.id, response.status_code, diagnostic,
            )
            operation.write({
                "state": "declined",
                "provider_reference": payload.get("id"),
                "state_message": self._ddcl_decline_message(response, payload),
            })
            return request.make_json_response({"ok": False, "error": operation.state_message}, status=400)
        if str(payload.get("status", "")).lower() not in ("approved", "succeeded", "paid", "captured"):
            operation.write({"state": "unknown", "provider_reference": payload.get("id"), "state_message": _("Clover respondió sin un estado de aprobación concluyente. Revise la transacción antes de reintentar.")})
            return request.make_json_response({"ok": False, "error": operation.state_message}, status=409)
        try:
            payment = operation._ddcl_register_approved_payment()
            operation.write({"state": "approved", "provider_reference": payload.get("id"), "payment_id": payment.id, "state_message": _("Cobro aprobado por Clover y registrado en Odoo.")})
        except Exception:
            operation.write({"state": "unknown", "provider_reference": payload.get("id"), "state_message": _("Clover aprobó el cobro, pero Odoo no pudo completar su registro contable. Revisión requerida.")})
            raise
        return request.make_json_response({"ok": True, "redirect_url": redirect_url})

    @http.route("/payment/clover/portal/charge/<int:operation_id>/<string:portal_token>", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def clover_portal_charge(self, operation_id, portal_token, source=None, **kwargs):
        return self.clover_charge(operation_id=operation_id, source=source, portal_token=portal_token, **kwargs)
