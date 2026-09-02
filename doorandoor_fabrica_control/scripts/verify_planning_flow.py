"""Verify the complete planning flow and roll back all test actions."""

plan = env["ddfc.daily.plan"].search([("notes", "=", "DDFC-PLAN-PRUEBA-CONTROLADA")], limit=1)
assert plan and plan.state == "draft", "No existe el plan de prueba en borrador"
assert len(plan.line_ids) == 3, f"Se esperaban 3 lineas y existen {len(plan.line_ids)}"

components = env["product.product"].search([("default_code", "like", "DDFC-COMP-%")])
before = {product.id: product.with_context(location=plan.production_warehouse_id.lot_stock_id.id).qty_available for product in components}

plan.action_approve()
assert plan.state == "approved", "El plan no quedo aprobado"
assert len(plan.production_ids) == 3, f"Se esperaban 3 OF y se crearon {len(plan.production_ids)}"
assert all(production.state == "confirmed" for production in plan.production_ids), "Hay OF sin confirmar"
assert len(plan.component_line_ids) == 9, f"Se esperaban 9 componentes consolidados y existen {len(plan.component_line_ids)}"

vertical = plan.component_line_ids.filtered(lambda line: line.product_id.default_code == "DDFC-COMP-MARCO-V")
assert len(vertical) == 1 and vertical.required_qty == 18.0, f"Marco vertical esperado 18, calculado {vertical.required_qty}"

plan.action_request_materials()
assert plan.state == "materials" and plan.material_picking_id, "No se creo el pedido de salida"
assert plan.material_picking_id.state not in ("done", "cancel"), "El pedido no debe validarse automaticamente"
assert len(plan.material_picking_id.move_ids) == 9, "El pedido no coincide con componentes consolidados"

after = {product.id: product.with_context(location=plan.production_warehouse_id.lot_stock_id.id).qty_available for product in components}
assert before == after, "Confirmar el pedido altero existencias antes de la validacion del almacen"

for report_xmlid in (
    "doorandoor_fabrica_control.action_report_ddfc_daily_plan",
    "doorandoor_fabrica_control.action_report_ddfc_material_request",
):
    pdf, output_type = env["ir.actions.report"]._render_qweb_pdf(report_xmlid, [plan.id])
    assert output_type == "pdf" and pdf.startswith(b"%PDF") and len(pdf) > 1000, f"PDF invalido: {report_xmlid}"
    print("PDF OK", report_xmlid, len(pdf))

print("PLAN OK", plan.name, len(plan.line_ids), len(plan.production_ids), len(plan.component_line_ids))
print("MATERIAL PICKING OK", plan.material_picking_id.name, plan.material_picking_id.state, len(plan.material_picking_id.move_ids))
print("INVENTORY UNCHANGED", len(before))
env.cr.rollback()
print("ROLLBACK OK: el plan permanece en borrador para la prueba visual")
