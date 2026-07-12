from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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

    ddsn_warehouse_stock_html = fields.Html(
        string="Warehouses",
        compute="_compute_ddsn_stock_visibility",
        sanitize=False,
        readonly=True,
    )

    ddsn_warehouse_stock_display = fields.Char(
        string="Warehouse Stock",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    ddsn_warehouse_stock_text = fields.Text(
        string="Warehouse Stock Detail",
        compute="_compute_ddsn_stock_visibility",
        readonly=True,
    )

    ddsn_bonus_percent = fields.Float(
        string="Applied Bonus %",
        readonly=True,
        copy=False,
    )

    ddsn_bonus_source = fields.Selection(
        [
            ("partner", "Customer"),
            ("group", "Group"),
            ("manual", "Manual"),
        ],
        string="Bonus Source",
        readonly=True,
        copy=False,
    )

    @api.depends("product_id", "product_uom_qty", "order_id.warehouse_id", "order_id.company_id")
    def _compute_ddsn_stock_visibility(self):
        for line in self:
            line.ddsn_available_qty = 0.0
            line.ddsn_stock_uom_name = False
            line.ddsn_stock_display = False
            line.ddsn_warehouse_stock_html = False
            line.ddsn_warehouse_stock_display = False
            line.ddsn_warehouse_stock_text = False

            product = line.product_id
            if not product or product.type not in ("product", "consu"):
                continue

            warehouse = line.order_id.warehouse_id
            product_ctx = product.with_company(line.order_id.company_id)
            if warehouse and warehouse.lot_stock_id:
                product_ctx = product_ctx.with_context(location=warehouse.lot_stock_id.id)

            available_qty = (
                product_ctx.qty_available
                - line._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - line._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
            )
            uom_name = product.uom_id.display_name or product.uom_id.name

            line.ddsn_available_qty = available_qty
            line.ddsn_stock_uom_name = uom_name
            line.ddsn_stock_display = f"{available_qty:.2f} {uom_name}"
            line.ddsn_warehouse_stock_html = line._ddsn_get_warehouse_stock_html()
            line.ddsn_warehouse_stock_display = line._ddsn_get_warehouse_stock_display()
            line.ddsn_warehouse_stock_text = line._ddsn_get_warehouse_stock_text()

    def _ddsn_get_warehouse_stock_html(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self.env["stock.warehouse"].search(
            [("company_id", "=", self.order_id.company_id.id)],
            order="sequence, id",
        )
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
                product.with_company(self.order_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
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

    def _ddsn_get_warehouse_stock_display(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self.env["stock.warehouse"].search(
            [("company_id", "=", self.order_id.company_id.id)],
            order="sequence, id",
        )
        if not warehouses:
            return False

        chunks = []
        for warehouse in warehouses:
            location = warehouse.lot_stock_id
            if not location:
                continue

            qty = (
                product.with_company(self.order_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
            )
            warehouse_label = warehouse.code or warehouse.name
            chunks.append(f"{warehouse_label}: {qty:.2f}")

        return " | ".join(chunks) or False

    def _ddsn_get_warehouse_stock_text(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self.env["stock.warehouse"].search(
            [("company_id", "=", self.order_id.company_id.id)],
            order="sequence, id",
        )
        if not warehouses:
            return False

        lines = []
        for warehouse in warehouses:
            location = warehouse.lot_stock_id
            if not location:
                continue

            qty = (
                product.with_company(self.order_id.company_id).with_context(location=location.id).qty_available
                - self._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                - self._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
            )
            warehouse_label = warehouse.code or warehouse.name
            lines.append(f"{warehouse_label}: {qty:.2f}")

        return "\n".join(lines) or False

    def _ddsn_get_committed_qty_for_display(self, warehouse=False):
        self.ensure_one()
        product = self.product_id
        order = self.order_id
        if not product or not order:
            return 0.0

        committed_moves = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", order.company_id.id),
            ]
        )
        committed_qty = 0.0
        for committed_move in committed_moves:
            committed_qty += committed_move._ddsn_get_committed_qty_for_product(product, warehouse=warehouse)
        return committed_qty

    def _ddsn_get_reserved_qty_for_display(self, warehouse=False):
        self.ensure_one()
        product = self.product_id
        order = self.order_id
        if not product or not order:
            return 0.0

        reserved_moves = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("company_id", "=", order.company_id.id),
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

    @api.onchange("product_id")
    def _onchange_ddsn_apply_partner_bonus(self):
        for line in self:
            if not line.product_id or line.display_type:
                continue
            if line.discount:
                line.ddsn_bonus_percent = line.discount
                line.ddsn_bonus_source = "manual"
                continue

            partner = line.order_id.partner_id.commercial_partner_id or line.order_id.partner_id
            partner_bonus = partner.ddsn_bonus_percent
            group_bonus = partner._ddsn_get_group_bonus_percent()

            if partner_bonus:
                line.discount = partner_bonus
                line.ddsn_bonus_percent = partner_bonus
                line.ddsn_bonus_source = "partner"
            elif group_bonus:
                line.discount = group_bonus
                line.ddsn_bonus_percent = group_bonus
                line.ddsn_bonus_source = "group"

    @api.onchange("discount")
    def _onchange_ddsn_sync_bonus_percent(self):
        for line in self:
            line.ddsn_bonus_percent = line.discount or 0.0
            if not line.discount:
                line.ddsn_bonus_source = False
            elif line.ddsn_bonus_source not in ("partner", "group"):
                line.ddsn_bonus_source = "manual"
