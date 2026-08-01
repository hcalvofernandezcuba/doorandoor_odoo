from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorAndDoorProcessTask(models.Model):
    _name = "doorandoor.process.task"
    _description = "DoorAndDoor Process Task"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, write_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    flow_id = fields.Many2one("doorandoor.process.flow", string="Process", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="flow_id.company_id", store=True, index=True)
    user_id = fields.Many2one("res.users", string="Assigned To", tracking=True)
    area = fields.Selection(
        [
            ("ventas", "Ventas"),
            ("facturacion", "Facturacion / Caja"),
            ("manufactura", "Manufactura"),
            ("almacen", "Almacen / Inventario"),
            ("control", "Control de procesos"),
            ("gerencia", "Gerencia"),
            ("delivery", "Delivery"),
        ],
        required=True,
        default="control",
        tracking=True,
    )
    task_type = fields.Selection(
        [
            ("revisar_venta", "Revisar venta"),
            ("confirmar_direccion_entrega", "Confirmar direccion entrega"),
            ("emitir_prefactura_o_factura", "Emitir prefactura o factura"),
            ("registrar_pago", "Registrar pago"),
            ("liberar_fabricacion", "Liberar fabricacion"),
            ("liberar_despacho", "Liberar despacho"),
            ("iniciar_manufactura", "Iniciar manufactura"),
            ("imprimir_label_produccion", "Imprimir label produccion"),
            ("cerrar_manufactura", "Cerrar manufactura"),
            ("crear_transferencia_interna", "Crear transferencia interna"),
            ("validar_transferencia_interna", "Validar transferencia interna"),
            ("preparar_picking", "Preparar picking"),
            ("imprimir_label_factura", "Imprimir label factura"),
            ("validar_despacho", "Validar despacho"),
            ("registrar_entrega", "Registrar entrega"),
            ("cerrar_proceso", "Cerrar proceso"),
        ],
        required=True,
        default="revisar_venta",
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
    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent")],
        default="1",
        tracking=True,
    )
    sale_order_id = fields.Many2one(related="flow_id.sale_order_id", store=True, readonly=True)
    account_move_id = fields.Many2one(related="flow_id.account_move_id", store=True, readonly=True)
    mrp_production_id = fields.Many2one(related="flow_id.mrp_production_id", store=True, readonly=True)
    stock_picking_id = fields.Many2one(related="flow_id.stock_picking_id", store=True, readonly=True)
    partner_id = fields.Many2one(related="flow_id.partner_id", store=True, readonly=True)
    due_datetime = fields.Datetime(string="Due Date")
    started_at = fields.Datetime(string="Started At", readonly=True)
    in_progress_at = fields.Datetime(string="In Progress At", readonly=True)
    delivered_at = fields.Datetime(string="Delivered At", readonly=True)
    en_route_at = fields.Datetime(string="En Route At", readonly=True)
    closed_at = fields.Datetime(string="Closed At", readonly=True)
    last_state_change_at = fields.Datetime(string="Last State Change", readonly=True)
    notes = fields.Text()
    time_in_current_state_hours = fields.Float(compute="_compute_time_in_current_state_hours", string="Hours In State")
    semaphor_state = fields.Selection(
        [("red", "Red"), ("orange", "Orange"), ("green", "Green")],
        compute="_compute_semaphor_state",
        string="Semaphor",
    )
    semaphor_label = fields.Char(compute="_compute_semaphor_state", string="Semaphor Label")
    semaphor_color = fields.Char(compute="_compute_semaphor_state", string="Semaphor Color")

    @api.depends("last_state_change_at")
    def _compute_time_in_current_state_hours(self):
        now = fields.Datetime.now()
        for record in self:
            if record.last_state_change_at:
                delta = now - record.last_state_change_at
                record.time_in_current_state_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                record.time_in_current_state_hours = 0.0

    @api.model
    def _group_expand_states(self, states, domain):
        return ["iniciado", "en_proceso", "entregado", "en_ruta", "cerrado"]

    @api.depends("state", "due_datetime", "company_id.ddpc_color_overdue", "company_id.ddpc_color_in_progress", "company_id.ddpc_color_done")
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
        for vals in vals_list:
            self._apply_state_timestamps(vals)
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals:
            vals = dict(vals)
            self._apply_state_timestamps(vals)
        result = super().write(vals)
        if "state" in vals:
            for task in self:
                if task.flow_id and task.flow_id.state != task.state and task.state in ("en_proceso", "entregado", "en_ruta", "cerrado"):
                    task.flow_id.write({"state": task.state, "user_id": task.user_id.id or self.env.user.id})
        return result

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
            raise UserError(_("This task has no related sale order."))
        return self.sale_order_id.get_formview_action()

    def action_open_invoice(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_("This task has no related invoice."))
        return self.account_move_id.get_formview_action()

    def action_open_mrp_production(self):
        self.ensure_one()
        if not self.mrp_production_id:
            raise UserError(_("This task has no related manufacturing order."))
        return self.mrp_production_id.get_formview_action()

    def action_open_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            raise UserError(_("This task has no related picking."))
        return self.stock_picking_id.get_formview_action()

    def action_print_invoice_labels(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_("This task has no related invoice for labels."))
        return self.account_move_id.action_open_ddsl_document_label_wizard()

    def action_print_mrp_labels(self):
        self.ensure_one()
        if not self.mrp_production_id:
            raise UserError(_("This task has no related manufacturing order for labels."))
        return self.mrp_production_id.action_open_ddsl_document_label_wizard()
