from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price = fields.Float(groups="base.group_system")


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(groups="base.group_system")
    value_svl = fields.Float(groups="base.group_system")
    avg_cost = fields.Monetary(groups="base.group_system")
    total_value = fields.Monetary(groups="base.group_system")


class StockQuant(models.Model):
    _inherit = "stock.quant"

    value = fields.Monetary(groups="base.group_system")


class StockMove(models.Model):
    _inherit = "stock.move"

    price_unit = fields.Float(groups="base.group_system")


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    unit_cost = fields.Float(groups="base.group_system")
    value = fields.Monetary(groups="base.group_system")
    remaining_value = fields.Monetary(groups="base.group_system")
    price_diff_value = fields.Float(groups="base.group_system")
