import hashlib
import hmac
import secrets
import time

import requests

from odoo import _, fields, http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request


class DoorAndDoorAuthSignup(AuthSignupHome):
    _CUSTOM_FIELDS = (
        "phone",
        "mobile",
        "company_name",
        "street",
        "street2",
        "city",
        "state_name",
        "zip",
        "country_id",
        "customer_type",
        "builder_name_claim",
        "builder_license",
        "project_interest",
        "privacy_consent",
        "verification_code",
    )

    @http.route("/registro", type="http", auth="public", website=True, sitemap=True)
    def doorandoor_registration(self, **kwargs):
        return request.redirect("/web/signup")

    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        for field_name in self._CUSTOM_FIELDS:
            qcontext[field_name] = request.params.get(field_name, qcontext.get(field_name, ""))
        qcontext["ddwr_countries"] = request.env["res.country"].sudo().search([], order="name")
        qcontext["ddwr_verification_pending"] = bool(
            request.session.get("ddwr_signup_otp_email") == (qcontext.get("login") or "").strip().lower()
        )
        return qcontext

    @staticmethod
    def _otp_hash(salt, email, code):
        return hashlib.sha256(f"{salt}:{email}:{code}".encode()).hexdigest()

    def _send_signup_otp(self, qcontext):
        params = request.env["ir.config_parameter"].sudo()
        if params.get_param("doorandoor_registration.verification_channel") != "telegram_test":
            raise UserError(_("El canal de verificación del registro no está configurado."))
        token = params.get_param("doorandoor_credit.telegram_bot_token")
        configured_chat_ids = params.get_param("doorandoor_registration.telegram_chat_ids")
        fallback_chat_id = params.get_param("doorandoor_credit.telegram_chat_id")
        chat_ids = list(dict.fromkeys(
            chat_id.strip()
            for chat_id in (configured_chat_ids or fallback_chat_id or "").replace(";", ",").split(",")
            if chat_id.strip()
        ))
        if not token or not chat_ids:
            raise UserError(_("Configure el bot y los chats de Telegram para la prueba."))
        email = (qcontext.get("login") or "").strip().lower()
        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        expires_at = int(time.time()) + 600
        text = (
            "DOORANDDOOR — VERIFICACIÓN DE REGISTRO (PRUEBA LOCAL)\n\n"
            f"Correo solicitado: {email}\n"
            f"Cliente: {(qcontext.get('name') or '').strip()}\n"
            f"Código: {code}\n"
            "Vigencia: 10 minutos\n\n"
            "Introduzca este código en el formulario local. No lo comparta."
        )
        failed_chat_ids = []
        for chat_id in chat_ids:
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": text},
                    timeout=10,
                )
                response.raise_for_status()
                payload = response.json()
                if not payload.get("ok"):
                    failed_chat_ids.append(chat_id)
            except (requests.RequestException, ValueError):
                failed_chat_ids.append(chat_id)
        if failed_chat_ids:
            raise UserError(
                _("No se pudo entregar el código a todos los chats internos configurados.")
            )
        request.session["ddwr_signup_otp_email"] = email
        request.session["ddwr_signup_otp_salt"] = salt
        request.session["ddwr_signup_otp_hash"] = self._otp_hash(salt, email, code)
        request.session["ddwr_signup_otp_expires"] = expires_at
        request.session["ddwr_signup_otp_attempts"] = 0
        qcontext["ddwr_verification_pending"] = True

    def _verify_signup_otp(self, qcontext):
        email = (qcontext.get("login") or "").strip().lower()
        code = (qcontext.get("verification_code") or "").strip()
        pending_email = request.session.get("ddwr_signup_otp_email")
        if not pending_email or pending_email != email:
            self._send_signup_otp(qcontext)
            raise UserError(_("Enviamos un código de seis dígitos al bot de prueba. Introdúzcalo para crear la cuenta."))
        expires_at = int(request.session.get("ddwr_signup_otp_expires") or 0)
        if expires_at <= int(time.time()):
            self._clear_signup_otp()
            raise UserError(_("El código venció. Envíe nuevamente el formulario para solicitar otro."))
        if not code:
            qcontext["ddwr_verification_pending"] = True
            raise UserError(_("Introduzca el código enviado al bot de prueba."))
        attempts = int(request.session.get("ddwr_signup_otp_attempts") or 0) + 1
        request.session["ddwr_signup_otp_attempts"] = attempts
        if attempts > 5:
            self._clear_signup_otp()
            raise UserError(_("Se excedió el número de intentos. Solicite un código nuevo."))
        salt = request.session.get("ddwr_signup_otp_salt") or ""
        expected = request.session.get("ddwr_signup_otp_hash") or ""
        candidate = self._otp_hash(salt, email, code)
        if not hmac.compare_digest(candidate, expected):
            qcontext["ddwr_verification_pending"] = True
            raise UserError(_("El código de verificación no es correcto."))
        self._clear_signup_otp()

    @staticmethod
    def _clear_signup_otp():
        for key in (
            "ddwr_signup_otp_email", "ddwr_signup_otp_salt", "ddwr_signup_otp_hash",
            "ddwr_signup_otp_expires", "ddwr_signup_otp_attempts",
        ):
            request.session.pop(key, None)

    def _validate_doorandoor_signup(self, qcontext):
        required = {
            "phone": _("Teléfono"),
            "street": _("Dirección"),
            "city": _("Ciudad"),
            "state_name": _("Estado / provincia"),
            "zip": _("Código postal"),
            "country_id": _("País"),
            "customer_type": _("Tipo de cliente"),
        }
        missing = [label for key, label in required.items() if not (qcontext.get(key) or "").strip()]
        if missing:
            raise UserError(_("Complete los campos obligatorios: %s") % ", ".join(missing))
        if qcontext.get("customer_type") not in {"individual", "builder", "builder_client"}:
            raise UserError(_("Seleccione un tipo de cliente válido."))
        if qcontext.get("customer_type") == "builder" and not (qcontext.get("company_name") or "").strip():
            raise UserError(_("Indique el nombre de la empresa constructora."))
        if qcontext.get("customer_type") == "builder_client" and not (
            qcontext.get("builder_name_claim") or ""
        ).strip():
            raise UserError(_("Escriba el nombre de la constructora con la que está asociado."))
        if qcontext.get("privacy_consent") != "on":
            raise UserError(_("Debe aceptar el tratamiento de sus datos para crear la cuenta."))
        try:
            country_id = int(qcontext.get("country_id"))
        except (TypeError, ValueError):
            raise UserError(_("Seleccione un país válido."))
        if not request.env["res.country"].sudo().browse(country_id).exists():
            raise UserError(_("Seleccione un país válido."))

    def do_signup(self, qcontext):
        self._validate_doorandoor_signup(qcontext)
        self._verify_signup_otp(qcontext)
        super().do_signup(qcontext)
        user = request.env["res.users"].sudo().search(
            request.env["res.users"]._get_login_domain(qcontext.get("login")), limit=1
        )
        if not user:
            raise UserError(_("No fue posible completar el perfil del cliente."))
        country_id = int(qcontext["country_id"])
        partner = user.partner_id.sudo()
        partner.write(
            {
                "phone": (qcontext.get("phone") or "").strip(),
                "mobile": (qcontext.get("mobile") or "").strip(),
                "company_name": (qcontext.get("company_name") or "").strip(),
                "street": (qcontext.get("street") or "").strip(),
                "street2": (qcontext.get("street2") or "").strip(),
                "city": (qcontext.get("city") or "").strip(),
                "zip": (qcontext.get("zip") or "").strip(),
                "country_id": country_id,
                "ddwr_state_name": (qcontext.get("state_name") or "").strip(),
                "ddwr_customer_type": qcontext.get("customer_type"),
                "ddwr_builder_name_claim": (qcontext.get("builder_name_claim") or "").strip(),
                "ddwr_builder_license": (qcontext.get("builder_license") or "").strip(),
                "ddwr_project_interest": (qcontext.get("project_interest") or "").strip(),
                "ddwr_registration_status": "pending",
                "ddwr_privacy_consent": True,
                "ddwr_privacy_consent_date": fields.Datetime.now(),
            }
        )
