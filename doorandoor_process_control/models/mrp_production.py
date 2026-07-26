from odoo import _, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    ddpc_process_flow_count = fields.Integer(compute="_compute_ddpc_process_flow_count")

    def _compute_ddpc_process_flow_count(self):
        flow_model = self.env["doorandoor.process.flow"]
        for production in self:
            production.ddpc_process_flow_count = flow_model.search_count([("mrp_production_id", "=", production.id)])

    def action_view_ddpc_process_flows(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_process_control.action_doorandoor_process_flow").read()[0]
        action["domain"] = [("mrp_production_id", "=", self.id)]
        action["context"] = {"default_mrp_production_id": self.id}
        return action

    def action_create_ddpc_process_flow(self):
        self.ensure_one()
        flow = self.env["doorandoor.process.flow"].create(
            {
                "mrp_production_id": self.id,
                "user_id": (getattr(self, "user_id", False) or self.env.user).id,
                "notes": _("Proceso creado manualmente desde manufactura."),
            }
        )
        return flow.get_formview_action()
