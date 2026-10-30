# -*- coding: utf-8 -*-

from urllib.parse import quote_plus

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorandoorLoadPlan(models.Model):
    _name = "doorandoor.load.plan"
    _description = "DoorAndDoor Load and Route Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_departure desc, id desc"

    name = fields.Char(
        string="Referencia",
        default=lambda self: _("Nuevo"),
        readonly=True,
        copy=False,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("route_ready", "Ruta preparada"),
            ("loading", "Preparando carga"),
            ("loaded", "Carga verificada"),
            ("in_transit", "En tránsito"),
            ("partial_unload", "Descarga parcial"),
            ("done", "Completado"),
            ("incident", "En incidencia"),
            ("cancel", "Cancelado"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    origin_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén de origen",
        required=True,
        tracking=True,
        check_company=True,
    )
    scheduled_departure = fields.Datetime(
        string="Salida prevista",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    actual_departure = fields.Datetime(string="Salida real", readonly=True, tracking=True)
    actual_arrival = fields.Datetime(string="Cierre real", readonly=True, tracking=True)
    vehicle_name = fields.Char(string="Camión / vehículo", required=True, tracking=True)
    license_plate = fields.Char(string="Matrícula", tracking=True)
    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle", string="Camión de flota", tracking=True, check_company=True,
        domain="[('ddcc_available_for_loads', '=', True)]",
    )
    driver_id = fields.Many2one("res.users", string="Chofer", tracking=True)
    driver_profile_id = fields.Many2one(
        "doorandoor.driver.profile", string="Perfil de chofer", tracking=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    origin_address = fields.Char(
        string="Dirección logística de salida", required=True, tracking=True
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsable de carga",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    route_mode = fields.Selection(
        [("manual", "Manual"), ("google", "Recomendada por Google")],
        string="Modo de ruta",
        default="manual",
        required=True,
        tracking=True,
    )
    simulation_mode = fields.Boolean(
        string="Ruta de simulación",
        tracking=True,
        help="Permite probar la planificación sin documentos reales de inventario.",
    )
    stop_ids = fields.One2many(
        "doorandoor.load.plan.stop", "plan_id", string="Paradas", copy=True
    )
    crew_ids = fields.One2many(
        "doorandoor.load.plan.crew", "plan_id", string="Tripulación", copy=True
    )
    trip_control_ids = fields.One2many(
        "doorandoor.load.trip.control", "plan_id", string="Controles de viaje", copy=False
    )
    odometer_start = fields.Float(compute="_compute_trip_metrics", string="Odómetro inicial")
    odometer_end = fields.Float(compute="_compute_trip_metrics", string="Odómetro final")
    distance_traveled = fields.Float(compute="_compute_trip_metrics", string="Distancia recorrida")
    fuel_added = fields.Float(compute="_compute_trip_metrics", string="Combustible cargado")
    fuel_used = fields.Float(compute="_compute_trip_metrics", string="Combustible consumido")
    fuel_efficiency = fields.Float(compute="_compute_trip_metrics", string="Rendimiento")
    stop_count = fields.Integer(compute="_compute_totals", string="Paradas")
    picking_count = fields.Integer(compute="_compute_totals", string="Documentos")
    total_units = fields.Float(compute="_compute_totals", string="Unidades previstas")
    last_checkpoint_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Último punto confirmado", readonly=True, tracking=True
    )
    last_checkpoint_at = fields.Datetime(
        string="Hora del último punto", readonly=True, tracking=True
    )
    next_stop_id = fields.Many2one(
        "doorandoor.load.plan.stop", string="Próxima parada", compute="_compute_next_stop"
    )
    google_maps_url = fields.Char(
        string="Ruta en Google Maps", compute="_compute_google_maps_url"
    )
    notes = fields.Html(string="Observaciones")

    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name, company_id)",
            "La referencia del plan debe ser única por compañía.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "doorandoor.load.plan"
                ) or _("Nuevo")
        return super().create(vals_list)

    def _warehouse_logistic_address(self, warehouse):
        if warehouse.ddcc_delivery_address:
            return warehouse.ddcc_delivery_address
        office = self.env["doorandoor.commercial.office"].sudo().search(
            [("operational_warehouse_id", "=", warehouse.id)], limit=1
        )
        if office:
            return office.address_display
        return warehouse.partner_id.contact_address.replace("\n", ", ") if warehouse.partner_id else ""

    @api.onchange("origin_warehouse_id")
    def _onchange_origin_warehouse_id(self):
        if self.origin_warehouse_id:
            self.origin_address = self._warehouse_logistic_address(self.origin_warehouse_id)

    @api.onchange("fleet_vehicle_id")
    def _onchange_fleet_vehicle_id(self):
        if self.fleet_vehicle_id:
            self.vehicle_name = self.fleet_vehicle_id.name
            self.license_plate = self.fleet_vehicle_id.license_plate

    @api.onchange("driver_profile_id")
    def _onchange_driver_profile_id(self):
        if self.driver_profile_id:
            self.driver_id = self.driver_profile_id.user_id

    @api.depends(
        "trip_control_ids.odometer",
        "trip_control_ids.fuel_added_gallons",
        "trip_control_ids.fuel_used_gallons",
        "trip_control_ids.control_type",
    )
    def _compute_trip_metrics(self):
        for plan in self:
            controls = plan.trip_control_ids.sorted(lambda item: (item.recorded_at, item.id))
            odometers = controls.filtered(lambda item: item.odometer > 0).mapped("odometer")
            plan.odometer_start = odometers[0] if odometers else 0.0
            plan.odometer_end = odometers[-1] if odometers else 0.0
            plan.distance_traveled = max(plan.odometer_end - plan.odometer_start, 0.0)
            plan.fuel_added = sum(controls.mapped("fuel_added_gallons"))
            plan.fuel_used = sum(controls.mapped("fuel_used_gallons"))
            plan.fuel_efficiency = (
                plan.distance_traveled / plan.fuel_used if plan.fuel_used else 0.0
            )

    @api.depends(
        "stop_ids",
        "stop_ids.picking_ids",
        "stop_ids.picking_ids.move_ids.product_uom_qty",
    )
    def _compute_totals(self):
        for plan in self:
            pickings = plan.stop_ids.mapped("picking_ids")
            plan.stop_count = len(plan.stop_ids)
            plan.picking_count = len(pickings)
            plan.total_units = sum(pickings.mapped("move_ids.product_uom_qty"))

    @api.depends("stop_ids.state", "stop_ids.sequence")
    def _compute_next_stop(self):
        for plan in self:
            plan.next_stop_id = plan.stop_ids.filtered(
                lambda stop: stop.state not in ("departed", "unloaded")
            ).sorted(lambda stop: (stop.sequence, stop._origin.id or 0))[:1]

    @api.depends(
        "origin_address",
        "stop_ids.sequence",
        "stop_ids.destination_address",
    )
    def _compute_google_maps_url(self):
        for plan in self:
            stops = plan.stop_ids.sorted(
                lambda stop: (stop.sequence, stop._origin.id or 0)
            )
            origin = plan.origin_address
            destinations = [stop.destination_address for stop in stops]
            destinations = [item for item in destinations if item]
            if not origin or not destinations:
                plan.google_maps_url = False
                continue
            destination = destinations[-1]
            waypoints = destinations[:-1]
            url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={quote_plus(origin)}"
                f"&destination={quote_plus(destination)}"
                "&travelmode=driving"
            )
            if waypoints:
                url += "&waypoints=" + quote_plus("|".join(waypoints))
            plan.google_maps_url = url

    @api.constrains("stop_ids", "origin_warehouse_id")
    def _check_route(self):
        for plan in self:
            warehouses = plan.stop_ids.filtered(
                lambda stop: stop.destination_type == "warehouse"
            ).mapped("warehouse_id")
            if plan.origin_warehouse_id in warehouses:
                raise ValidationError(_("El almacén de origen no puede repetirse como parada."))
            keys = [stop.destination_key for stop in plan.stop_ids]
            if len(keys) != len(set(keys)):
                raise ValidationError(_("Cada almacén de destino puede aparecer una sola vez."))

    def action_prepare_route(self):
        for plan in self:
            if not plan.stop_ids:
                raise UserError(_("Agregue al menos una parada antes de preparar la ruta."))
            plan.state = "route_ready"

    def action_start_loading(self):
        for plan in self:
            if not plan.simulation_mode and not plan.stop_ids.mapped("picking_ids"):
                raise UserError(_(
                    "Esta carga real no tiene documentos asociados. Abra cada parada "
                    "en la pestaña 'Paradas y documentos' y seleccione sus entregas o "
                    "traslados en 'Operaciones asociadas'. Si solo está probando la "
                    "ruta, active 'Ruta de simulación'."
                ))
        self.write({"state": "loading"})

    def action_mark_loaded(self):
        for plan in self:
            if not plan.simulation_mode and not plan.stop_ids.mapped("picking_ids"):
                raise UserError(_(
                    "Faltan documentos de almacén. Abra cada parada y seleccione "
                    "las entregas o traslados en 'Operaciones asociadas'."
                ))
            plan.state = "loaded"

    def action_return_route_ready(self):
        self.write({"state": "route_ready"})

    def action_start_trip(self):
        self._check_driver_or_planner()
        now = fields.Datetime.now()
        for plan in self:
            plan.sudo().write({
                "state": "in_transit",
                "actual_departure": now,
                "last_checkpoint_warehouse_id": plan.origin_warehouse_id.id,
                "last_checkpoint_at": now,
            })

    def action_mark_partial_unload(self):
        self.write({"state": "partial_unload"})

    def action_done(self):
        self.write({"state": "done", "actual_arrival": fields.Datetime.now()})

    def action_incident(self):
        self._check_driver_or_planner()
        self.sudo().write({"state": "incident"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_draft(self):
        self.write({
            "state": "draft",
            "actual_departure": False,
            "actual_arrival": False,
        })

    def _check_driver_or_planner(self):
        is_planner = self.env.user.has_group(
            "doorandoor_cargas_control.group_load_control_planner"
        )
        is_driver = self.env.user.has_group(
            "doorandoor_cargas_control.group_load_control_driver"
        )
        for plan in self:
            if not is_planner and not (is_driver and plan.driver_id == self.env.user):
                raise UserError(_("Solo el chofer asignado o Planificación puede registrar este hito."))
        return True

    def action_open_google_maps(self):
        self.ensure_one()
        if not self.google_maps_url:
            raise UserError(_("Complete las direcciones de origen y paradas."))
        return {"type": "ir.actions.act_url", "url": self.google_maps_url, "target": "new"}

    def action_print_load_manifest(self):
        self.ensure_one()
        return self.env.ref(
            "doorandoor_cargas_control.action_report_load_manifest"
        ).report_action(self)

    @api.model
    def ddcc_route_map_payload(self):
        """Operational checkpoint map; it deliberately does not claim live GPS."""
        active_states = (
            "route_ready", "loading", "loaded", "in_transit",
            "partial_unload", "incident",
        )
        active_plans = self.search(
            [("state", "in", active_states)],
            order="scheduled_departure asc, id asc",
        )
        last_completed = self.search(
            [("state", "=", "done")],
            order="actual_arrival desc, scheduled_departure desc, id desc",
            limit=1,
        )
        plans = active_plans | last_completed

        # Temporary city anchors allow the operational view to work while
        # management progressively verifies exact delivery coordinates.
        fallback = {
            "DD": (25.8195, -80.3313), "DMI": (25.7617, -80.1918),
            "DWPB": (26.7153, -80.0534), "DO": (28.4218, -81.4033),
            "DT": (27.9506, -82.4572), "DTP": (27.9506, -82.4572),
            "DFM": (26.5484, -81.8570), "DCP": (26.5629, -81.9495),
            "CWH": (25.8195, -80.3313), "DDL": (25.8195, -80.3313),
        }

        def point(warehouse):
            exact = warehouse.ddcc_has_coordinates
            if exact:
                latitude = warehouse.ddcc_latitude
                longitude = warehouse.ddcc_longitude
            else:
                latitude, longitude = fallback.get(warehouse.code, (27.6648, -81.5158))
            return {
                "warehouse_id": warehouse.id,
                "warehouse": warehouse.name,
                "code": warehouse.code,
                "latitude": latitude,
                "longitude": longitude,
                "exact": exact,
            }

        labels = dict(self._fields["state"].selection)
        routes = []
        for plan in plans:
            stops = plan.stop_ids.sorted(
                lambda stop: (stop.sequence, stop._origin.id or 0)
            )
            points = [point(plan.origin_warehouse_id)]
            points.extend(stop._ddcc_map_point(fallback) for stop in stops)
            if plan == last_completed:
                color_key = "completed"
            elif plan.state == "incident":
                color_key = "incident"
            elif plan.state in ("in_transit", "partial_unload"):
                color_key = "transit"
            elif plan.state in ("loading", "loaded"):
                color_key = "loading"
            else:
                color_key = "ready"
            routes.append({
                "id": plan.id,
                "name": plan.name,
                "state": plan.state,
                "state_label": labels.get(plan.state, plan.state),
                "color_key": color_key,
                "is_last_completed": plan == last_completed,
                "vehicle": plan.vehicle_name,
                "driver": plan.driver_id.name or _("Sin asignar"),
                "origin": plan.origin_warehouse_id.name,
                "last_checkpoint_id": plan.last_checkpoint_warehouse_id.id,
                "last_checkpoint": plan.last_checkpoint_warehouse_id.name or _("Sin confirmar"),
                "next_stop_id": plan.next_stop_id.warehouse_id.id,
                "next_stop": plan.next_stop_id.destination_display_name or _("Ruta terminada"),
                "documents": plan.picking_count,
                "units": plan.total_units,
                "points": points,
                "uses_provisional_points": any(not item["exact"] for item in points),
            })
        return {
            "routes": routes,
            "active_count": len(active_plans),
            "last_completed_id": last_completed.id,
            "headquarters": point(
                self.env["stock.warehouse"].search([("code", "=", "DD")], limit=1)
            ) if self.env["stock.warehouse"].search([("code", "=", "DD")], limit=1) else False,
        }


class DoorandoorLoadPlanStop(models.Model):
    _name = "doorandoor.load.plan.stop"
    _description = "DoorAndDoor Load Plan Stop"
    _order = "sequence, id"

    plan_id = fields.Many2one(
        "doorandoor.load.plan", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="plan_id.company_id", store=True, index=True)
    sequence = fields.Integer(string="Orden de descarga", default=10, required=True)
    load_sequence = fields.Integer(
        string="Orden de carga", compute="_compute_load_sequence", store=True
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén de destino",
        check_company=True,
    )
    destination_type = fields.Selection(
        [("warehouse", "Almacén"), ("customer", "Cliente / entrega")],
        string="Tipo de destino", default="warehouse", required=True,
    )
    partner_id = fields.Many2one("res.partner", string="Cliente / destinatario")
    destination_display_name = fields.Char(
        string="Destino", compute="_compute_destination_display_name", store=True
    )
    destination_key = fields.Char(compute="_compute_destination_display_name")
    destination_address = fields.Char(
        string="Dirección logística", required=True
    )
    planned_arrival = fields.Datetime(string="Llegada prevista")
    actual_arrival = fields.Datetime(string="Llegada real", readonly=True)
    count_started_at = fields.Datetime(string="Inicio de conteo", readonly=True)
    count_finished_at = fields.Datetime(string="Fin de conteo", readonly=True)
    departed_at = fields.Datetime(string="Salida de la parada", readonly=True)
    transit_minutes = fields.Float(
        string="Minutos de tránsito", compute="_compute_elapsed_times"
    )
    counting_minutes = fields.Float(
        string="Minutos de conteo", compute="_compute_elapsed_times"
    )
    unloading_minutes = fields.Integer(string="Minutos de descarga", default=30)
    load_zone = fields.Selection(
        [
            ("door", "Zona 1 - Puerta"),
            ("middle", "Zona 2 - Centro"),
            ("rear", "Zona 3 - Fondo"),
            ("custom", "Zona especial"),
        ],
        string="Zona sugerida",
    )
    picking_ids = fields.Many2many(
        "stock.picking",
        "doorandoor_load_stop_picking_rel",
        "stop_id",
        "picking_id",
        string="Operaciones asociadas",
        domain="[('company_id', '=', company_id), ('state', 'not in', ('done', 'cancel'))]",
    )
    picking_count = fields.Integer(compute="_compute_document_totals", string="Documentos")
    total_units = fields.Float(compute="_compute_document_totals", string="Unidades")
    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("ready", "Preparada"),
            ("en_route", "En ruta"),
            ("arrived", "En destino"),
            ("counting", "Contando mercancía"),
            ("counted", "Conteo terminado"),
            ("departed", "Salida confirmada"),
            ("unloaded", "Descargada / final"),
            ("incident", "Incidencia"),
        ],
        default="pending",
        required=True,
    )
    notes = fields.Text(string="Observaciones")

    @api.depends("destination_type", "warehouse_id.name", "partner_id.name", "destination_address")
    def _compute_destination_display_name(self):
        for stop in self:
            if stop.destination_type == "warehouse":
                stop.destination_display_name = stop.warehouse_id.name
                stop.destination_key = "warehouse:%s" % (stop.warehouse_id.id or 0)
            else:
                stop.destination_display_name = stop.partner_id.name or stop.destination_address
                stop.destination_key = "customer:%s:%s" % (
                    stop.partner_id.id or 0, stop.destination_address or ""
                )

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.destination_address = self.plan_id._warehouse_logistic_address(self.warehouse_id)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.destination_address = self.partner_id.contact_address.replace("\n", ", ")

    @api.constrains("destination_type", "warehouse_id", "partner_id", "destination_address")
    def _check_destination(self):
        for stop in self:
            if stop.destination_type == "warehouse" and not stop.warehouse_id:
                raise ValidationError(_("Seleccione el almacén de destino."))
            if stop.destination_type == "customer" and not stop.partner_id:
                raise ValidationError(_("Seleccione el cliente o destinatario."))
            if not stop.destination_address:
                raise ValidationError(_("La parada requiere una dirección logística."))

    def _ddcc_map_point(self, fallback):
        self.ensure_one()
        if self.destination_type == "warehouse":
            warehouse = self.warehouse_id
            exact = warehouse.ddcc_has_coordinates
            latitude, longitude = (
                (warehouse.ddcc_latitude, warehouse.ddcc_longitude)
                if exact else fallback.get(warehouse.code, (27.6648, -81.5158))
            )
            return {
                "warehouse_id": warehouse.id, "warehouse": warehouse.name,
                "code": warehouse.code, "latitude": latitude,
                "longitude": longitude, "exact": exact,
            }
        partner = self.partner_id
        latitude = getattr(partner, "partner_latitude", 0.0) or 27.6648
        longitude = getattr(partner, "partner_longitude", 0.0) or -81.5158
        exact = bool(getattr(partner, "partner_latitude", 0.0) and getattr(partner, "partner_longitude", 0.0))
        return {
            "warehouse_id": 0, "warehouse": self.destination_display_name,
            "code": "CLIENT", "latitude": latitude, "longitude": longitude,
            "exact": exact,
        }

    @api.depends("sequence", "plan_id.stop_ids.sequence")
    def _compute_load_sequence(self):
        plans = self.mapped("plan_id")
        for plan in plans:
            ordered = plan.stop_ids.sorted(
                lambda stop: (stop.sequence, stop._origin.id or 0)
            )
            total = len(ordered)
            for position, stop in enumerate(ordered, start=1):
                stop.load_sequence = total - position + 1
        for stop in self.filtered(lambda rec: not rec.plan_id):
            stop.load_sequence = 0

    @api.depends("picking_ids", "picking_ids.move_ids.product_uom_qty")
    def _compute_document_totals(self):
        for stop in self:
            stop.picking_count = len(stop.picking_ids)
            stop.total_units = sum(stop.picking_ids.mapped("move_ids.product_uom_qty"))

    @api.depends(
        "actual_arrival",
        "count_started_at",
        "count_finished_at",
        "plan_id.actual_departure",
        "plan_id.stop_ids.departed_at",
        "sequence",
    )
    def _compute_elapsed_times(self):
        for stop in self:
            previous = stop.plan_id.stop_ids.filtered(
                lambda candidate: candidate.sequence < stop.sequence and candidate.departed_at
            ).sorted(
                lambda candidate: (candidate.sequence, candidate._origin.id or 0),
                reverse=True,
            )[:1]
            start = previous.departed_at if previous else stop.plan_id.actual_departure
            stop.transit_minutes = (
                (stop.actual_arrival - start).total_seconds() / 60.0
                if start and stop.actual_arrival else 0.0
            )
            stop.counting_minutes = (
                (stop.count_finished_at - stop.count_started_at).total_seconds() / 60.0
                if stop.count_started_at and stop.count_finished_at else 0.0
            )

    def _check_driver_or_planner(self):
        self.mapped("plan_id")._check_driver_or_planner()

    def action_arrive(self):
        self.ensure_one()
        self._check_driver_or_planner()
        if self.plan_id.next_stop_id != self:
            raise UserError(_("Esta no es la próxima parada activa de la ruta."))
        now = fields.Datetime.now()
        self.sudo().write({"state": "arrived", "actual_arrival": now})
        self.plan_id.sudo().write({
            "last_checkpoint_at": now,
        })
        if self.warehouse_id:
            self.plan_id.sudo().last_checkpoint_warehouse_id = self.warehouse_id
        return True

    def action_start_count(self):
        self.ensure_one()
        self._check_driver_or_planner()
        if self.state != "arrived":
            raise UserError(_("Primero confirme la llegada al almacén."))
        self.sudo().write({"state": "counting", "count_started_at": fields.Datetime.now()})
        return True

    def action_finish_count(self):
        self.ensure_one()
        self._check_driver_or_planner()
        if self.state != "counting":
            raise UserError(_("El conteo de esta parada no está iniciado."))
        self.sudo().write({"state": "counted", "count_finished_at": fields.Datetime.now()})
        return True

    def action_depart(self):
        self.ensure_one()
        self._check_driver_or_planner()
        if self.state != "counted":
            raise UserError(_("Debe terminar el conteo antes de salir de la parada."))
        self.sudo().write({"state": "departed", "departed_at": fields.Datetime.now()})
        self.plan_id.sudo().write({"state": "partial_unload"})
        return True

    @api.constrains("unloading_minutes")
    def _check_unloading_minutes(self):
        if any(stop.unloading_minutes < 0 for stop in self):
            raise ValidationError(_("El tiempo de descarga no puede ser negativo."))


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddcc_load_stop_ids = fields.Many2many(
        "doorandoor.load.plan.stop",
        "doorandoor_load_stop_picking_rel",
        "picking_id",
        "stop_id",
        string="Paradas de carga",
        readonly=True,
    )
    ddcc_load_plan_names = fields.Char(
        string="Planes de carga",
        compute="_compute_ddcc_load_references",
    )
    ddcc_load_stop_names = fields.Char(
        string="Paradas / destinos",
        compute="_compute_ddcc_load_references",
    )

    @api.depends(
        "ddcc_load_stop_ids.plan_id.name",
        "ddcc_load_stop_ids.destination_display_name",
    )
    def _compute_ddcc_load_references(self):
        for picking in self:
            picking.ddcc_load_plan_names = ", ".join(
                picking.ddcc_load_stop_ids.mapped("plan_id.name")
            )
            picking.ddcc_load_stop_names = ", ".join(
                picking.ddcc_load_stop_ids.mapped("destination_display_name")
            )


class DoorandoorLoadPlanCrew(models.Model):
    _name = "doorandoor.load.plan.crew"
    _description = "DoorAndDoor Trip Crew"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    plan_id = fields.Many2one("doorandoor.load.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    driver_profile_id = fields.Many2one(
        "doorandoor.driver.profile", string="Miembro", required=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    role = fields.Selection(
        [("main_driver", "Chofer principal"), ("alternate_driver", "Chofer alterno"),
         ("helper", "Ayudante"), ("supervisor", "Supervisor")],
        required=True, default="helper",
    )
    notes = fields.Char(string="Responsabilidad / notas")


class DoorandoorLoadTripControl(models.Model):
    _name = "doorandoor.load.trip.control"
    _description = "DoorAndDoor Trip Checkpoint Control"
    _order = "recorded_at, id"

    plan_id = fields.Many2one("doorandoor.load.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    stop_id = fields.Many2one(
        "doorandoor.load.plan.stop", string="Parada",
        domain="[('plan_id', '=', plan_id)]", ondelete="cascade",
    )
    control_type = fields.Selection(
        [("departure", "Salida"), ("checkpoint", "Control de ruta"),
         ("arrival", "Llegada"), ("fuel", "Carga de combustible"),
         ("close", "Cierre")], required=True, default="checkpoint",
    )
    recorded_at = fields.Datetime(required=True, default=fields.Datetime.now)
    recorded_by = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    odometer = fields.Float(string="Odómetro")
    fuel_level_pct = fields.Float(string="Nivel de combustible %")
    fuel_added_gallons = fields.Float(string="Combustible cargado (gal)")
    fuel_used_gallons = fields.Float(string="Combustible consumido (gal)")
    notes = fields.Text(string="Observaciones")

    @api.constrains("odometer", "fuel_level_pct", "fuel_added_gallons", "fuel_used_gallons")
    def _check_values(self):
        for control in self:
            if control.odometer < 0 or control.fuel_added_gallons < 0 or control.fuel_used_gallons < 0:
                raise ValidationError(_("Odómetro y combustible no pueden ser negativos."))
            if control.fuel_level_pct < 0 or control.fuel_level_pct > 100:
                raise ValidationError(_("El nivel de combustible debe estar entre 0 y 100 %."))
