# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DdfcBuilderProfileWizard(models.TransientModel):
    _name = "ddfc.builder.profile.wizard"
    _description = "Wizard para completar datos del constructor"

    # Datos del constructor
    builder_name = fields.Char(string="Nombre del Constructor", required=True)
    builder_code = fields.Char(string="Código")
    builder_phone = fields.Char(string="Teléfono")
    builder_mobile = fields.Char(string="Móvil")
    builder_email = fields.Char(string="Correo")
    builder_city = fields.Char(string="Ciudad")
    builder_state_id = fields.Many2one("res.country.state", string="Estado")
    builder_country_id = fields.Many2one("res.country", string="País")
    builder_notes = fields.Text(string="Notas internas")
    
    # Datos del contacto asociado
    partner_name = fields.Char(string="Nombre del Contacto", required=True)
    partner_phone = fields.Char(string="Teléfono Contacto")
    partner_mobile = fields.Char(string="Móvil Contacto")
    partner_email = fields.Char(string="Correo Contacto")
    partner_city = fields.Char(string="Ciudad Contacto")
    partner_state_id = fields.Many2one("res.country.state", string="Estado Contacto")
    partner_country_id = fields.Many2one("res.country", string="País Contacto")
    partner_street = fields.Char(string="Dirección")
    partner_website = fields.Char(string="Sitio Web")
    
    # Etiqueta de constructor
    builder_category_id = fields.Many2one(
        "res.partner.category",
        string="Etiqueta Constructor",
        help="Etiqueta para marcar este contacto como constructor",
    )
    
    # Contexto para saber desde dónde se está creando
    ddfc_discount_for_new_process = fields.Boolean(
        string="Constructor nuevo para descuento",
        default=False,
    )
    
    # Referencia al documento actual (factura o cotización)
    active_model = fields.Char(string="Modelo activo")
    active_id = fields.Integer(string="ID activo")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Buscar o crear la categoría de constructor
        category = self.env["res.partner.category"].search(
            [("name", "=", "Constructor")], limit=1
        )
        if not category:
            category = self.env["res.partner.category"].create({"name": "Constructor"})
        res["builder_category_id"] = category.id
        
        # Usar el contexto del flujo de ventas si está disponible
        if self.env.context.get("default_ddfc_discount_for_new_process"):
            res["ddfc_discount_for_new_process"] = True
        
        # Obtener el modelo e ID activo del contexto
        if self.env.context.get("active_model") and self.env.context.get("active_id"):
            res["active_model"] = self.env.context.get("active_model")
            res["active_id"] = self.env.context.get("active_id")
        
        return res

    def action_create_builder(self):
        """Crea el constructor y el contacto asociado"""
        self.ensure_one()
        
        # Crear el contacto (partner)
        partner_vals = {
            "name": self.partner_name,
            "is_company": True,
            "company_type": "company",
            "customer_rank": 1,
            "supplier_rank": 1,
            "phone": self.partner_phone,
            "mobile": self.partner_mobile,
            "email": self.partner_email,
            "city": self.partner_city,
            "state_id": self.partner_state_id.id if self.partner_state_id else False,
            "country_id": self.partner_country_id.id if self.partner_country_id else False,
            "street": self.partner_street,
            "website": self.partner_website,
            "category_id": [(4, self.builder_category_id.id)],  # Marcar como constructor
        }
        
        partner = self.env["res.partner"].create(partner_vals)
        
        # Crear el constructor
        builder_vals = {
            "name": self.builder_name,
            "code": self.builder_code,
            "partner_id": partner.id,
            "phone": self.builder_phone,
            "mobile": self.builder_mobile,
            "email": self.builder_email,
            "city": self.builder_city,
            "state_id": self.builder_state_id.id if self.builder_state_id else False,
            "country_id": self.builder_country_id.id if self.builder_country_id else False,
            "notes": self.builder_notes,
            "ddfc_discount_for_new_process": self.ddfc_discount_for_new_process,
        }
        
        builder = self.env["ddfc.builder.profile"].create(builder_vals)
        
        # Si se está creando desde una factura o cotización, asignar el constructor
        if self.active_model and self.active_id:
            if self.active_model == "account.move":
                document = self.env["account.move"].browse(self.active_id)
                document.write({"ddfc_builder_id": builder.id})
            elif self.active_model == "sale.order":
                document = self.env["sale.order"].browse(self.active_id)
                document.write({"ddfc_builder_id": builder.id})
        
        # Retornar la acción para abrir el formulario del constructor creado
        return {
            "type": "ir.actions.act_window",
            "name": "Constructor Creado",
            "res_model": "ddfc.builder.profile",
            "res_id": builder.id,
            "view_mode": "form",
            "target": "current",
        }
