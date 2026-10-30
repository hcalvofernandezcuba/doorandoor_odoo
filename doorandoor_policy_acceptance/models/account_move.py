from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    ddpa_policy_acceptance_id = fields.Many2one(
        "doorandoor.policy.acceptance", string="Aceptación de políticas", copy=False, readonly=True, tracking=True
    )
    ddpa_policy_status = fields.Char(compute="_compute_ddpa_policy_status", string="Políticas")
    ddpa_policy_valid_until = fields.Date(compute="_compute_ddpa_policy_status", string="Vigente hasta")
    ddpa_customer_email_missing = fields.Boolean(compute="_compute_ddpa_policy_status")

    def _ddpa_resolve_acceptance(self):
        self.ensure_one()
        acceptance = self.partner_id._ddpa_get_valid_acceptance() if self.partner_id else False
        if acceptance and self.ddpa_policy_acceptance_id != acceptance:
            self.ddpa_policy_acceptance_id = acceptance
        return acceptance

    def _compute_ddpa_policy_status(self):
        for move in self:
            acceptance = move._ddpa_resolve_acceptance()
            missing_email = bool(move.partner_id and not move.partner_id.email and not acceptance)
            move.ddpa_policy_status = (
                "Vigente" if acceptance else
                "Falta email del cliente" if missing_email else
                "Pendiente de aceptación"
            )
            move.ddpa_policy_valid_until = acceptance.valid_until if acceptance else False
            move.ddpa_customer_email_missing = missing_email

    def _ddpa_get_or_create_request(self, source="present"):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Seleccione un cliente antes de solicitar la aceptación."))
        policy = self.env["doorandoor.policy.document"].get_current_policy()
        if not policy:
            raise ValidationError(_("No existe una versión activa de las políticas comerciales."))
        valid = self._ddpa_resolve_acceptance()
        if valid:
            return valid
        acceptance = self.env["doorandoor.policy.acceptance"].sudo().search([
            ("partner_id.commercial_partner_id", "=", self.partner_id.commercial_partner_id.id),
            ("policy_id", "=", policy.id),
            ("account_move_id", "=", self.id),
            ("state", "=", "pending"),
        ], order="id desc", limit=1)
        if not acceptance:
            acceptance = self.env["doorandoor.policy.acceptance"].sudo().create({
                "partner_id": self.partner_id.commercial_partner_id.id,
                "policy_id": policy.id,
                "account_move_id": self.id,
                "sale_order_id": self.sale_order_id.id,
                "source": source,
            })
        elif acceptance.source != source:
            acceptance.source = source
        self.ddpa_policy_acceptance_id = acceptance
        return acceptance

    def action_ddpa_open_signature(self):
        self.ensure_one()
        acceptance = self._ddpa_get_or_create_request("present")
        if acceptance._is_valid_now():
            raise ValidationError(_("El cliente ya tiene una aceptación vigente hasta %s.") % acceptance.valid_until)
        return {"type": "ir.actions.act_url", "url": acceptance._get_public_url(), "target": "new"}

    def action_ddpa_send_signature_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise ValidationError(_("El cliente no tiene correo electrónico."))
        acceptance = self._ddpa_get_or_create_request("email")
        if acceptance._is_valid_now():
            raise ValidationError(_("El cliente ya tiene una aceptación vigente hasta %s.") % acceptance.valid_until)
        channel = acceptance._send_invitation_once()
        if channel == "telegram":
            self.message_post(body=_("Enlace de aceptación enviado al Telegram de pruebas Local."))
        elif channel == "email":
            self.message_post(body=_("Solicitud de aceptación de políticas enviada a %s.") % self.partner_id.email)
        return True

    def action_ddpa_open_customer(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Seleccione un cliente."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Completar datos del cliente"),
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _ddpa_require_policy_acceptance(self):
        for move in self:
            if move.move_type == "out_invoice" and not move._ddpa_resolve_acceptance():
                raise ValidationError(_(
                    "El cliente %(customer)s debe aceptar las políticas comerciales vigentes antes de continuar. "
                    "Use Firmar políticas para atención presencial o Enviar políticas por correo."
                ) % {"customer": move.partner_id.display_name})

    def action_ddsn_confirm_preinvoice(self):
        self._ddpa_require_policy_acceptance()
        return super().action_ddsn_confirm_preinvoice()

    def action_ddsn_create_invoice_from_preinvoice(self):
        self._ddpa_require_policy_acceptance()
        return super().action_ddsn_create_invoice_from_preinvoice()

    def action_post(self):
        self._ddpa_require_policy_acceptance()
        return super().action_post()

    def action_invoice_sent(self):
        self._ddpa_require_policy_acceptance()
        return super().action_invoice_sent()

    def action_send_and_print(self):
        self._ddpa_require_policy_acceptance()
        return super().action_send_and_print()

    def _generate_and_send(self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings):
        self._ddpa_require_policy_acceptance()
        return super()._generate_and_send(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
            **custom_settings,
        )

    def action_print_pdf(self):
        # Gerencia retains its previously approved print-only exception.  It
        # does not bypass sending, confirmation, posting or downstream flows.
        if not self.env.user.has_group("base.group_system"):
            self._ddpa_require_policy_acceptance()
        return super().action_print_pdf()
