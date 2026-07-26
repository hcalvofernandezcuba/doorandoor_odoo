from odoo import _, fields, models


class DoorAndDoorProcessBackfillWizard(models.TransientModel):
    _name = "doorandoor.process.backfill.wizard"
    _description = "DoorAndDoor Process Backfill Wizard"

    include_sales = fields.Boolean(string="Include Sales", default=True)
    include_invoices = fields.Boolean(string="Include Invoices", default=True)
    include_manufacturing = fields.Boolean(string="Include Manufacturing Orders", default=True)
    include_pickings = fields.Boolean(string="Include Pickings", default=True)
    create_review_task = fields.Boolean(string="Create Review Task", default=True)
    per_model_limit = fields.Integer(string="Max Records Per Type", default=5, required=True)
    created_flow_count = fields.Integer(string="Created Flows", readonly=True)
    created_task_count = fields.Integer(string="Created Tasks", readonly=True)
    result_message = fields.Text(string="Result", readonly=True)

    def _prepare_flow_vals_from_sale(self, sale):
        return {
            "sale_order_id": sale.id,
            "partner_id": sale.partner_id.id,
            "user_id": sale.user_id.id or self.env.user.id,
            "state": "en_proceso" if sale.state in ("sale", "done") else "iniciado",
            "notes": _("Cargado historicamente desde venta existente."),
        }

    def _prepare_flow_vals_from_invoice(self, move):
        state = "en_proceso"
        if move.state == "posted" and move.payment_state in ("paid", "in_payment"):
            state = "entregado"
        return {
            "account_move_id": move.id,
            "sale_order_id": move.sale_order_id.id if "sale_order_id" in move._fields and move.sale_order_id else False,
            "partner_id": move.partner_id.id,
            "user_id": (move.invoice_user_id or self.env.user).id,
            "state": state,
            "notes": _("Cargado historicamente desde factura existente."),
        }

    def _prepare_flow_vals_from_mrp(self, production):
        return {
            "mrp_production_id": production.id,
            "user_id": (getattr(production, "user_id", False) or self.env.user).id,
            "state": "entregado" if production.state == "done" else "en_proceso",
            "notes": _("Cargado historicamente desde orden de manufactura existente."),
        }

    def _prepare_flow_vals_from_picking(self, picking):
        state = "en_proceso"
        if picking.state == "done":
            state = "cerrado" if picking.picking_type_code == "outgoing" else "entregado"
        return {
            "stock_picking_id": picking.id,
            "partner_id": picking.partner_id.id,
            "user_id": self.env.user.id,
            "state": state,
            "notes": _("Cargado historicamente desde picking existente."),
        }

    def _create_review_task_for_flow(self, flow, area):
        return self.env["doorandoor.process.task"].create(
            {
                "name": _("Revision historica - %s") % flow.name,
                "flow_id": flow.id,
                "area": area,
                "task_type": "revisar_venta",
                "user_id": flow.user_id.id or self.env.user.id,
                "state": flow.state if flow.state in ("iniciado", "en_proceso", "entregado", "en_ruta", "cerrado") else "iniciado",
                "notes": _("Tarea inicial creada para revisar la consistencia del proceso historico cargado."),
            }
        )

    def action_backfill(self):
        self.ensure_one()
        flow_model = self.env["doorandoor.process.flow"]
        created_flows = self.env["doorandoor.process.flow"]
        created_tasks = self.env["doorandoor.process.task"]
        limit = max(self.per_model_limit, 1)

        sale_existing_ids = set(flow_model.search([("sale_order_id", "!=", False)]).mapped("sale_order_id").ids)
        invoice_existing_ids = set(flow_model.search([("account_move_id", "!=", False)]).mapped("account_move_id").ids)
        mrp_existing_ids = set(flow_model.search([("mrp_production_id", "!=", False)]).mapped("mrp_production_id").ids)
        picking_existing_ids = set(flow_model.search([("stock_picking_id", "!=", False)]).mapped("stock_picking_id").ids)

        if self.include_sales:
            sales = self.env["sale.order"].search(
                [("state", "in", ("sale", "done")), ("id", "not in", list(sale_existing_ids))],
                order="id desc",
                limit=limit,
            )
            for sale in sales:
                flow = flow_model.create(self._prepare_flow_vals_from_sale(sale))
                created_flows |= flow
                if self.create_review_task:
                    created_tasks |= self._create_review_task_for_flow(flow, "ventas")

        if self.include_invoices:
            invoices = self.env["account.move"].search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("id", "not in", list(invoice_existing_ids)),
                ],
                order="id desc",
                limit=limit,
            )
            for move in invoices:
                flow = flow_model.create(self._prepare_flow_vals_from_invoice(move))
                created_flows |= flow
                if self.create_review_task:
                    created_tasks |= self._create_review_task_for_flow(flow, "facturacion")

        if self.include_manufacturing:
            productions = self.env["mrp.production"].search(
                [("state", "in", ("confirmed", "progress", "to_close", "done")), ("id", "not in", list(mrp_existing_ids))],
                order="id desc",
                limit=limit,
            )
            for production in productions:
                flow = flow_model.create(self._prepare_flow_vals_from_mrp(production))
                created_flows |= flow
                if self.create_review_task:
                    created_tasks |= self._create_review_task_for_flow(flow, "manufactura")

        if self.include_pickings:
            pickings = self.env["stock.picking"].search(
                [("state", "in", ("assigned", "confirmed", "done")), ("id", "not in", list(picking_existing_ids))],
                order="id desc",
                limit=limit,
            )
            for picking in pickings:
                flow = flow_model.create(self._prepare_flow_vals_from_picking(picking))
                created_flows |= flow
                if self.create_review_task:
                    created_tasks |= self._create_review_task_for_flow(flow, "almacen")

        self.write(
            {
                "created_flow_count": len(created_flows),
                "created_task_count": len(created_tasks),
                "result_message": _(
                    "Carga historica completada.\nProcesos creados: %(flows)s\nTareas creadas: %(tasks)s"
                )
                % {"flows": len(created_flows), "tasks": len(created_tasks)},
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.process.backfill.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
