"""Create two persistent, non-completed MOs for visual local testing."""

test_cases = [
    ("DDFC-VENTA-1L-3680", "DDFC-PRUEBA-VISUAL-VENTA"),
    ("DDFC-REPO-SOL-3680-ORL", "DDFC-PRUEBA-VISUAL-REPOSICION-ORLANDO"),
]

tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion")], limit=1)
assert tampa and tampa.manu_type_id, "No se encontro la operacion de fabricacion de Tampa"

created_or_found = env["mrp.production"]
for product_code, origin in test_cases:
    product = env["product.product"].search([("default_code", "=", product_code)], limit=1)
    assert product, f"No se encontro el producto {product_code}"
    bom = env["mrp.bom"].search(
        [("product_tmpl_id", "=", product.product_tmpl_id.id)], limit=1
    )
    assert bom, f"No se encontro la LdM de {product_code}"

    production = env["mrp.production"].search([("origin", "=", origin)], limit=1)
    if not production:
        production = env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_qty": 1.0,
                "product_uom_id": product.uom_id.id,
                "bom_id": bom.id,
                "picking_type_id": tampa.manu_type_id.id,
                "location_src_id": tampa.manu_type_id.default_location_src_id.id,
                "location_dest_id": tampa.manu_type_id.default_location_dest_id.id,
                "origin": origin,
            }
        )
        production.action_confirm()
    created_or_found |= production

env.cr.commit()
print("DDFC PERSISTENT TEST ORDERS READY")
for production in created_or_found:
    print(
        "MO",
        production.id,
        production.name,
        production.origin,
        production.product_id.default_code,
        production.state,
        "raw_moves=",
        len(production.move_raw_ids),
        "finished_moves=",
        len(production.move_finished_ids),
    )
