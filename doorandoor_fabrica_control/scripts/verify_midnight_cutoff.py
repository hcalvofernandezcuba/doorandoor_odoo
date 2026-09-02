"""Validate immutable midnight snapshots and deferred sales manufacturing."""

from datetime import datetime

from odoo.exceptions import UserError


tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion")], limit=1)
orlando = env["stock.warehouse"].search([("name", "ilike", "Orlando")], limit=1)
product = env["product.product"].search([("default_code", "=", "DDFC-VENTA-1L-3680")], limit=1)
assert tampa and orlando and product

early = env["ddfc.production.need"].create({
    "warehouse_id": orlando.id, "product_id": product.id, "requested_qty": 2,
    "required_date": "2099-01-02", "eligible_at": datetime(2099, 1, 2, 4, 59, 59),
    "source_type": "sale", "origin": "DDFC-CUTOFF-EARLY",
})
late = env["ddfc.production.need"].create({
    "warehouse_id": orlando.id, "product_id": product.id, "requested_qty": 3,
    "required_date": "2099-01-02", "eligible_at": datetime(2099, 1, 2, 5, 0, 1),
    "source_type": "sale", "origin": "DDFC-CUTOFF-LATE",
})
plan = env["ddfc.daily.plan"].create({
    "plan_date": "2099-01-02", "production_warehouse_id": tampa.id,
    "material_destination_location_id": tampa.manu_type_id.default_location_src_id.id,
    "snapshot_at": datetime(2099, 1, 2, 5, 0, 0),
})
plan.action_load_pending_needs()
assert plan.snapshot_locked and len(plan.line_ids) == 1
assert early in plan.line_ids.need_ids and late not in plan.line_ids.need_ids

try:
    plan.action_load_pending_needs()
    raise AssertionError("El corte permitio una segunda carga")
except UserError:
    pass
try:
    plan.line_ids.write({"requested_qty": 99})
    raise AssertionError("El corte permitio alterar la cantidad solicitada")
except UserError:
    pass
plan.line_ids.approved_qty = 1
plan.action_approve()
assert len(plan.production_ids) == 1 and plan.production_ids.state == "confirmed"
assert early.state == "pending" and early.pending_qty == 1
assert late.state == "pending" and late.pending_qty == 3

invoice = env["account.move"].search([
    ("sale_order_id", "!=", False), ("invoice_line_ids.product_id", "!=", False),
], limit=1)
assert invoice, "No existe una factura con pedido para probar el lanzador"
invoice_line = invoice.invoice_line_ids.filtered("product_id")[:1]
fulfillment = env["doorandoor.fulfillment.line"].create({
    "move_id": invoice.id, "move_line_id": invoice_line.id,
    "sale_order_id": invoice.sale_order_id.id, "qty_invoiced": 1,
    "qty_released": 1, "state": "ready_mrp",
})
invoice._ddsn_sync_mrp_fulfillment_documents()
assert fulfillment.qty_sent_planning == 1
assert fulfillment.production_need_ids and not fulfillment.mrp_production_id

count_before = env["ddfc.daily.plan"].search_count([])
env["ddfc.daily.plan"]._cron_generate_daily_plans()
env["ddfc.daily.plan"]._cron_generate_daily_plans()
assert env["ddfc.daily.plan"].search_count([]) == count_before

print("CUTOFF OK", plan.name, early.name, late.name)
print("LOCK OK", plan.snapshot_at, len(plan.line_ids))
print("DEFERRED SALE OK", fulfillment.id, fulfillment.production_need_ids.ids)
print("CRON IDEMPOTENT OK", count_before)
env.cr.rollback()
print("ROLLBACK OK")
