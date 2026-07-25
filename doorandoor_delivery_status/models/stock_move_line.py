# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    qty_ordered = fields.Float(
        string="Cantidad Pedida",
        related="move_id.qty_ordered",
        readonly=True,
        digits="Product Unit of Measure",
    )

    qty_delivered_this = fields.Float(
        string="Entregado",
        related="move_id.qty_delivered_this",
        readonly=True,
        digits="Product Unit of Measure",
    )

    qty_pending = fields.Float(
        string="Pendiente",
        related="move_id.qty_pending",
        readonly=True,
        digits="Product Unit of Measure",
    )
