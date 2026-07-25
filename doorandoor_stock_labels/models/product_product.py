from odoo import models

from .barcode_utils import make_code128_data_uri, make_qr_data_uri


class ProductProduct(models.Model):
    _inherit = "product.product"

    def ddsl_get_label_reference(self):
        self.ensure_one()
        return self.barcode or self.default_code or str(self.id)

    def ddsl_get_label_title(self):
        self.ensure_one()
        return self.display_name or self.name or ""

    def ddsl_get_mobile_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return f"{base_url}/web#id={self.id}&model=product.product&view_type=form"

    def ddsl_get_lot_mobile_url(self, lot):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return f"{base_url}/web#id={lot.id}&model=stock.lot&view_type=form"

    def ddsl_get_mobile_qr_src(self, mobile_url=None):
        self.ensure_one()
        return make_qr_data_uri(mobile_url or self.ddsl_get_mobile_url())

    def ddsl_get_label_barcode_src(self, value=None):
        self.ensure_one()
        return make_code128_data_uri(value or self.ddsl_get_label_reference())
