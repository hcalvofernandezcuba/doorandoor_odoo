from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockReceiptScanWizard(models.TransientModel):
    _name = "ddsl.stock.receipt.scan.wizard"
    _description = "DoorAndDoor Receipt Scan Wizard"

    picking_id = fields.Many2one("stock.picking", required=True, readonly=True)
    scan_code = fields.Char(string="Codigo escaneado")
    line_ids = fields.One2many(
        "ddsl.stock.receipt.scan.wizard.line",
        "wizard_id",
        string="Conteo de recepcion",
    )

    @api.model
    def ddsl_create_for_picking(self, picking):
        wizard = self.create({
            "picking_id": picking.id,
        })
        wizard.line_ids.unlink()
        wizard.line_ids = [
            (
                0,
                0,
                {
                    "move_id": move.id,
                    "product_id": move.product_id.id,
                    "expected_qty": move.product_uom_qty,
                    "counted_qty": 0.0,
                },
            )
            for move in picking.move_ids.filtered(lambda move: move.product_id)
        ]
        return wizard

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        picking = self.env["stock.picking"].browse(self.env.context.get("default_picking_id"))
        if not picking:
            return values
        values["picking_id"] = picking.id
        values["line_ids"] = []
        return values

    def _ddsl_find_target_line(self, code):
        self.ensure_one()
        normalized = (code or "").strip().upper()
        if not normalized:
            return self.env["ddsl.stock.receipt.scan.wizard.line"]
        candidates = self.line_ids.filtered(
            lambda line: normalized in {
                (line.product_id.barcode or "").strip().upper(),
                (line.product_id.default_code or "").strip().upper(),
                (line.product_id.display_name or "").strip().upper(),
            }
        )
        if candidates:
            return candidates[:1]
        # Fallback robusto: resolver por los movimientos esperados del picking y
        # luego mapear a la linea del wizard correspondiente.
        move = self.picking_id.move_ids.filtered(
            lambda candidate: normalized in {
                (candidate.product_id.barcode or "").strip().upper(),
                (candidate.product_id.default_code or "").strip().upper(),
                (candidate.product_id.display_name or "").strip().upper(),
            }
        )[:1]
        if not move:
            return self.env["ddsl.stock.receipt.scan.wizard.line"]
        return self.line_ids.filtered(lambda line: line.move_id == move)[:1]

    def action_register_scan(self, scanned_code=None):
        self.ensure_one()
        code = (scanned_code or self.scan_code or "").strip()
        if not code:
            raise UserError(_("Escanee o escriba un codigo antes de contar."))
        line = self._ddsl_find_target_line(code)
        if not line:
            raise UserError(
                _("El codigo %s no coincide con ningun producto esperado en esta recepcion.") % code
            )
        line.counted_qty += 1.0
        self.scan_code = False
        return {
            "type": "ir.actions.act_window",
            "res_model": "ddsl.stock.receipt.scan.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply_count(self):
        self.ensure_one()
        StockMoveLine = self.env["stock.move.line"]
        for line in self.line_ids.filtered(lambda wizard_line: wizard_line.counted_qty > 0):
            move = line.move_id
            move_line = move.move_line_ids[:1]
            tracking = move.product_id.tracking
            existing_lot = move.move_line_ids.filtered(lambda candidate: candidate.lot_id or candidate.lot_name)[:1]
            if tracking == "serial":
                raise UserError(
                    _(
                        "El producto %s usa seguimiento por serie. Registre primero los seriales reales desde 'Register Lots / Serials'."
                    )
                    % move.product_id.display_name
                )
            if tracking == "lot" and not existing_lot:
                raise UserError(
                    _(
                        "Debe proporcionar un numero de lote para el producto:\n- %s\n\nRegistre primero el lote en 'Register Lots / Serials' y luego aplique el conteo con hanger."
                    )
                    % move.product_id.display_name
                )
            vals = {
                "picking_id": self.picking_id.id,
                "move_id": move.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "quantity": line.counted_qty,
            }
            if tracking == "lot" and existing_lot:
                vals["lot_id"] = existing_lot.lot_id.id or False
                vals["lot_name"] = existing_lot.lot_name or False
            if move_line:
                move_line.write(vals)
            else:
                StockMoveLine.create(vals)
        return {"type": "ir.actions.act_window_close"}


class StockReceiptScanWizardLine(models.TransientModel):
    _name = "ddsl.stock.receipt.scan.wizard.line"
    _description = "DoorAndDoor Receipt Scan Wizard Line"
    _order = "product_id, id"

    wizard_id = fields.Many2one("ddsl.stock.receipt.scan.wizard", required=True, ondelete="cascade")
    move_id = fields.Many2one("stock.move", readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    expected_qty = fields.Float(string="Esperado", readonly=True)
    counted_qty = fields.Float(string="Contado")
