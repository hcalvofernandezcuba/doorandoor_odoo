from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockSerialWizard(models.TransientModel):
    _name = "ddsl.stock.serial.wizard"
    _description = "DoorAndDoor Receipt Lot Serial Wizard"

    picking_id = fields.Many2one("stock.picking", required=True, readonly=True)
    line_ids = fields.One2many("ddsl.stock.serial.wizard.line", "wizard_id", string="Tracking Lines")

    def _ddsl_get_receipt_moves(self):
        self.ensure_one()
        return self.picking_id.move_ids.filtered(lambda move: move.product_id and move.product_id.tracking in ("serial", "lot"))

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        picking = self.env["stock.picking"].browse(self.env.context.get("default_picking_id"))
        if not picking:
            return values
        values["picking_id"] = picking.id
        lines = []
        tracked_moves = picking.move_ids.filtered(lambda move: move.product_id and move.product_id.tracking in ("serial", "lot"))
        for move in tracked_moves:
            qty = int(round(move.product_uom_qty or 0))
            existing = move.move_line_ids.filtered(lambda line: line.lot_name or line.lot_id)
            existing_names = [line.lot_name or line.lot_id.name for line in existing]
            if move.product_id.tracking == "lot":
                lines.append(
                    (
                        0,
                        0,
                        {
                            "move_id": move.id,
                            "product_id": move.product_id.id,
                            "sequence": 1,
                            "tracking_type": "lot",
                            "tracking_number": existing_names[0] if existing_names else "",
                            "qty": qty,
                        },
                    )
                )
                continue
            for index in range(qty):
                serial_value = existing_names[index] if index < len(existing_names) else ""
                lines.append(
                    (
                        0,
                        0,
                        {
                            "move_id": move.id,
                            "product_id": move.product_id.id,
                            "sequence": index + 1,
                            "tracking_type": "serial",
                            "tracking_number": serial_value,
                            "qty": 1.0,
                        },
                    )
                )
        values["line_ids"] = lines
        return values

    def action_apply_serials(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No tracked products were found in this receipt."))
        grouped = {}
        picking_moves = self._ddsl_get_receipt_moves()
        for line in self.line_ids:
            if not line.tracking_number:
                raise UserError(
                    _("Please complete all lot or serial numbers before saving. Product: %s") % line.product_id.display_name
                )
            move = line.move_id or picking_moves.filtered(lambda candidate: candidate.product_id == line.product_id)[:1]
            if not move:
                raise UserError(
                    _("Could not determine the stock move for product: %s") % line.product_id.display_name
                )
            grouped.setdefault(move, []).append(line)

        StockMoveLine = self.env["stock.move.line"]
        for move, wizard_lines in grouped.items():
            move.move_line_ids.unlink()
            for wizard_line in wizard_lines:
                StockMoveLine.create(
                    {
                        "move_id": move.id,
                        "picking_id": self.picking_id.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "quantity": wizard_line.qty if wizard_line.tracking_type == "lot" else 1.0,
                        "lot_name": wizard_line.tracking_number.strip(),
                    }
                )
        return {"type": "ir.actions.act_window_close"}

    def action_auto_generate_serials(self):
        self.ensure_one()
        serial_date = fields.Date.to_date(self.picking_id.scheduled_date or fields.Date.context_today(self))
        date_prefix = serial_date.strftime("%d%m%y")
        serial_lines = self.line_ids.filtered(lambda line: line.tracking_type == "serial")
        used_serials = set(filter(None, serial_lines.mapped("tracking_number")))
        counters_by_product = {}

        for line in serial_lines.sorted(key=lambda wizard_line: (wizard_line.product_id.id, wizard_line.sequence, wizard_line.id)):
            if line.tracking_number:
                continue
            product = line.product_id
            if product.id not in counters_by_product:
                counters_by_product[product.id] = self._ddsl_get_next_daily_counter(product, date_prefix)
            candidate = f"{date_prefix}{counters_by_product[product.id]:04d}"
            while candidate in used_serials:
                counters_by_product[product.id] += 1
                candidate = f"{date_prefix}{counters_by_product[product.id]:04d}"
            line.tracking_number = candidate
            used_serials.add(candidate)
            counters_by_product[product.id] += 1
        return {
            "type": "ir.actions.act_window",
            "res_model": "ddsl.stock.serial.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _ddsl_get_next_daily_counter(self, product, date_prefix):
        self.ensure_one()
        domain = [
            ("product_id", "=", product.id),
            ("picking_id.picking_type_id.code", "=", "incoming"),
            ("lot_name", "=like", f"{date_prefix}%"),
        ]
        serial_candidates = self.env["stock.move.line"].search_read(domain, ["lot_name"])
        highest_counter = 0
        for candidate in serial_candidates:
            lot_name = candidate.get("lot_name") or ""
            if not lot_name.startswith(date_prefix):
                continue
            suffix = lot_name[len(date_prefix):]
            if suffix.isdigit():
                highest_counter = max(highest_counter, int(suffix))
        return highest_counter + 1


class StockSerialWizardLine(models.TransientModel):
    _name = "ddsl.stock.serial.wizard.line"
    _description = "DoorAndDoor Receipt Lot Serial Wizard Line"
    _order = "product_id, sequence, id"

    wizard_id = fields.Many2one("ddsl.stock.serial.wizard", required=True, ondelete="cascade")
    move_id = fields.Many2one("stock.move", readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    sequence = fields.Integer(string="Unit", readonly=True)
    tracking_type = fields.Selection(
        [("serial", "Serial"), ("lot", "Lot")],
        string="Tracking Type",
        readonly=True,
    )
    tracking_number = fields.Char(string="Lot / Serial Number")
    qty = fields.Float(string="Qty", readonly=True)
