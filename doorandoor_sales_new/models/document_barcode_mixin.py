from urllib.parse import quote

from odoo import models


class DoorAndDoorDocumentBarcodeMixin(models.AbstractModel):
    _name = "doorandoor.document.barcode.mixin"
    _description = "DoorAndDoor Document Barcode Mixin"

    def _ddsn_get_report_barcode_base_url(self):
        self.ensure_one()
        return (self.env["ir.config_parameter"].sudo().get_param("web.base.url", "") or "").rstrip("/")

    def _ddsn_get_barcode_document_name(self):
        self.ensure_one()
        return self.display_name or ""

    def _ddsn_get_barcode_backend_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"

    def _ddsn_get_barcode_img_src(self):
        self.ensure_one()
        value = quote(self._ddsn_get_barcode_document_name() or "")
        base_url = self._ddsn_get_report_barcode_base_url()
        return (
            f"{base_url}/report/barcode/?barcode_type=Code128"
            f"&value={value}&width=600&height=100&humanreadable=1"
        )

    def _ddsn_get_document_qr_img_src(self):
        self.ensure_one()
        value = quote(self._ddsn_get_barcode_backend_url() or "", safe="")
        base_url = self._ddsn_get_report_barcode_base_url()
        return f"{base_url}/report/barcode/?barcode_type=QR&value={value}&width=180&height=180"
