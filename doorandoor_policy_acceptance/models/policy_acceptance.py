import secrets
from datetime import date, timedelta

import requests

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoorAndDoorPolicyAcceptance(models.Model):
    _name = "doorandoor.policy.acceptance"
    _description = "Aceptación de políticas DoorAndDoor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "accepted_at desc, create_date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner", required=True, index=True, ondelete="restrict", tracking=True
    )
    policy_id = fields.Many2one(
        "doorandoor.policy.document", required=True, index=True, ondelete="restrict", tracking=True
    )
    access_token = fields.Char(required=True, copy=False, readonly=True, index=True)
    state = fields.Selection(
        [("pending", "Pendiente"), ("accepted", "Aceptada"), ("expired", "Vencida"), ("cancelled", "Cancelada")],
        default="pending", required=True, index=True, tracking=True
    )
    signer_name = fields.Char(readonly=True, tracking=True)
    accepted_at = fields.Datetime(readonly=True, tracking=True)
    valid_until = fields.Date(readonly=True, tracking=True, index=True)
    ip_address = fields.Char(readonly=True)
    user_agent = fields.Char(readonly=True)
    email_sent_at = fields.Datetime(readonly=True, tracking=True)
    telegram_sent_at = fields.Datetime(readonly=True, tracking=True)
    source = fields.Selection(
        [("email", "Correo"), ("present", "Presencial"), ("portal", "Portal")],
        default="present", required=True, tracking=True
    )
    sale_order_id = fields.Many2one("sale.order", copy=False, ondelete="set null", tracking=True)
    account_move_id = fields.Many2one("account.move", copy=False, ondelete="set null", tracking=True)
    policy_version = fields.Char(related="policy_id.version", store=True, readonly=True)
    policy_sha256 = fields.Char(related="policy_id.sha256", store=True, readonly=True)
    accepted_language = fields.Selection(
        [("en", "English"), ("es", "Español")], readonly=True, tracking=True
    )
    accepted_document_sha256 = fields.Char(readonly=True)

    _sql_constraints = [
        ("access_token_unique", "unique(access_token)", "El enlace de aceptación debe ser único."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("access_token", secrets.token_urlsafe(32))
        return super().create(vals_list)

    def _get_public_url(self):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        if params.get_param("doorandoor_policy_acceptance.local_test_mode") == "1":
            base_url = params.get_param(
                "doorandoor_policy_acceptance.local_base_url", "http://doorandoor.local"
            ).rstrip("/")
        else:
            base_url = params.get_param("web.base.url").rstrip("/")
        return "%s/politicas/firmar/%s" % (base_url, self.access_token)

    def _send_invitation_once(self):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        local_test_mode = params.get_param("doorandoor_policy_acceptance.local_test_mode") == "1"
        if self._is_valid_now() or (local_test_mode and self.telegram_sent_at) or (not local_test_mode and self.email_sent_at):
            return False
        if local_test_mode:
            token = params.get_param("doorandoor_policy_acceptance.local_telegram_bot_token")
            chat_id = params.get_param("doorandoor_policy_acceptance.local_telegram_chat_id")
            if not token or not chat_id:
                raise ValidationError(_("El modo de prueba local no tiene configurado Telegram."))
            message = (
                "Prueba Local DoorAndDoor\n"
                "Cliente: %s\n"
                "Documento: %s\n"
                "Abra en una ventana privada para simular la aceptación:\n%s"
            ) % (
                self.partner_id.display_name,
                self.sale_order_id.name or self.account_move_id.display_name or "Cotización nueva",
                self._get_public_url(),
            )
            try:
                response = requests.post(
                    "https://api.telegram.org/bot%s/sendMessage" % token,
                    data={"chat_id": chat_id, "text": message},
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ValidationError(_("No se pudo enviar el enlace de prueba por Telegram: %s") % exc) from exc
            self.telegram_sent_at = fields.Datetime.now()
            return "telegram"
        if not self.partner_id.email:
            raise ValidationError(_("El cliente no tiene correo electrónico configurado."))
        self.env.ref("doorandoor_policy_acceptance.mail_template_policy_acceptance").send_mail(
            self.id, force_send=False, raise_exception=True
        )
        self.email_sent_at = fields.Datetime.now()
        return "email"

    def _is_valid_now(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return self.state == "accepted" and self.accepted_at and self.valid_until and self.valid_until >= today

    def _accept(self, signer_name, ip_address=None, user_agent=None, document_language="en"):
        self.ensure_one()
        if self.state != "pending":
            raise ValidationError(_("Este enlace ya no está pendiente de aceptación."))
        signer_name = (signer_name or "").strip()
        if len(signer_name) < 3:
            raise ValidationError(_("Indique el nombre completo de la persona que acepta las políticas."))
        accepted_date = fields.Date.context_today(self)
        end_of_year = date(accepted_date.year, 12, 31)
        valid_until = min(end_of_year, accepted_date + timedelta(days=365))
        document_language = "es" if document_language == "es" else "en"
        document_sha256 = self.policy_id.sha256_es if document_language == "es" else self.policy_id.sha256
        self.write({
            "state": "accepted",
            "signer_name": signer_name,
            "accepted_at": fields.Datetime.now(),
            "valid_until": valid_until,
            "ip_address": ip_address or False,
            "user_agent": (user_agent or "")[:512],
            "accepted_language": document_language,
            "accepted_document_sha256": document_sha256,
        })
        commercial_partner = self.partner_id.commercial_partner_id
        commercial_partner.message_post(body=_(
            "Políticas comerciales aceptadas por %(signer)s. Versión: %(version)s. "
            "Huella SHA-256: %(sha)s. Vigencia hasta: %(valid_until)s. Origen: %(source)s."
        ) % {
            "signer": signer_name,
            "version": self.policy_version,
            "sha": document_sha256,
            "valid_until": valid_until,
            "source": dict(self._fields["source"].selection).get(self.source),
        })
        for document in self.sale_order_id | self.account_move_id.sale_order_id:
            document.message_post(body=_("Cliente aceptó las políticas %(version)s mediante %(source)s.") % {
                "version": self.policy_version,
                "source": dict(self._fields["source"].selection).get(self.source),
            })
        if self.account_move_id:
            self.account_move_id.message_post(body=_("Cliente aceptó las políticas %(version)s mediante %(source)s.") % {
                "version": self.policy_version,
                "source": dict(self._fields["source"].selection).get(self.source),
            })
        return True
