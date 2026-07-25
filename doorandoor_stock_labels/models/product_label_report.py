from odoo import models


class ReportDoorAndDoorProductLabels(models.AbstractModel):
    _name = "report.doorandoor_stock_labels.product_labels_report"
    _description = "DoorAndDoor Product Labels Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["ddsl.product.label.wizard"].browse(docids)
        data = data or {}
        return {
            "doc_ids": docs.ids,
            "doc_model": "ddsl.product.label.wizard",
            "docs": docs,
            "labels": data.get("labels", []),
        }
