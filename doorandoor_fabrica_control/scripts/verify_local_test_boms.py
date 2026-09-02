"""Verify the repeatable DoorAndDoor local BoM fixture without persisting MOs."""

sale_codes = [
    "DDFC-VENTA-1L-3680",
    "DDFC-VENTA-FR-7280",
    "DDFC-VENTA-SH-3680",
]
replenishment_codes = [
    "DDFC-REPO-SOL-3680-ORL",
    "DDFC-REPO-6P-3280-ORL",
    "DDFC-REPO-1L-3080-ORL",
]
all_codes = sale_codes + replenishment_codes

products = env["product.product"].search([("default_code", "in", all_codes)])
assert len(products) == 6, f"Se esperaban 6 productos y se encontraron {len(products)}"
assert len(set(products.mapped("default_code"))) == 6, "Hay codigos de prueba duplicados"

manufacture_route = env.ref("mrp.route_warehouse0_manufacture")
mto_route = env.ref("stock.route_warehouse0_mto")
tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion")], limit=1)
assert tampa and tampa.manu_type_id, "Tampa no tiene operacion de fabricacion"
print("MTO ROUTE", mto_route.id, mto_route.name, "active=", mto_route.active)
print(
    "PRODUCT ROUTES",
    [(product.default_code, product.product_tmpl_id.route_ids.ids) for product in products],
)

for code in all_codes:
    product = products.filtered(lambda item: item.default_code == code)
    boms = env["mrp.bom"].search([("product_tmpl_id", "=", product.product_tmpl_id.id)])
    assert len(boms) == 1, f"{code}: se esperaba una LdM y se encontraron {len(boms)}"
    assert boms.bom_line_ids, f"{code}: LdM sin componentes"
    assert manufacture_route in product.route_ids, f"{code}: falta ruta Fabricar"
    if code in sale_codes:
        assert mto_route in product.route_ids, f"{code}: falta ruta Bajo pedido"
    else:
        assert mto_route not in product.route_ids, f"{code}: reposicion no debe ser Bajo pedido"

for code in (sale_codes[0], replenishment_codes[0]):
    product = products.filtered(lambda item: item.default_code == code)
    bom = env["mrp.bom"].search([("product_tmpl_id", "=", product.product_tmpl_id.id)], limit=1)
    production = env["mrp.production"].create(
        {
            "product_id": product.id,
            "product_qty": 1.0,
            "product_uom_id": product.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": tampa.manu_type_id.id,
            "location_src_id": tampa.manu_type_id.default_location_src_id.id,
            "location_dest_id": tampa.manu_type_id.default_location_dest_id.id,
            "origin": f"DDFC-SMOKE-{code}",
        }
    )
    production.action_confirm()
    assert production.state == "confirmed", f"{code}: OF no confirmada"
    assert len(production.move_raw_ids) == len(bom.bom_line_ids), (
        f"{code}: consumos {len(production.move_raw_ids)} != lineas LdM {len(bom.bom_line_ids)}"
    )
    print("MO OK", code, production.name, len(production.move_raw_ids), production.state)

print(
    "ROUTES OK",
    [(product.default_code, product.route_ids.mapped("name")) for product in products.sorted("default_code")],
)
env.cr.rollback()
print("ROLLBACK OK: las OF de humo no se guardaron")
