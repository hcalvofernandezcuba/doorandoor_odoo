# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddfc_builder_id = fields.Many2one(
        "ddfc.builder.profile",
        string="Constructor asociado",
        tracking=True,
        help=(
            "Constructor, instalador o aliado comercial vinculado a este cliente "
            "para marketing, postventa y garantias."
        ),
    )
    ddfc_builder_discount_percent = fields.Float(
        related="ddfc_builder_id.discount_percent",
        string="Descuento constructor (%)",
        readonly=True,
        store=False,
    )
    ddfc_builder_discount_active = fields.Boolean(
        related="ddfc_builder_id.discount_active",
        string="Descuento constructor activo",
        readonly=True,
        store=False,
    )
    ddfc_builder_name = fields.Char(
        related="ddfc_builder_id.name",
        string="Nombre de constructor",
        readonly=True,
        store=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        
        # Verificar si es una creación de constructor desde el flujo de ventas
        if self.env.context.get("default_ddfc_is_builder_creation"):
            for partner in partners:
                partner._create_builder_from_contact()
        
        return partners
    ddfc_is_builder_creation = fields.Boolean(
        string="Creación de constructor",
        default=False,
        store=False,
        compute=lambda self: False,
        help="Indica si este contacto se está creando como parte del proceso de creación de constructor.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        
        # Verificar si es una creación de constructor desde el flujo de ventas
        if self.env.context.get("default_ddfc_is_builder_creation"):
            for partner in partners:
                partner._create_builder_from_contact()
        
        return partners

    def _create_builder_from_contact(self):
        """Crea automáticamente el constructor asociado al contacto"""
        self.ensure_one()
        
        # Buscar o crear la categoría de constructor
        category = self.env["res.partner.category"].search(
            [("name", "=", "Constructor")], limit=1
        )
        if not category:
            category = self.env["res.partner.category"].create({"name": "Constructor"})
        
        # Marcar el contacto con la etiqueta de constructor
        self.write({"category_id": [(4, category.id)]})
        
        # Crear el constructor
        builder_vals = {
            "name": self.name,
            "partner_id": self.id,
            "phone": self.phone,
            "mobile": self.mobile,
            "email": self.email,
            "city": self.city,
            "state_id": self.state_id.id if self.state_id else False,
            "country_id": self.country_id.id if self.country_id else False,
            "ddfc_discount_for_new_process": True,
        }
        
        builder = self.env["ddfc.builder.profile"].create(builder_vals)
        
        # Asignar el constructor al documento origen si existe
        source_model = self.env.context.get("ddfc_source_model")
        source_id = self.env.context.get("ddfc_source_id")
        
        if source_model and source_id:
            if source_model == "sale.order":
                document = self.env["sale.order"].browse(source_id)
                document.write({"ddfc_builder_id": builder.id})
            elif source_model == "account.move":
                document = self.env["account.move"].browse(source_id)
                document.write({"ddfc_builder_id": builder.id})
        
        return builder
