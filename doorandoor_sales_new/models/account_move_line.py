from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddsn_available_qty = fields.Float(
        string="Available Stock",
        compute="_compute_ddsn_stock_visibility",
        digits="Product Unit of Measure",
        readonly=True,
    )

    ddsn_stock_uom_name = fields.Char(
        string="Stock UoM",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    ddsn_stock_display = fields.Char(
        string="Stock Available",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    ddsn_warehouse_stock_display = fields.Char(
        string="Warehouse Stock",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    ddsn_warehouse_stock_html = fields.Html(
        string="Warehouses",
        compute="_compute_ddsn_stock_visibility",
        sanitize=False,
        readonly=True,
    )

    ddsn_warehouse_stock_text = fields.Text(
        string="Warehouse Stock Detail",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    generated_sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Generated Sale Order Line",
        copy=False,
        readonly=True,
    )

    fulfillment_line_id = fields.Many2one(
        "doorandoor.fulfillment.line",
        string="Fulfillment Line",
        copy=False,
        readonly=True,
    )

    @api.depends("product_id", "quantity", "move_id.company_id", "move_id.sale_order_id.warehouse_id")
    def _compute_ddsn_stock_visibility(self):
        for line in self:
            line.ddsn_available_qty = 0.0
            line.ddsn_stock_uom_name = False
            line.ddsn_stock_display = False
            line.ddsn_warehouse_stock_display = False
            line.ddsn_warehouse_stock_html = False
            line.ddsn_warehouse_stock_text = False

            product = line.product_id
            move = line.move_id
            if not product or product.type not in ("product", "consu") or not move:
                continue

            company = move.company_id
            warehouse = move.sale_order_id.warehouse_id
            product_ctx = product.with_company(company)
            if warehouse and warehouse.lot_stock_id:
                product_ctx = product_ctx.with_context(location=warehouse.lot_stock_id.id)

            available_qty = (
                product_ctx.qty_available
                - line._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - line._ddsn_get_quote_reserved_qty_for_display(warehouse=warehouse)
            )
            uom_name = product.uom_id.display_name or product.uom_id.name

            line.ddsn_available_qty = available_qty
            line.ddsn_stock_uom_name = uom_name
            line.ddsn_stock_display = f"{available_qty:.2f} {uom_name}"
            line.ddsn_warehouse_stock_display = line._ddsn_get_warehouse_stock_display()
            line.ddsn_warehouse_stock_html = line._ddsn_get_warehouse_stock_html()
            line.ddsn_warehouse_stock_text = line._ddsn_get_warehouse_stock_text()

    def _ddsn_get_company_warehouses(self):
        self.ensure_one()
        return self.env["stock.warehouse"].search(
            [("company_id", "=", self.move_id.company_id.id)],
            order="sequence, id",
        )

    def _ddsn_get_committed_qty_for_display(self, warehouse=False):
        self.ensure_one()
        product = self.product_id
        move = self.move_id
        if not product or not move:
            return 0.0

        committed_qty = 0.0
        committed_moves = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", move.company_id.id),
                ("id", "!=", move.id or 0),
            ]
        )
        for committed_move in committed_moves:
            committed_qty += committed_move._ddsn_get_committed_qty_for_product(product, warehouse=warehouse)
        return committed_qty

    def _ddsn_get_quote_reserved_qty_for_display(self, warehouse=False):
        self.ensure_one()
        product = self.product_id
        move = self.move_id
        if not product or not move:
            return 0.0

        reserved_moves = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("company_id", "=", move.company_id.id),
                ("id", "!=", move.id or 0),
            ]
        )
        reserved_qty = 0.0
        for reserved_move in reserved_moves:
            if not reserved_move._ddsn_has_active_reservation():
                continue
            reservation_warehouse = reserved_move.sale_order_id.warehouse_id
            if warehouse and reservation_warehouse and reservation_warehouse != warehouse:
                continue
            reserved_qty += sum(
                reserved_move.invoice_line_ids.filtered(
                    lambda line: line.product_id == product and line.display_type in (False, "product")
                ).mapped("quantity")
            )
        return reserved_qty

    def _ddsn_get_warehouse_stock_display(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self._ddsn_get_company_warehouses()
        if not warehouses:
            return False

        chunks = []
        for warehouse in warehouses:
            location = warehouse.lot_stock_id
            if not location:
                continue

            qty = (
                product.with_company(self.move_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_quote_reserved_qty_for_display(warehouse=warehouse)
            )
            warehouse_label = warehouse.code or warehouse.name
            chunks.append(f"{warehouse_label}: {qty:.2f}")

        return " | ".join(chunks) or False

    def _ddsn_get_warehouse_stock_html(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self._ddsn_get_company_warehouses()
        if not warehouses:
            return False

        has_bom = bool(
            self.env["mrp.bom"].search(
                [
                    "|",
                    ("product_id", "=", product.id),
                    "&",
                    ("product_id", "=", False),
                    ("product_tmpl_id", "=", product.product_tmpl_id.id),
                ],
                limit=1,
            )
        )

        badges = []
        for warehouse in warehouses:
            location = warehouse.lot_stock_id
            if not location:
                continue

            qty = (
                product.with_company(self.move_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_quote_reserved_qty_for_display(warehouse=warehouse)
            )
            if qty > 0:
                background = "#d1fae5"
                color = "#065f46"
            elif has_bom:
                background = "#fed7aa"
                color = "#9a3412"
            else:
                background = "#fecaca"
                color = "#991b1b"

            warehouse_label = warehouse.code or warehouse.name
            badges.append(
                (
                    f"<span style='display:inline-block;margin:1px 4px 1px 0;padding:2px 8px;"
                    f"border-radius:999px;background:{background};color:{color};font-weight:600;"
                    f"white-space:nowrap;'>{warehouse_label}: {qty:.2f}</span>"
                )
            )

        return "".join(badges) or False

    def _ddsn_get_warehouse_stock_text(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self._ddsn_get_company_warehouses()
        if not warehouses:
            return False

        lines = []
        for warehouse in warehouses:
            location = warehouse.lot_stock_id
            if not location:
                continue

            qty = (
                product.with_company(self.move_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_quote_reserved_qty_for_display(warehouse=warehouse)
            )
            warehouse_label = warehouse.code or warehouse.name
            lines.append(f"{warehouse_label}: {qty:.2f}")

        return "\n".join(lines) or False
