from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ExternalOrder(models.Model):
    _name = "ddem.external.order"
    _description = "Pedido externo de fabricación"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(default="Nuevo", copy=False, readonly=True, index=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Preparación"),
            ("ready", "Listo para ordenar"),
            ("ordered", "Ordenado al proveedor"),
            ("manufacturing", "En fabricación"),
            ("ready_pickup", "Listo / En tránsito"),
            ("received", "Recibido"),
            ("delivered", "Entregado"),
            ("issue", "Con incidencia"),
            ("cancelled", "Cancelado"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", related="sale_order_id.company_id", store=True, readonly=True
    )
    sale_order_id = fields.Many2one(
        "sale.order", string="Cotización / Venta", required=True, ondelete="restrict", check_company=True, tracking=True
    )
    customer_id = fields.Many2one(related="sale_order_id.partner_id", string="Cliente", store=True, readonly=True)
    salesperson_id = fields.Many2one(related="sale_order_id.user_id", string="Comercial", store=True, readonly=True)
    vendor_id = fields.Many2one(
        "res.partner", string="Proveedor", required=True, domain="[('supplier_rank', '>', 0)]", tracking=True
    )
    supply_route = fields.Selection(
        [("external", "Fabricación externa"), ("subcontract", "Subcontratación")],
        required=True,
        tracking=True,
    )
    logistic_route = fields.Selection(
        [
            ("warehouse", "Recibir en almacén"),
            ("predispatch", "Recibir en predespacho"),
            ("direct", "Entrega directa al cliente"),
            ("pickup", "Recoger en proveedor"),
        ],
        required=True,
        tracking=True,
    )
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén", check_company=True, tracking=True)
    requested_date = fields.Date(string="Fecha requerida", tracking=True)
    promised_date = fields.Date(string="Fecha prometida", tracking=True)
    vendor_quote_reference = fields.Char(string="Cotización del proveedor", tracking=True)
    vendor_quote_attachment_ids = fields.Many2many("ir.attachment", string="Documentos del proveedor")
    notes = fields.Html(string="Instrucciones / observaciones")
    line_ids = fields.One2many("ddem.external.order.line", "external_order_id", string="Productos", copy=True)
    purchase_order_id = fields.Many2one("purchase.order", string="Orden de compra", copy=False, readonly=True, tracking=True)
    min_payment_percent = fields.Float(string="Pago mínimo (%)", default=100.0, tracking=True)
    min_margin_percent = fields.Float(string="Margen mínimo (%)", default=0.0, tracking=True)
    manager_approval_required = fields.Boolean(string="Requiere aprobación", tracking=True)
    manager_approved = fields.Boolean(string="Aprobado por Gerencia", copy=False, tracking=True)
    manager_approved_by_id = fields.Many2one("res.users", string="Aprobado por", copy=False, readonly=True)
    manager_approved_at = fields.Datetime(string="Fecha de aprobación", copy=False, readonly=True)
    policy_ok = fields.Boolean(compute="_compute_controls", string="Políticas firmadas")
    paid_amount = fields.Monetary(compute="_compute_controls", string="Total pagado", currency_field="currency_id")
    payment_percent = fields.Float(compute="_compute_controls", string="Pago realizado (%)")
    payment_ok = fields.Boolean(compute="_compute_controls", string="Pago suficiente")
    sale_amount = fields.Monetary(compute="_compute_controls", string="Importe de venta", currency_field="currency_id")
    vendor_amount = fields.Monetary(compute="_compute_controls", string="Costo proveedor", currency_field="currency_id")
    margin_percent = fields.Float(compute="_compute_controls", string="Margen previsto (%)")
    margin_ok = fields.Boolean(compute="_compute_controls", string="Margen suficiente")
    approval_ok = fields.Boolean(compute="_compute_controls", string="Aprobación suficiente")
    ready_to_order = fields.Boolean(compute="_compute_controls", string="Listo para ordenar")
    blocking_reason = fields.Text(compute="_compute_controls", string="Pendientes")
    currency_id = fields.Many2one(related="sale_order_id.currency_id", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("name", "Nuevo") == "Nuevo":
                values["name"] = self.env["ir.sequence"].next_by_code("ddem.external.order") or "EXT"
        return super().create(vals_list)

    @api.depends(
        "sale_order_id.amount_total",
        "sale_order_id.invoice_ids.state",
        "sale_order_id.invoice_ids.amount_total",
        "sale_order_id.invoice_ids.amount_residual",
        "line_ids.sale_subtotal",
        "line_ids.vendor_subtotal",
        "min_payment_percent",
        "min_margin_percent",
        "manager_approval_required",
        "manager_approved",
    )
    def _compute_controls(self):
        for request in self:
            valid_policy = bool(request.customer_id and request.customer_id._ddpa_get_valid_acceptance())
            invoices = request.sale_order_id.invoice_ids.filtered(
                lambda move: move.move_type == "out_invoice" and move.state == "posted"
            )
            paid = sum(max(move.amount_total - move.amount_residual, 0.0) for move in invoices)
            sale_amount = sum(request.line_ids.mapped("sale_subtotal"))
            vendor_amount = sum(request.line_ids.mapped("vendor_subtotal"))
            payment_percent = (paid / request.sale_order_id.amount_total * 100.0) if request.sale_order_id.amount_total else 0.0
            margin_percent = ((sale_amount - vendor_amount) / sale_amount * 100.0) if sale_amount else 0.0
            payment_ok = payment_percent + 1e-6 >= request.min_payment_percent
            margin_ok = margin_percent + 1e-6 >= request.min_margin_percent
            approval_ok = not request.manager_approval_required or request.manager_approved
            reasons = []
            if not valid_policy:
                reasons.append(_("Políticas del cliente pendientes"))
            if not payment_ok:
                reasons.append(_("Pago %(current).2f%% de %(required).2f%% requerido") % {
                    "current": payment_percent, "required": request.min_payment_percent
                })
            if not margin_ok:
                reasons.append(_("Margen %(current).2f%% inferior al mínimo %(required).2f%%") % {
                    "current": margin_percent, "required": request.min_margin_percent
                })
            if not approval_ok:
                reasons.append(_("Falta aprobación de Gerencia"))
            if not request.line_ids:
                reasons.append(_("No hay productos"))
            if request.line_ids.filtered(lambda line: line.vendor_unit_price <= 0):
                reasons.append(_("Falta precio del proveedor"))
            request.policy_ok = valid_policy
            request.paid_amount = paid
            request.payment_percent = payment_percent
            request.payment_ok = payment_ok
            request.sale_amount = sale_amount
            request.vendor_amount = vendor_amount
            request.margin_percent = margin_percent
            request.margin_ok = margin_ok
            request.approval_ok = approval_ok
            request.ready_to_order = not reasons
            request.blocking_reason = "\n".join(reasons)

    def action_manager_approve(self):
        if not (self.env.user.has_group("purchase.group_purchase_manager") or self.env.user.has_group("base.group_system")):
            raise UserError(_("Solo Compras/Administrador o Administrador/Ajustes puede aprobar el pedido externo."))
        self.write({
            "manager_approved": True,
            "manager_approved_by_id": self.env.user.id,
            "manager_approved_at": fields.Datetime.now(),
        })
        return True

    def action_check_ready(self):
        for request in self:
            if not request.ready_to_order:
                raise UserError(_("El pedido no puede liberarse:\n%s") % request.blocking_reason)
            if request.state == "draft":
                request.state = "ready"
        return True

    def action_create_purchase_order(self):
        self.ensure_one()
        if self.purchase_order_id:
            return self.action_open_purchase_order()
        self.action_check_ready()
        if not self.line_ids:
            raise UserError(_("Agregue al menos un producto."))
        if self.logistic_route == "direct":
            destination = self.sale_order_id.partner_shipping_id
        else:
            destination = False
        order_date = fields.Date.context_today(self)
        po = self.env["purchase.order"].create({
            "partner_id": self.vendor_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "origin": "%s / %s" % (self.name, self.sale_order_id.name),
            "partner_ref": self.vendor_quote_reference,
            "dest_address_id": destination.id if destination else False,
            "date_order": fields.Datetime.now(),
            "ddem_external_order_id": self.id,
            "order_line": [
                (0, 0, line._prepare_purchase_line_values(order_date)) for line in self.line_ids
            ],
        })
        for po_line, external_line in zip(po.order_line, self.line_ids):
            if "ddpfw_supply_allocation_ids" in po_line._fields:
                po_line.ddpfw_supply_allocation_ids = [(0, 0, {
                    "quantity": external_line.quantity,
                    "origin_type": "sale",
                    "sale_order_id": self.sale_order_id.id,
                    "warehouse_id": self.warehouse_id.id,
                })]
        self.write({"purchase_order_id": po.id, "state": "ordered"})
        self.sale_order_id.message_post(body=_("Pedido externo %(request)s vinculado a la compra %(purchase)s.") % {
            "request": self.name, "purchase": po.name
        })
        return self.action_open_purchase_order()

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError(_("Todavía no existe una orden de compra."))
        return {
            "type": "ir.actions.act_window",
            "name": self.purchase_order_id.name,
            "res_model": "purchase.order",
            "res_id": self.purchase_order_id.id,
            "view_mode": "form",
            "target": "current",
        }


class ExternalOrderLine(models.Model):
    _name = "ddem.external.order.line"
    _description = "Producto de pedido externo"
    _order = "id"
    _check_company_auto = True

    external_order_id = fields.Many2one("ddem.external.order", required=True, ondelete="cascade", check_company=True)
    company_id = fields.Many2one(related="external_order_id.company_id", store=True)
    currency_id = fields.Many2one(related="external_order_id.currency_id")
    sale_line_id = fields.Many2one("sale.order.line", string="Línea de venta", required=True, ondelete="restrict", check_company=True)
    product_id = fields.Many2one(related="sale_line_id.product_id", string="Producto", store=True, readonly=True)
    description = fields.Text(related="sale_line_id.name", string="Especificaciones", readonly=True)
    quantity = fields.Float(related="sale_line_id.product_uom_qty", string="Cantidad", readonly=True)
    product_uom_id = fields.Many2one(related="sale_line_id.product_uom", string="UdM", readonly=True)
    sale_unit_price = fields.Monetary(related="sale_line_id.price_unit", string="Precio de venta", currency_field="currency_id", readonly=True)
    sale_subtotal = fields.Monetary(related="sale_line_id.price_subtotal", string="Subtotal venta", currency_field="currency_id", readonly=True)
    vendor_unit_price = fields.Monetary(string="Precio proveedor", currency_field="currency_id")
    vendor_subtotal = fields.Monetary(compute="_compute_vendor_subtotal", string="Costo proveedor", currency_field="currency_id")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("sale_line_id") and not values.get("vendor_unit_price"):
                line = self.env["sale.order.line"].browse(values["sale_line_id"])
                vendor = self.env["res.partner"].browse(values.get("external_order_id") and self.env["ddem.external.order"].browse(values["external_order_id"]).vendor_id.id)
                seller = line.product_id._select_seller(partner_id=vendor, quantity=line.product_uom_qty, uom_id=line.product_uom)
                values["vendor_unit_price"] = seller.price if seller else line.product_id.standard_price
        return super().create(vals_list)

    @api.depends("vendor_unit_price", "quantity")
    def _compute_vendor_subtotal(self):
        for line in self:
            line.vendor_subtotal = line.vendor_unit_price * line.quantity

    def _prepare_purchase_line_values(self, order_date):
        self.ensure_one()
        planned = order_date + timedelta(
            days=self.product_id.product_tmpl_id.ddem_manufacturing_days
            + self.product_id.product_tmpl_id.ddem_transport_days
        )
        return {
            "product_id": self.product_id.id,
            "name": self.description or self.product_id.display_name,
            "product_qty": self.quantity,
            "product_uom": self.product_uom_id.id,
            "price_unit": self.vendor_unit_price,
            "date_planned": planned,
        }

    @api.constrains("sale_line_id", "external_order_id")
    def _check_sale_line_order(self):
        for line in self:
            if line.sale_line_id.order_id != line.external_order_id.sale_order_id:
                raise ValidationError(_("La línea no pertenece a la cotización del pedido externo."))
