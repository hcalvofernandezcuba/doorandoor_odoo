# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    ddcc_available_for_loads = fields.Boolean(
        string="Disponible para cargas", default=True, tracking=True
    )
    ddcc_home_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén base", check_company=True, tracking=True
    )
    ddcc_empty_weight = fields.Float(string="Peso vacío", tracking=True)
    ddcc_max_payload = fields.Float(string="Capacidad de carga", tracking=True)
    ddcc_max_gross_weight = fields.Float(string="Peso bruto máximo", tracking=True)
    ddcc_fuel_tank_capacity = fields.Float(
        string="Capacidad del tanque", tracking=True,
        help="Capacidad operativa del tanque en galones.",
    )
    ddcc_logistic_notes = fields.Text(string="Notas logísticas")

    @api.constrains(
        "ddcc_empty_weight", "ddcc_max_payload", "ddcc_max_gross_weight",
        "ddcc_fuel_tank_capacity",
    )
    def _check_ddcc_positive_values(self):
        for vehicle in self:
            values = (
                vehicle.ddcc_empty_weight,
                vehicle.ddcc_max_payload,
                vehicle.ddcc_max_gross_weight,
                vehicle.ddcc_fuel_tank_capacity,
            )
            if any(value < 0 for value in values):
                raise ValidationError("Los datos de peso y combustible no pueden ser negativos.")


class DoorandoorDriverProfile(models.Model):
    _name = "doorandoor.driver.profile"
    _description = "DoorAndDoor Driver Profile"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    active = fields.Boolean(default=True)
    name = fields.Char(string="Nombre del chofer", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    user_id = fields.Many2one(
        "res.users", string="Usuario de Odoo (opcional)", tracking=True,
        domain="[('share', '=', False)]",
        help=(
            "Vincúlo solo cuando el chofer necesite entrar a Odoo para consultar "
            "o registrar sus rutas. Crear el perfil no crea una cuenta de usuario."
        ),
    )
    partner_id = fields.Many2one(
        "res.partner", related="user_id.partner_id", store=True, string="Contacto"
    )
    license_number = fields.Char(string="Licencia", tracking=True)
    license_class = fields.Char(string="Clase", tracking=True)
    license_expiration = fields.Date(string="Vencimiento", tracking=True)
    phone = fields.Char(string="Teléfono", tracking=True)
    emergency_contact = fields.Char(string="Contacto de emergencia")
    notes = fields.Text(string="Observaciones")

    _sql_constraints = [
        ("driver_user_company_unique", "unique(user_id, company_id)",
         "El usuario ya tiene un perfil de chofer en esta compañía."),
    ]

    @api.onchange("user_id")
    def _onchange_user_id_driver_data(self):
        for profile in self.filtered("user_id"):
            if not profile.name:
                profile.name = profile.user_id.name
            if not profile.phone:
                profile.phone = profile.user_id.partner_id.phone

    @api.model_create_multi
    def create(self, vals_list):
        User = self.env["res.users"]
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            user = User.browse(vals.get("user_id")).exists()
            if user:
                vals.setdefault("name", user.name)
                vals.setdefault("phone", user.partner_id.phone)
            prepared.append(vals)
        return super().create(prepared)
