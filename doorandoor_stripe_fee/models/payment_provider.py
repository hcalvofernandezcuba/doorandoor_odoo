from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    ddtp_card_fee_rate = fields.Float(
        string="Cargo por procesamiento (%)",
        default=3.0,
        help="Porcentaje añadido a cada cobro realizado con tarjeta.",
    )
    ddtp_card_fee_product_id = fields.Many2one(
        "product.product",
        string="Producto de cargo por tarjeta",
        domain="[('type', '=', 'service')]",
        help="Producto de servicio usado para facturar el cargo de procesamiento.",
    )
    ddtp_payment_notification_partner_ids = fields.Many2many(
        "res.partner",
        "payment_provider_ddtp_notification_partner_rel",
        "provider_id",
        "partner_id",
        string="Destinatarios adicionales de pagos",
        help="Además de administradores de Ajustes y Control de Cobros.",
    )

    def _ddtp_validate_card_fee_configuration(self):
        self.ensure_one()
        if self.code not in ("stripe", "clover"):
            return True
        if self.ddtp_card_fee_rate < 0:
            raise ValidationError(_("El cargo por procesamiento no puede ser negativo."))
        if not self.ddtp_card_fee_product_id:
            raise ValidationError(
                _("Configure el producto de cargo por tarjeta antes de usar esta vía de cobro.")
            )
        return True
    @api.model
    def _ddtp_get_active_card_provider(self, company):
        """Return the active card provider, preferring Clover when available.

        Clover is the active card channel during the current rollout. Stripe
        remains compatible for historical flows or a future reactivation.
        """
        providers = self.sudo().search([
            ("code", "in", ("clover", "stripe")),
            ("state", "in", ("test", "enabled")),
            ("company_id", "=", company.id),
        ])
        return providers.sorted(lambda provider: (provider.code != "clover", provider.id))[:1]
