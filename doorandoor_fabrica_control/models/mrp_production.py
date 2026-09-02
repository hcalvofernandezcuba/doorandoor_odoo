from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    ddfc_requesting_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén solicitante",
        compute="_compute_ddfc_requesting_warehouse_id",
        store=True,
        index=True,
        help=(
            "Almacén que necesita el producto fabricado. Se toma primero del "
            "almacén de entrega, luego del almacén origen y finalmente de la "
            "operación de fabricación."
        ),
    )
    ddfc_daily_plan_id = fields.Many2one(
        "ddfc.daily.plan", string="Plan diario", readonly=True, copy=False, index=True
    )
    ddfc_source_need_id = fields.Many2one(
        "ddfc.production.need", string="Necesidad origen", readonly=True, copy=False, index=True
    )
    ddfc_source_invoice_id = fields.Many2one(
        "account.move", string="Factura origen", readonly=True, copy=False, index=True
    )
    ddfc_machining_handoff_ids = fields.One2many(
        "ddfc.machining.handoff", "production_id", string="Entregas Maquinado a Ensamblaje"
    )
    ddfc_machining_handoff_count = fields.Integer(
        string="Entregas a Ensamblaje", compute="_compute_ddfc_machining_handoff_count"
    )

    @api.depends("ddfc_machining_handoff_ids")
    def _compute_ddfc_machining_handoff_count(self):
        for production in self:
            production.ddfc_machining_handoff_count = len(production.ddfc_machining_handoff_ids)

    def action_open_ddfc_machining_handoffs(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_fabrica_control.action_ddfc_machining_handoff").read()[0]
        action["domain"] = [("production_id", "=", self.id)]
        action["context"] = {"default_production_id": self.id}
        return action

    @api.depends(
        "ddpa_delivery_warehouse_id",
        "ddpa_origin_warehouse_id",
        "picking_type_id",
        "picking_type_id.warehouse_id",
    )
    def _compute_ddfc_requesting_warehouse_id(self):
        for production in self:
            production.ddfc_requesting_warehouse_id = (
                production.ddpa_delivery_warehouse_id
                or production.ddpa_origin_warehouse_id
                or production.picking_type_id.warehouse_id
            )
