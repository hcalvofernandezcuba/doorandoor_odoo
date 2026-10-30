# Execute with: odoo shell -d pruebas < import_catalog_for_training.py
# `env` is supplied by the Odoo shell. This intentionally never imports stock,
# partners, sales, accounting documents, or product quantities.
import base64
import json

INPUT = "/tmp/doorandoor_catalog_training.json"
MODULE = "doorandoor_initial_inventory_import"


def external(name, model, source_id):
    xml_name = "%s_%s" % (name, source_id)
    data = env["ir.model.data"].search([
        ("module", "=", MODULE), ("name", "=", xml_name), ("model", "=", model),
    ], limit=1)
    return data, xml_name


def mark(name, model, source_id, record):
    data, xml_name = external(name, model, source_id)
    values = {"module": MODULE, "name": xml_name, "model": model, "res_id": record.id, "noupdate": True}
    if data:
        data.write(values)
    else:
        env["ir.model.data"].create(values)


def category(complete_name):
    return env["product.category"].search([( "complete_name", "=", complete_name)], limit=1) or env["product.category"].search([], limit=1)


def target_attribute(source):
    marker, _ = external("gestion_attribute", "product.attribute", source["source_id"])
    if marker:
        return env["product.attribute"].browse(marker.res_id)
    attribute = env["product.attribute"].search([
        ("name", "=", source["name"]),
        ("create_variant", "=", source["create_variant"]),
        ("display_type", "=", source["display_type"]),
    ], limit=1)
    if not attribute:
        attribute = env["product.attribute"].create({
            "name": source["name"], "create_variant": source["create_variant"],
            "display_type": source["display_type"], "sequence": source["sequence"],
        })
    mark("gestion_attribute", "product.attribute", source["source_id"], attribute)
    return attribute


def target_value(attribute, source):
    marker, _ = external("gestion_value", "product.attribute.value", source["source_id"])
    if marker:
        return env["product.attribute.value"].browse(marker.res_id)
    value = env["product.attribute.value"].search([
        ("attribute_id", "=", attribute.id), ("name", "=", source["name"]),
    ], limit=1)
    if not value:
        value = env["product.attribute.value"].create({"attribute_id": attribute.id, "name": source["name"]})
    mark("gestion_value", "product.attribute.value", source["source_id"], value)
    return value


with open(INPUT, encoding="utf-8") as stream:
    payload = json.load(stream)

# Keep the same operational ceiling in the training database. It is required
# for Interior Door, whose valid catalogue contains 7,488 combinations.
env["ir.config_parameter"].sudo().set_param("product.dynamic_variant_limit", "10000")

for source in payload["templates"]:
    marker, _ = external("gestion_template", "product.template", source["source_id"])
    template = env["product.template"].browse(marker.res_id) if marker else env["product.template"]
    if template and not template.exists():
        template = env["product.template"]
    if not template:
        template = env["product.template"].create({
            "name": source["name"], "type": source["type"], "categ_id": category(source["category"]).id,
            "sale_ok": source["sale_ok"], "purchase_ok": source["purchase_ok"], "active": source["active"],
            "list_price": source["list_price"], "standard_price": source["standard_price"],
            "image_1920": base64.b64decode(source["image_1920"]) if source["image_1920"] else False,
        })
        mark("gestion_template", "product.template", source["source_id"], template)
        commands = []
        for attribute_source in source["attributes"]:
            attribute = target_attribute(attribute_source)
            values = [target_value(attribute, value).id for value in attribute_source["values"]]
            commands.append((0, 0, {"attribute_id": attribute.id, "value_ids": [(6, 0, values)]}))
        template.write({"attribute_line_ids": commands})

    target_variants = {}
    for variant in template.product_variant_ids:
        key = tuple(sorted("%s=%s" % (ptav.attribute_id.name, ptav.product_attribute_value_id.name)
                           for ptav in variant.product_template_attribute_value_ids))
        target_variants[key] = variant
    for source_variant in source["variants"]:
        variant = target_variants.get(tuple(source_variant["combination"]))
        if not variant:
            values = env["product.template.attribute.value"]
            for key in source_variant["combination"]:
                attribute_name, value_name = key.split("=", 1)
                value = template.valid_product_template_attribute_line_ids.product_template_value_ids.filtered(
                    lambda ptav: ptav.attribute_id.name == attribute_name and ptav.product_attribute_value_id.name == value_name
                )
                values |= value
            if len(values) == len(source_variant["combination"]):
                variant = template._create_product_variant(values)
        if variant:
            variant.write({"default_code": source_variant["default_code"], "active": source_variant["active"]})
            barcode = source_variant["barcode"]
            if barcode:
                duplicate = env["product.product"].search([
                    ("barcode", "=", barcode), ("id", "!=", variant.id),
                ], limit=1)
                if duplicate:
                    print("BARCODE_CONFLICT", barcode, "kept on", duplicate.display_name)
                else:
                    variant.barcode = barcode
    env.cr.commit()
    print("IMPORTED", source["name"], template.product_variant_count)

print("DONE")
