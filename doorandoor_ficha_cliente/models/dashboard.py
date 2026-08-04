# -*- coding: utf-8 -*-

from odoo import fields, models


class DdfcDashboard(models.Model):
    _name = "ddfc.dashboard"
    _description = "Dashboard de constructores y clientes"
    _auto = False

    builder_id = fields.Many2one("ddfc.builder.profile", string="Constructor")
    builder_name = fields.Char(string="Constructor")
    customer_count = fields.Integer(string="Clientes asociados")
    seller_id = fields.Many2one("res.users", string="Vendedor")
    seller_name = fields.Char(string="Vendedor")
    sale_count = fields.Integer(string="Ventas")
    invoice_count = fields.Integer(string="Facturas")

    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW ddfc_dashboard AS (
                SELECT
                    row_number() OVER () AS id,
                    b.id AS builder_id,
                    b.name AS builder_name,
                    COALESCE(COUNT(DISTINCT p.id), 0) AS customer_count,
                    s.id AS seller_id,
                    s.name AS seller_name,
                    COALESCE(COUNT(DISTINCT so.id), 0) AS sale_count,
                    COALESCE(COUNT(DISTINCT am.id), 0) AS invoice_count
                FROM ddfc_builder_profile b
                LEFT JOIN res_partner p ON p.ddfc_builder_id = b.id
                LEFT JOIN sale_order so ON so.ddfc_builder_id = b.id
                LEFT JOIN account_move am ON am.ddfc_builder_id = b.id
                LEFT JOIN res_users s ON s.id = so.user_id
                GROUP BY b.id, b.name, s.id, s.name
            )
        """)
