"""Seed repeatable local products and BoMs for DoorAndDoor factory tests.

Run only through ``odoo shell`` against a development database. The script is
idempotent by product ``default_code`` and never deletes business records.
"""

from odoo import Command


def get_or_create_category(name, parent=False):
    domain = [("name", "=", name), ("parent_id", "=", parent.id if parent else False)]
    category = env["product.category"].search(domain, limit=1)
    return category or env["product.category"].create(
        {"name": name, "parent_id": parent.id if parent else False}
    )


def get_or_create_product(code, name, category, routes=False, list_price=0.0, cost=0.0):
    product = env["product.product"].search([("default_code", "=", code)], limit=1)
    values = {
        "name": name,
        "default_code": code,
        "categ_id": category.id,
        "type": "consu",
        "is_storable": True,
        "sale_ok": True,
        "purchase_ok": False,
        "list_price": list_price,
        "standard_price": cost,
    }
    if routes is not False:
        values["route_ids"] = [Command.set(routes.ids)]
    if product:
        product.product_tmpl_id.write(values)
        return product
    return env["product.template"].create(values).product_variant_id


root_category = get_or_create_category("PRUEBAS DDFC")
component_category = get_or_create_category("Componentes de puertas", root_category)
sale_category = get_or_create_category("Fabricacion por venta", root_category)
replenishment_category = get_or_create_category("Fabricacion para reposicion Orlando", root_category)

manufacture_route = env.ref("mrp.route_warehouse0_manufacture")
mto_route = env.ref("stock.route_warehouse0_mto")
# Odoo distributes MTO archived by default in some databases. It must be active
# before assigning it to products; otherwise the product write silently drops it.
if not mto_route.active:
    mto_route.active = True
sale_routes = manufacture_route | mto_route
replenishment_routes = manufacture_route

component_specs = [
    ("DDFC-COMP-MARCO-V", "Perfil vertical de marco de aluminio"),
    ("DDFC-COMP-MARCO-H", "Perfil horizontal de marco de aluminio"),
    ("DDFC-COMP-PANEL", "Panel solido de aluminio para puerta"),
    ("DDFC-COMP-VIDRIO", "Unidad de vidrio de impacto"),
    ("DDFC-COMP-BISAGRA", "Bisagra reforzada para puerta"),
    ("DDFC-COMP-CERRADURA", "Juego de cerradura y manija"),
    ("DDFC-COMP-TORNILLOS", "Juego de tornillos de ensamblaje"),
    ("DDFC-COMP-SELLO", "Tramo de sello perimetral"),
    ("DDFC-COMP-TRAVESANO", "Travesano de aluminio"),
    ("DDFC-COMP-ACABADO", "Juego de acabado y proteccion"),
]

components = {
    code: get_or_create_product(code, name, component_category, routes=env["stock.route"])
    for code, name in component_specs
}

door_specs = [
    {
        "code": "DDFC-VENTA-1L-3680",
        "name": "Puerta residencial 1 Lite 36x80 personalizada - Venta",
        "category": sale_category,
        "routes": sale_routes,
        "price": 1450.0,
        "cost": 720.0,
        "components": {
            "DDFC-COMP-MARCO-V": 2,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 1,
            "DDFC-COMP-VIDRIO": 1,
            "DDFC-COMP-BISAGRA": 3,
            "DDFC-COMP-CERRADURA": 1,
            "DDFC-COMP-TORNILLOS": 1,
            "DDFC-COMP-SELLO": 1,
            "DDFC-COMP-ACABADO": 1,
        },
    },
    {
        "code": "DDFC-VENTA-FR-7280",
        "name": "Puerta francesa doble 72x80 personalizada - Venta",
        "category": sale_category,
        "routes": sale_routes,
        "price": 2600.0,
        "cost": 1380.0,
        "components": {
            "DDFC-COMP-MARCO-V": 3,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 2,
            "DDFC-COMP-VIDRIO": 2,
            "DDFC-COMP-BISAGRA": 6,
            "DDFC-COMP-CERRADURA": 2,
            "DDFC-COMP-TORNILLOS": 2,
            "DDFC-COMP-SELLO": 2,
            "DDFC-COMP-ACABADO": 2,
        },
    },
    {
        "code": "DDFC-VENTA-SH-3680",
        "name": "Puerta de impacto SH 36x80 personalizada - Venta",
        "category": sale_category,
        "routes": sale_routes,
        "price": 1850.0,
        "cost": 960.0,
        "components": {
            "DDFC-COMP-MARCO-V": 2,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 1,
            "DDFC-COMP-VIDRIO": 2,
            "DDFC-COMP-TRAVESANO": 1,
            "DDFC-COMP-BISAGRA": 3,
            "DDFC-COMP-CERRADURA": 1,
            "DDFC-COMP-TORNILLOS": 1,
            "DDFC-COMP-SELLO": 1,
            "DDFC-COMP-ACABADO": 1,
        },
    },
    {
        "code": "DDFC-REPO-SOL-3680-ORL",
        "name": "Puerta aluminio solida 36x80 estandar - Reposicion Orlando",
        "category": replenishment_category,
        "routes": replenishment_routes,
        "price": 980.0,
        "cost": 480.0,
        "components": {
            "DDFC-COMP-MARCO-V": 2,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 1,
            "DDFC-COMP-BISAGRA": 3,
            "DDFC-COMP-CERRADURA": 1,
            "DDFC-COMP-TORNILLOS": 1,
            "DDFC-COMP-SELLO": 1,
            "DDFC-COMP-ACABADO": 1,
        },
    },
    {
        "code": "DDFC-REPO-6P-3280-ORL",
        "name": "Puerta seis paneles 32x80 estandar - Reposicion Orlando",
        "category": replenishment_category,
        "routes": replenishment_routes,
        "price": 1150.0,
        "cost": 570.0,
        "components": {
            "DDFC-COMP-MARCO-V": 2,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 1,
            "DDFC-COMP-TRAVESANO": 3,
            "DDFC-COMP-BISAGRA": 3,
            "DDFC-COMP-CERRADURA": 1,
            "DDFC-COMP-TORNILLOS": 1,
            "DDFC-COMP-SELLO": 1,
            "DDFC-COMP-ACABADO": 1,
        },
    },
    {
        "code": "DDFC-REPO-1L-3080-ORL",
        "name": "Puerta 1 Lite 30x80 estandar - Reposicion Orlando",
        "category": replenishment_category,
        "routes": replenishment_routes,
        "price": 1250.0,
        "cost": 630.0,
        "components": {
            "DDFC-COMP-MARCO-V": 2,
            "DDFC-COMP-MARCO-H": 2,
            "DDFC-COMP-PANEL": 1,
            "DDFC-COMP-VIDRIO": 1,
            "DDFC-COMP-BISAGRA": 3,
            "DDFC-COMP-CERRADURA": 1,
            "DDFC-COMP-TORNILLOS": 1,
            "DDFC-COMP-SELLO": 1,
            "DDFC-COMP-ACABADO": 1,
        },
    },
]

tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion")], limit=1)
orlando = env["stock.warehouse"].search([("name", "ilike", "Orlando")], limit=1)
assert tampa and orlando, "No se encontraron Tampa Produccion y Orlando"

doors = env["product.product"]
boms = env["mrp.bom"]
for spec in door_specs:
    door = get_or_create_product(
        spec["code"],
        spec["name"],
        spec["category"],
        routes=spec["routes"],
        list_price=spec["price"],
        cost=spec["cost"],
    )
    doors |= door
    bom = env["mrp.bom"].search(
        [("product_tmpl_id", "=", door.product_tmpl_id.id), ("product_id", "=", False)],
        limit=1,
    )
    bom_values = {
        "product_tmpl_id": door.product_tmpl_id.id,
        "product_qty": 1.0,
        "product_uom_id": door.uom_id.id,
        "type": "normal",
        "picking_type_id": tampa.manu_type_id.id,
    }
    if bom:
        bom.write(bom_values)
    else:
        bom = env["mrp.bom"].create(bom_values)
    wanted_codes = set(spec["components"])
    bom.bom_line_ids.filtered(
        lambda line: line.product_id.default_code not in wanted_codes
    ).unlink()
    for component_code, quantity in spec["components"].items():
        component = components[component_code]
        line = bom.bom_line_ids.filtered(lambda item: item.product_id == component)[:1]
        line_values = {
            "bom_id": bom.id,
            "product_id": component.id,
            "product_qty": quantity,
            "product_uom_id": component.uom_id.id,
        }
        if line:
            line.write(line_values)
        else:
            env["mrp.bom.line"].create(line_values)
    boms |= bom

for component in components.values():
    quant = env["stock.quant"].search(
        [("product_id", "=", component.id), ("location_id", "=", tampa.lot_stock_id.id)],
        limit=1,
    )
    current_qty = quant.quantity if quant else 0.0
    if current_qty < 500.0:
        env["stock.quant"]._update_available_quantity(
            component, tampa.lot_stock_id, 500.0 - current_qty
        )

env.cr.commit()
print("DDFC TEST DATA READY")
print("TAMPA", tampa.id, tampa.display_name)
print("ORLANDO", orlando.id, orlando.display_name)
print("DOORS", [(product.id, product.default_code, product.display_name) for product in doors])
print(
    "BOMS",
    [(bom.id, bom.display_name, len(bom.bom_line_ids)) for bom in boms],
)
