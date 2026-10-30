from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLabelWizard(models.TransientModel):
    _name = "ddsl.stock.label.wizard"
    _description = "DoorAndDoor Stock Label Wizard"

    picking_id = fields.Many2one("stock.picking", required=True, readonly=True)
    print_mode = fields.Selection(
        selection=[
            ("tracking", "Tracking / Lot / Serial"),
            ("product_code", "Product Code"),
        ],
        string="Label Mode",
        default="tracking",
        required=True,
        help="Use tracking data for receipt labels or force labels by product code for supplier preparation.",
    )
    label_format = fields.Selection(
        [("small", "Almacén — Zebra 3×1"), ("large", "Entrega — Zebra 4×6")],
        string="Tamaño de etiqueta", default="small", required=True,
    )
    include_untracked_qty = fields.Boolean(
        string="Include Untracked Quantities",
        default=True,
        help="When a product has no serial/lot, print labels based on received quantity.",
    )
    only_flagged_products = fields.Boolean(
        string="Only Products Marked For Labels",
        default=True,
        help="If enabled, only products configured to print labels on receipt are included.",
    )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        picking_id = self.env.context.get("default_picking_id")
        if picking_id:
            values["picking_id"] = picking_id
        return values

    def _iter_label_payloads(self):
        self.ensure_one()
        if self.print_mode == "product_code":
            return self._iter_product_code_payloads(), []

        payloads = []
        missing_tracked_products = []
        move_lines = self.picking_id.move_line_ids.filtered(lambda line: line.product_id)
        if self.only_flagged_products:
            move_lines = move_lines.filtered(lambda line: line.ddsl_should_print_label())
        processed_lot_keys = set()

        for line in move_lines:
            product = line.product_id
            tracking = product.tracking
            label_reference = (
                product.barcode
                if product.product_tmpl_id.ddsl_label_use_barcode and product.barcode
                else product.default_code or product.barcode or product.display_name
            )
            if tracking == "lot" and (line.lot_id or line.lot_name):
                lot_name = line.lot_id.name if line.lot_id else line.lot_name
                lot_key = (product.id, lot_name)
                if lot_key in processed_lot_keys:
                    continue
                processed_lot_keys.add(lot_key)
                lot = line.lot_id or self.env["stock.lot"]
                mobile_url = product.ddsl_get_lot_mobile_url(lot) if lot else product.ddsl_get_mobile_url()
                payloads.append(
                    {
                        "product_id": product.id,
                        "product_name": product.ddsl_get_label_title(),
                        "default_code": product.default_code or "",
                        "product_barcode": product.barcode or "",
                        "label_reference": lot_name,
                        "barcode_value": lot_name,
                        "lot_name": lot_name,
                        "mobile_url": mobile_url,
                        "mobile_qr_src": product.ddsl_get_mobile_qr_src(mobile_url),
                        "barcode_src": product.ddsl_get_label_barcode_src(lot_name),
                    }
                )
                continue

            if tracking == "serial" and (line.lot_id or line.lot_name):
                lot_name = line.lot_id.name if line.lot_id else line.lot_name
                mobile_url = product.ddsl_get_lot_mobile_url(line.lot_id) if line.lot_id else product.ddsl_get_mobile_url()
                payloads.append(
                    {
                        "product_id": product.id,
                        "product_name": product.ddsl_get_label_title(),
                        "default_code": product.default_code or "",
                        "product_barcode": product.barcode or "",
                        "label_reference": lot_name,
                        "barcode_value": lot_name,
                        "lot_name": lot_name,
                        "mobile_url": mobile_url,
                        "mobile_qr_src": product.ddsl_get_mobile_qr_src(mobile_url),
                        "barcode_src": product.ddsl_get_label_barcode_src(lot_name),
                    }
                )
                continue

            if tracking != "none":
                missing_tracked_products.append(product.display_name)
                continue

            if not self.include_untracked_qty:
                continue

            qty = int(round(line.quantity or line.qty_done or 0))
            mobile_url = product.ddsl_get_mobile_url()
            for _index in range(max(qty, 0)):
                payloads.append(
                    {
                        "product_id": product.id,
                        "product_name": product.ddsl_get_label_title(),
                        "default_code": product.default_code or "",
                        "product_barcode": product.barcode or "",
                        "label_reference": label_reference or "",
                        "barcode_value": label_reference or "",
                        "lot_name": "",
                        "mobile_url": mobile_url,
                        "mobile_qr_src": product.ddsl_get_mobile_qr_src(mobile_url),
                        "barcode_src": product.ddsl_get_label_barcode_src(label_reference),
                    }
                )
        return payloads, missing_tracked_products

    def _iter_product_code_payloads(self):
        self.ensure_one()
        payloads = []
        move_lines = self.picking_id.move_line_ids.filtered(lambda line: line.product_id)
        if self.only_flagged_products:
            move_lines = move_lines.filtered(lambda line: line.ddsl_should_print_label())

        for line in move_lines:
            product = line.product_id
            label_reference = (
                product.barcode
                if product.product_tmpl_id.ddsl_label_use_barcode and product.barcode
                else product.default_code or product.barcode or product.display_name
            )
            qty = int(round(line.quantity or line.qty_done or 0))
            if qty <= 0:
                qty = 1
            mobile_url = product.ddsl_get_mobile_url()
            for _index in range(qty):
                payloads.append(
                    {
                        "product_id": product.id,
                        "product_name": product.ddsl_get_label_title(),
                        "default_code": product.default_code or "",
                        "product_barcode": product.barcode or "",
                        "label_reference": label_reference or "",
                        "barcode_value": label_reference or "",
                        "lot_name": "",
                        "mobile_url": mobile_url,
                        "mobile_qr_src": product.ddsl_get_mobile_qr_src(mobile_url),
                        "barcode_src": product.ddsl_get_label_barcode_src(label_reference),
                    }
                )
        return payloads

    def action_print_labels(self):
        self.ensure_one()
        payloads, missing_tracked_products = self._iter_label_payloads()
        if missing_tracked_products:
            unique_products = sorted(set(missing_tracked_products))
            raise UserError(
                _(
                    "Antes de imprimir etiquetas, registre los numeros de serie o lote reales en las operaciones detalladas para estos productos:\n- %s"
                )
                % "\n- ".join(unique_products)
            )
        if not payloads:
            raise UserError(
                _(
                    "No se generaron etiquetas. Revise cantidades recibidas, numeros de serie/lote, modo de impresion o configuracion del producto."
                )
            )
        action_xmlid = (
            "doorandoor_stock_labels.action_report_ddsl_stock_labels_large"
            if self.label_format == "large"
            else "doorandoor_stock_labels.action_report_ddsl_stock_labels"
        )
        action = self.env.ref(action_xmlid)
        return action.report_action(self, data={"labels": payloads, "picking_name": self.picking_id.name})
