from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddhi_historical_special = fields.Boolean(
        string="Especial histórico", copy=False, index=True,
        help="Creado desde una venta histórica para reconstruir su ciclo documental sin exigir fabricación retroactiva.",
    )
    ddhi_source_document_id = fields.Many2one(
        "doorandoor.legacy.delivery.ocr", string="OCR histórico origen",
        readonly=True, copy=False, ondelete="restrict",
    )
    ddhi_source_line_id = fields.Many2one(
        "doorandoor.legacy.delivery.ocr.line", string="Línea OCR origen",
        readonly=True, copy=False, ondelete="restrict",
    )
