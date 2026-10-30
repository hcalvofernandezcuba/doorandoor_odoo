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
    def _ddsl_can_count_picking(self, picking):
        """Extension point for explicitly controlled non-receipt operations."""
        return picking.picking_type_code == "incoming"

    @api.model
    def _ddsl_allow_unexpected_product(self, picking):
        """Only receipts may add a product not planned on the operation."""
        return picking.picking_type_code == "incoming"

    @api.model
    def ddsl_create_for_picking(self, picking):
        if picking.state in ("done", "cancel"):
            raise UserError(_("No puede contar productos en una recepcion terminada o cancelada."))
        if not self._ddsl_can_count_picking(picking):
            raise UserError(_("El conteo con hanger solo esta disponible para recepciones."))
        expected_by_product = {}
        for move in picking.move_ids.filtered(
            lambda candidate: candidate.product_id and not candidate.ddsl_receipt_scan_generated
        ):
            expected_by_product[move.product_id] = (
                expected_by_product.get(move.product_id, 0.0) + move.product_uom_qty
            )
        existing_counts = {line.product_id: line for line in picking.ddsl_receipt_count_ids}
        for product, expected_qty in expected_by_product.items():
            count_line = existing_counts.get(product)
            if count_line:
                count_line.expected_qty = expected_qty
            else:
                self.env["ddsl.stock.receipt.count"].create({
                    "picking_id": picking.id,
                    "product_id": product.id,
                    "expected_qty": expected_qty,
                })
        wizard = self.create({
            "picking_id": picking.id,
        })
        wizard.line_ids = [
            (
                0,
                0,
                {
                    "count_id": count_line.id,
                    "move_id": picking.move_ids.filtered(
                        lambda move: move.product_id == count_line.product_id
                    )[:1].id,
                    "product_id": count_line.product_id.id,
                    "expected_qty": count_line.expected_qty,
                    "counted_qty": count_line.counted_qty,
                    "is_counted": count_line.is_counted,
                    "difference_qty": count_line.difference_qty,
                },
            )
            for count_line in picking.ddsl_receipt_count_ids
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

    def _ddsl_find_product(self, code):
        self.ensure_one()
        normalized = (code or "").strip()
        if not normalized:
            return self.env["product.product"]
        products = self.env["product.product"].search([
            ("active", "=", True),
            "|", "|",
            ("barcode", "=", normalized),
            ("default_code", "=", normalized),
            ("product_tmpl_id.ddsl_product_label_code", "=", normalized),
        ])
        if len(products) > 1:
            raise UserError(
                _("El codigo %s esta asignado a mas de un producto. Corrija los codigos duplicados antes de continuar.")
                % normalized
            )
        return products

    def _ddsl_get_or_create_wizard_line(self, product):
        self.ensure_one()
        line = self.line_ids.filtered(lambda candidate: candidate.product_id == product)[:1]
        if line:
            return line
        expected_move = self.picking_id.move_ids.filtered(
            lambda move: move.product_id == product
        )[:1]
        if not expected_move and not self._ddsl_allow_unexpected_product(self.picking_id):
            raise UserError(
                _("El producto %s no pertenece a esta operación. No se agregó ni se modificó inventario.")
                % product.display_name
            )
        expected_qty = sum(
            self.picking_id.move_ids.filtered(
                lambda move: move.product_id == product
            ).mapped("product_uom_qty")
        )
        count_line = self.env["ddsl.stock.receipt.count"].search([
            ("picking_id", "=", self.picking_id.id),
            ("product_id", "=", product.id),
        ], limit=1)
        if not count_line:
            count_line = self.env["ddsl.stock.receipt.count"].create({
                "picking_id": self.picking_id.id,
                "product_id": product.id,
                "expected_qty": expected_qty,
            })
        return self.env["ddsl.stock.receipt.scan.wizard.line"].create({
            "wizard_id": self.id,
            "count_id": count_line.id,
            "move_id": expected_move.id,
            "product_id": product.id,
            "expected_qty": count_line.expected_qty,
            "counted_qty": count_line.counted_qty,
            "is_counted": count_line.is_counted,
            "difference_qty": count_line.difference_qty,
        })

    def action_register_scan(self, scanned_code=None):
        self.ensure_one()
        code = (scanned_code or self.scan_code or "").strip()
        if not code:
            raise UserError(_("Escanee o escriba un codigo antes de contar."))
        if self.picking_id.state in ("done", "cancel"):
            raise UserError(_("No puede contar productos en una recepcion terminada o cancelada."))
        product = self._ddsl_find_product(code)
        if not product:
            raise UserError(
                _("El codigo %s no corresponde a ningun producto registrado.") % code
            )
        line = self._ddsl_get_or_create_wizard_line(product)
        line.counted_qty += 1.0
        line.is_counted = True
        line.count_id.write({
            "counted_qty": line.counted_qty,
            "is_counted": True,
            "last_scan_date": fields.Datetime.now(),
            "last_scan_user_id": self.env.user.id,
        })
        self.scan_code = False
        return {
            "continuous_scan": True,
            "product_id": product.id,
            "product_name": product.display_name,
            "barcode": code,
            "expected_qty": line.expected_qty,
            "counted_qty": line.counted_qty,
            "difference_qty": line.count_id.difference_qty,
        }

    def action_apply_count(self):
        self.ensure_one()
        if self.picking_id.state in ("done", "cancel"):
            raise UserError(_("No puede aplicar conteos en una recepcion terminada o cancelada."))
        StockMoveLine = self.env["stock.move.line"]
        StockMove = self.env["stock.move"]
        for count_line in self.picking_id.ddsl_receipt_count_ids.filtered(
            lambda candidate: candidate.counted_qty > 0
        ):
            product = count_line.product_id
            move = self.picking_id.move_ids.filtered(
                lambda candidate: candidate.product_id == product
            )[:1]
            if not move:
                move = StockMove.create({
                    "name": product.display_name,
                    "picking_id": self.picking_id.id,
                    "product_id": product.id,
                    "product_uom": product.uom_id.id,
                    "product_uom_qty": count_line.counted_qty,
                    "location_id": self.picking_id.location_id.id,
                    "location_dest_id": self.picking_id.location_dest_id.id,
                    "ddsl_receipt_scan_generated": True,
                })
            move_line = move.move_line_ids[:1]
            tracking = product.tracking
            existing_lot = move.move_line_ids.filtered(lambda candidate: candidate.lot_id or candidate.lot_name)[:1]
            if tracking == "serial":
                raise UserError(
                    _(
                        "El producto %s usa seguimiento por serie. Registre primero los seriales reales desde 'Register Lots / Serials'."
                    )
                    % product.display_name
                )
            if tracking == "lot" and not existing_lot:
                raise UserError(
                    _(
                        "Debe proporcionar un numero de lote para el producto:\n- %s\n\nRegistre primero el lote en 'Register Lots / Serials' y luego aplique el conteo con hanger."
                    )
                    % product.display_name
                )
            vals = {
                "picking_id": self.picking_id.id,
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
                "quantity": count_line.counted_qty,
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
    count_id = fields.Many2one("ddsl.stock.receipt.count", readonly=True)
    move_id = fields.Many2one("stock.move", readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    expected_qty = fields.Float(string="Esperado", readonly=True)
    counted_qty = fields.Float(string="Contado")
    is_counted = fields.Boolean(string="Contado fisicamente")
    difference_qty = fields.Float(string="Diferencia", readonly=True)

    def write(self, vals):
        result = super().write(vals)
        if "counted_qty" in vals:
            for line in self.filtered("count_id"):
                line.count_id.write({
                    "counted_qty": line.counted_qty,
                    "is_counted": True,
                    "last_scan_date": fields.Datetime.now(),
                    "last_scan_user_id": self.env.user.id,
                })
                line.is_counted = True
                line.difference_qty = line.count_id.difference_qty
        return result
