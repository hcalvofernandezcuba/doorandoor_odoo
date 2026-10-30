import base64
from io import BytesIO
from urllib.parse import quote

import qrcode
from reportlab.graphics.barcode import createBarcodeDrawing

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
        value = self._ddsn_get_barcode_document_name() or ""
        try:
            drawing = createBarcodeDrawing(
                "Code128", value=value, width=300, height=50, humanReadable=True
            )
            payload = base64.b64encode(drawing.asString("png")).decode()
            return f"data:image/png;base64,{payload}"
        except Exception:
            encoded_value = quote(value)
            base_url = self._ddsn_get_report_barcode_base_url()
            return (
                f"{base_url}/report/barcode/?barcode_type=Code128"
                f"&value={encoded_value}&width=600&height=100&humanreadable=1"
            )

    def _ddsn_get_document_qr_img_src(self):
        self.ensure_one()
        value = self._ddsn_get_barcode_backend_url() or ""
        try:
            image = qrcode.make(value)
            stream = BytesIO()
            image.save(stream, format="PNG")
            payload = base64.b64encode(stream.getvalue()).decode()
            return f"data:image/png;base64,{payload}"
        except Exception:
            encoded_value = quote(value, safe="")
            base_url = self._ddsn_get_report_barcode_base_url()
            return f"{base_url}/report/barcode/?barcode_type=QR&value={encoded_value}&width=180&height=180"
