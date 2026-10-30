from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import UserError


class HistoricalSpecialProductWizard(models.TransientModel):
    _name = "doorandoor.legacy.special.product.wizard"
    _description = "Crear ITEM especial para venta histórica"

    line_id = fields.Many2one(
        "doorandoor.legacy.delivery.ocr.line", required=True, readonly=True,
    )
    name = fields.Char(string="Nombre histórico", required=True)
    size = fields.Char(string="Medida")
    swing = fields.Char(string="Mano")
    color = fields.Char(string="Color")
    glass = fields.Char(string="Cristal")
    model_code = fields.Char(string="Modelo")
    category_id = fields.Many2one(
        "product.category", string="Categoría", required=True,
        default=lambda self: self.env["product.category"].search([], order="id", limit=1),
    )
    notes = fields.Text(
        string="Observaciones",
        default="ITEM creado para reconstrucción documental de una venta histórica. Configuración fabril pendiente.",
        required=True,
    )

    def action_create_historical_special(self):
        self.ensure_one()
        line = self.line_id.exists()
        document = line.document_id
        if not line or document.state not in ("review", "ready"):
            raise UserError(_("La línea OCR ya no está disponible para crear el especial histórico."))
        code = self.env["ir.sequence"].next_by_code("ddsp.special.product") or "ESP-HIST"
        evidence = [
            {"attribute_name": label, "value": value.strip(), "modified": False}
            for label, value in (
                ("MEDIDA", self.size), ("swing", self.swing),
                ("color", self.color), ("glass", self.glass),
                ("modelo", self.model_code),
            ) if (value or "").strip()
        ]
        template = self.env["product.template"].sudo().create({
            "name": self.name.strip(),
            "default_code": code,
            "barcode": self.env["product.template"]._ddsp_next_special_barcode(),
            "type": "consu",
            "is_storable": True,
            # DoorAndDoor serializes every physical unit through
            # inventory.unit.serial.  Native stock.lot tracking must remain
            # disabled or the historical receipt would require a second,
            # incompatible serial number for the same unit.
            "tracking": "none",
            "categ_id": self.category_id.id,
            "uom_id": self.env.ref("uom.product_uom_unit").id,
            "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            "sale_ok": True,
            "purchase_ok": False,
            "company_id": document.company_id.id,
            "ddsp_is_special": True,
            "ddsp_product_kind": "special",
            "ddsp_allow_special": False,
            "ddsp_manufacturing_family": "windows" if "WINDOW" in self.name.upper() else "doors",
            "ddsp_special_changes": evidence,
            "ddsp_special_notes": self.notes,
            "ddsp_production_instructions": "Pendiente de completar después de estabilizar el inventario histórico.",
            "ddsp_bom_state": "draft",
            "ddhi_historical_special": True,
            "ddhi_source_document_id": document.id,
            "ddhi_source_line_id": line.id,
        })
        product = template.product_variant_id
        if not product:
            raise UserError(_("No fue posible crear la variante del especial histórico."))

        line.write({
            "product_id": product.id,
            "match_state": "matched",
            "confidence": 100.0,
            "mapping_proposed": False,
            "mapping_confirmed": True,
        })
        document._save_reviewed_product_mappings()
        document.message_post(body=Markup(
            "<p>Se creó el ITEM especial histórico <strong>%(product)s</strong> "
            "desde la línea OCR. Puede continuar el ciclo documental, labels y "
            "controles Hanger sin una fabricación retroactiva. La configuración "
            "fabril permanece pendiente.</p>"
        ) % {"product": escape(product.display_name)})
        template.message_post(body=Markup(
            "<p>Origen histórico: %(document)s / %(reference)s. Evidencia conservada "
            "en el documento OCR %(ocr)s.</p>"
        ) % {
            "document": escape(document.file_name),
            "reference": escape(document.external_reference or ""),
            "ocr": escape(document.display_name),
        })
        return {"type": "ir.actions.act_window_close"}
