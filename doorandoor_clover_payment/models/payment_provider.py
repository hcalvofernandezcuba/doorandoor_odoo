from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("clover", "Clover")],
        ondelete={"clover": "set default"},
    )
    ddcl_environment = fields.Selection(
        [("sandbox", "Sandbox"), ("production", "Producción")],
        string="Entorno Clover", default="sandbox", required=True,
    )
    ddcl_integration_type = fields.Selection(
        [("iframe", "Formulario seguro integrado"), ("hosted_checkout", "Checkout alojado")],
        string="Integración Clover", default="iframe", required=True,
        help="El formulario real siempre pertenece a Clover; Odoo no recibe PAN ni CVC.",
    )
    ddcl_merchant_id = fields.Char(string="Merchant ID Clover", copy=False)
    ddcl_public_token = fields.Char(string="Clave pública Ecommerce", copy=False, password=True)
    ddcl_private_token = fields.Char(string="Clave privada Ecommerce", copy=False, password=True)
    ddcl_mock_mode = fields.Boolean(
        string="Simulador local Clover", default=False,
        help="Solo para desarrollo local. No transmite ni registra tarjetas.",
    )

    @api.model
    def _ddcl_enable_card_method_on_clover_providers(self):
        """Keep Clover visible in Odoo's online-payment selector.

        A Clover provider is configured from the generic payment-provider
        form, so Odoo does not automatically attach the standard online
        ``card`` payment method.  The accounting journal line alone is not
        enough for the portal/payment form, which then reports that no method
        is available.  This is intentionally idempotent and is called from
        module data on every upgrade.
        """
        card_method = self.env.ref("payment.payment_method_card", raise_if_not_found=False).with_context(active_test=False)
        providers = self.with_context(active_test=False).search([("code", "=", "clover")])
        if card_method:
            missing_card_method = providers.filtered(lambda provider: card_method not in provider.payment_method_ids)
            # Odoo only permits activating a payment method after a provider
            # supports it.  Associate Clover first so the first provider can
            # be created even when Stripe had archived the shared method.
            if missing_card_method:
                missing_card_method.with_context(ddcl_enabling_card_method=True).write({
                    "payment_method_ids": [(4, card_method.id)],
                })
            # ``card`` is shared by online providers.  Archiving Stripe must
            # not archive it for a still-active Clover provider.
            if not card_method.active and providers.filtered(lambda provider: provider.state in ("test", "enabled")):
                card_method.write({"active": True})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        providers.filtered(lambda provider: provider.code == "clover")._ddcl_enable_card_method_on_clover_providers()
        return providers

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("ddcl_enabling_card_method") and ("code" in vals or "payment_method_ids" in vals):
            self.filtered(lambda provider: provider.code == "clover")._ddcl_enable_card_method_on_clover_providers()
        return result

    def _ddcl_validate_ecommerce_configuration(self):
        self.ensure_one()
        if self.code != "clover":
            return True
        if self.ddcl_mock_mode:
            return True
        missing = []
        if not self.ddcl_merchant_id:
            missing.append(_("Merchant ID"))
        if not self.ddcl_public_token:
            missing.append(_("clave pública Ecommerce"))
        if not self.ddcl_private_token:
            missing.append(_("clave privada Ecommerce"))
        if missing:
            raise ValidationError(_(
                "Clover no está configurado. Faltan: %(items)s. "
                "Use el simulador local o complete la configuración sandbox."
            ) % {"items": ", ".join(missing)})
        return True
