import json

from odoo import http
from odoo.http import request


class DoorAndDoorWebsiteCatalog(http.Controller):
    @http.route(
        ["/catalogo", "/catalogo/<string:category_slug>"],
        type="http", auth="public", website=True, sitemap=True,
    )
    def catalog(self, category_slug=None, category=None, **kwargs):
        product_model = request.env["product.template"].sudo()
        category_model = request.env["doorandoor.website.catalog.category"].sudo()
        domain = [("active", "=", True), ("ddwc_catalog_visible", "=", True)]
        selected_category = False
        if category_slug:
            selected_category = category_model.search([
                ("slug", "=", category_slug), ("active", "=", True)
            ], limit=1)
            if not selected_category:
                return request.not_found()
        elif category:
            try:
                selected_category = category_model.browse(int(category)).exists()
            except (TypeError, ValueError):
                selected_category = False
            if selected_category:
                return request.redirect(f"/catalogo/{selected_category.slug}", code=301)
        if selected_category:
            domain.append(("ddwc_catalog_category_id", "=", selected_category.id))
        return request.render(
            "doorandoor_website_catalog.catalog_index",
            {
                "products": product_model.search(domain, order="ddwc_catalog_featured desc, name, id"),
                "categories": category_model.search([("active", "=", True)]),
                "selected_category": selected_category,
            },
        )

    @http.route("/catalogo/producto/<int:product_id>", type="http", auth="public", website=True, sitemap=True)
    def catalog_product(self, product_id, **kwargs):
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or not product.active or not product.ddwc_catalog_visible:
            return request.not_found()

        variants = product.product_variant_ids.filtered("active")
        attribute_lines = product.attribute_line_ids.filtered(
            lambda line: line.value_ids and any(
                variant.product_template_attribute_value_ids.filtered(
                    lambda ptav: ptav.attribute_id == line.attribute_id
                )
                for variant in variants
            )
        )
        attributes = []
        for line in attribute_lines:
            used_values = variants.product_template_attribute_value_ids.filtered(
                lambda ptav: ptav.attribute_id == line.attribute_id
            ).product_attribute_value_id
            attributes.append({
                "id": line.attribute_id.id,
                "name": line.attribute_id.name,
                "values": [
                    {"id": value.id, "name": value.name}
                    for value in line.value_ids.filtered(lambda value: value in used_values)
                ],
            })

        variant_payload = []
        for variant in variants:
            values = {
                str(ptav.attribute_id.id): ptav.product_attribute_value_id.id
                for ptav in variant.product_template_attribute_value_ids
                if ptav.attribute_id in attribute_lines.attribute_id
            }
            if len(values) != len(attributes):
                continue
            variant_payload.append({
                "i": variant.id,
                "c": variant.default_code or "",
                "v": values,
            })
        return request.render(
            "doorandoor_website_catalog.catalog_product",
            {
                "product": product,
                "catalog_attributes": attributes,
                "catalog_variants_json": json.dumps(
                    variant_payload, separators=(",", ":")
                ),
            },
        )
