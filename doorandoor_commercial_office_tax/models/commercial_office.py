# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DoorandoorCommercialOffice(models.Model):
    _name = "doorandoor.commercial.office"
    _description = "DoorAndDoor Commercial Office"
    _order = "company_id, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, ondelete="cascade")
    street = fields.Char(required=True)
    street2 = fields.Char()
    city = fields.Char(required=True)
    state_id = fields.Many2one("res.country.state", required=True, ondelete="restrict")
    zip = fields.Char()
    country_id = fields.Many2one("res.country", required=True, default=lambda self: self.env.company.country_id, ondelete="restrict")
    phone = fields.Char(required=True)
    sale_tax_id = fields.Many2one(
        "account.tax", string="Sales Tax", required=True, ondelete="restrict",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )
    operational_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Operational Warehouse",
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        help=(
            "Warehouse used by quotations, internal sales, manufacturing needs, "
            "deliveries and Pickup Orders created for this office."
        ),
    )
    user_ids = fields.One2many(
        "res.users",
        "ddco_office_id",
        string="Salespeople",
        help="Users assigned here receive the minimum Sales and Invoicing roles.",
    )
    address_display = fields.Char(compute="_compute_address_display")

    @api.depends("street", "street2", "city", "state_id", "zip", "country_id")
    def _compute_address_display(self):
        for office in self:
            locality = " ".join(value for value in (office.city, office.state_id.code, office.zip) if value)
            office.address_display = ", ".join(value for value in (office.street, office.street2, locality, office.country_id.name) if value)

    @api.constrains("sale_tax_id", "company_id")
    def _check_sale_tax_company(self):
        for office in self:
            if office.sale_tax_id and office.sale_tax_id.company_id != office.company_id:
                raise ValidationError("El impuesto de la oficina debe pertenecer a la misma compañía.")

    @api.constrains("operational_warehouse_id", "company_id")
    def _check_operational_warehouse_company(self):
        for office in self:
            if office.operational_warehouse_id and office.operational_warehouse_id.company_id != office.company_id:
                raise ValidationError("El almacén operativo debe pertenecer a la misma compañía de la oficina.")
