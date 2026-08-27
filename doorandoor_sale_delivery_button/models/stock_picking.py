# -*- coding: utf-8 -*-
"""
DoorAndDoor - Botón de Entrega desde Ventas
Modelo: stock.picking
"""

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # CAMPOS
    # -------------------------------------------------------------------------

    sale_id = fields.Many2one(
        'sale.order',
        string='Pedido de Venta',
        index=True,
        ondelete='set null',
        help='Pedido de venta relacionado con esta operación de almacén',
        copy=False,
    )

    # -------------------------------------------------------------------------
    # MÉTODOS HEREDADOS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribe create para vincular automáticamente el picking con la venta
        cuando el origin coincide con un sale.order.name y sale_id no está establecido.
        """
        pickings = super(StockPicking, self).create(vals_list)

        for picking in pickings:
            # Solo sincronizar si sale_id está vacío y origin tiene valor
            if not picking.sale_id and picking.origin:
                # Buscar si el origin coincide con un sale.order
                sale_order = self.env['sale.order'].search([
                    ('name', '=', picking.origin),
                ], limit=1)
                if sale_order:
                    picking.sale_id = sale_order.id

        pickings._dddb_assert_paid_customer_delivery()

        return pickings

    def action_confirm(self):
        self._dddb_assert_paid_customer_delivery()
        return super().action_confirm()

    def action_assign(self):
        self._dddb_assert_paid_customer_delivery()
        return super().action_assign()

    def write(self, vals):
        """
        Sobrescribe write para mantener sincronizado sale_id con origin
        solo cuando sale_id no está establecido manualmente.
        """
        res = super(StockPicking, self).write(vals)

        # Solo sincronizar si origin cambió y sale_id sigue vacío
        if 'origin' in vals:
            for picking in self:
                if picking.origin and not picking.sale_id:
                    sale_order = self.env['sale.order'].search([
                        ('name', '=', picking.origin),
                    ], limit=1)
                    if sale_order:
                        picking.sale_id = sale_order.id

        return res
    def _dddb_get_related_sales(self):
        sales = self.mapped('sale_id') | self.mapped('move_ids.sale_line_id.order_id')
        origins = {origin for origin in self.mapped('origin') if origin}
        if origins:
            sales |= self.env['sale.order'].search([('name', 'in', list(origins))])
        return sales

    def _dddb_assert_paid_customer_delivery(self):
        outgoing = self.filtered(lambda picking: picking.picking_type_code == 'outgoing')
        outgoing._dddb_get_related_sales()._dddb_assert_delivery_allowed()
        return True
