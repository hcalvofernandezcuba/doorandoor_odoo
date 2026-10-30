# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorandoorDispatchPreparationWizard(models.TransientModel):
    _name = "doorandoor.dispatch.preparation.wizard"
    _description = "Prepare DoorAndDoor Dispatch"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    origin_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén de salida", required=True,
        check_company=True,
    )
    scheduled_departure = fields.Datetime(
        string="Salida prevista", required=True, default=fields.Datetime.now
    )
    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle", string="Camión", required=True, check_company=True,
        domain="[('ddcc_available_for_loads', '=', True)]",
    )
    driver_profile_id = fields.Many2one(
        "doorandoor.driver.profile", string="Chofer principal", required=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    responsible_id = fields.Many2one(
        "res.users", string="Responsable de carga", required=True,
        default=lambda self: self.env.user,
    )
    eligible_picking_ids = fields.Many2many(
        "stock.picking", compute="_compute_eligible_pickings"
    )
    picking_ids = fields.Many2many(
        "stock.picking", string="Despachos y traslados",
        domain="[('id', 'in', eligible_picking_ids)]",
    )
    crew_ids = fields.Many2many(
        "doorandoor.driver.profile", "ddcc_dispatch_wizard_crew_rel",
        "wizard_id", "driver_id", string="Tripulación adicional",
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    eligible_count = fields.Integer(compute="_compute_eligible_pickings")

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        warehouse = self.env.user.ddpc_default_warehouse_id
        if warehouse and "origin_warehouse_id" in field_list:
            values["origin_warehouse_id"] = warehouse.id
        return values

    def _eligible_domain(self):
        self.ensure_one()
        if not self.origin_warehouse_id:
            return [("id", "=", 0)]
        return [
            ("company_id", "=", self.company_id.id),
            ("state", "not in", ("done", "cancel")),
            ("ddpc_operation_category", "in", ("delivery", "transfer")),
            ("ddpc_source_warehouse_id", "=", self.origin_warehouse_id.id),
        ]

    @api.depends("origin_warehouse_id", "company_id")
    def _compute_eligible_pickings(self):
        Picking = self.env["stock.picking"]
        for wizard in self:
            if not wizard.origin_warehouse_id:
                wizard.eligible_picking_ids = False
                wizard.eligible_count = 0
                continue
            # A negative one2many domain excludes operations already attached
            # to another active route while allowing never-planned documents.
            candidates = Picking.search(wizard._eligible_domain())
            active_states = {
                "draft", "route_ready", "loading", "loaded", "in_transit",
                "partial_unload", "incident",
            }
            eligible = candidates.filtered(
                lambda picking: not any(
                    plan.state in active_states
                    for plan in picking.ddcc_load_stop_ids.mapped("plan_id")
                )
            )
            wizard.eligible_picking_ids = eligible
            wizard.eligible_count = len(eligible)

    @api.onchange("origin_warehouse_id")
    def _onchange_origin(self):
        self.picking_ids = False

    def _destination_values(self, picking):
        if picking.ddpc_dest_warehouse_id:
            warehouse = picking.ddpc_dest_warehouse_id
            return (
                "warehouse:%s" % warehouse.id,
                {
                    "destination_type": "warehouse",
                    "warehouse_id": warehouse.id,
                    "destination_address": self.env["doorandoor.load.plan"]._warehouse_logistic_address(warehouse),
                },
            )
        partner = picking.partner_id.commercial_partner_id or picking.partner_id
        if not partner:
            raise UserError(_("La operación %s no tiene almacén destino ni destinatario.") % picking.display_name)
        address = picking.partner_id.contact_address.replace("\n", ", ")
        return (
            "customer:%s:%s" % (partner.id, address),
            {
                "destination_type": "customer",
                "partner_id": picking.partner_id.id,
                "destination_address": address,
            },
        )

    def action_create_dispatch(self):
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("Seleccione al menos un despacho o traslado pendiente."))
        invalid = self.picking_ids - self.eligible_picking_ids
        if invalid:
            raise UserError(_(
                "Estas operaciones ya no están disponibles para esta carga: %s"
            ) % ", ".join(invalid.mapped("name")))

        grouped = defaultdict(lambda: {"pickings": self.env["stock.picking"], "values": {}})
        for picking in self.picking_ids:
            key, values = self._destination_values(picking)
            grouped[key]["values"] = values
            grouped[key]["pickings"] |= picking

        plan = self.env["doorandoor.load.plan"].create({
            "origin_warehouse_id": self.origin_warehouse_id.id,
            "origin_address": self.env["doorandoor.load.plan"]._warehouse_logistic_address(self.origin_warehouse_id),
            "scheduled_departure": self.scheduled_departure,
            "fleet_vehicle_id": self.fleet_vehicle_id.id,
            "vehicle_name": self.fleet_vehicle_id.name,
            "license_plate": self.fleet_vehicle_id.license_plate,
            "driver_profile_id": self.driver_profile_id.id,
            "driver_id": self.driver_profile_id.user_id.id,
            "responsible_id": self.responsible_id.id,
            "crew_ids": [(0, 0, {
                "driver_profile_id": self.driver_profile_id.id,
                "role": "main_driver",
            })] + [(0, 0, {
                "driver_profile_id": member.id,
                "role": "helper",
            }) for member in self.crew_ids if member != self.driver_profile_id],
        })
        for sequence, data in enumerate(grouped.values(), start=1):
            self.env["doorandoor.load.plan.stop"].create({
                "plan_id": plan.id,
                "sequence": sequence * 10,
                **data["values"],
                "picking_ids": [(6, 0, data["pickings"].ids)],
            })
        plan.message_post(body=_(
            "Despacho preparado desde %(warehouse)s con %(documents)s documentos reales. "
            "Las operaciones de inventario no fueron validadas ni duplicadas."
        ) % {"warehouse": self.origin_warehouse_id.display_name, "documents": len(self.picking_ids)})
        for picking in self.picking_ids:
            picking.message_post(body=_(
                "Operación asociada al plan de carga %s durante la preparación del despacho."
            ) % plan.name)
        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.load.plan",
            "res_id": plan.id,
            "view_mode": "form",
            "target": "current",
        }
