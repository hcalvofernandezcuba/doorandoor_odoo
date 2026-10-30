from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class DoorAndDoorLoadPlan(models.Model):
    _inherit = "doorandoor.load.plan"

    def _ddhl_check_historical_load_ready(self):
        Historical = self.env["doorandoor.historical.delivery"]
        for plan in self:
            problems = []
            for picking in plan.stop_ids.mapped("picking_ids"):
                histories = Historical.search([
                    "|",
                    ("transfer_dispatch_id", "=", picking.id),
                    ("picking_id", "=", picking.id),
                ])
                if not histories:
                    continue
                demand = sum(picking.move_ids.filtered(
                    lambda move: move.state != "cancel"
                ).mapped("product_uom_qty"))
                reserved = sum(picking.move_ids.filtered(
                    lambda move: move.state != "cancel"
                ).mapped("quantity"))
                rounding = picking.move_ids[:1].product_uom.rounding or 1.0
                if picking.state != "assigned" or float_compare(
                    reserved, demand, precision_rounding=rounding
                ) < 0:
                    problems.append(_(
                        "%(operation)s: reservado %(reserved).2f de %(demand).2f"
                    ) % {
                        "operation": picking.display_name,
                        "reserved": reserved,
                        "demand": demand,
                    })
                    continue
                if "ddmh_count_complete" in picking._fields and not picking.ddmh_count_complete:
                    problems.append(_(
                        "%s: falta completar el conteo Hanger."
                    ) % picking.display_name)
            if problems:
                raise UserError(_(
                    "La carga contiene operaciones históricas que todavía no están físicamente listas:\n%s"
                ) % "\n".join(problems))
        return True

    def action_mark_loaded(self):
        self._ddhl_check_historical_load_ready()
        return super().action_mark_loaded()
