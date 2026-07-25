from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def ddsl_should_print_label(self):
        self.ensure_one()
        return bool(self.product_id.product_tmpl_id.ddsl_print_label_on_receipt)

