from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.float_utils import float_is_zero


class ProductProduct(models.Model):
    _inherit = "product.product"

    ddpc_variant_extra_price = fields.Float(
        string="Variant Extra Price",
        digits="Product Price",
        help="Additional amount to add over the product template sales price when this variant is invoiced.",
    )
    ddpc_is_custom_variant = fields.Boolean(string="Variante personalizada", copy=False, index=True)
    ddpc_custom_attribute_value_id = fields.Many2one(
        "product.attribute.value", string="Valor personalizado", copy=False, readonly=True
    )
    ddpc_origin_invoice_id = fields.Many2one(
        "account.move", string="Factura de origen", copy=False, readonly=True
    )
    ddpc_last_delivery_date = fields.Date(string="Ultima entrega", copy=False, readonly=True)
    ddpc_archive_after_date = fields.Date(
        string="Archivar despues de", copy=False, readonly=True, index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        if (
            any("ddpc_variant_extra_price" in vals for vals in vals_list)
            and not self.env.su
            and not self.env.user.has_group("base.group_system")
        ):
            raise AccessError(_("Solo Administradores/Ajustes puede configurar precios de variantes."))
        return super().create(vals_list)

    def write(self, vals):
        if (
            "ddpc_variant_extra_price" in vals
            and not self.env.su
            and not self.env.user.has_group("base.group_system")
        ):
            raise AccessError(_("Solo Administradores/Ajustes puede configurar precios de variantes."))
        return super().write(vals)

    def _ddpc_mark_custom_variant_delivered(self, delivery_date=None):
        delivery_date = fields.Date.to_date(delivery_date or fields.Date.context_today(self))
        custom_variants = self.filtered("ddpc_is_custom_variant")
        if custom_variants:
            from datetime import timedelta

            custom_variants.write(
                {
                    "ddpc_last_delivery_date": delivery_date,
                    "ddpc_archive_after_date": delivery_date + timedelta(days=30),
                }
            )

    @api.model
    def _ddpc_open_document_domain(self, product):
        return [
            ("product_id", "=", product.id),
            ("move_id.state", "=", "draft"),
            ("move_id.move_type", "in", ("out_invoice", "out_refund")),
        ]

    def _ddpc_can_archive_custom_variant(self):
        self.ensure_one()
        if not float_is_zero(self.qty_available, precision_rounding=self.uom_id.rounding):
            return False
        if self.env["stock.move"].search_count(
            [("product_id", "=", self.id), ("state", "not in", ("done", "cancel"))], limit=1
        ):
            return False
        return not self.env["account.move.line"].search_count(
            self._ddpc_open_document_domain(self), limit=1
        )

    @api.model
    def _ddpc_archive_due_custom_variants(self):
        today = fields.Date.context_today(self)
        candidates = self.search(
            [
                ("ddpc_is_custom_variant", "=", True),
                ("active", "=", True),
                ("ddpc_archive_after_date", "!=", False),
                ("ddpc_archive_after_date", "<=", today),
            ]
        )
        archived = self.browse()
        for variant in candidates:
            if variant._ddpc_can_archive_custom_variant():
                variant.product_tmpl_id.message_post(
                    body=_("Variante personalizada %s archivada tras 30 dias sin actividad.")
                    % variant.display_name
                )
                variant.active = False
                archived |= variant
        return len(archived)
