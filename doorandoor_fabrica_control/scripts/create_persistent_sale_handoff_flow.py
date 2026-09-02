"""Create an idempotent full sale-to-handoff pilot in the local database."""

from datetime import timedelta

from odoo import Command, fields


MARKER = "DDFC-FLUJO-COMPLETO-MAQ-ENS-20260830"

sale = env["sale.order"].search([("client_order_ref", "=", MARKER)], order="id asc", limit=1)
if sale:
    invoice = sale.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")[:1]
    need = invoice.fulfillment_line_ids.mapped("production_need_ids")[:1]
    production = need.plan_line_ids.mapped("production_id")[:1]
    print("FLOW ALREADY EXISTS", sale.name, invoice.name, need.name, production.name)
    print("WORK ORDERS", [(wo.sequence, wo.name, wo.workcenter_id.name, wo.state) for wo in production.workorder_ids])
    env.cr.rollback()
    raise SystemExit

company = env.company
tampa = env["stock.warehouse"].search([("name", "ilike", "Tampa Produccion"), ("company_id", "=", company.id)], limit=1)
orlando = env["stock.warehouse"].search([("name", "ilike", "Orlando"), ("company_id", "=", company.id)], limit=1)
assert tampa and orlando, "No se encontraron Tampa Produccion y Orlando"

source_product = env["product.product"].search([("default_code", "=", "DDFC-VENTA-1L-3680")], limit=1)
source_bom = env["mrp.bom"].search([("product_tmpl_id", "=", source_product.product_tmpl_id.id)], limit=1)
assert source_product and source_bom, "Faltan el producto o la LdM demostrativa base"

product = env["product.product"].search([("default_code", "=", "DDFC-HANDOFF-DOOR")], limit=1)
if not product:
    template = env["product.template"].create({
        "name": "Puerta piloto Maquinado a Ensamblaje",
        "default_code": "DDFC-HANDOFF-DOOR",
        "is_storable": True,
        "sale_ok": True,
        "purchase_ok": False,
        "list_price": 1500.0,
        "uom_id": source_product.uom_id.id,
        "uom_po_id": source_product.uom_id.id,
    })
    product = template.product_variant_id

bom = env["mrp.bom"].search([("product_tmpl_id", "=", product.product_tmpl_id.id)], limit=1)
if not bom:
    bom = env["mrp.bom"].create({
        "product_tmpl_id": product.product_tmpl_id.id,
        "product_qty": 1.0,
        "product_uom_id": product.uom_id.id,
        "type": "normal",
        "allow_operation_dependencies": True,
        "bom_line_ids": [Command.create({
            "product_id": line.product_id.id,
            "product_qty": line.product_qty,
            "product_uom_id": line.product_uom_id.id,
        }) for line in source_bom.bom_line_ids],
    })
else:
    bom.allow_operation_dependencies = True

machining_wc = env["mrp.workcenter"].search([("code", "=", "DDFC-MAQ")], limit=1)
if not machining_wc:
    machining_wc = env["mrp.workcenter"].create({"name": "Maquinado", "code": "DDFC-MAQ", "sequence": 10})
assembly_wc = env["mrp.workcenter"].search([("code", "=", "DDFC-ENS")], limit=1)
if not assembly_wc:
    assembly_wc = env["mrp.workcenter"].create({"name": "Ensamblaje", "code": "DDFC-ENS", "sequence": 20})

Operation = env["mrp.routing.workcenter"]
machining = Operation.create({
    "name": "Maquinado", "bom_id": bom.id, "workcenter_id": machining_wc.id,
    "sequence": 10, "time_cycle_manual": 30.0, "allow_operation_dependencies": True,
    "note": "Procesar las partes de la puerta y registrar la cantidad que sale de Maquinado.",
})
receipt = Operation.create({
    "name": "Recepción desde Maquinado", "bom_id": bom.id, "workcenter_id": assembly_wc.id,
    "sequence": 20, "time_cycle_manual": 5.0, "allow_operation_dependencies": True,
    "blocked_by_operation_ids": [Command.set(machining.ids)],
    "note": "Confirmar cantidad, condición y hora de entrada al área de Ensamblaje.",
})
Operation.create({
    "name": "Ensamblaje", "bom_id": bom.id, "workcenter_id": assembly_wc.id,
    "sequence": 30, "time_cycle_manual": 45.0, "allow_operation_dependencies": True,
    "blocked_by_operation_ids": [Command.set(receipt.ids)],
    "note": "Ensamblar únicamente después de validar la recepción desde Maquinado.",
})

partner = env["res.partner"].search([("ref", "=", "DDFC-HANDOFF-CLIENT")], limit=1)
if not partner:
    partner = env["res.partner"].create({
        "name": "Cliente Piloto Maquinado Ensamblaje",
        "ref": "DDFC-HANDOFF-CLIENT",
        "customer_rank": 1,
    })

sale_vals = {
    "partner_id": partner.id,
    "warehouse_id": orlando.id,
    "client_order_ref": MARKER,
    "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 2.0, "price_unit": 1500.0})],
}
if "ddpa_delivery_warehouse_id" in env["sale.order"]._fields:
    sale_vals["ddpa_delivery_warehouse_id"] = orlando.id
sale = env["sale.order"].create(sale_vals)
sale.action_confirm()

invoice = sale._create_invoices()
invoice.write({"fulfillment_route_policy": "force_mrp", "invoice_date": fields.Date.context_today(env.user)})
invoice.action_post()

journal = env["account.journal"].search([("type", "in", ("bank", "cash")), ("company_id", "=", company.id)], limit=1)
assert journal, "No existe diario de banco o caja para registrar el pago"
payment_wizard = env["account.payment.register"].with_context(
    active_model="account.move", active_ids=invoice.ids,
).create({
    "journal_id": journal.id,
    "payment_date": fields.Date.context_today(env.user),
    "amount": invoice.amount_residual,
})
payments = payment_wizard._create_payments()
invoice.invalidate_recordset()
invoice._ddsn_sync_release_from_payments()

need = invoice.fulfillment_line_ids.mapped("production_need_ids")[:1]
assert invoice.payment_state in ("paid", "in_payment"), "La factura no quedó pagada"
assert need and need.source_invoice_id == invoice, "El pago no generó la necesidad vinculada a la factura"

plan_date = fields.Date.context_today(env.user) + timedelta(days=1)
while env["ddfc.daily.plan"].search_count([
    ("company_id", "=", company.id), ("plan_date", "=", plan_date),
    ("production_warehouse_id", "=", tampa.id),
]):
    plan_date += timedelta(days=1)
plan = env["ddfc.daily.plan"].create({
    "plan_date": plan_date,
    "production_warehouse_id": tampa.id,
    "material_destination_location_id": tampa.manu_type_id.default_location_src_id.id,
    "notes": MARKER,
    "snapshot_at": fields.Datetime.now(),
    "snapshot_user_id": env.user.id,
    "snapshot_locked": True,
})
env["ddfc.daily.plan.line"].with_context(ddfc_snapshot_loading=True).create({
    "plan_id": plan.id,
    "warehouse_id": orlando.id,
    "product_id": product.id,
    "bom_id": bom.id,
    "requested_qty": need.pending_qty,
    "approved_qty": need.pending_qty,
    "need_ids": [Command.set(need.ids)],
})
plan.action_approve()
production = plan.production_ids[:1]
assert production and len(production.workorder_ids) == 3, "La OF no creó las tres órdenes de trabajo"
assert production.workorder_ids[1].state == "pending", "Recepción no quedó bloqueada por Maquinado"
assert production.workorder_ids[2].state == "pending", "Ensamblaje no quedó bloqueado por Recepción"

env.cr.commit()
print("FULL FLOW READY")
print("SALE", sale.id, sale.name, sale.amount_total)
print("INVOICE", invoice.id, invoice.name, invoice.payment_state)
print("PAYMENTS", payments.ids)
print("NEED", need.id, need.name, need.source_document)
print("PLAN", plan.id, plan.name, plan.plan_date)
print("MO", production.id, production.name)
print("WORK ORDERS", [(wo.sequence, wo.name, wo.workcenter_id.name, wo.state) for wo in production.workorder_ids])
