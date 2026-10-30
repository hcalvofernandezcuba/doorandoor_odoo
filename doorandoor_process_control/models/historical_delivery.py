from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorAndDoorHistoricalDelivery(models.Model):
    _name = "doorandoor.historical.delivery"
    _description = "Entrega de venta del sistema anterior"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sale_date desc, id desc"

    name = fields.Char(
        string="Control histórico", required=True, copy=False, readonly=True,
        default=lambda self: _("Nuevo"), tracking=True,
    )
    external_reference = fields.Char(
        string="Factura del sistema anterior", required=True, index=True, tracking=True,
    )
    sale_date = fields.Date(
        string="Fecha de venta", required=True, default=fields.Date.context_today,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Cliente", required=True, tracking=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén de entrega al cliente", required=True, tracking=True,
        domain=lambda self: self._warehouse_domain(),
    )
    supply_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén proveedor", required=True, tracking=True,
        domain=lambda self: self._warehouse_domain(),
        default=lambda self: self._default_supply_warehouse(),
        help="Almacén físico desde el cual sale inicialmente la mercancía.",
    )
    line_ids = fields.One2many(
        "doorandoor.historical.delivery.line", "delivery_id",
        string="Productos", copy=True,
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment", "ddpc_historical_delivery_attachment_rel",
        "delivery_id", "attachment_id", string="Documentos de respaldo",
    )
    payment_note = fields.Char(
        string="Referencia del pago anterior", required=True,
        help="Método, número o constancia con que se verificó el pago en el sistema anterior.",
    )
    note = fields.Text(string="Observaciones")
    picking_id = fields.Many2one(
        "stock.picking", string="Entrega final al cliente", readonly=True, copy=False,
        tracking=True,
    )
    transfer_dispatch_id = fields.Many2one(
        "stock.picking", string="Despacho entre almacenes", readonly=True,
        copy=False, tracking=True,
    )
    transfer_receipt_id = fields.Many2one(
        "stock.picking", string="Recepción en destino", readonly=True,
        copy=False, tracking=True,
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("transfer_pending", "Traslado en proceso"),
         ("ready", "Lista para entregar"),
         ("done", "Entregada"), ("cancel", "Anulada")],
        default="draft", required=True, copy=False, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True,
    )
    created_by_id = fields.Many2one(
        "res.users", string="Creada por", default=lambda self: self.env.user,
        readonly=True,
    )

    _sql_constraints = [
        (
            "external_reference_company_uniq",
            "unique(external_reference, company_id)",
            "Ya existe una entrega histórica con esa factura del sistema anterior.",
        ),
    ]

    @api.model
    def _warehouse_domain(self):
        user = self.env.user
        if (
            user.has_group("doorandoor_process_control.group_ddpc_manager")
            or user.has_group("stock.group_stock_manager")
            or user.has_group("base.group_system")
        ):
            return []
        return [("id", "in", user.ddpc_warehouse_ids.ids)]

    @api.model
    def _default_supply_warehouse(self):
        return self.env.user.ddpc_warehouse_ids[:1] or self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id)
        ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            vals["external_reference"] = (vals.get("external_reference") or "").strip().upper()
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("doorandoor.historical.delivery") or _("Nuevo")
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("external_reference"):
            vals["external_reference"] = vals["external_reference"].strip().upper()
        protected = {
            "external_reference", "sale_date", "partner_id", "warehouse_id",
            "supply_warehouse_id",
            "line_ids", "company_id", "payment_note",
        }
        if protected.intersection(vals) and any(record.state != "draft" for record in self):
            raise UserError(_("Una entrega histórica liberada no puede modificarse. Anúlela mediante el proceso autorizado."))
        return super().write(vals)

    def action_create_operation(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Esta entrega histórica ya fue liberada."))
        if not self.line_ids:
            raise UserError(_("Agregue al menos un producto."))
        if any(line.quantity <= 0 for line in self.line_ids):
            raise UserError(_("Todas las cantidades deben ser mayores que cero."))
        direct_attachments = self.env["ir.attachment"].search_count([
            ("res_model", "=", self._name), ("res_id", "=", self.id),
        ])
        if not self.evidence_attachment_ids and not direct_attachments:
            raise UserError(_("Adjunte el documento de respaldo de la venta anterior."))

        if self.supply_warehouse_id != self.warehouse_id:
            return self._create_transfer_dispatch()
        picking = self._create_customer_delivery()
        self.write({"picking_id": picking.id, "state": "ready"})
        self._post_release_audit(picking)
        return self.action_open_operation()

    def _create_customer_delivery(self):
        self.ensure_one()

        picking_type = self.warehouse_id.out_type_id
        if not picking_type or not picking_type.default_location_src_id:
            raise UserError(_("El almacén seleccionado no tiene configurada una operación de entrega."))
        destination = self.partner_id.property_stock_customer
        if not destination:
            raise UserError(_("El cliente no tiene configurada su ubicación de entrega."))

        picking = self.env["stock.picking"].create({
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": destination.id,
            "origin": _("Factura histórica %(reference)s") % {
                "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
        })
        for line in self.line_ids:
            self.env["stock.move"].create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.quantity,
                "product_uom": line.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_id.id,
            })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _post_release_audit(self, picking):
        self.ensure_one()
        audit = _(
            "Entrega histórica liberada desde %(control)s. Factura anterior: %(reference)s. "
            "Pago verificado: %(payment)s. Almacén de entrega: %(warehouse)s. Creada por: %(user)s."
        ) % {
            "control": self.name,
            "reference": self.external_reference,
            "payment": self.payment_note,
            "warehouse": self.warehouse_id.display_name,
            "user": self.env.user.display_name,
        }
        self.message_post(body=audit)
        picking.message_post(body=audit)

    def _create_transfer_dispatch(self):
        self.ensure_one()
        picking_type = self.supply_warehouse_id.int_type_id
        source = self.supply_warehouse_id.lot_stock_id
        destination = self.warehouse_id.lot_stock_id
        if not picking_type or not source or not destination:
            raise UserError(_("Los almacenes seleccionados no tienen configurado el traslado interno."))
        dispatch = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "origin": _("Entrega histórica %(control)s / %(reference)s") % {
                "control": self.name, "reference": self.external_reference,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.company_id.id,
        })
        for line in self.line_ids:
            self.env["stock.move"].create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.quantity,
                "product_uom": line.product_uom_id.id,
                "picking_id": dispatch.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "company_id": self.company_id.id,
            })
        dispatch.action_confirm()
        dispatch.action_assign()
        self.write({"transfer_dispatch_id": dispatch.id, "state": "transfer_pending"})
        audit = _(
            "Flujo histórico liberado: %(source)s despacha hacia %(destination)s. "
            "La entrega al cliente se habilitará únicamente después de validar la recepción."
        ) % {
            "source": self.supply_warehouse_id.display_name,
            "destination": self.warehouse_id.display_name,
        }
        self.message_post(body=audit)
        dispatch.message_post(body=audit)
        return dispatch.get_formview_action()

    def _release_after_transfer_receipt(self, receipt):
        for record in self.filtered(lambda item: item.state == "transfer_pending" and not item.picking_id):
            record.transfer_receipt_id = receipt
            requested = {line.product_id.id: line.quantity for line in record.line_ids}
            received = {}
            for move in receipt.move_ids.filtered(lambda item: item.state == "done"):
                received[move.product_id.id] = received.get(move.product_id.id, 0.0) + move.quantity
            if any(received.get(product_id, 0.0) < quantity for product_id, quantity in requested.items()):
                record.message_post(body=_("Recepción parcial registrada. La entrega al cliente continúa bloqueada hasta recibir toda la mercancía."))
                return False
            picking = record._create_customer_delivery()
            record.write({"picking_id": picking.id, "state": "ready"})
            audit = _(
                "Recepción %(receipt)s validada en %(warehouse)s. Se habilitó la entrega final %(delivery)s al cliente."
            ) % {
                "receipt": receipt.name,
                "warehouse": record.warehouse_id.display_name,
                "delivery": picking.name,
            }
            record.message_post(body=audit)
            receipt.message_post(body=audit)
            picking.message_post(body=audit)
        return True

    def action_open_operation(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("Esta entrega todavía no tiene una operación de salida."))
        if hasattr(self.picking_id, "action_ddmh_open_mobile"):
            return self.picking_id.action_ddmh_open_mobile()
        return {
            "type": "ir.actions.act_window",
            "name": self.picking_id.display_name,
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_transfer_dispatch(self):
        self.ensure_one()
        if not self.transfer_dispatch_id:
            raise UserError(_("Esta entrega todavía no tiene despacho entre almacenes."))
        return self.transfer_dispatch_id.get_formview_action()

    def action_open_transfer_receipt(self):
        self.ensure_one()
        receipt = self.transfer_receipt_id or self.transfer_dispatch_id.ddpc_transfer_receipt_picking_id
        if not receipt:
            raise UserError(_("La recepción se genera después de validar el despacho."))
        return receipt.get_formview_action()

    def action_sync_state(self):
        for record in self:
            if record.transfer_dispatch_id and record.transfer_dispatch_id.ddpc_transfer_receipt_picking_id:
                record.transfer_receipt_id = record.transfer_dispatch_id.ddpc_transfer_receipt_picking_id
            if record.picking_id.state == "done" and record.state != "done":
                record.state = "done"
            elif record.picking_id.state == "cancel" and record.state != "cancel":
                record.state = "cancel"
        return True


class DoorAndDoorHistoricalDeliveryLine(models.Model):
    _name = "doorandoor.historical.delivery.line"
    _description = "Producto de entrega histórica"
    _order = "id"

    delivery_id = fields.Many2one(
        "doorandoor.historical.delivery", required=True, ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product", string="Producto / variante", required=True,
        domain="[('is_storable', '=', True)]",
    )
    quantity = fields.Float(
        string="Cantidad", required=True, default=1.0,
        digits="Product Unit of Measure",
    )
    product_uom_id = fields.Many2one(
        "uom.uom", string="UdM", related="product_id.uom_id",
        store=True, readonly=True,
    )

    @api.constrains("quantity")
    def _check_quantity(self):
        if any(line.quantity <= 0 for line in self):
            raise ValidationError(_("La cantidad debe ser mayor que cero."))


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddpc_historical_delivery_ids = fields.One2many(
        "doorandoor.historical.delivery", "picking_id",
        string="Entregas históricas", readonly=True,
    )
