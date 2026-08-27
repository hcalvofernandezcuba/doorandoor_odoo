
from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddpc_process_flow_count = fields.Integer(compute="_compute_ddpc_process_flow_count")

    def _compute_ddpc_process_flow_count(self):
        flow_model = self.env["doorandoor.process.flow"]
        for order in self:
            order.ddpc_process_flow_count = flow_model.search_count([("sale_order_id", "=", order.id)])

    def action_view_ddpc_process_flows(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_process_control.action_doorandoor_process_flow").read()[0]
        action["domain"] = [("sale_order_id", "=", self.id)]
        action["context"] = {"default_sale_order_id": self.id, "default_partner_id": self.partner_id.id}
        return action

    def action_create_ddpc_process_flow(self):
        self.ensure_one()
        flow = self.env["doorandoor.process.flow"].create(
            {
                "sale_order_id": self.id,
                "partner_id": self.partner_id.id,
                "user_id": self.user_id.id or self.env.user.id,
                "notes": _("Proceso creado manualmente desde la venta."),
            }
        )
        return flow.get_formview_action()
