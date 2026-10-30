# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    ddcc_delivery_address = fields.Char(
        string="Dirección logística de entrega",
        help="Dirección operativa que se utilizará en planes de carga, entregas y mapas.",
    )
    ddcc_latitude = fields.Float(
        string="Latitud de entrega",
        digits=(10, 7),
        help="Coordenada del punto donde el camión entrega o recibe mercancía.",
    )
    ddcc_longitude = fields.Float(
        string="Longitud de entrega",
        digits=(10, 7),
        help="Coordenada del punto donde el camión entrega o recibe mercancía.",
    )
    ddcc_coordinate_status = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("provisional", "Provisional"),
            ("verified", "Verificada"),
        ],
        string="Estado de coordenadas",
        default="pending",
        required=True,
    )
    ddcc_coordinate_notes = fields.Text(
        string="Indicaciones de acceso y entrega",
        help="Puerta, muelle, acceso para camiones u otra referencia logística.",
    )
    ddcc_has_coordinates = fields.Boolean(
        string="Coordenadas registradas",
        compute="_compute_ddcc_has_coordinates",
    )

    @api.depends("ddcc_latitude", "ddcc_longitude")
    def _compute_ddcc_has_coordinates(self):
        for warehouse in self:
            warehouse.ddcc_has_coordinates = bool(
                warehouse.ddcc_latitude and warehouse.ddcc_longitude
            )

    @api.constrains("ddcc_latitude", "ddcc_longitude")
    def _check_ddcc_coordinates(self):
        for warehouse in self:
            latitude = warehouse.ddcc_latitude
            longitude = warehouse.ddcc_longitude
            if bool(latitude) != bool(longitude):
                raise ValidationError(
                    "La latitud y la longitud deben registrarse juntas."
                )
            if latitude and not -90 <= latitude <= 90:
                raise ValidationError("La latitud debe estar entre -90 y 90.")
            if longitude and not -180 <= longitude <= 180:
                raise ValidationError("La longitud debe estar entre -180 y 180.")
