# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    ddpfw_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        related="move_id.picking_type_id.warehouse_id",
        store=True,
        index=True,
        readonly=True,
    )
    ddpfw_partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        related="picking_id.partner_id",
        store=True,
        index=True,
        readonly=True,
    )
    ddpfw_reference = fields.Char(
        string="Receipt",
        related="picking_id.name",
        store=True,
        index=True,
        readonly=True,
    )
    ddpfw_origin = fields.Char(
        string="Origin",
        related="move_id.origin",
        store=True,
        index=True,
        readonly=True,
    )
    ddpfw_state = fields.Selection(
        related="move_id.state",
        string="Move State",
        store=True,
        readonly=True,
    )
    ddpfw_move_qty = fields.Float(
        string="Planned Qty",
        related="move_id.product_uom_qty",
        store=True,
        readonly=True,
    )
