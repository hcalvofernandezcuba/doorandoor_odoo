# Execute with: odoo shell -d doorandoor < export_catalog_for_training.py
# `env` is supplied by the Odoo shell.
import base64
import json

OUTPUT = "/tmp/doorandoor_catalog_training.json"
TEMPLATE_NAMES = [
    "Impact Doors", "impact ", "Interior Door", "Baseboard trim",
    "hardware", "designer doors", "mullion",
]


def value_key(value):
    return "%s=%s" % (value.attribute_id.name, value.name)


templates = env["product.template"].search([( "name", "in", TEMPLATE_NAMES)], order="id")
payload = {"schema": 1, "templates": []}
for template in templates:
    attributes = []
    for line in template.attribute_line_ids:
        attribute = line.attribute_id
        attributes.append({
            "source_id": attribute.id,
            "name": attribute.name,
            "create_variant": attribute.create_variant,
            "display_type": attribute.display_type,
            "sequence": attribute.sequence,
            "values": [{"source_id": value.id, "name": value.name} for value in line.value_ids],
        })
    variants = []
    for variant in template.product_variant_ids:
        variants.append({
            "combination": sorted(value_key(value.product_attribute_value_id)
                                  for value in variant.product_template_attribute_value_ids),
            "default_code": variant.default_code,
            "barcode": variant.barcode,
            "active": variant.active,
        })
    payload["templates"].append({
        "source_id": template.id,
        "name": template.name,
        "type": template.type,
        "sale_ok": template.sale_ok,
        "purchase_ok": template.purchase_ok,
        "active": template.active,
        "list_price": template.list_price,
        "standard_price": template.standard_price,
        "category": template.categ_id.complete_name,
        "image_1920": base64.b64encode(template.image_1920).decode() if template.image_1920 else False,
        "attributes": attributes,
        "variants": variants,
    })

with open(OUTPUT, "w", encoding="utf-8") as stream:
    json.dump(payload, stream, ensure_ascii=False)
print("EXPORTED", len(payload["templates"]), "templates", sum(len(x["variants"]) for x in payload["templates"]), "variants", OUTPUT)
