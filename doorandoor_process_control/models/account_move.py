from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddpc_process_flow_count = fields.Integer(compute="_compute_ddpc_process_flow_count")

    def _compute_ddpc_process_flow_count(self):
        flow_model = self.env["doorandoor.process.flow"]
        for move in self:
            move.ddpc_process_flow_count = flow_model.search_count([("account_move_id", "=", move.id)])

    def action_view_ddpc_process_flows(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_process_control.action_doorandoor_process_flow").read()[0]
        action["domain"] = [("account_move_id", "=", self.id)]
        action["context"] = {"default_account_move_id": self.id, "default_partner_id": self.partner_id.id}
        return action

    def action_create_ddpc_process_flow(self):
        self.ensure_one()
        flow = self.env["doorandoor.process.flow"].create(
            {
                "account_move_id": self.id,
                "sale_order_id": getattr(self, "sale_order_id", False).id if "sale_order_id" in self._fields else False,
                "partner_id": self.partner_id.id,
                "user_id": (self.invoice_user_id or self.env.user).id,
                "notes": _("Proceso creado manualmente desde la factura."),
            }
        )
        return flow.get_formview_action()
