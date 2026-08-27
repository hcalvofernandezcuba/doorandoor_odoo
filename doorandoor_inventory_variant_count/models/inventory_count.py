from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InventoryCountSession(models.Model):
    _name = "inventory.count.session"
    _description = "Inventory Count Session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False)
    date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, required=True, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    location_id = fields.Many2one(
        "stock.location", required=True, tracking=True,
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [False, company_id])]",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("counting", "Counting"),
         ("review", "Review"), ("done", "Validated"), ("cancel", "Cancelled")],
        default="draft", required=True, tracking=True,
    )
    line_ids = fields.One2many(
        "inventory.count.line", "session_id", copy=False, string="Variant Counts"
    )
    item_line_ids = fields.One2many(
        "inventory.count.item.line", "session_id", copy=False, string="Item Counts"
    )
    barcode_input = fields.Char(
        string="Scan Barcode", copy=False,
        help="Scan an item barcode and press Enter, or type it manually."
    )
    scan_qty = fields.Float(default=1.0, digits="Product Unit of Measure")
    note = fields.Text()
    line_count = fields.Integer(compute="_compute_totals")
    difference_count = fields.Integer(compute="_compute_totals")
    counted_line_ids = fields.Many2many(
        "inventory.count.line",
        string="Products Counted in This Session",
        compute="_compute_counted_lines",
    )
    last_scanned_product_id = fields.Many2one(
        "product.product", string="Last Counted Product", readonly=True, copy=False
    )
    last_scanned_barcode = fields.Char(
        string="Last Barcode", readonly=True, copy=False
    )
    last_scanned_qty = fields.Float(
        string="Accumulated Count", readonly=True, copy=False,
        digits="Product Unit of Measure",
    )
    last_scan_at = fields.Datetime(
        string="Last Scan At", readonly=True, copy=False
    )

    @api.depends("line_ids", "line_ids.difference_qty")
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.difference_count = len(rec.line_ids.filtered(
                lambda line: not fields.Float.is_zero(
                    line.difference_qty,
                    precision_rounding=line.uom_id.rounding,
                )
            ))

    @api.depends("line_ids.is_counted", "line_ids.counted_qty", "line_ids.write_date")
    def _compute_counted_lines(self):
        for rec in self:
            rec.counted_line_ids = rec.line_ids.filtered("is_counted").sorted(
                key=lambda line: (line.write_date or line.create_date, line.id),
                reverse=True,
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.count.session"
                ) or _("New")
        return super().create(vals_list)

    def action_start(self):
        for session in self:
            if session.state != "draft":
                continue
            session._load_snapshot()
            session.state = "counting"
        return True

    def _load_snapshot(self):
        self.ensure_one()
        if self.line_ids:
            raise UserError(_("This session already contains count lines."))
        Quant = self.env["stock.quant"]
        quants = Quant.search([
            ("location_id", "=", self.location_id.id),
            ("product_id.is_storable", "=", True),
        ])
        quantities = {}
        for quant in quants:
            key = (quant.product_id, quant.lot_id, quant.package_id, quant.owner_id)
            quantities[key] = quantities.get(key, 0.0) + quant.quantity
        line_commands = []
        for (product, lot, package, owner), qty in quantities.items():
            line_commands.append((0, 0, {
                "product_id": product.id,
                "lot_id": lot.id,
                "package_id": package.id,
                "owner_id": owner.id,
                "expected_qty": qty,
            }))
        if not line_commands:
            raise UserError(_("No stock was found in the selected location."))
        self.line_ids = line_commands
        item_commands = []
        for line in self.line_ids:
            for item in line.product_id.count_item_ids.filtered("active"):
                item_commands.append((0, 0, {
                    "variant_line_id": line.id,
                    "item_id": item.id,
                    "expected_qty": line.expected_qty * item.qty_per_product,
                }))
        self.item_line_ids = item_commands

    def action_scan(self, scanned_barcode=None):
        self.ensure_one()
        if self.state != "counting":
            raise UserError(_("Barcodes can only be recorded while counting."))
        # Mobile camera widgets send the decoded value directly. This avoids a
        # client-side race where the button RPC could run before barcode_input
        # had been persisted on the session. The stored field remains supported
        # for manual entry and conventional USB/Bluetooth scanners.
        barcode = (scanned_barcode or self.barcode_input or "").strip()
        if not barcode:
            raise ValidationError(_("Scan or enter a barcode first."))
        scan_qty = self.scan_qty or 1.0
        if scan_qty <= 0:
            raise ValidationError(_("The scan quantity must be greater than zero."))
        product = self.env["product.product"].search([
            ("barcode", "=", barcode), ("active", "=", True)
        ], limit=1)
        item = self.env["product.count.item"].search([
            ("barcode", "=", barcode), ("active", "=", True)
        ], limit=1)
        if product and item:
            raise UserError(_(
                "Barcode %s is assigned both to a product variant and to a count item. "
                "Correct the duplicate before continuing."
            ) % barcode)
        if product:
            lines = self.line_ids.filtered(lambda line: line.product_id == product)
            if not lines:
                # A physical count may reveal stock that Odoo expected to be
                # zero. Add that variant to this location's session instead of
                # rejecting a valid product label.
                lines = self.env["inventory.count.line"].create({
                    "session_id": self.id,
                    "product_id": product.id,
                    "expected_qty": 0.0,
                })
            if len(lines) > 1:
                raise UserError(_(
                    "The product variant occurs on multiple stock-detail lines. Enter "
                    "the quantity on the appropriate line to preserve lot/package/owner "
                    "traceability."
                ))
            line = lines[0]
            if line.item_line_ids.filtered("is_counted"):
                raise UserError(_(
                    "Some count items for %s were already recorded. Do not mix direct "
                    "variant scans with component counts on the same line."
                ) % product.display_name)
            line.counted_qty += scan_qty
            line.is_counted = True
            result_product = product
            result_qty = line.counted_qty
        elif item:
            lines = self.item_line_ids.filtered(lambda line: line.item_id == item)
            if not lines:
                raise UserError(_("This item is not part of the current count session."))
            if len(lines) > 1:
                raise UserError(_(
                    "The barcode occurs on multiple stock-detail lines. Enter the quantity "
                    "on the appropriate line to preserve lot/package/owner traceability."
                ))
            if lines.variant_line_id.is_counted:
                raise UserError(_(
                    "The product variant %s was already counted directly. Do not mix "
                    "component counts with direct variant scans on the same line."
                ) % lines.product_id.display_name)
            lines.counted_qty += scan_qty
            lines.is_counted = True
            result_product = lines.product_id
            result_qty = lines.counted_qty
        else:
            raise UserError(_(
                "Barcode %s is not assigned to an active product variant or count "
                "item. Print the variant label again so its inventory barcode is "
                "generated and stored on the product."
            ) % barcode)
        self.write({
            "barcode_input": False,
            "last_scanned_product_id": result_product.id,
            "last_scanned_barcode": barcode,
            "last_scanned_qty": result_qty,
            "last_scan_at": fields.Datetime.now(),
        })
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_review(self):
        for rec in self:
            if rec.state != "counting":
                continue
            started_lines = rec.line_ids.filtered(
                lambda line: line.is_counted or any(line.item_line_ids.mapped("is_counted"))
            )
            if not started_lines:
                raise UserError(_("Count at least one product variant before review."))
            for line in started_lines.filtered(lambda count: not count.is_counted):
                missing_items = line.item_line_ids.filtered(lambda item: not item.is_counted)
                if missing_items:
                    raise UserError(_(
                        "Complete all count items for %s before review. Missing: %s."
                    ) % (
                        line.product_id.display_name,
                        ", ".join(missing_items.mapped("item_id.display_name")),
                    ))
            rec.state = "review"
        return True

    def action_back_to_counting(self):
        self.filtered(lambda rec: rec.state == "review").write({"state": "counting"})
        return True

    def action_validate(self):
        self.ensure_one()
        if self.state != "review":
            raise UserError(_("The session must be in review before validation."))
        self._derive_variant_counts()
        counted_lines = self.line_ids.filtered("is_counted")
        if not counted_lines:
            raise UserError(_("There are no counted product variants to validate."))
        Quant = self.env["stock.quant"]
        for line in counted_lines:
            quant = Quant.search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", self.location_id.id),
                ("lot_id", "=", line.lot_id.id),
                ("package_id", "=", line.package_id.id),
                ("owner_id", "=", line.owner_id.id),
            ], limit=1)
            if not quant:
                quant = Quant.create({
                    "product_id": line.product_id.id,
                    "location_id": self.location_id.id,
                    "lot_id": line.lot_id.id,
                    "package_id": line.package_id.id,
                    "owner_id": line.owner_id.id,
                    "inventory_quantity": line.counted_qty,
                })
            else:
                quant.inventory_quantity = line.counted_qty
            quant.with_context(inventory_name=self.name).action_apply_inventory()
        self.state = "done"
        self.message_post(body=_(
            "Inventory adjustment applied to %s counted variant(s) from session %s. "
            "Uncounted variants were left unchanged."
        ) % (len(counted_lines), self.name))
        return True

    def _derive_variant_counts(self):
        for line in self.line_ids:
            if line.is_counted:
                continue
            item_lines = line.item_line_ids
            if not item_lines:
                continue
            counted_items = item_lines.filtered("is_counted")
            if not counted_items:
                # This variant was not part of the current partial count. It
                # remains untouched in stock.
                continue
            missing_items = item_lines - counted_items
            if missing_items:
                raise UserError(_(
                    "Complete all count items for %s before validation. Missing: %s."
                ) % (
                    line.product_id.display_name,
                    ", ".join(missing_items.mapped("item_id.display_name")),
                ))
            derived = [
                item_line.counted_qty / item_line.item_id.qty_per_product
                for item_line in item_lines
            ]
            rounded = [line.uom_id._compute_quantity(qty, line.uom_id) for qty in derived]
            if max(rounded) - min(rounded) > line.uom_id.rounding:
                raise UserError(_(
                    "Item counts for %s are inconsistent. Their quantities per product "
                    "produce different variant totals: %s"
                ) % (line.product_id.display_name, ", ".join(str(qty) for qty in rounded)))
            line.counted_qty = min(derived)
            line.is_counted = True

    def action_cancel(self):
        self.filtered(lambda rec: rec.state != "done").write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for rec in self.filtered(lambda r: r.state == "cancel"):
            rec.write({"state": "draft", "line_ids": [(5, 0, 0)],
                       "item_line_ids": [(5, 0, 0)]})
        return True


class InventoryCountLine(models.Model):
    _name = "inventory.count.line"
    _description = "Inventory Count Variant Line"
    _order = "is_counted desc, write_date desc, product_id, id"

    session_id = fields.Many2one(
        "inventory.count.session", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="session_id.company_id", store=True)
    state = fields.Selection(related="session_id.state", store=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    barcode = fields.Char(related="product_id.barcode", string="Barcode")
    uom_id = fields.Many2one(related="product_id.uom_id")
    lot_id = fields.Many2one("stock.lot")
    package_id = fields.Many2one("stock.quant.package")
    owner_id = fields.Many2one("res.partner")
    expected_qty = fields.Float(readonly=True, digits="Product Unit of Measure")
    counted_qty = fields.Float(digits="Product Unit of Measure")
    is_counted = fields.Boolean(string="Counted")
    difference_qty = fields.Float(
        compute="_compute_difference", store=True, digits="Product Unit of Measure"
    )
    item_line_ids = fields.One2many(
        "inventory.count.item.line", "variant_line_id", string="Items"
    )

    @api.depends("expected_qty", "counted_qty", "is_counted")
    def _compute_difference(self):
        for line in self:
            line.difference_qty = (
                line.counted_qty - line.expected_qty if line.is_counted else 0.0
            )


class InventoryCountItemLine(models.Model):
    _name = "inventory.count.item.line"
    _description = "Inventory Count Item Line"
    _order = "product_id, item_id, id"

    session_id = fields.Many2one(
        "inventory.count.session", required=True, ondelete="cascade", index=True
    )
    variant_line_id = fields.Many2one(
        "inventory.count.line", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="session_id.company_id", store=True)
    state = fields.Selection(related="session_id.state", store=True)
    product_id = fields.Many2one(related="variant_line_id.product_id", store=True)
    item_id = fields.Many2one("product.count.item", required=True, index=True)
    item_code = fields.Char(related="item_id.code", store=True)
    barcode = fields.Char(related="item_id.barcode", store=True)
    uom_id = fields.Many2one(related="item_id.uom_id")
    expected_qty = fields.Float(readonly=True, digits="Product Unit of Measure")
    counted_qty = fields.Float(digits="Product Unit of Measure")
    is_counted = fields.Boolean(string="Counted")
    difference_qty = fields.Float(
        compute="_compute_difference", store=True, digits="Product Unit of Measure"
    )

    @api.depends("expected_qty", "counted_qty", "is_counted")
    def _compute_difference(self):
        for line in self:
            line.difference_qty = (
                line.counted_qty - line.expected_qty if line.is_counted else 0.0
            )

    @api.onchange("counted_qty")
    def _onchange_counted_qty(self):
        self.is_counted = True
