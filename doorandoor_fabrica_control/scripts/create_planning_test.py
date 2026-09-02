"""Create an idempotent local scenario for daily manufacturing planning."""

from odoo import fields


tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion")], limit=1)
orlando = env["stock.warehouse"].search([("name", "ilike", "Orlando")], limit=1)
assert tampa and orlando, "No se encontraron Tampa Produccion y Orlando"

destination = tampa.manu_type_id.default_location_src_id
assert destination and destination.usage == "internal", "Falta ubicacion interna de produccion"

specs = [
    ("DDFC-VENTA-1L-3680", orlando, 3.0, "DDFC-PLAN-ORLANDO-1"),
    ("DDFC-REPO-SOL-3680-ORL", orlando, 4.0, "DDFC-PLAN-ORLANDO-2"),
    ("DDFC-VENTA-1L-3680", tampa, 2.0, "DDFC-PLAN-TAMPA-1"),
]
needs = env["ddfc.production.need"]
for code, warehouse, quantity, origin in specs:
    product = env["product.product"].search([("default_code", "=", code)], limit=1)
    assert product, f"No existe {code}; ejecuta primero seed_local_test_boms.py"
    need = env["ddfc.production.need"].search([("origin", "=", origin)], limit=1)
    values = {
        "warehouse_id": warehouse.id,
        "product_id": product.id,
        "requested_qty": quantity,
        "required_date": fields.Date.context_today(env.user),
        "source_type": "replenishment" if "REPO" in code else "sale",
        "origin": origin,
    }
    if need:
        if need.state == "pending":
            need.write(values)
    else:
        need = env["ddfc.production.need"].create(values)
    needs |= need

plan = env["ddfc.daily.plan"].search([("notes", "=", "DDFC-PLAN-PRUEBA-CONTROLADA")], limit=1)
if not plan:
    plan = env["ddfc.daily.plan"].create(
        {
            "plan_date": fields.Date.context_today(env.user),
            "production_warehouse_id": tampa.id,
            "material_destination_location_id": destination.id,
            "notes": "DDFC-PLAN-PRUEBA-CONTROLADA",
        }
    )
    plan.action_load_pending_needs()

env.cr.commit()
print("PLANNING TEST READY", plan.id, plan.name, plan.state)
print("NEEDS", [(need.name, need.warehouse_id.name, need.product_id.default_code, need.requested_qty) for need in needs])
print("LINES", [(line.warehouse_id.name, line.product_id.default_code, line.requested_qty, line.approved_qty) for line in plan.line_ids])
print("DESTINATION", destination.id, destination.complete_name)
