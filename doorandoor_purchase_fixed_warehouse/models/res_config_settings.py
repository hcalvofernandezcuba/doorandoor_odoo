# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ddpfw_purchase_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Mandatory Purchase Warehouse",
        config_parameter="doorandoor_purchase_fixed_warehouse.purchase_warehouse_id",
        help="Warehouse whose incoming operation type will be forced on all purchase orders.",
    )
