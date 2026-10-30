"""Create persistent Local-only demo records for the guided receipt flow.

Run only from an Odoo shell against the local DoorAndDoor database.  The
records are intentionally persistent and carry the DEMO-GR-20261023 marker.
"""

from odoo import fields


MARKER = "DEMO-GR-20261023"


def _position(warehouse, aisle, horizontal, level, side="L", slot=1):
    Position = env["doorandoor.warehouse.map.position"]
    domain = [
        ("warehouse_id", "=", warehouse.id),
        ("aisle", "=", aisle),
        ("horizontal_position", "=", horizontal),
        ("vertical_position", "=", level),
        ("side", "=", side),
        ("slot_number", "=", slot),
    ]
    return Position.search(domain, limit=1) or Position.create({
        "warehouse_id": warehouse.id,
        "aisle": aisle,
        "horizontal_position": horizontal,
        "vertical_position": level,
        "side": side,
        "slot_number": slot,
        "status": "available",
        "capacity": 33,
        "note": "%s - escenario visible de capacitación" % MARKER,
    })


def _picking(warehouse, product, quantity, origin, source=None, picking_type=None):
    source = source or env.ref("stock.stock_location_suppliers")
    picking_type = picking_type or warehouse.in_type_id
    picking = env["stock.picking"].create({
        "picking_type_id": picking_type.id,
        "location_id": source.id,
        "location_dest_id": warehouse.lot_stock_id.id,
        "origin": origin,
    })
    env["stock.move"].create({
        "name": product.display_name,
        "picking_id": picking.id,
        "product_id": product.id,
        "product_uom_qty": quantity,
        "product_uom": product.uom_id.id,
        "location_id": source.id,
        "location_dest_id": warehouse.lot_stock_id.id,
    })
    picking.action_confirm()
    return picking


def main():
    Picking = env["stock.picking"]
    existing = Picking.search([("origin", "=", "%s-A" % MARKER)], limit=1)
    if existing:
        print("Demo already exists; no duplicate records were created.")
        for receipt in env["inventory.serial.receipt"].search([
            ("picking_id.origin", "like", MARKER),
        ], order="id"):
            print(receipt.name, receipt.state, receipt.picking_id.name)
        return

    destination = env["stock.warehouse"].search([
        ("name", "=", "Central Warehouse"),
    ], limit=1)
    source = env["stock.warehouse"].search([
        ("name", "=", "Doorandoor - Tampa"),
    ], limit=1)
    if not destination or not source:
        raise RuntimeError("Central Warehouse and Doorandoor - Tampa are required")

    Product = env["product.product"]
    product = Product.search([("default_code", "=", "DEMO-GR-33")], limit=1)
    if not product:
        product = Product.create({
            "name": "DEMO - ITEM RECEPCION GUIADA CAPACIDAD 33",
            "default_code": "DEMO-GR-33",
            "is_storable": True,
        })
    campaign = env["inventory.serial.campaign"].search([
        ("name", "=", "%s - CAPACITACION" % MARKER),
        ("company_id", "=", destination.company_id.id),
    ], limit=1) or env["inventory.serial.campaign"].create({
        "name": "%s - CAPACITACION" % MARKER,
        "company_id": destination.company_id.id,
    })

    occupied = _position(destination, "90", "A", 1, "L")
    near = _position(destination, "90", "A", 1, "R")
    _position(destination, "99", "Z", 9, "R")
    Batch = env["inventory.serial.label.batch"]
    existing_batch = Batch.create({
        "name": occupied.name,
        "campaign_id": campaign.id,
        "warehouse_id": destination.id,
        "product_id": product.id,
        "quantity": 30,
        "ddwm_storage_type": "fixed",
        "ddwm_position_id": occupied.id,
    })
    existing_batch.action_generate_serials()
    existing_batch.serial_ids.write({
        "current_warehouse_id": destination.id,
        "current_batch_id": existing_batch.id,
        "current_location_id": destination.lot_stock_id.id,
        "inventory_loaded": True,
    })
    env["stock.quant"]._update_available_quantity(
        product, destination.lot_stock_id, 30,
    )

    picking_a = _picking(destination, product, 3, "%s-A" % MARKER)
    receipt_a = env["inventory.serial.receipt"].create({
        "picking_id": picking_a.id,
        "warehouse_id": destination.id,
        "product_id": product.id,
        "batch_id": existing_batch.id,
        "quantity": 3,
        "destination_purpose": "storage",
    })

    picking_b = _picking(destination, product, 32, "%s-B" % MARKER)
    receipt_b = env["inventory.serial.receipt"].create({
        "picking_id": picking_b.id,
        "warehouse_id": destination.id,
        "product_id": product.id,
        "quantity": 32,
        "destination_purpose": "storage",
    })
    receipt_b._compute_candidate_batches()
    receipt_b._compute_candidate_empty_positions()
    if receipt_b.recommended_empty_position_id != near:
        raise RuntimeError("The nearest empty position was not recommended")

    automatic_position = _position(destination, "91", "B", 1, "L")
    receipt_c = env["inventory.serial.receipt"].create({
        "warehouse_id": destination.id,
        "product_id": product.id,
        "quantity": 2,
        "operation_type": "supplier",
        "destination_purpose": "storage",
        "new_document_reference": "%s-C-AUTOMATICA" % MARKER,
        "create_new_batch": True,
        "new_storage_type": "fixed",
        "empty_position_id": automatic_position.id,
    })
    receipt_c.action_start()

    compatible_position = _position(destination, "92", "C", 1, "L")
    picking_d = _picking(destination, product, 2, "%s-D" % MARKER)
    receipt_d = env["inventory.serial.receipt"].create({
        "picking_id": picking_d.id,
        "warehouse_id": destination.id,
        "product_id": product.id,
        "quantity": 2,
        "destination_purpose": "storage",
        "create_new_batch": True,
        "new_storage_type": "fixed",
        "empty_position_id": compatible_position.id,
    })
    receipt_d.action_start()
    for code in ("DEMO-VENDOR-20261023-01", "DEMO-VENDOR-20261023-02"):
        receipt_d.scan_code = code
        receipt_d.action_scan()

    internal_position = _position(destination, "93", "D", 1, "L")
    source_batch = Batch.create({
        "name": "%s-SOURCE" % MARKER,
        "campaign_id": campaign.id,
        "warehouse_id": source.id,
        "product_id": product.id,
        "quantity": 2,
    })
    source_batch.action_generate_serials()
    source_batch.serial_ids.write({
        "current_warehouse_id": source.id,
        "current_batch_id": source_batch.id,
        "current_location_id": source.lot_stock_id.id,
        "inventory_loaded": True,
    })
    env["stock.quant"]._update_available_quantity(product, source.lot_stock_id, 2)
    picking_e = _picking(
        destination, product, 2, "%s-E" % MARKER,
        source=source.lot_stock_id, picking_type=source.int_type_id,
    )
    for serial in source_batch.serial_ids:
        env["ddmh.picking.serial.scan"].create({
            "picking_id": picking_e.id,
            "serial_id": serial.id,
        })
    picking_e.action_prepare_serial_receipt_lines()
    receipt_e = picking_e.serial_receipt_ids.filtered(
        lambda receipt: receipt.product_id == product
    )[:1]
    receipt_e.empty_position_id = internal_position
    receipt_e.action_start()
    for serial in source_batch.serial_ids:
        receipt_e.scan_code = serial.code
        receipt_e.action_scan()

    env.cr.commit()
    print("Persistent guided-receipt demo created at", fields.Datetime.now())
    for code, receipt in (
        ("A", receipt_a), ("B", receipt_b), ("C", receipt_c),
        ("D", receipt_d), ("E", receipt_e),
    ):
        print(
            code, receipt.name, receipt.state, receipt.picking_id.name,
            receipt.label_mode, receipt.batch_id.name or "-",
            receipt.recommended_empty_position_id.name or "-",
        )


main()
