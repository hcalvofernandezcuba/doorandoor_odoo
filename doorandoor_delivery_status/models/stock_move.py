# -*- coding: utf-8 -*-
"""
DoorAndDoor - Estado de Entrega en Picking
Modelo: stock.move

CORRECCIÓN Odoo 18 - Versión 1.0.2:
- El campo qty_done no existe en stock.move.line en todas las instalaciones de Odoo 18
- Usamos un enfoque seguro: leer la cantidad desde las move_lines con getattr
- Fallback a 0.0 si no hay move_lines o el campo no existe
"""

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    # CAMPOS
    # -------------------------------------------------------------------------

    qty_ordered = fields.Float(
        string='Cantidad Pedida',
        compute='_compute_qty_ordered',
        store=False,
        readonly=True,
        help='Cantidad original pedida en la venta (desde sale.order.line)',
        digits='Product Unit of Measure',
    )

    qty_delivered_this = fields.Float(
        string='Entregado',
        compute='_compute_qty_delivered_this',
        store=False,
        readonly=True,
        help='Cantidad entregada en ESTE picking específico',
        digits='Product Unit of Measure',
    )

    qty_pending = fields.Float(
        string='Pendiente',
        compute='_compute_qty_pending',
        store=False,
        readonly=True,
        help='Cantidad pendiente por entregar = Pedida - Entregado (este picking)',
        digits='Product Unit of Measure',
    )

    has_sale_order = fields.Boolean(
        string='Tiene Venta',
        compute='_compute_has_sale_order',
        store=False,
        help='Indica si este movimiento está vinculado a una venta',
    )

    # -------------------------------------------------------------------------
    # MÉTODOS COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('sale_line_id', 'sale_line_id.product_uom_qty')
    def _compute_qty_ordered(self):
        """
        Calcula la cantidad pedida original desde la línea de venta.
        Si no hay venta relacionada, muestra 0.
        """
        for move in self:
            if move.sale_line_id:
                move.qty_ordered = move.sale_line_id.product_uom_qty
            else:
                move.qty_ordered = 0.0

    @api.depends('move_line_ids')
    def _compute_qty_delivered_this(self):
        """
        Calcula la cantidad entregada en ESTE picking.

        Intenta leer qty_done de las move_lines. Si no existe el campo,
        usa quantity como fallback. Si tampoco existe, usa 0.0.

        Este enfoque es compatible con diferentes configuraciones de Odoo 18.
        """
        for move in self:
            total = 0.0
            if move.move_line_ids:
                for line in move.move_line_ids:
                    # Intentar diferentes nombres de campo para compatibilidad
                    qty = 0.0
                    if hasattr(line, 'qty_done'):
                        qty = line.qty_done or 0.0
                    elif hasattr(line, 'quantity'):
                        qty = line.quantity or 0.0
                    elif hasattr(line, 'product_uom_qty'):
                        qty = line.product_uom_qty or 0.0
                    total += qty
            move.qty_delivered_this = total

    @api.depends('qty_ordered', 'qty_delivered_this')
    def _compute_qty_pending(self):
        """
        Calcula la cantidad pendiente: Pedida - Entregado (este picking).
        Si no hay venta, muestra 0.
        """
        for move in self:
            if move.sale_line_id:
                move.qty_pending = move.qty_ordered - move.qty_delivered_this
            else:
                move.qty_pending = 0.0

    @api.depends('picking_id.sale_id')
    def _compute_has_sale_order(self):
        """
        Indica si el movimiento está vinculado a una venta.
        """
        for move in self:
            move.has_sale_order = bool(move.picking_id.sale_id)
