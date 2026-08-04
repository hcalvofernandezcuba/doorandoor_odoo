# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DdfcBuilderProfile(models.Model):
    _name = "ddfc.builder.profile"
    _description = "Constructor / Instalador asociado"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    active = fields.Boolean(default=True, tracking=True)
    name = fields.Char(string="Constructor / Instalador", required=True, tracking=True)
    code = fields.Char(string="Codigo", tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto principal",
        tracking=True,
        domain="[('is_company', '=', True)]",
    )
    phone = fields.Char(string="Telefono", tracking=True)
    mobile = fields.Char(string="Movil", tracking=True)
    email = fields.Char(string="Correo", tracking=True)
    city = fields.Char(string="Ciudad")
    state_id = fields.Many2one("res.country.state", string="Estado")
    country_id = fields.Many2one("res.country", string="Pais")
    notes = fields.Text(string="Notas internas")
    discount_active = fields.Boolean(string="Descuento activo", default=True, tracking=True)
    discount_percent = fields.Float(string="Descuento especial (%)", default=0.0, tracking=True)
    customer_ids = fields.One2many(
        "res.partner",
        "ddfc_builder_id",
        string="Clientes asociados",
    )
    sale_order_ids = fields.One2many(
        "sale.order",
        "ddfc_builder_id",
        string="Cotizaciones / pedidos",
    )
    invoice_ids = fields.One2many(
        "account.move",
        "ddfc_builder_id",
        string="Facturas",
    )
    customer_count = fields.Integer(string="Cantidad de clientes", compute="_compute_customer_count")
    sale_order_count = fields.Integer(string="Cotizaciones / pedidos", compute="_compute_sales_and_invoices")
    invoice_count = fields.Integer(string="Facturas", compute="_compute_sales_and_invoices")
    last_sale_date = fields.Date(string="Ultima venta", compute="_compute_sales_and_invoices")
    last_invoice_date = fields.Date(string="Ultima factura", compute="_compute_sales_and_invoices")

    _sql_constraints = [
        ("ddfc_builder_profile_name_uniq", "unique(name)", "Ya existe un constructor con este nombre."),
        ("ddfc_builder_profile_code_uniq", "unique(code)", "Ya existe un constructor con este codigo."),
    ]

    @api.depends("customer_ids")
    def _compute_customer_count(self):
        for record in self:
            record.customer_count = len(record.customer_ids)

    @api.depends("sale_order_ids", "invoice_ids")
    def _compute_sales_and_invoices(self):
        for record in self:
            sales = record.sale_order_ids
            invoices = record.invoice_ids
            record.sale_order_count = len(sales)
            record.invoice_count = len(invoices)
            record.last_sale_date = sales and sales.sorted("date_order", reverse=True)[0].date_order.date() or False
            record.last_invoice_date = invoices and invoices.sorted("date", reverse=True)[0].date or False

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for record in self:
            partner = record.partner_id
            if not partner:
                continue
            record.phone = partner.phone or record.phone
            record.mobile = partner.mobile or record.mobile
            record.email = partner.email or record.email
            record.city = partner.city or record.city
            record.state_id = partner.state_id or record.state_id
            record.country_id = partner.country_id or record.country_id

    def _sync_partner_profile(self):
        for record in self:
            if not record.partner_id:
                continue
            record.partner_id.write({
                "is_company": True,
                "company_type": "company",
                "customer_rank": max(record.partner_id.customer_rank or 0, 1),
                "phone": record.phone or record.partner_id.phone or False,
                "mobile": record.mobile or record.partner_id.mobile or False,
                "email": record.email or record.partner_id.email or False,
                "city": record.city or record.partner_id.city or False,
                "state_id": record.state_id.id or record.partner_id.state_id.id or False,
                "country_id": record.country_id.id or record.partner_id.country_id.id or False,
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_partner_profile()
        return records

    def write(self, vals):
        result = super().write(vals)
        if any(key in vals for key in ["partner_id", "phone", "mobile", "email", "city", "state_id", "country_id", "name", "active"]):
            self._sync_partner_profile()
        return result

    def action_view_customers(self):
        self.ensure_one()
        action = self.env.ref("contacts.action_contacts").read()[0]
        action["domain"] = [("ddfc_builder_id", "=", self.id)]
        action["context"] = {
            "default_ddfc_builder_id": self.id,
            "search_default_filter_customers": 1,
            "default_customer_rank": 1,
        }
        return action

    def action_view_sales(self):
        self.ensure_one()
        action = self.env.ref("sale.action_quotations_with_onboarding").read()[0]
        action["domain"] = [("ddfc_builder_id", "=", self.id)]
        action["context"] = {"default_ddfc_builder_id": self.id}
        return action

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        action["domain"] = [("ddfc_builder_id", "=", self.id)]
        action["context"] = {"default_ddfc_builder_id": self.id}
        return action
