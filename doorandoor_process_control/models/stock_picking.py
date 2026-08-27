from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddpc_process_flow_count = fields.Integer(compute="_compute_ddpc_process_flow_count")
    ddpc_source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacen de inicio",
        compute="_compute_ddpc_warehouses",
        store=True,
        readonly=True,
    )
    ddpc_dest_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacen de destino",
        compute="_compute_ddpc_warehouses",
        store=True,
        readonly=True,
    )
    ddpc_operation_category = fields.Selection(
        [
            ("receipt", "Recepcion"),
            ("delivery", "Entrega"),
            ("factory_entry", "Entrada de fabrica"),
            ("transfer", "Traslado"),
            ("other", "Otra operacion"),
        ],
        string="Operacion DoorAndDoor",
        compute="_compute_ddpc_operation_category",
        store=True,
        index=True,
    )
    ddpc_transfer_alert_active = fields.Boolean(
        string="Alerta de recepcion activa", copy=False, readonly=True
    )
    ddpc_transfer_last_alert_at = fields.Datetime(
        string="Ultimo aviso de recepcion", copy=False, readonly=True
    )
    ddpc_transfer_next_alert_at = fields.Datetime(
        string="Proximo aviso de recepcion", copy=False, readonly=True, index=True
    )
    ddpc_transfer_stage = fields.Selection(
        [("dispatch", "Despacho de traslado"), ("receipt", "Recepcion de traslado")],
        string="Etapa del traslado",
        copy=True,
        readonly=True,
        index=True,
    )
    ddpc_transfer_target_location_id = fields.Many2one(
        "stock.location",
        string="Destino final del traslado",
        copy=True,
        readonly=True,
    )
    ddpc_transfer_origin_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacen que despacho",
        copy=True,
        readonly=True,
    )
    ddpc_transfer_source_picking_id = fields.Many2one(
        "stock.picking",
        string="Despacho origen",
        copy=False,
        readonly=True,
        index=True,
    )
    ddpc_transfer_receipt_picking_id = fields.Many2one(
        "stock.picking",
        string="Recepcion destino",
        copy=False,
        readonly=True,
        index=True,
    )
    ddpc_realtime_status = fields.Text(
        string="Estado en Tiempo Real",
        compute="_compute_ddpc_realtime_status",
        store=False,
        help="Estado descriptivo del picking para actualización en tiempo real"
    )
    ddpc_last_activity_timestamp = fields.Datetime(
        string="Última Actividad",
        compute="_compute_ddpc_realtime_status",
        store=False,
        help="Timestamp de la última actividad relevante para actualizaciones en tiempo real"
    )

    @api.depends(
        "location_id.warehouse_id",
        "location_dest_id.warehouse_id",
        "ddpc_transfer_stage",
        "ddpc_transfer_origin_warehouse_id",
        "ddpc_transfer_target_location_id.warehouse_id",
    )
    def _compute_ddpc_warehouses(self):
        for picking in self:
            picking.ddpc_source_warehouse_id = (
                picking.ddpc_transfer_origin_warehouse_id
                or picking.location_id.warehouse_id
            )
            picking.ddpc_dest_warehouse_id = (
                picking.ddpc_transfer_target_location_id.warehouse_id
                if picking.ddpc_transfer_stage == "dispatch"
                else picking.location_dest_id.warehouse_id
            )

    @api.depends(
        "picking_type_code",
        "location_id.usage",
        "location_dest_id.usage",
        "ddpc_source_warehouse_id",
        "ddpc_dest_warehouse_id",
        "ddpc_transfer_stage",
        "ddpc_transfer_target_location_id.warehouse_id",
    )
    def _compute_ddpc_operation_category(self):
        for picking in self:
            if (
                picking.location_id.usage == "production"
                and picking.ddpc_dest_warehouse_id
            ):
                category = "factory_entry"
            elif picking.ddpc_transfer_stage == "dispatch":
                category = "transfer"
            elif (
                picking.location_id.usage == "internal"
                and picking.location_dest_id.usage == "internal"
                and picking.ddpc_source_warehouse_id
                and picking.ddpc_dest_warehouse_id
                and picking.ddpc_source_warehouse_id != picking.ddpc_dest_warehouse_id
            ):
                category = "transfer"
            elif picking.picking_type_code == "incoming":
                category = "receipt"
            elif picking.picking_type_code == "outgoing":
                category = "delivery"
            else:
                category = "other"
            picking.ddpc_operation_category = category

    @api.depends(
        "ddpc_transfer_stage",
        "state",
        "write_date",
        "move_ids.state",
    )
    def _compute_ddpc_realtime_status(self):
        """
        Calcula el estado descriptivo y timestamp para actualizaciones en tiempo real.
        Este campo computado permite que las vistas se actualicen automáticamente cuando
        cambian los estados relevantes del picking.
        """
        for picking in self:
            if picking.ddpc_transfer_stage == "dispatch":
                if picking.state == "done":
                    picking.ddpc_realtime_status = "En tránsito hacia {}".format(
                        picking.ddpc_dest_warehouse_id.display_name if picking.ddpc_dest_warehouse_id else "destino"
                    )
                else:
                    picking.ddpc_realtime_status = "Preparando despacho"
            elif picking.ddpc_transfer_stage == "receipt":
                if picking.state == "done":
                    picking.ddpc_realtime_status = "Recepción completada"
                else:
                    picking.ddpc_realtime_status = "Pendiente de recepción física en {}".format(
                        picking.ddpc_dest_warehouse_id.display_name if picking.ddpc_dest_warehouse_id else "almacén destino"
                    )
            else:
                picking.ddpc_realtime_status = picking.state
            
            picking.ddpc_last_activity_timestamp = picking.write_date

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings._ddpc_sync_transfer_receipt_alerts(first_notice=True)
        return pickings

    def write(self, vals):
        result = super().write(vals)
        if {"state", "location_id", "location_dest_id", "picking_type_id"}.intersection(vals):
            self._ddpc_sync_transfer_receipt_alerts(first_notice=False)
        return result

    def _ddpc_transfer_alert_users(self):
        self.ensure_one()
        users = self.ddpc_dest_warehouse_id.ddpc_operator_user_ids.filtered("active")
        if not users and self.user_id:
            users = self.user_id
        if not users:
            users = self.env.ref(
                "doorandoor_process_control.group_ddpc_manager"
            ).users.filtered("active")
        return users

    def _ddpc_broadcast_picking_update(self, event_type, extra_data=None):
        """
        Envía actualización en tiempo real a usuarios del almacén destino usando bus.bus
        para permitir actualización automática de vistas de recepciones.
        """
        self.ensure_one()
        target_users = self._ddpc_transfer_alert_users()
        message = {
            'type': 'picking_update',
            'event': event_type,
            'picking_id': self.id,
            'picking_name': self.name,
            'stage': self.ddpc_transfer_stage,
            'state': self.state,
            'source_warehouse': self.ddpc_source_warehouse_id.display_name if self.ddpc_source_warehouse_id else '',
            'dest_warehouse': self.ddpc_dest_warehouse_id.display_name if self.ddpc_dest_warehouse_id else '',
            'timestamp': fields.Datetime.now().isoformat(),
            **(extra_data or {})
        }
        for user in target_users:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'doorandoor.picking.update',
                message
            )

    def _ddpc_close_transfer_receipt_alerts(self):
        activity_type = self.env.ref(
            "doorandoor_process_control.mail_activity_type_transfer_receipt",
            raise_if_not_found=False,
        )
        for picking in self:
            if activity_type:
                picking.activity_ids.filtered(
                    lambda activity: activity.activity_type_id == activity_type
                ).sudo().unlink()
            picking.with_context(ddpc_skip_alert_sync=True).write(
                {
                    "ddpc_transfer_alert_active": False,
                    "ddpc_transfer_next_alert_at": False,
                }
            )

    def _ddpc_sync_transfer_receipt_alerts(self, first_notice=False):
        if self.env.context.get("ddpc_skip_alert_sync"):
            return True
        activity_type = self.env.ref(
            "doorandoor_process_control.mail_activity_type_transfer_receipt",
            raise_if_not_found=False,
        )
        now = fields.Datetime.now()
        for picking in self:
            active = (
                picking.ddpc_transfer_stage == "receipt"
                and picking.state not in ("done", "cancel")
                and picking.ddpc_dest_warehouse_id
            )
            if not active:
                picking._ddpc_close_transfer_receipt_alerts()
                continue
            interval = max(picking.company_id.ddpc_transfer_alert_interval_hours or 4, 1)
            users = picking._ddpc_transfer_alert_users()
            if activity_type:
                existing_by_user = {
                    activity.user_id.id: activity
                    for activity in picking.activity_ids.filtered(
                        lambda activity: activity.activity_type_id == activity_type
                    )
                }
                for user in users:
                    if user.id not in existing_by_user:
                        picking.activity_schedule(
                            activity_type_id=activity_type.id,
                            user_id=user.id,
                            date_deadline=fields.Date.context_today(picking),
                            summary=_("Recibir traslado %s") % picking.name,
                            note=_(
                                "Mercancia pendiente de recibir desde %s hacia %s."
                            )
                            % (
                                picking.ddpc_source_warehouse_id.display_name,
                                picking.ddpc_dest_warehouse_id.display_name,
                            ),
                        )
            if first_notice or not picking.ddpc_transfer_alert_active:
                picking.message_post(
                    body=_(
                        "Recepcion de traslado pendiente en %s. Se enviaran recordatorios hasta validar la llegada."
                    )
                    % picking.ddpc_dest_warehouse_id.display_name,
                    subtype_xmlid="mail.mt_note",
                )
            picking.with_context(ddpc_skip_alert_sync=True).write(
                {
                    "ddpc_transfer_alert_active": True,
                    "ddpc_transfer_last_alert_at": now if first_notice else picking.ddpc_transfer_last_alert_at,
                    "ddpc_transfer_next_alert_at": now + timedelta(hours=interval),
                }
            )
        return True

    @api.model
    def _cron_ddpc_transfer_receipt_alerts(self):
        now = fields.Datetime.now()
        pickings = self.sudo().search(
            [
                ("ddpc_transfer_stage", "=", "receipt"),
                ("state", "not in", ("done", "cancel")),
                "|",
                ("ddpc_transfer_next_alert_at", "=", False),
                ("ddpc_transfer_next_alert_at", "<=", now),
            ]
        )
        for picking in pickings:
            interval = max(picking.company_id.ddpc_transfer_alert_interval_hours or 4, 1)
            overdue_hours = max(picking.company_id.ddpc_transfer_overdue_hours or 24, interval)
            overdue = bool(
                picking.scheduled_date
                and now > picking.scheduled_date + timedelta(hours=overdue_hours)
            )
            title = _("Traslado vencido") if overdue else _("Recepcion de traslado pendiente")
            message = _("El traslado %s sigue pendiente de recepción en %s.") % (
                picking.name,
                picking.ddpc_dest_warehouse_id.display_name,
            )
            for user in picking._ddpc_transfer_alert_users():
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "simple_notification",
                    {
                        "title": title,
                        "message": message,
                        "type": "danger" if overdue else "warning",
                        "sticky": overdue,
                    },
                )
            picking.with_context(ddpc_skip_alert_sync=True).write(
                {
                    "ddpc_transfer_alert_active": True,
                    "ddpc_transfer_last_alert_at": now,
                    "ddpc_transfer_next_alert_at": now + timedelta(hours=interval),
                }
            )
        return len(pickings)

    @api.model
    def _ddpc_get_transfer_transit_location(self, company):
        location = company.ddpc_transfer_transit_location_id
        if location:
            return location
        location = self.env["stock.location"].search(
            [
                ("usage", "=", "transit"),
                ("company_id", "=", company.id),
                ("name", "=", "DoorAndDoor - Mercancia en transito"),
            ],
            limit=1,
        )
        if not location:
            location = self.env["stock.location"].create(
                {
                    "name": "DoorAndDoor - Mercancia en transito",
                    "usage": "transit",
                    "company_id": company.id,
                }
            )
        company.ddpc_transfer_transit_location_id = location
        return location

    def _ddpc_prepare_cross_warehouse_dispatch(self):
        """Route a direct cross-warehouse transfer through a transit location."""
        for picking in self:
            if picking.ddpc_transfer_stage == "receipt":
                continue
            source_warehouse = picking.location_id.warehouse_id
            target_location = picking.ddpc_transfer_target_location_id or picking.location_dest_id
            target_warehouse = target_location.warehouse_id
            is_cross_warehouse = bool(
                picking.picking_type_code == "internal"
                and source_warehouse
                and target_warehouse
                and source_warehouse != target_warehouse
            )
            if not is_cross_warehouse and picking.ddpc_transfer_stage != "dispatch":
                continue
            transit = picking._ddpc_get_transfer_transit_location(picking.company_id)
            values = {
                "ddpc_transfer_stage": "dispatch",
                "ddpc_transfer_target_location_id": target_location.id,
                "ddpc_transfer_origin_warehouse_id": source_warehouse.id,
            }
            if picking.location_dest_id != transit:
                values["location_dest_id"] = transit.id
            picking.with_context(ddpc_skip_alert_sync=True).write(values)
            open_moves = picking.move_ids.filtered(
                lambda move: move.state not in ("done", "cancel")
            )
            open_moves.write({"location_dest_id": transit.id})
            open_moves.mapped("move_line_ids").write({"location_dest_id": transit.id})

    def _ddpc_create_destination_receipt(self):
        for dispatch in self.filtered(
            lambda picking: picking.state == "done"
            and picking.ddpc_transfer_stage == "dispatch"
            and picking.ddpc_transfer_target_location_id
        ):
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)", (77102, dispatch.id)
            )
            dispatch.invalidate_recordset(["ddpc_transfer_receipt_picking_id"])
            if dispatch.ddpc_transfer_receipt_picking_id:
                continue
            target_location = dispatch.ddpc_transfer_target_location_id
            target_warehouse = target_location.warehouse_id
            picking_type = target_warehouse.in_type_id
            if not picking_type:
                picking_type = self.env["stock.picking.type"].search(
                    [
                        ("warehouse_id", "=", target_warehouse.id),
                        ("code", "=", "incoming"),
                    ],
                    limit=1,
                )
            done_moves = dispatch.move_ids.filtered(
                lambda move: move.state == "done" and move.quantity > 0
            )
            if not picking_type or not done_moves:
                continue
            receipt = self.create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": dispatch.location_dest_id.id,
                    "location_dest_id": target_location.id,
                    "origin": _("Recepcion de %s") % dispatch.name,
                    "scheduled_date": fields.Datetime.now(),
                    "company_id": dispatch.company_id.id,
                    "user_id": False,
                    "ddpc_transfer_stage": "receipt",
                    "ddpc_transfer_source_picking_id": dispatch.id,
                    "ddpc_transfer_target_location_id": target_location.id,
                    "ddpc_transfer_origin_warehouse_id": dispatch.ddpc_source_warehouse_id.id,
                }
            )
            for move in done_moves:
                self.env["stock.move"].create(
                    {
                        "name": move.name,
                        "product_id": move.product_id.id,
                        "product_uom_qty": move.quantity,
                        "product_uom": move.product_uom.id,
                        "location_id": dispatch.location_dest_id.id,
                        "location_dest_id": target_location.id,
                        "picking_id": receipt.id,
                        "company_id": dispatch.company_id.id,
                        "origin": dispatch.name,
                        "move_orig_ids": [(4, move.id)],
                    }
                )
            receipt.action_confirm()
            dispatch.with_context(ddpc_skip_alert_sync=True).write(
                {"ddpc_transfer_receipt_picking_id": receipt.id}
            )
            receipt._ddpc_sync_transfer_receipt_alerts(first_notice=True)
            dispatch.message_post(
                body=Markup(
                    "%s <a href='#' data-oe-model='stock.picking' "
                    "data-oe-id='%s'>%s</a> %s"
                )
                % (
                    _("Despacho validado hacia transito. Se genero la recepcion"),
                    receipt.id,
                    receipt.name,
                    _("para el almacen %s.") % target_warehouse.display_name,
                ),
                subtype_xmlid="mail.mt_note",
            )
            receipt.message_post(
                body=_(
                    "Mercancia despachada desde %s y pendiente de confirmacion fisica en %s."
                )
                % (
                    dispatch.ddpc_source_warehouse_id.display_name,
                    target_warehouse.display_name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def _action_done(self):
        self._ddpc_prepare_cross_warehouse_dispatch()
        result = super()._action_done()
        
        # Broadcast actualización en tiempo real para traslados despachados
        for picking in self.filtered(lambda p: p.ddpc_transfer_stage == 'dispatch'):
            picking._ddpc_broadcast_picking_update('transfer_dispatched', {
                'location_dest': picking.location_dest_id.display_name,
                'move_count': len(picking.move_ids.filtered(lambda m: m.state == 'done'))
            })
        
        self._ddpc_create_destination_receipt()
        self._ddpc_sync_transfer_receipt_alerts(first_notice=False)
        return result

    def button_validate(self):
        result = super().button_validate()
        
        # Broadcast cuando se valida la recepción de un traslado
        for picking in self.filtered(lambda p: p.ddpc_transfer_stage == 'receipt' and p.state == 'done'):
            picking._ddpc_broadcast_picking_update('transfer_received', {
                'validated_by': self.env.user.display_name,
                'validation_timestamp': fields.Datetime.now().isoformat()
            })
        
        return result

    def action_ddpc_open_transfer_receipt(self):
        self.ensure_one()
        return self.ddpc_transfer_receipt_picking_id.get_formview_action()

    def action_ddpc_open_transfer_dispatch(self):
        self.ensure_one()
        return self.ddpc_transfer_source_picking_id.get_formview_action()

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
