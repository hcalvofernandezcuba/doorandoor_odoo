from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ddsn_supply_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén proveedor",
        domain="[('company_id', '=', company_id)]",
        help=(
            "Almacén que aportará físicamente este producto. Si queda vacío, "
            "se utiliza el almacén comercial de la cotización. Para dividir una "
            "cantidad entre almacenes, utilice una línea por cada origen."
        ),
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
            ("fixed_price", "Fixed Price"),
            ("product", "Product"),
            ("partner", "Customer"),
            ("constructor", "Constructor"),
            ("group", "Group"),
            ("manual", "Manual"),
        ],
        string="Bonus Source",
        readonly=True,
        copy=False,
    )

    ddsn_bonus_rule_reference = fields.Char(
        string="Bonus Rule", readonly=True, copy=False
    )
    ddsn_bonus_authorized_by_id = fields.Many2one(
        "res.users", string="Bonus Authorized By", readonly=True, copy=False
    )

    def _ddsn_get_stock_control_product(self):
        """Return the stored product whose stock supports this sale line.

        A transformed product consumes one finished base product through its
        BoM.  Other products control their own variant stock.  Special products
        manufactured from raw materials are intentionally excluded here.
        """
        self.ensure_one()
        product = self.product_id
        if not product:
            return product, 0.0, False

        template = product.product_tmpl_id
        product_kind = getattr(template, "ddsp_product_kind", False)
        if product_kind == "special":
            return self.env["product.product"], 0.0, False
        if product_kind != "transformed":
            return product, self.product_uom_qty, False

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
            return product, self.product_uom_qty, False

        required_in_bom_uom = (self.product_uom_qty / (bom.product_qty or 1.0)) * base_line.product_qty
        required_qty = base_line.product_uom_id._compute_quantity(
            required_in_bom_uom,
            base_line.product_id.uom_id,
        )
        return base_line.product_id, required_qty, product

    def _ddsn_select_supply_warehouse(self):
        """Sales always consume from the commercial office warehouse."""
        self.ensure_one()
        return self.order_id.warehouse_id

    @api.onchange("product_id", "product_uom_qty", "order_id.warehouse_id")
    def _onchange_ddsn_warn_insufficient_stock(self):
        for line in self:
            warehouse = line._ddsn_select_supply_warehouse()
            line.ddsn_supply_warehouse_id = warehouse
            control_product, required_qty, transformed_product = line._ddsn_get_stock_control_product()
            if (
                not warehouse
                or not warehouse.lot_stock_id
                or not control_product
                or not control_product.is_storable
                or required_qty <= 0
            ):
                continue

            available_qty = control_product.with_company(line.order_id.company_id).with_context(
                location=warehouse.lot_stock_id.id
            ).qty_available
            if not transformed_product:
                available_qty -= line._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                available_qty -= line._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
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
                        "\nCantidad disponible: %(available).2f\n\nAl confirmar se creará una solicitud para Logística."
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

        warehouses = self._ddsn_visible_stock_warehouses()
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

        warehouses = self._ddsn_visible_stock_warehouses()
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

    def ddsn_get_live_warehouse_stock_tooltip(self):
        """Return a fresh warehouse snapshot whenever the user opens the tooltip."""
        self.ensure_one()
        return self._ddsn_get_warehouse_stock_text() or _(
            "No hay información de existencias disponible."
        )

    def _ddsn_get_warehouse_stock_text(self):
        self.ensure_one()
        product = self.product_id
        if not product or product.type not in ("product", "consu"):
            return False

        warehouses = self._ddsn_visible_stock_warehouses()
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

    def _ddsn_visible_stock_warehouses(self):
        self.ensure_one()
        if self.env.user.has_group("stock.group_stock_manager") or self.env.user.has_group("base.group_system"):
            return self.env["stock.warehouse"].search(
                [("company_id", "=", self.order_id.company_id.id)], order="sequence, id"
            )
        return self.order_id.warehouse_id

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

    @api.onchange("product_id")
    def _onchange_ddsn_apply_partner_bonus(self):
        for line in self:
            if not line.product_id or line.display_type:
                continue
            if line.product_id.ddsn_fixed_price:
                line._ddsn_apply_automatic_bonus()
                continue
            if line.ddsn_bonus_source == "manual" and line.discount:
                line.ddsn_bonus_percent = line.discount
                continue
            line._ddsn_apply_automatic_bonus()

    def _ddsn_get_automatic_bonus_candidate(self):
        self.ensure_one()
        product = self.product_id
        if product and product._ddsn_product_bonus_is_current():
            return (
                product.ddsn_product_bonus_percent,
                "product",
                product.display_name,
                product.ddsn_product_bonus_authorized_by_id,
            )
        partner = self.order_id.partner_id
        if not partner:
            return 0.0, False, False, False
        partner = partner.commercial_partner_id or partner
        if partner._ddsn_bonus_is_current():
            return (
                partner.ddsn_bonus_percent,
                "partner",
                partner.display_name,
                partner.ddsn_bonus_authorized_by_id,
            )
        category = partner._ddsn_get_group_bonus_category()
        if category:
            return (
                category.ddsn_bonus_percent,
                "group",
                category.display_name,
                category.ddsn_bonus_authorized_by_id,
            )
        return 0.0, False, False, False

    def _ddsn_apply_automatic_bonus(self):
        for line in self:
            if line.product_id.ddsn_fixed_price:
                line.update({
                    "discount": 0.0,
                    "ddsn_bonus_percent": 0.0,
                    "ddsn_bonus_source": "fixed_price",
                    "ddsn_bonus_rule_reference": line.product_id.display_name,
                    "ddsn_bonus_authorized_by_id": False,
                })
                continue
            if line.ddsn_bonus_source == "manual" and line.discount:
                continue
            percent, source, reference, authorized_by = line._ddsn_get_automatic_bonus_candidate()
            line.update({
                "discount": percent,
                "ddsn_bonus_percent": percent,
                "ddsn_bonus_source": source,
                "ddsn_bonus_rule_reference": reference,
                "ddsn_bonus_authorized_by_id": authorized_by.id if authorized_by else False,
            })
        return True

    @api.onchange("discount")
    def _onchange_ddsn_sync_bonus_percent(self):
        for line in self:
            if line.product_id.ddsn_fixed_price:
                line.discount = 0.0
                line.ddsn_bonus_percent = 0.0
                line.ddsn_bonus_source = "fixed_price"
                line.ddsn_bonus_rule_reference = line.product_id.display_name
                line.ddsn_bonus_authorized_by_id = False
                continue
            line.ddsn_bonus_percent = line.discount or 0.0
            if not line.discount:
                line.ddsn_bonus_source = False
            elif line.ddsn_bonus_source not in ("partner", "constructor", "group"):
                line.ddsn_bonus_source = "manual"
                line.ddsn_bonus_rule_reference = "Ajuste manual"
                line.ddsn_bonus_authorized_by_id = self.env.user

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        values.update({
            "ddsn_bonus_percent": self.ddsn_bonus_percent,
            "ddsn_bonus_source": self.ddsn_bonus_source,
            "ddsn_bonus_rule_reference": self.ddsn_bonus_rule_reference,
            "ddsn_bonus_authorized_by_id": self.ddsn_bonus_authorized_by_id.id,
        })
        return values

    def write(self, vals):
        if vals.get("discount", 0.0):
            replacement = self.env["product.product"].browse(vals.get("product_id"))
            for line in self:
                target_product = replacement or line.product_id
                if target_product.ddsn_fixed_price:
                    raise ValidationError(_(
                        "El ITEM %(product)s tiene Precio fijo y no admite descuentos ni bonificaciones."
                    ) % {"product": target_product.display_name})
        if (
            {"price_unit", "discount"}.intersection(vals)
            and not self.env.context.get("ddsn_automatic_pricing")
            and not self.env.user.has_group("base.group_system")
        ):
            raise ValidationError(
                _("Solo un administrador de Ajustes puede modificar precios o descuentos.")
            )
        protected_product_fields = {
            "product_id",
            "name",
            "product_uom_qty",
            "product_uom",
            "price_unit",
            "discount",
            "tax_id",
            "analytic_distribution",
            "display_type",
        }
        if protected_product_fields.intersection(vals):
            protected_lines = self.filtered(
                lambda line: line.order_id.state in ("sale", "done")
            )
            if protected_lines:
                raise ValidationError(
                    _("No se pueden modificar líneas de producto en una cotización confirmada. "
                      "El documento está cerrado para edición.")
                )
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        Product = self.env["product.product"]
        for vals in vals_list:
            product = Product.browse(vals.get("product_id"))
            if not product:
                continue
            if product.ddsn_fixed_price:
                vals.update({
                    "discount": 0.0,
                    "ddsn_bonus_percent": 0.0,
                    "ddsn_bonus_source": "fixed_price",
                    "ddsn_bonus_rule_reference": product.display_name,
                    "ddsn_bonus_authorized_by_id": False,
                })
            elif vals.get("discount", 0.0) and self.env.user.has_group("base.group_system"):
                vals.update({
                    "ddsn_bonus_percent": vals["discount"],
                    "ddsn_bonus_source": "manual",
                    "ddsn_bonus_rule_reference": "Ajuste manual",
                    "ddsn_bonus_authorized_by_id": self.env.user.id,
                })
        if (
            not self.env.context.get("ddsn_automatic_pricing")
            and not self.env.user.has_group("base.group_system")
        ):
            vals_list = [
                {key: value for key, value in vals.items() if key not in {"price_unit", "discount"}}
                for vals in vals_list
            ]
        order_ids = {vals.get("order_id") for vals in vals_list if vals.get("order_id")}
        locked_orders = self.env["sale.order"].browse(order_ids).filtered(
            lambda order: order.state in ("sale", "done")
        )
        if locked_orders:
            raise ValidationError(
                _("No se pueden agregar productos a una cotización confirmada. Devuélvala a borrador primero.")
            )
        lines = super().create(vals_list)
        automatic_lines = lines.filtered(
            lambda line: line.product_id
            and not line.product_id.ddsn_fixed_price
            and line.ddsn_bonus_source != "manual"
        )
        if automatic_lines:
            automatic_lines.with_context(
                ddsn_automatic_pricing=True
            )._ddsn_apply_automatic_bonus()
        return lines

    def unlink(self):
        if self.filtered(lambda line: line.order_id.state in ("sale", "done")):
            raise ValidationError(
                _("No se pueden eliminar productos de una cotización confirmada. Devuélvala a borrador primero.")
            )
        return super().unlink()
