from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseSupplyAllocation(models.Model):
    _name = "ddpfw.purchase.supply.allocation"
    _description = "Purchase quantity logistic origin"
    _order = "purchase_order_id, purchase_line_id, id"
    _check_company_auto = True

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Orden de compra",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Línea de compra",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="purchase_order_id.company_id",
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        related="purchase_line_id.product_id",
        string="Producto",
        store=True,
    )
    product_uom_id = fields.Many2one(
        related="purchase_line_id.product_uom",
        string="UdM",
        store=True,
    )
    quantity = fields.Float(string="Cantidad", required=True, default=1.0)
    origin_type = fields.Selection(
        [("sale", "Venta"), ("replenishment", "Reposición")],
        string="Motivo",
        required=True,
        default="replenishment",
        index=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta",
        check_company=True,
        ondelete="restrict",
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Factura",
        domain="[('move_type', '=', 'out_invoice'), ('company_id', '=', company_id)]",
        check_company=True,
        ondelete="restrict",
    )
    invoice_line_id = fields.Many2one(
        "account.move.line",
        string="Línea de factura",
        domain="[('move_id', '=', invoice_id), ('product_id', '=', product_id)]",
        check_company=True,
        ondelete="restrict",
    )
    fulfillment_line_id = fields.Many2one(
        "doorandoor.fulfillment.line",
        string="Necesidad de entrega",
        ondelete="restrict",
        index=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén destino",
        check_company=True,
    )
    customer_id = fields.Many2one(
        related="invoice_id.partner_id",
        string="Cliente",
        store=True,
    )
    origin_document = fields.Char(
        string="Documento origen",
        compute="_compute_origin_document",
        store=True,
    )
    automatic = fields.Boolean(string="Asignación automática", default=False, index=True)

    @api.depends("origin_type", "invoice_id.name", "sale_order_id.name", "warehouse_id.name")
    def _compute_origin_document(self):
        for allocation in self:
            if allocation.origin_type == "sale":
                documents = [
                    value
                    for value in (allocation.invoice_id.name, allocation.sale_order_id.name)
                    if value and value != "/"
                ]
                allocation.origin_document = " / ".join(documents) or _("Venta pendiente")
            else:
                allocation.origin_document = _("Reposición %s") % (
                    allocation.warehouse_id.display_name or allocation.purchase_order_id.picking_type_id.warehouse_id.display_name
                )

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        for allocation in self:
            if allocation.invoice_id:
                allocation.sale_order_id = allocation.invoice_id.invoice_line_ids.sale_line_ids.order_id[:1]
                if allocation.invoice_line_id.move_id != allocation.invoice_id:
                    allocation.invoice_line_id = False

    @api.onchange("purchase_line_id")
    def _onchange_purchase_line_id(self):
        for allocation in self:
            if allocation.purchase_line_id:
                allocation.purchase_order_id = allocation.purchase_line_id.order_id

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("purchase_line_id"):
                line = self.env["purchase.order.line"].browse(values["purchase_line_id"])
                values["purchase_order_id"] = line.order_id.id
        return super().create(vals_list)

    @api.constrains(
        "quantity",
        "origin_type",
        "invoice_id",
        "invoice_line_id",
        "sale_order_id",
        "purchase_line_id",
    )
    def _check_allocation(self):
        for allocation in self:
            if allocation.quantity <= 0:
                raise ValidationError(_("La cantidad asociada debe ser mayor que cero."))
            if allocation.purchase_line_id.order_id != allocation.purchase_order_id:
                raise ValidationError(_("La línea de compra no pertenece a la orden indicada."))
            if allocation.origin_type == "sale" and not (
                allocation.invoice_id or allocation.sale_order_id
            ):
                raise ValidationError(
                    _("Una cantidad destinada a venta debe indicar la factura o el pedido de venta.")
                )
            if allocation.origin_type == "replenishment" and (
                allocation.invoice_id or allocation.sale_order_id or allocation.invoice_line_id
            ):
                raise ValidationError(
                    _("Una reposición no puede conservar documentos de una venta.")
                )
            if allocation.invoice_line_id:
                if allocation.invoice_line_id.move_id != allocation.invoice_id:
                    raise ValidationError(_("La línea seleccionada no pertenece a la factura indicada."))
                if allocation.invoice_line_id.product_id != allocation.product_id:
                    raise ValidationError(_("La línea de factura y la línea de compra deben tener el mismo producto."))

        for line in self.mapped("purchase_line_id"):
            allocated = sum(line.ddpfw_supply_allocation_ids.mapped("quantity"))
            if allocated > line.product_qty + 1e-6:
                raise ValidationError(
                    _("La cantidad asociada de %(product)s (%(allocated)s) supera la cantidad comprada (%(ordered)s).")
                    % {
                        "product": line.product_id.display_name,
                        "allocated": allocated,
                        "ordered": line.product_qty,
                    }
                )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    ddpfw_supply_allocation_ids = fields.One2many(
        "ddpfw.purchase.supply.allocation",
        "purchase_line_id",
        string="Origen logístico",
        copy=True,
    )
    ddpfw_allocated_qty = fields.Float(
        string="Cantidad asociada",
        compute="_compute_ddpfw_supply_info",
    )
    ddpfw_supply_origin = fields.Char(
        string="Destino / Documento de venta",
        compute="_compute_ddpfw_supply_info",
    )

    @api.depends(
        "product_qty",
        "ddpfw_supply_allocation_ids.quantity",
        "ddpfw_supply_allocation_ids.origin_type",
        "ddpfw_supply_allocation_ids.origin_document",
    )
    def _compute_ddpfw_supply_info(self):
        for line in self:
            allocations = line.ddpfw_supply_allocation_ids
            line.ddpfw_allocated_qty = sum(allocations.mapped("quantity"))
            descriptions = []
            for allocation in allocations:
                label = dict(allocation._fields["origin_type"].selection).get(
                    allocation.origin_type
                )
                descriptions.append(
                    "%s: %s (%s)"
                    % (label, allocation.origin_document, allocation.quantity)
                )
            remainder = max(line.product_qty - line.ddpfw_allocated_qty, 0.0)
            if remainder:
                descriptions.append(_("Reposición sin asignar (%s)") % remainder)
            line.ddpfw_supply_origin = "; ".join(descriptions) or _("Pendiente de clasificar")

    @api.constrains("product_qty")
    def _check_ddpfw_allocated_qty(self):
        for line in self:
            if line.ddpfw_allocated_qty > line.product_qty + 1e-6:
                raise ValidationError(
                    _("No puede reducir la compra por debajo de la cantidad ya asociada a ventas o reposición.")
                )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    ddpfw_supply_allocation_ids = fields.One2many(
        "ddpfw.purchase.supply.allocation",
        "purchase_order_id",
        string="Trazabilidad logística",
    )
    ddpfw_source_invoice_ids = fields.Many2many(
        "account.move",
        string="Facturas asociadas",
        compute="_compute_ddpfw_supply_summary",
    )
    ddpfw_supply_summary = fields.Char(
        string="Origen de la compra",
        compute="_compute_ddpfw_supply_summary",
    )
    ddpfw_demand_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén a abastecer",
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        help=(
            "Almacén cuya demanda se atenderá. La recepción física continúa usando "
            "el almacén central configurado para Compras."
        ),
    )

    @api.onchange("picking_type_id")
    def _onchange_ddpfw_demand_warehouse(self):
        for order in self:
            if not order.ddpfw_demand_warehouse_id and order.picking_type_id.warehouse_id:
                order.ddpfw_demand_warehouse_id = order.picking_type_id.warehouse_id

    def _ddpfw_pending_sale_needs(self, product, warehouse):
        """Return uncovered customer deliveries in FIFO order.

        Physical stock covers the oldest open deliveries first. Quantities already
        linked to another active purchase are also considered incoming coverage.
        """
        self.ensure_one()
        fulfillment_model = self.env["doorandoor.fulfillment.line"]
        needs = fulfillment_model.search(
            [
                ("product_id", "=", product.id),
                ("move_id.state", "=", "posted"),
                ("qty_pending_delivery", ">", 0),
                ("state", "!=", "delivered"),
                ("move_id.company_id", "=", self.company_id.id),
            ],
            order="move_id asc, id asc",
        ).filtered(
            lambda need: (
                need.move_line_id.ddsn_supply_warehouse_id
                or need.sale_order_id.warehouse_id
            ) == warehouse
        )

        available = product.with_company(self.company_id).with_context(
            location=warehouse.lot_stock_id.id
        ).qty_available
        other_allocations = self.env["ddpfw.purchase.supply.allocation"].search(
            [
                ("purchase_order_id.state", "not in", ("cancel", "done")),
                ("product_id", "=", product.id),
                ("warehouse_id", "=", warehouse.id),
            ]
        )
        available += sum(other_allocations.mapped("quantity"))

        uncovered = []
        for need in needs:
            quantity = need.qty_pending_delivery
            covered = min(max(available, 0.0), quantity)
            available -= covered
            missing = quantity - covered
            if missing > 0:
                uncovered.append((need, missing))
        return uncovered

    def action_ddpfw_auto_allocate_supply(self):
        """Rebuild automatic traceability without touching manual exceptions."""
        for order in self:
            warehouse = (
                order.ddpfw_demand_warehouse_id
                or order.picking_type_id.warehouse_id
                or order.ddpfw_enforced_warehouse_id
            )
            if not warehouse or not warehouse.lot_stock_id:
                raise ValidationError(_("Seleccione un almacén válido para calcular la logística."))

            order.ddpfw_supply_allocation_ids.filtered("automatic").unlink()
            for line in order.order_line.filtered(
                lambda item: item.product_id and not item.display_type and item.product_qty > 0
            ):
                remaining = line.product_qty - sum(
                    line.ddpfw_supply_allocation_ids.mapped("quantity")
                )
                if remaining <= 0:
                    continue
                for need, missing in order._ddpfw_pending_sale_needs(line.product_id, warehouse):
                    quantity = min(remaining, missing)
                    self.env["ddpfw.purchase.supply.allocation"].create(
                        {
                            "purchase_line_id": line.id,
                            "quantity": quantity,
                            "origin_type": "sale",
                            "invoice_id": need.move_id.id,
                            "invoice_line_id": need.move_line_id.id,
                            "sale_order_id": need.sale_order_id.id,
                            "fulfillment_line_id": need.id,
                            "warehouse_id": warehouse.id,
                            "automatic": True,
                        }
                    )
                    remaining -= quantity
                    if remaining <= 0:
                        break
                if remaining > 0:
                    self.env["ddpfw.purchase.supply.allocation"].create(
                        {
                            "purchase_line_id": line.id,
                            "quantity": remaining,
                            "origin_type": "replenishment",
                            "warehouse_id": warehouse.id,
                            "automatic": True,
                        }
                    )
        return True

    @api.depends(
        "order_line.product_qty",
        "order_line.ddpfw_supply_allocation_ids.quantity",
        "order_line.ddpfw_supply_allocation_ids.origin_type",
        "order_line.ddpfw_supply_allocation_ids.invoice_id",
    )
    def _compute_ddpfw_supply_summary(self):
        for order in self:
            allocations = order.order_line.ddpfw_supply_allocation_ids
            order.ddpfw_source_invoice_ids = allocations.mapped("invoice_id")
            sale_qty = sum(allocations.filtered(lambda item: item.origin_type == "sale").mapped("quantity"))
            explicit_replenishment_qty = sum(
                allocations.filtered(lambda item: item.origin_type == "replenishment").mapped("quantity")
            )
            unallocated_qty = sum(order.order_line.mapped("product_qty")) - sum(
                allocations.mapped("quantity")
            )
            replenishment_qty = explicit_replenishment_qty + max(unallocated_qty, 0.0)
            if sale_qty and replenishment_qty:
                order.ddpfw_supply_summary = _("Mixta: venta %(sale)s / reposición %(stock)s") % {
                    "sale": sale_qty,
                    "stock": replenishment_qty,
                }
            elif sale_qty:
                order.ddpfw_supply_summary = _("Venta: %s unidades") % sale_qty
            else:
                order.ddpfw_supply_summary = _("Reposición: %s unidades") % replenishment_qty
