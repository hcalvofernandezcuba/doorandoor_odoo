from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddsn_bonus_percent = fields.Float(string="Applied Bonus %", readonly=True, copy=False)
    ddsn_bonus_source = fields.Selection(
        [("fixed_price", "Fixed Price"), ("product", "Product"),
         ("partner", "Customer"), ("constructor", "Constructor"),
         ("group", "Group"), ("manual", "Manual")],
        string="Bonus Source", readonly=True, copy=False,
    )
    ddsn_bonus_rule_reference = fields.Char(string="Bonus Rule", readonly=True, copy=False)
    ddsn_bonus_authorized_by_id = fields.Many2one(
        "res.users", string="Bonus Authorized By", readonly=True, copy=False
    )

    ddsn_supply_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén proveedor",
        domain="[('company_id', '=', company_id)]",
        help="Almacén donde se prereserva el producto y desde el cual se solicitará el traslado.",
    )
    ddsn_supply_transfer_id = fields.Many2one(
        "stock.picking",
        string="Traslado de abastecimiento",
        copy=False,
        readonly=True,
    )

    ddsn_can_edit_commercial_price = fields.Boolean(
        string="Puede editar precio comercial",
        compute="_compute_ddsn_can_edit_commercial_price",
    )

    def _compute_ddsn_can_edit_commercial_price(self):
        allowed = self.env.user.has_group("base.group_system")
        for line in self:
            line.ddsn_can_edit_commercial_price = allowed

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

    def _ddsn_get_stock_control_product(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return product, 0.0, False

        template = product.product_tmpl_id
        product_kind = getattr(template, "ddsp_product_kind", False)
        if product_kind == "special":
            return self.env["product.product"], 0.0, False
        if product_kind != "transformed":
            return product, self.quantity, False

        bom = self.env["mrp.bom"].search(
            [
                "|",
                ("product_id", "=", product.id),
                "&",
                ("product_id", "=", False),
                ("product_tmpl_id", "=", template.id),
            ],
            limit=1,
        )
        base_template = getattr(template, "ddsp_base_product_tmpl_id", False)
        base_line = bom.bom_line_ids.filtered(
            lambda item: not base_template or item.product_id.product_tmpl_id == base_template
        )[:1]
        if not bom or not base_line:
            return product, self.quantity, False

        required_in_bom_uom = (self.quantity / (bom.product_qty or 1.0)) * base_line.product_qty
        required_qty = base_line.product_uom_id._compute_quantity(
            required_in_bom_uom,
            base_line.product_id.uom_id,
        )
        return base_line.product_id, required_qty, product

    @api.onchange("product_id", "quantity")
    def _onchange_ddsn_warn_insufficient_stock(self):
        for line in self:
            move = line.move_id
            warehouse = move.sale_order_id.warehouse_id
            control_product, required_qty, transformed_product = line._ddsn_get_stock_control_product()
            if (
                not warehouse
                or not warehouse.lot_stock_id
                or not control_product
                or not control_product.is_storable
                or required_qty <= 0
            ):
                continue

            available_qty = control_product.with_company(move.company_id).with_context(
                location=warehouse.lot_stock_id.id
            ).qty_available
            if not transformed_product:
                available_qty -= line._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                available_qty -= line._ddsn_get_quote_reserved_qty_for_display(warehouse=warehouse)
            if required_qty <= available_qty:
                continue

            transformed_detail = ""
            if transformed_product:
                transformed_detail = _("\nProducto transformado: %(product)s") % {
                    "product": transformed_product.display_name,
                }
            return {
                "warning": {
                    "title": _("Alerta de inventario"),
                    "message": _(
                        "La cantidad solicitada supera la existencia disponible."
                        "%(transformed_detail)s\nProducto controlado: %(product)s"
                        "\nAlmacén: %(warehouse)s\nCantidad requerida: %(required).2f"
                        "\nCantidad disponible: %(available).2f\n\nPuede continuar con la venta."
                    )
                    % {
                        "transformed_detail": transformed_detail,
                        "product": control_product.display_name,
                        "warehouse": warehouse.display_name,
                        "required": required_qty,
                        "available": available_qty,
                    },
                    "type": "notification",
                }
            }

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
            for reserved_line in reserved_move.invoice_line_ids.filtered(
                lambda item: item.product_id and item.display_type in (False, "product")
            ):
                controlled_product, required_qty, _transformed = (
                    reserved_line._ddsn_get_stock_control_product()
                )
                reservation_warehouse = (
                    reserved_line.ddsn_supply_warehouse_id
                    or reserved_move.sudo().sale_order_id.warehouse_id
                )
                if controlled_product != product:
                    continue
                if warehouse and reservation_warehouse != warehouse:
                    continue
                reserved_qty += required_qty
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

    def ddsn_get_live_warehouse_stock_tooltip(self):
        """Return current stock by warehouse without modifying reservations."""
        self.ensure_one()
        return self._ddsn_get_warehouse_stock_text() or _(
            "No hay información de existencias disponible."
        )

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

    def write(self, vals):
        if (
            {"price_unit", "discount"}.intersection(vals)
            and not self.env.context.get("ddsn_automatic_pricing")
            and not self.env.user.has_group("base.group_system")
        ):
            raise ValidationError(
                _("Solo un administrador de Ajustes puede modificar precios o descuentos.")
            )
        # Restringir solamente la edicion comercial de la linea. Odoo necesita
        # escribir campos tecnicos y calculados despues de contabilizar (por
        # ejemplo durante conciliaciones, impuestos y enlaces de fulfillment).
        protected_product_fields = {
            "product_id",
            "name",
            "quantity",
            "product_uom_id",
            "price_unit",
            "discount",
            "tax_ids",
            "account_id",
            "analytic_distribution",
            "display_type",
        }
        if protected_product_fields.intersection(vals):
            protected_lines = self.filtered(
                lambda line: (
                    line.move_id.state in ("posted", "cancel")
                    or (
                        line.move_id.ddsn_is_preinvoice
                        and line.move_id.ddsn_preinvoice_state == "confirmed"
                    )
                )
                and line.move_id.is_invoice(include_receipts=True)
            )
            if protected_lines:
                raise ValidationError(
                    _("No se pueden modificar líneas de producto en una factura confirmada. "
                      "El documento está cerrado para edición.")
                )
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.context.get("ddsn_automatic_pricing")
            and not self.env.user.has_group("base.group_system")
        ):
            vals_list = [
                {key: value for key, value in vals.items() if key not in {"price_unit", "discount"}}
                for vals in vals_list
            ]
        move_ids = {vals.get("move_id") for vals in vals_list if vals.get("move_id")}
        locked_moves = self.env["account.move"].browse(move_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True)
            and (
                move.state in ("posted", "cancel")
                or (
                    move.ddsn_is_preinvoice
                    and move.ddsn_preinvoice_state == "confirmed"
                )
            )
        )
        if locked_moves:
            raise ValidationError(
                _("No se pueden agregar líneas a una factura o prefactura confirmada.")
            )
        return super().create(vals_list)

    def unlink(self):
        if self.filtered(
            lambda line: line.move_id.is_invoice(include_receipts=True)
            and (
                line.move_id.state in ("posted", "cancel")
                or (
                    line.move_id.ddsn_is_preinvoice
                    and line.move_id.ddsn_preinvoice_state == "confirmed"
                )
            )
        ):
            raise ValidationError(
                _("No se pueden eliminar líneas de una factura o prefactura confirmada.")
            )
        return super().unlink()
