from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorAndDoorProcessFlow(models.Model):
    _name = "doorandoor.process.flow"
    _description = "DoorAndDoor Process Flow"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "write_date desc, id desc"

    name = fields.Char(
        string="Process Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", tracking=True)
    account_move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain="[('move_type', '=', 'out_invoice')]",
        tracking=True,
    )
    mrp_production_id = fields.Many2one("mrp.production", string="Manufacturing Order", tracking=True)
    stock_picking_id = fields.Many2one("stock.picking", string="Picking", tracking=True)
    pickup_order_id = fields.Many2one("doorandoor.pickup.order", string="Pickup Order", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", tracking=True)
    user_id = fields.Many2one("res.users", string="Current Responsible", tracking=True)
    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent")],
        default="1",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("iniciado", "Iniciado"),
            ("en_proceso", "En proceso"),
            ("entregado", "Entregado"),
            ("en_ruta", "En ruta"),
            ("cerrado", "Cerrado"),
        ],
        default="iniciado",
        required=True,
        tracking=True,
        index=True,
        group_expand="_group_expand_states",
    )
    due_datetime = fields.Datetime(string="Due Date")
    started_at = fields.Datetime(string="Started At", readonly=True)
    in_progress_at = fields.Datetime(string="In Progress At", readonly=True)
    delivered_at = fields.Datetime(string="Delivered At", readonly=True)
    en_route_at = fields.Datetime(string="En Route At", readonly=True)
    closed_at = fields.Datetime(string="Closed At", readonly=True)
    last_state_change_at = fields.Datetime(string="Last State Change", readonly=True)
    notes = fields.Text()
    task_ids = fields.One2many("doorandoor.process.task", "flow_id", string="Tasks")
    task_count = fields.Integer(compute="_compute_task_count")
    current_document_name = fields.Char(compute="_compute_current_document_name", string="Current Document")
    time_in_current_state_hours = fields.Float(compute="_compute_time_in_current_state_hours", string="Hours In State")
    semaphor_state = fields.Selection(
        [("red", "Red"), ("orange", "Orange"), ("green", "Green")],
        compute="_compute_semaphor_state",
        string="Semaphor",
    )
    semaphor_label = fields.Char(compute="_compute_semaphor_state", string="Semaphor Label")
    semaphor_color = fields.Char(compute="_compute_semaphor_state", string="Semaphor Color")

    @api.depends("task_ids")
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)

    @api.model
    def _group_expand_states(self, states, domain):
        return ["iniciado", "en_proceso", "entregado", "en_ruta", "cerrado"]

    @api.depends("sale_order_id", "account_move_id", "mrp_production_id", "stock_picking_id", "pickup_order_id")
    def _compute_current_document_name(self):
        for record in self:
            document = record.stock_picking_id or record.mrp_production_id or record.account_move_id or record.sale_order_id or record.pickup_order_id
            record.current_document_name = document.display_name if document else ""

    @api.depends("last_state_change_at")
    def _compute_time_in_current_state_hours(self):
        now = fields.Datetime.now()
        for record in self:
            if record.last_state_change_at:
                delta = now - record.last_state_change_at
                record.time_in_current_state_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                record.time_in_current_state_hours = 0.0

    @api.depends("state", "due_datetime", "closed_at", "company_id.ddpc_color_overdue", "company_id.ddpc_color_in_progress", "company_id.ddpc_color_done")
    def _compute_semaphor_state(self):
        now = fields.Datetime.now()
        for record in self:
            if record.state == "cerrado":
                record.semaphor_state = "green"
                record.semaphor_label = "Terminado"
                record.semaphor_color = record.company_id.ddpc_color_done or "#16a34a"
            elif record.due_datetime and record.due_datetime < now:
                record.semaphor_state = "red"
                record.semaphor_label = "Atrasado"
                record.semaphor_color = record.company_id.ddpc_color_overdue or "#dc2626"
            else:
                if record.state in ("entregado", "en_ruta"):
                    record.semaphor_state = "green"
                    record.semaphor_label = "Terminado"
                    record.semaphor_color = record.company_id.ddpc_color_done or "#16a34a"
                else:
                    record.semaphor_state = "orange"
                    record.semaphor_label = "En curso"
                    record.semaphor_color = record.company_id.ddpc_color_in_progress or "#ea580c"

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("doorandoor.process.flow") or _("New")
            self._sync_partner_from_links(vals)
            self._apply_state_timestamps(vals)
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals:
            vals = dict(vals)
            self._apply_state_timestamps(vals)
        self._sync_partner_from_links(vals)
        return super().write(vals)

    @api.model
    def _sync_partner_from_links(self, vals):
        if vals.get("partner_id"):
            return vals
        if vals.get("sale_order_id"):
            sale = self.env["sale.order"].browse(vals["sale_order_id"])
            vals["partner_id"] = sale.partner_id.id
        elif vals.get("account_move_id"):
            move = self.env["account.move"].browse(vals["account_move_id"])
            vals["partner_id"] = move.partner_id.id
        elif vals.get("pickup_order_id"):
            pickup = self.env["doorandoor.pickup.order"].browse(vals["pickup_order_id"])
            vals["partner_id"] = pickup.partner_id.id if "partner_id" in pickup._fields else False
        return vals

    @api.model
    def _apply_state_timestamps(self, vals):
        state = vals.get("state")
        if not state:
            return vals
        now = fields.Datetime.now()
        vals["last_state_change_at"] = now
        if state == "iniciado" and not vals.get("started_at"):
            vals["started_at"] = now
        elif state == "en_proceso":
            vals["in_progress_at"] = now
        elif state == "entregado":
            vals["delivered_at"] = now
        elif state == "en_ruta":
            vals["en_route_at"] = now
        elif state == "cerrado":
            vals["closed_at"] = now
        return vals

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_process_control.action_doorandoor_process_task").read()[0]
        action["domain"] = [("flow_id", "=", self.id)]
        action["context"] = {"default_flow_id": self.id}
        return action

    def action_mark_in_progress(self):
        self.write({"state": "en_proceso"})

    def action_mark_delivered(self):
        self.write({"state": "entregado"})

    def action_mark_en_route(self):
        self.write({"state": "en_ruta"})

    def action_mark_closed(self):
        self.write({"state": "cerrado"})

    def action_open_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("This process has no related sale order."))
        return self.sale_order_id.get_formview_action()

    def action_open_invoice(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_("This process has no related invoice."))
        return self.account_move_id.get_formview_action()

    def action_open_mrp_production(self):
        self.ensure_one()
        if not self.mrp_production_id:
            raise UserError(_("This process has no related manufacturing order."))
        return self.mrp_production_id.get_formview_action()

    def action_open_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            raise UserError(_("This process has no related picking."))
        return self.stock_picking_id.get_formview_action()
