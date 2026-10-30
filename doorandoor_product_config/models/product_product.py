from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.tools.float_utils import float_is_zero


class ProductProduct(models.Model):
    _inherit = "product.product"

    ddpc_item_search = fields.Char(
        string="ITEM / Variante",
        compute="_compute_ddpc_item_search",
        search="_search_ddpc_item_search",
        help=(
            "Busque una variante escribiendo varios valores de atributos, "
            "por ejemplo: shaker 2 30 80 LH Gold."
        ),
    )

    ddpc_item_group = fields.Char(
        string="ITEM / Variante",
        compute="_compute_ddpc_item_group",
        store=True,
        index=True,
    )

    def _compute_ddpc_item_search(self):
        for product in self:
            product.ddpc_item_search = " ".join(
                product.product_template_attribute_value_ids.mapped("name")
            )

    @api.depends("product_template_attribute_value_ids.name")
    def _compute_ddpc_item_group(self):
        for product in self:
            product.ddpc_item_group = " / ".join(
                product.product_template_attribute_value_ids.sorted(
                    lambda value: (
                        value.attribute_id.sequence,
                        value.attribute_id.id,
                        value.id,
                    )
                ).mapped("name")
            ) or product.display_name

    @api.model
    def _search_ddpc_item_search(self, operator, value):
        if not value:
            return []
        tokens = [
            token.strip()
            for token in str(value).replace(",", " ").split()
            if token.strip()
        ]
        if not tokens:
            return []
        if operator not in ("=", "ilike", "=ilike", "like", "=like"):
            return [("id", "=", 0)]
        return expression.AND([
            [("product_template_attribute_value_ids.name", "ilike", token)]
            for token in tokens
        ])

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Find ITEM variants by any combination of attribute values.

        Odoo's standard product lookup already handles product name, internal
        reference, barcode and supplier references.  Keep those results and
        append variants for which *every* word entered by the user matches an
        attribute value.  Consequently ``72 80 LH gray`` narrows the selector
        to an ITEM carrying all four values while the domain of the originating
        field (warehouse, storable product, active record, etc.) remains in
        force.
        """
        standard_results = super().name_search(
            name=name, args=args, operator=operator, limit=limit
        )
        if (
            not name
            or operator in expression.NEGATIVE_TERM_OPERATORS
            or operator not in ("=", "ilike", "=ilike", "like", "=like")
        ):
            return standard_results

        tokens = [token.strip() for token in name.replace(",", " ").split() if token.strip()]
        if not tokens:
            return standard_results

        attribute_domain = expression.AND([
            [("product_template_attribute_value_ids.name", "ilike", token)]
            for token in tokens
        ])
        domain = expression.AND([args or [], attribute_domain])
        standard_ids = [product_id for product_id, _display_name in standard_results]
        if standard_ids:
            domain = expression.AND([domain, [("id", "not in", standard_ids)]])
        remaining = None if limit is None else max(limit - len(standard_results), 0)
        if remaining == 0:
            return standard_results
        attribute_products = self.search_fetch(
            domain, ["display_name"], limit=remaining
        )
        return standard_results + [
            (product.id, product.display_name) for product in attribute_products.sudo()
        ]

    @api.model
    def _ddpc_can_edit_variant_price(self):
        return (
            self.env.su
            or self.env.user.has_group("base.group_system")
            or self.env.user.has_group(
                "doorandoor_product_config.group_ddpc_variant_price_editor"
            )
        )

    ddpc_variant_extra_price = fields.Float(
        string="Variant Extra Price",
        digits="Product Price",
        help="Additional amount to add over the product template sales price when this variant is invoiced.",
    )
    ddpc_variant_final_price = fields.Float(
        string="Precio final",
        digits="Product Price",
        compute="_compute_ddpc_variant_final_price",
        inverse="_inverse_ddpc_variant_final_price",
        help="Precio de venta final de esta variante: precio base más adicional.",
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

    @api.depends("product_tmpl_id.list_price", "ddpc_variant_extra_price")
    def _compute_ddpc_variant_final_price(self):
        for variant in self:
            variant.ddpc_variant_final_price = (
                variant.product_tmpl_id.list_price + variant.ddpc_variant_extra_price
            )

    def _inverse_ddpc_variant_final_price(self):
        if not self._ddpc_can_edit_variant_price():
            raise AccessError(_(
                "Solo Administradores/Ajustes o Editores de precios finales pueden "
                "configurar precios de variantes."
            ))
        for variant in self:
            variant.ddpc_variant_extra_price = (
                variant.ddpc_variant_final_price - variant.product_tmpl_id.list_price
            )

    @api.model_create_multi
    def create(self, vals_list):
        if (
            any("ddpc_variant_extra_price" in vals for vals in vals_list)
            and not self._ddpc_can_edit_variant_price()
        ):
            raise AccessError(_(
                "Solo Administradores/Ajustes o Editores de precios finales pueden "
                "configurar precios de variantes."
            ))
        return super().create(vals_list)

    def write(self, vals):
        if (
            "ddpc_variant_extra_price" in vals
            and not self._ddpc_can_edit_variant_price()
        ):
            raise AccessError(_(
                "Solo Administradores/Ajustes o Editores de precios finales pueden "
                "configurar precios de variantes."
            ))
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
