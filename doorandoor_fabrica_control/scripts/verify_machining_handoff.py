"""Prueba reversible para ejecutar con ``odoo shell``.

Valida el vale completo contra la OF persistente del piloto y revierte la
transacción para no dejar documentos operativos ficticios.
"""

from odoo import Command

production = env["mrp.production"].search([("name", "=", "WH/MO/00023")], limit=1)
if not production:
    production = env["mrp.production"].search([
        ("ddfc_source_invoice_id", "!=", False),
        ("workorder_ids", "!=", False),
    ], order="id desc", limit=1)
assert production, "No existe una OF de venta con factura y órdenes de trabajo"
assert production.ddfc_source_invoice_id, "La OF piloto no conserva la factura origen"

workorders = production.workorder_ids
machining = workorders.filtered(lambda wo: "maquin" in (wo.name or "").lower())[:1]
reception = workorders.filtered(lambda wo: "recep" in (wo.name or "").lower())[:1]
assert machining and reception, "Faltan las operaciones Maquinado o Recepción"

handoff = env["ddfc.machining.handoff"].create({
    "production_id": production.id,
    "machining_workorder_id": machining.id,
    "reception_workorder_id": reception.id,
    "line_ids": [Command.create({
        "product_id": production.product_id.id,
        "delivered_qty": 1.0,
        "product_uom_id": production.product_uom_id.id,
    })],
})
assert handoff.origin_type == "sale"
assert handoff.origin_document == production.ddfc_source_invoice_id.name
handoff.action_dispatch()
handoff.line_ids.write({"received_qty": 1.0})
handoff.action_receive()
assert handoff.state == "received"

pdf, file_type = env["ir.actions.report"]._render_qweb_pdf(
    "doorandoor_fabrica_control.action_report_ddfc_machining_handoff", handoff.ids
)
assert file_type == "pdf" and pdf.startswith(b"%PDF") and len(pdf) > 1000
print("HANDOFF OK", handoff.name, handoff.origin_document, len(pdf))
env.cr.rollback()
