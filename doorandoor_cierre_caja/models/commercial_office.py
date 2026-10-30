from odoo import fields, models


class DoorAndDoorCommercialOffice(models.Model):
    _inherit = "doorandoor.commercial.office"

    cash_register_ids = fields.One2many(
        "doorandoor.cash.register",
        "office_id",
        string="Cajas comerciales",
        readonly=True,
    )
