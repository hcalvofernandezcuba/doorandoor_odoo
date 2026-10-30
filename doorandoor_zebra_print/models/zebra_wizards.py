# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class ZebraZplMixin(models.AbstractModel):
    _name = "ddzp.zpl.mixin"
    _description = "DoorAndDoor Zebra ZPL helpers"

    @staticmethod
    def _zpl_text(value):
        """Escape ZPL control characters while keeping UTF-8 text readable."""
        text = str(value or "").replace("\r", " ").replace("\n", " ")
        return text.replace("\\", "_5C").replace("^", "_5E").replace("~", "_7E")

    def _zpl_field(self, value):
        return "^FH\\^FD%s^FS" % self._zpl_text(value)

    def _zpl_small(self, label):
        name = label.get("product_name") or "Producto"
        warehouse = label.get("warehouse_name") or label.get("document_name") or "Almacén"
        variant = " · ".join(
            filter(None, [label.get("label_model"), label.get("label_size"), label.get("label_design")])
        )
        code = label.get("barcode_value") or label.get("product_code") or label.get("label_reference")
        if not code:
            raise UserError(_("No existe un código imprimible para una de las etiquetas."))
        return "".join([
            "^XA^MMT^PW609^LL203^LS0^CI28",
            "^FO16,8^A0N,27,24^FB577,2,2,L,0", self._zpl_field(name),
            "^FO16,65^A0N,20,18^FB577,1,0,L,0", self._zpl_field(warehouse),
            "^FO16,88^A0N,18,16^FB577,1,0,L,0", self._zpl_field(variant),
            "^FO16,111^BY2,2,54^BCN,54,Y,N,N", self._zpl_field(code),
            "^XZ",
        ])

    def _zpl_large(self, label):
        name = label.get("product_name") or "Producto"
        code = label.get("product_code") or label.get("barcode_value") or label.get("label_reference")
        if not code:
            raise UserError(_("No existe un código imprimible para una de las etiquetas."))
        attributes = label.get("variant_attributes") or []
        attribute_text = "   ".join(
            "%s: %s" % (item.get("name", ""), item.get("value", ""))
            for item in attributes if item.get("name") or item.get("value")
        )
        details = " · ".join(filter(None, [
            label.get("label_model"), label.get("label_size"), label.get("label_design"),
            label.get("label_swing"), label.get("label_hinge"),
        ]))
        return "".join([
            "^XA^MMT^PW812^LL1218^LS0^CI28",
            "^FO42,36^A0N,40,35^FB728,2,8,L,0", self._zpl_field(label.get("document_name") or "Entrega"),
            "^FO42,145^A0N,52,45^FB728,3,8,L,0", self._zpl_field(name),
            "^FO42,330^A0N,31,27^FB728,2,6,L,0", self._zpl_field(label.get("customer_name")),
            "^FO42,425^A0N,28,24^FB728,5,6,L,0", self._zpl_field(attribute_text or details),
            "^FO60,790^BY3,2,150^BCN,150,Y,N,N", self._zpl_field(code),
            "^FO42,1050^A0N,24,21^FB728,2,4,L,0",
            self._zpl_field(_("Preparado por: %s   Impreso por: %s") % (
                label.get("prepared_by") or "", label.get("printed_by") or ""
            )),
            "^XZ",
        ])

    def _zebra_action(self, payloads, label_format):
        if not payloads:
            raise UserError(_("No se generaron etiquetas para imprimir."))
        renderer = self._zpl_large if label_format == "large" else self._zpl_small
        zpl = "".join(renderer(label) for label in payloads)
        return {
            "type": "ir.actions.client",
            "tag": "doorandoor_zebra_print.print",
            "params": {
                "zpl": zpl,
                "label_count": len(payloads),
                "format_name": "4×6" if label_format == "large" else "3×1",
            },
        }


class ProductLabelWizard(models.TransientModel):
    _name = "ddsl.product.label.wizard"
    _inherit = ["ddsl.product.label.wizard", "ddzp.zpl.mixin"]
    _description = "DoorAndDoor Product Label Wizard"

    def action_print_zebra(self):
        self.ensure_one()
        return self._zebra_action(self._prepare_label_payloads(), self.label_format)


class StockLabelWizard(models.TransientModel):
    _name = "ddsl.stock.label.wizard"
    _inherit = ["ddsl.stock.label.wizard", "ddzp.zpl.mixin"]
    _description = "DoorAndDoor Stock Label Wizard"

    def action_print_zebra(self):
        self.ensure_one()
        payloads, missing = self._iter_label_payloads()
        if missing:
            raise UserError(_("Registre primero los lotes o series de: %s") % ", ".join(sorted(set(missing))))
        return self._zebra_action(payloads, self.label_format)


class DocumentLabelWizard(models.TransientModel):
    _name = "ddsl.document.label.wizard"
    _inherit = ["ddsl.document.label.wizard", "ddzp.zpl.mixin"]
    _description = "DoorAndDoor Document Label Wizard"

    def action_print_zebra(self):
        self.ensure_one()
        payloads = self._prepare_label_payloads()
        if self.quantity > 1:
            payloads *= self.quantity
        return self._zebra_action(payloads, self.label_format)
