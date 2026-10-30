from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockTransferRequest(models.Model):
    _name = "ddsn.stock.transfer.request"
    _description = "Solicitud logística de traslado por venta"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(default="Nuevo", readonly=True, copy=False)
    sale_order_id = fields.Many2one("sale.order", required=True, readonly=True, index=True)
    sale_line_id = fields.Many2one("sale.order.line", required=True, readonly=True, index=True)
    product_id = fields.Many2one("product.product", required=True, readonly=True)
    quantity = fields.Float(required=True, readonly=True)
    destination_warehouse_id = fields.Many2one("stock.warehouse", required=True, readonly=True)
    source_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén de origen",
        domain="[('company_id', '=', company_id), ('id', '!=', destination_warehouse_id)]",
        tracking=True,
    )
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    requested_by_id = fields.Many2one("res.users", required=True, readonly=True)
    picking_id = fields.Many2one("stock.picking", readonly=True, tracking=True)
    state = fields.Selection([
        ("pending", "Pendiente de Logística"), ("transferred", "Traslado creado"),
        ("done", "Recibido"), ("cancel", "Cancelado"),
    ], default="pending", required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("ddsn.stock.transfer.request") or "Nuevo"
        return super().create(vals_list)

    def action_create_transfer(self):
        if not (self.env.user.has_group("stock.group_stock_manager") or self.env.user.has_group("base.group_system")):
            raise ValidationError(_("Solo Logística o Administración/Ajustes puede decidir el almacén de origen."))
        for request in self:
            if request.state != "pending" or request.picking_id:
                raise ValidationError(_("La solicitud ya fue procesada."))
            source = request.source_warehouse_id
            target = request.destination_warehouse_id
            if not source:
                raise ValidationError(_("Seleccione el almacén de origen."))
            available = request.product_id.with_company(request.company_id).with_context(
                location=source.lot_stock_id.id
            ).qty_available
            if available < request.quantity:
                raise ValidationError(_("El almacén seleccionado no tiene existencia suficiente."))
            picking = self.env["stock.picking"].create({
                "picking_type_id": source.int_type_id.id,
                "location_id": source.lot_stock_id.id,
                "location_dest_id": target.lot_stock_id.id,
                "origin": _("Solicitud %(request)s / venta %(sale)s") % {"request": request.name, "sale": request.sale_order_id.name},
                "move_ids": [(0, 0, {
                    "name": request.product_id.display_name,
                    "product_id": request.product_id.id,
                    "product_uom_qty": request.quantity,
                    "product_uom": request.product_id.uom_id.id,
                    "location_id": source.lot_stock_id.id,
                    "location_dest_id": target.lot_stock_id.id,
                })],
            })
            picking.action_confirm()
            picking.action_assign()
            request.write({"picking_id": picking.id, "state": "transferred"})
            body = _("Logística creó el traslado %(picking)s desde %(source)s hacia %(target)s.") % {
                "picking": picking.name, "source": source.display_name, "target": target.display_name,
            }
            request.message_post(body=body)
            request.sale_order_id.message_post(body=body)
        return True

    def action_open_picking(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "stock.picking", "view_mode": "form", "res_id": self.picking_id.id}
