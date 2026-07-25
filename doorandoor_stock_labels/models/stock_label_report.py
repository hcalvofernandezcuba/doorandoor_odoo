from odoo import models


class ReportDoorAndDoorStockLabels(models.AbstractModel):
    _name = "report.doorandoor_stock_labels.stock_labels_report"
    _description = "DoorAndDoor Stock Labels Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["ddsl.stock.label.wizard"].browse(docids)
        data = data or {}
        return {
            "doc_ids": docids,
            "doc_model": "ddsl.stock.label.wizard",
            "docs": docs,
            "labels": data.get("labels", []),
            "picking_name": data.get("picking_name", ""),
        }
