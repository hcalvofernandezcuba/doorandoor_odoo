from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_add_mode = fields.Selection(default="configurator")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["product_add_mode"] = "configurator"
        return super().create(vals_list)

    def get_single_product_variant(self):
        """Mantener el configurador estandar como selector unico en Ventas."""
        result = super().get_single_product_variant()
        if self.has_configurable_attributes:
            result["mode"] = "configurator"
        return result

    @api.model
    def _get_configurator_price(
        self, product_or_template, quantity, date, currency, pricelist, **kwargs
    ):
        """Show the selected item's configured final price in Sales.

        Odoo's configurator resolves an existing combination to a
        ``product.product`` before asking this hook for its price.  The
        standard pricelist engine only knows the template price and PTAV
        extras; DoorAndDoor's per-item final price is stored separately on
        the variant.  Consequently the dialog used to display the template
        base price even though the resulting quotation line was a different
        item.
        """
        if product_or_template._name == "product.product":
            product = product_or_template
            price = product.ddpc_variant_final_price
            uom = kwargs.get("uom")
            if uom and product.uom_id != uom:
                price = product.uom_id._compute_price(price, uom)
            if product.currency_id != currency:
                price = product.currency_id._convert(
                    price,
                    currency,
                    product.company_id or self.env.company,
                    date,
                )
            return price, False
        return super()._get_configurator_price(
            product_or_template,
            quantity,
            date,
            currency,
            pricelist,
            **kwargs,
        )

    def action_open_ddpc_variant_pricing(self):
        self.ensure_one()
        list_view = self.env.ref(
            "doorandoor_product_config.view_product_product_ddpc_variant_pricing_list"
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Precios por ítem",
            "res_model": "product.product",
            "view_mode": "list,form",
            "views": [(list_view.id, "list"), (False, "form")],
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "search_default_product_tmpl_id": self.id,
            },
            "target": "current",
        }
