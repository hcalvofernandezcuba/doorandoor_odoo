from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.osv import expression


class DdmhDailyTask(models.Model):
    _name = "ddmh.daily.task"
    _description = "Trabajo diario de almacén"
    _auto = False
    _rec_name = "name"
    _order = "scheduled_date, id"

    name = fields.Char(string="Documento", readonly=True)
    task_type = fields.Selection(
        [("operation", "Operación"), ("count", "Conteo")],
        string="Tipo", readonly=True,
    )
    work_stage = fields.Selection(
        [
            ("dispatch", "Por despachar"),
            ("receipt", "Por recibir"),
            ("delivery", "Listo para entregar"),
            ("count", "Conteo asignado"),
            ("completed", "Procesos validados"),
        ],
        string="Trabajo", readonly=True,
        group_expand="_group_expand_work_stage",
    )
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén", readonly=True)
    destination_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén destino", readonly=True,
    )
    assigned_user_id = fields.Many2one("res.users", string="Asignado a", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente / Proveedor", readonly=True)
    reference = fields.Char(string="Referencia", readonly=True)
    summary = fields.Char(string="Contenido", readonly=True)
    total_units = fields.Float(string="Unidades", readonly=True)
    scheduled_date = fields.Datetime(string="Fecha", readonly=True)
    source_model = fields.Char(readonly=True)
    source_res_id = fields.Integer(readonly=True)
    hanger_state = fields.Selection(
        [
            ("pending", "Sin abrir"),
            ("waiting_scan", "Esperando lectura"),
            ("counting", "Leyendo"),
            ("attention", "Requiere atención"),
            ("review", "Pendiente de validación"),
            ("validated", "Validado"),
        ],
        string="Estado Hanger", readonly=True,
    )
    hanger_progress = fields.Char(string="Progreso Hanger", readonly=True)
    last_hanger_at = fields.Datetime(string="Última actividad", readonly=True)
    last_hanger_result = fields.Char(string="Último resultado", readonly=True)
    reserved_labels = fields.Char(string="Labels reservados", readonly=True)
    scanned_labels = fields.Char(string="Labels leídos", readonly=True)
    accepted_scan_count = fields.Integer(string="Lecturas positivas", readonly=True)
    failed_scan_count = fields.Integer(string="Lecturas negativas", readonly=True)

    @api.model
    def _group_expand_work_stage(self, stages, domain):
        visible_stages = ["dispatch", "receipt", "delivery", "count"]
        if self._ddmh_has_global_access():
            visible_stages.append("completed")
        return visible_stages

    @api.model
    def _ddmh_has_global_access(self):
        return (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("stock.group_stock_manager")
        )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self._ddmh_has_global_access():
            allowed_ids = self.env.user.ddpc_warehouse_ids.ids
            operational_domain = [
                ("warehouse_id", "in", allowed_ids or [0]),
                ("work_stage", "!=", "completed"),
                "|",
                ("task_type", "!=", "count"),
                ("assigned_user_id", "=", self.env.user.id),
            ]
            domain = expression.AND([domain, operational_domain])
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def action_open_task(self):
        self.ensure_one()
        if not self._ddmh_has_global_access():
            if self.warehouse_id not in self.env.user.ddpc_warehouse_ids:
                raise AccessError(_("Esta tarea no pertenece a uno de sus almacenes."))
            if self.task_type == "count" and self.assigned_user_id != self.env.user:
                raise AccessError(_("Esta sesión de conteo está asignada a otro usuario."))

        record = self.env[self.source_model].browse(self.source_res_id).exists()
        if not record:
            raise AccessError(_("El documento de esta tarea ya no está disponible."))
        record.check_access_rights("read")
        record.check_access_rule("read")

        if self.task_type == "operation":
            return record.action_ddmh_open_mobile()
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": "inventory.count.session",
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_monitor_task(self):
        """Open the source document from the unified support monitor."""
        self.ensure_one()
        if not self._ddmh_has_global_access():
            raise AccessError(_("Solo Inventario o Administración puede abrir el monitoreo global."))
        record = self.env[self.source_model].browse(self.source_res_id).exists()
        if not record:
            raise AccessError(_("El documento monitoreado ya no está disponible."))
        if self.task_type == "operation":
            action = self.env.ref(
                "doorandoor_mobile_hanger.action_ddmh_picking_monitor_form"
            ).sudo().read()[0]
            action.update({"name": record.display_name, "res_id": record.id})
            return action
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": "inventory.count.session",
            "res_id": record.id,
            "view_mode": "form",
            "view_id": self.env.ref(
                "doorandoor_mobile_hanger.view_inventory_count_session_form_ddmh_monitor"
            ).id,
            "target": "current",
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW ddmh_daily_task AS (
                SELECT
                    p.id * 2 AS id,
                    p.name AS name,
                    'operation'::varchar AS task_type,
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM inventory_serial_receipt recovery
                            WHERE recovery.picking_id = p.id
                              AND recovery.state IN ('draft', 'scanning', 'ready')
                        ) THEN 'receipt'
                        WHEN p.state = 'done'
                            THEN 'completed'
                        WHEN p.ddmh_work_stage IN ('dispatch', 'receipt', 'delivery', 'completed')
                            THEN p.ddmh_work_stage
                        ELSE 'dispatch'
                    END::varchar AS work_stage,
                    COALESCE(p.ddpc_source_warehouse_id, p.ddpc_dest_warehouse_id) AS warehouse_id,
                    p.ddpc_dest_warehouse_id AS destination_warehouse_id,
                    hanger_event.user_id AS assigned_user_id,
                    p.partner_id AS partner_id,
                    p.origin AS reference,
                    COALESCE((
                        SELECT string_agg(DISTINCT COALESCE(
                            pt.name->>'es_ES', pt.name->>'es_419', pt.name->>'en_US'
                        ), ', ')
                        FROM stock_move sm
                        JOIN product_product pp ON pp.id = sm.product_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        WHERE sm.picking_id = p.id AND sm.state != 'cancel'
                    ), '') AS summary,
                    COALESCE((
                        SELECT sum(sm.product_uom_qty)
                        FROM stock_move sm
                        WHERE sm.picking_id = p.id AND sm.state != 'cancel'
                    ), 0.0)::double precision AS total_units,
                    p.scheduled_date AS scheduled_date,
                    'stock.picking'::varchar AS source_model,
                    p.id AS source_res_id,
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM inventory_serial_receipt recovery
                            WHERE recovery.picking_id = p.id
                              AND recovery.state IN ('draft', 'scanning', 'ready')
                        ) AND hanger_event.status IN ('rejected', 'duplicate', 'no_input')
                            THEN 'attention'
                        WHEN EXISTS (
                            SELECT 1 FROM inventory_serial_receipt recovery
                            WHERE recovery.picking_id = p.id
                              AND recovery.state IN ('draft', 'scanning', 'ready')
                        ) AND hanger_event.status = 'accepted'
                            THEN 'counting'
                        WHEN EXISTS (
                            SELECT 1 FROM inventory_serial_receipt recovery
                            WHERE recovery.picking_id = p.id
                              AND recovery.state IN ('draft', 'scanning', 'ready')
                        ) THEN 'waiting_scan'
                        WHEN p.state = 'done' OR p.ddmh_validation_state = 'validated'
                            THEN 'validated'
                        WHEN p.ddmh_validation_state = 'review'
                            THEN 'review'
                        WHEN hanger_event.status IN ('rejected', 'duplicate', 'no_input')
                            THEN 'attention'
                        WHEN hanger_event.status = 'accepted'
                            THEN 'counting'
                        WHEN hanger_event.status = 'opened'
                            THEN 'waiting_scan'
                        ELSE 'pending'
                    END::varchar AS hanger_state,
                    CONCAT(
                        COALESCE((
                            SELECT NULLIF(count(*), 0)
                            FROM ddmh_picking_serial_scan scan_progress
                            WHERE scan_progress.picking_id = p.id
                        ), (
                            SELECT sum(rc.counted_qty)
                            FROM ddsl_stock_receipt_count rc
                            WHERE rc.picking_id = p.id
                        ), 0.0),
                        ' / ',
                        COALESCE((
                            SELECT sum(sm.product_uom_qty)
                            FROM stock_move sm
                            WHERE sm.picking_id = p.id AND sm.state != 'cancel'
                        ), 0.0)
                    )::varchar AS hanger_progress,
                    hanger_event.event_at AS last_hanger_at,
                    CASE
                        WHEN hanger_event.id IS NULL THEN 'Sin actividad registrada'
                        ELSE CONCAT(hanger_event.status, ': ', COALESCE(hanger_event.message, ''))
                    END::varchar AS last_hanger_result,
                    COALESCE((
                        SELECT string_agg(serial.code, ', ' ORDER BY serial.code)
                        FROM inventory_unit_serial serial
                        WHERE serial.reserved_picking_id = p.id AND serial.active
                    ), '')::varchar AS reserved_labels,
                    COALESCE((
                        SELECT string_agg(serial.code, ', ' ORDER BY scan.id)
                        FROM ddmh_picking_serial_scan scan
                        JOIN inventory_unit_serial serial ON serial.id = scan.serial_id
                        WHERE scan.picking_id = p.id
                    ), '')::varchar AS scanned_labels,
                    COALESCE((
                        SELECT count(*)
                        FROM ddmh_hanger_scan_event event
                        WHERE event.picking_id = p.id AND event.status = 'accepted'
                    ), 0)::integer AS accepted_scan_count,
                    COALESCE((
                        SELECT count(*)
                        FROM ddmh_hanger_scan_event event
                        WHERE event.picking_id = p.id
                          AND event.status IN ('rejected', 'duplicate', 'no_input')
                    ), 0)::integer AS failed_scan_count
                FROM stock_picking p
                LEFT JOIN LATERAL (
                    SELECT event.id, event.user_id, event.event_at,
                           event.status, event.message
                    FROM ddmh_hanger_scan_event event
                    WHERE event.picking_id = p.id
                    ORDER BY event.event_at DESC, event.id DESC
                    LIMIT 1
                ) hanger_event ON TRUE
                WHERE p.ddpc_operation_category IN ('receipt', 'delivery', 'factory_entry', 'transfer')
                  AND p.state != 'cancel'

                UNION ALL

                SELECT
                    s.id * 2 + 1 AS id,
                    s.name AS name,
                    'count'::varchar AS task_type,
                    CASE WHEN s.state = 'done'
                         THEN 'completed' ELSE 'count' END::varchar AS work_stage,
                    l.warehouse_id AS warehouse_id,
                    NULL::integer AS destination_warehouse_id,
                    s.user_id AS assigned_user_id,
                    NULL::integer AS partner_id,
                    COALESCE(s.load_reference, b.name) AS reference,
                    COALESCE(b.name, s.note, 'Sesión de conteo') AS summary,
                    0.0::double precision AS total_units,
                    s.date AS scheduled_date,
                    'inventory.count.session'::varchar AS source_model,
                    s.id AS source_res_id,
                    CASE WHEN s.state = 'done'
                         THEN 'validated' ELSE 'counting' END::varchar AS hanger_state,
                    NULL::varchar AS hanger_progress,
                    NULL::timestamp AS last_hanger_at,
                    CASE WHEN s.state = 'done'
                         THEN 'Sesión IC validada' ELSE 'Sesión IC en proceso' END::varchar AS last_hanger_result,
                    NULL::varchar AS reserved_labels,
                    NULL::varchar AS scanned_labels,
                    0::integer AS accepted_scan_count,
                    0::integer AS failed_scan_count
                FROM inventory_count_session s
                JOIN stock_location l ON l.id = s.location_id
                LEFT JOIN inventory_serial_label_batch b ON b.id = s.serial_batch_id
                WHERE s.state != 'cancel'
            )
        """)
