from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

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
        for order in self:
            acceptance = order._ddpa_resolve_acceptance()
            missing_email = bool(order.partner_id and not order.partner_id.email and not acceptance)
            order.ddpa_policy_status = (
                "Vigente" if acceptance else
                "Falta email del cliente" if missing_email else
                "Pendiente de aceptación"
            )
            order.ddpa_policy_valid_until = acceptance.valid_until if acceptance else False
            order.ddpa_customer_email_missing = missing_email

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
            ("state", "=", "pending"),
        ], order="id desc", limit=1)
        if not acceptance:
            acceptance = self.env["doorandoor.policy.acceptance"].sudo().create({
                "partner_id": self.partner_id.commercial_partner_id.id,
                "policy_id": policy.id,
                "sale_order_id": self.id,
                "source": source,
            })
        elif acceptance.source != source:
            acceptance.source = source
        if not acceptance.sale_order_id:
            acceptance.sale_order_id = self
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
            self.message_post(body=_("Solicitud automática de aceptación de políticas enviada a %s.") % self.partner_id.email)
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
            "context": {"ddpa_return_sale_order_id": self.id},
        }

    def _ddpa_auto_prepare_policy(self):
        if self.env.context.get("ddpa_skip_auto_policy"):
            return
        for order in self.filtered(lambda record: record.partner_id and record.state in ("draft", "sent")):
            if order._ddpa_resolve_acceptance():
                continue
            local_test_mode = self.env["ir.config_parameter"].sudo().get_param(
                "doorandoor_policy_acceptance.local_test_mode"
            ) == "1"
            if not order.partner_id.email and not local_test_mode:
                order.message_post(body=_(
                    "Políticas pendientes: el cliente no tiene email. Complete su ficha antes de autorizar la venta."
                ))
                continue
            acceptance = order._ddpa_get_or_create_request("present" if local_test_mode else "email")
            channel = acceptance._send_invitation_once()
            if channel == "telegram":
                order.message_post(body=_(
                    "Modo Local: enlace de aceptación enviado por repo_update_bot para abrirlo en ventana privada."
                ))
            elif channel == "email":
                order.message_post(body=_(
                    "Solicitud automática de aceptación de políticas enviada a %s. La venta seguirá bloqueada hasta su aceptación web."
                ) % order.partner_id.email)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._ddpa_auto_prepare_policy()
        return orders

    def write(self, vals):
        result = super().write(vals)
        if "partner_id" in vals:
            self._ddpa_auto_prepare_policy()
        return result

    @api.onchange("partner_id")
    def _onchange_ddpa_partner_policy(self):
        if not self.partner_id or self.partner_id._ddpa_get_valid_acceptance():
            return
        params = self.env["ir.config_parameter"].sudo()
        local_test_mode = params.get_param("doorandoor_policy_acceptance.local_test_mode") == "1"
        policy = self.env["doorandoor.policy.document"].get_current_policy()
        if policy and (self.partner_id.email or local_test_mode):
            acceptance = self.env["doorandoor.policy.acceptance"].sudo().search([
                ("partner_id.commercial_partner_id", "=", self.partner_id.commercial_partner_id.id),
                ("policy_id", "=", policy.id),
                ("state", "=", "pending"),
            ], order="id desc", limit=1)
            if not acceptance:
                acceptance = self.env["doorandoor.policy.acceptance"].sudo().create({
                    "partner_id": self.partner_id.commercial_partner_id.id,
                    "policy_id": policy.id,
                    "source": "present" if local_test_mode else "email",
                })
            acceptance._send_invitation_once()
        if not self.partner_id.email and not local_test_mode:
            return {"warning": {
                "title": _("Email obligatorio para aprobar las políticas"),
                "message": _(
                    "Este cliente no tiene email. Puede completar su ficha para el envío automático o guardar "
                    "la cotización y usar Firmar políticas para que el cliente acepte directamente en pantalla."
                ),
            }}

    def _ddpa_require_policy_acceptance(self):
        for order in self:
            if not order._ddpa_resolve_acceptance():
                raise ValidationError(_(
                    "El cliente %(customer)s debe aceptar las políticas comerciales vigentes antes de confirmar la cotización. "
                    "Use Firmar políticas para atención presencial o Enviar políticas por correo."
                ) % {"customer": order.partner_id.display_name})

    def action_confirm(self):
        self._ddpa_require_policy_acceptance()
        return super().action_confirm()

    def action_quotation_send(self):
        """Do not send a commercial quotation before policy acceptance."""
        self._ddpa_require_policy_acceptance()
        return super().action_quotation_send()

    def action_ddsn_register_quote(self):
        """Block the commercial Next step before opening/creating a preinvoice."""
        self._ddpa_require_policy_acceptance()
        return super().action_ddsn_register_quote()

    def _ddsn_create_preinvoice(self):
        """Server-side backstop for every path that creates a preinvoice."""
        self._ddpa_require_policy_acceptance()
        return super()._ddsn_create_preinvoice()
