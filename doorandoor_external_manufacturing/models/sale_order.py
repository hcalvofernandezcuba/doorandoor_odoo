from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddem_external_order_ids = fields.One2many(
        "ddem.external.order", "sale_order_id", string="Pedidos externos"
    )
    ddem_external_order_count = fields.Integer(
        compute="_compute_ddem_external_order_count", string="Pedidos externos"
    )

    def _compute_ddem_external_order_count(self):
        for order in self:
            order.ddem_external_order_count = len(order.ddem_external_order_ids)

    def action_ddem_prepare_external_orders(self):
        self.ensure_one()
        eligible = self.order_line.filtered(
            lambda line: not line.display_type
            and line.product_id
            and line.product_uom_qty > 0
            and line.product_id.product_tmpl_id.ddem_supply_route in ("external", "subcontract")
        )
        if not eligible:
            raise UserError(_("La cotización no tiene productos configurados para fabricación externa o subcontratación."))
        existing_lines = self.ddem_external_order_ids.filtered(
            lambda request: request.state != "cancelled"
        ).line_ids.sale_line_id
        pending = eligible - existing_lines
        if not pending:
            return self.action_ddem_view_external_orders()
        grouped = {}
        for line in pending:
            template = line.product_id.product_tmpl_id
            if not template.ddem_primary_vendor_id:
                raise UserError(
                    _("Configure el proveedor principal en la plantilla de %s.")
                    % line.product_id.display_name
                )
            key = (
                template.ddem_primary_vendor_id.id,
                template.ddem_logistic_route,
                template.ddem_receipt_warehouse_id.id,
                template.ddem_supply_route,
            )
            grouped.setdefault(key, self.env["sale.order.line"])
            grouped[key] |= line
        created = self.env["ddem.external.order"]
        for (vendor_id, logistic_route, warehouse_id, supply_route), lines in grouped.items():
            template = lines[0].product_id.product_tmpl_id
            request = self.env["ddem.external.order"].create({
                "sale_order_id": self.id,
                "vendor_id": vendor_id,
                "supply_route": supply_route,
                "logistic_route": logistic_route,
                "warehouse_id": warehouse_id or self.warehouse_id.id,
                "min_payment_percent": max(lines.mapped("product_id.product_tmpl_id.ddem_min_payment_percent")),
                "min_margin_percent": max(lines.mapped("product_id.product_tmpl_id.ddem_min_margin_percent")),
                "manager_approval_required": any(lines.mapped("product_id.product_tmpl_id.ddem_requires_manager_approval")),
                "line_ids": [(0, 0, {"sale_line_id": line.id}) for line in lines],
            })
            created |= request
        self.message_post(body=_("Se prepararon %s pedido(s) de fabricación externa.") % len(created))
        return created[0].action_open_form() if len(created) == 1 else self.action_ddem_view_external_orders()

    def action_ddem_view_external_orders(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_external_manufacturing.action_ddem_external_order").read()[0]
        action["domain"] = [("sale_order_id", "=", self.id)]
        action["context"] = {"default_sale_order_id": self.id}
        return action
