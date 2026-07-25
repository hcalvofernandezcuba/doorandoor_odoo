from odoo import models


class ReportDoorAndDoorDocumentLabels(models.AbstractModel):
    _name = "report.doorandoor_stock_labels.document_labels_report"
    _description = "DoorAndDoor Document Labels Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["ddsl.document.label.wizard"].browse(docids)
        data = data or {}
        return {
            "doc_ids": docs.ids,
            "doc_model": "ddsl.document.label.wizard",
            "docs": docs,
            "labels": data.get("labels", []),
        }
