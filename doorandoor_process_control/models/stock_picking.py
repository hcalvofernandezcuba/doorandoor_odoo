from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddpc_process_flow_count = fields.Integer(compute="_compute_ddpc_process_flow_count")

    def _compute_ddpc_process_flow_count(self):
        flow_model = self.env["doorandoor.process.flow"]
        for picking in self:
            picking.ddpc_process_flow_count = flow_model.search_count([("stock_picking_id", "=", picking.id)])

    def action_view_ddpc_process_flows(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_process_control.action_doorandoor_process_flow").read()[0]
        action["domain"] = [("stock_picking_id", "=", self.id)]
        action["context"] = {"default_stock_picking_id": self.id}
        return action

    def action_create_ddpc_process_flow(self):
        self.ensure_one()
        flow = self.env["doorandoor.process.flow"].create(
            {
                "stock_picking_id": self.id,
                "partner_id": self.partner_id.id,
                "user_id": self.env.user.id,
                "notes": _("Proceso creado manualmente desde picking."),
            }
        )
        return flow.get_formview_action()
