from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentLabelWizard(models.TransientModel):
    _name = "ddsl.document.label.wizard"
    _description = "DoorAndDoor Document Label Wizard"

    move_id = fields.Many2one("account.move", readonly=True)
    production_id = fields.Many2one("mrp.production", readonly=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    quantity = fields.Integer(string="Labels Quantity", default=1, required=True)
    label_format = fields.Selection(
        [("small", "Almacén — Zebra 3×1"), ("large", "Entrega — Zebra 4×6")],
        string="Tamaño de etiqueta", default="small", required=True,
    )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        if self.env.context.get("default_move_id"):
            values["move_id"] = self.env.context["default_move_id"]
            values["label_format"] = "large"
        if self.env.context.get("default_production_id"):
            values["production_id"] = self.env.context["default_production_id"]
            values["label_format"] = "small"
        return values

    def _get_document_title(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id.name or self.move_id.ref or "INV"
        return self.production_id.name or "STOCK"

    def _get_customer_name(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id.partner_id.display_name or ""
        production = self.production_id
        move = self.env["account.move"].search(
            [("fulfillment_line_ids.mrp_production_id", "=", production.id)],
            order="id desc",
            limit=1,
        )
        if move:
            return move.partner_id.display_name or ""
        return "STOCK"

    def _get_prepared_by_name(self):
        self.ensure_one()
        if self.move_id:
            return (self.move_id.invoice_user_id or self.move_id.create_uid).name or ""
        production = self.production_id
        responsible = getattr(production, "user_id", False)
        return (responsible or production.create_uid).name or ""

    def _iter_products(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id.invoice_line_ids.filtered(
                lambda line: line.product_id and line.display_type in (False, "product")
            )
        product = self.production_id.product_id
        return self.env["product.product"].browse(product.id) if product else self.env["product.product"]

    def _prepare_label_payloads(self):
        self.ensure_one()
        payloads = []
        printed_by = self.env.user.name or ""
        prepared_by = self._get_prepared_by_name()
        document_name = self._get_document_title()
        customer_name = self._get_customer_name()

        if self.move_id:
            products = self.move_id.invoice_line_ids.filtered(
                lambda line: line.product_id and line.display_type in (False, "product")
            )
            for line in products:
                product = line.product_id
                tmpl = product.product_tmpl_id
                product_code = tmpl.ddsl_product_label_code or product.default_code or product.barcode
                if not product_code:
                    raise UserError(
                        _("El producto %s debe tener Codigo de producto para imprimir labels.") % product.display_name
                    )
                copies = max(int(round(line.quantity or 0)), 1)
                label = {
                    "document_name": document_name,
                    "customer_name": customer_name,
                    "product_name": product.display_name or "",
                    "variant_attributes": line._ddpc_get_configuration_attributes(),
                    "label_model": tmpl.ddsl_label_model or "",
                    "label_design": tmpl.ddsl_label_design or "",
                    "label_size": tmpl.ddsl_label_size or "",
                    "label_swing": tmpl.ddsl_label_swing or "",
                    "label_hinge": tmpl.ddsl_label_hinge or "",
                    "product_code": product_code,
                    "barcode_src": product.ddsl_get_label_barcode_src(product_code),
                    "prepared_by": prepared_by,
                    "printed_by": printed_by,
                }
                for _i in range(copies):
                    payloads.append(dict(label))
            return payloads

        production = self.production_id
        product = production.product_id
        tmpl = product.product_tmpl_id
        product_code = tmpl.ddsl_product_label_code or product.default_code or product.barcode
        if not product_code:
            raise UserError(
                _("El producto %s debe tener Codigo de producto para imprimir labels.") % product.display_name
            )
        copies = max(int(round(production.product_qty or 0)), 1)
        label = {
            "document_name": document_name,
            "customer_name": customer_name,
            "product_name": product.display_name or "",
            "variant_attributes": [
                {
                    "name": value.attribute_id.display_name or "",
                    "value": value.product_attribute_value_id.display_name or "",
                }
                for value in product.product_template_attribute_value_ids.sorted(
                    lambda item: (item.attribute_id.sequence, item.attribute_id.id, item.id)
                )
            ],
            "label_model": tmpl.ddsl_label_model or "",
            "label_design": tmpl.ddsl_label_design or "",
            "label_size": tmpl.ddsl_label_size or "",
            "label_swing": tmpl.ddsl_label_swing or "",
            "label_hinge": tmpl.ddsl_label_hinge or "",
            "product_code": product_code,
            "barcode_src": product.ddsl_get_label_barcode_src(product_code),
            "prepared_by": prepared_by,
            "printed_by": printed_by,
        }
        for _i in range(copies):
            payloads.append(dict(label))
        return payloads

    def action_print_labels(self):
        self.ensure_one()
        if not self.move_id and not self.production_id:
            raise UserError(_("Debe abrir este wizard desde una factura o una orden de manufactura."))
        payloads = self._prepare_label_payloads()
        if not payloads:
            raise UserError(
                _(
                    "No se generaron labels para este documento. Revise que existan lineas de producto validas y que los productos tengan Codigo de producto."
                )
            )
        if self.quantity > 1:
            payloads = payloads * self.quantity
        action_xmlid = (
            "doorandoor_stock_labels.action_report_ddsl_document_labels_large"
            if self.label_format == "large"
            else "doorandoor_stock_labels.action_report_ddsl_document_labels"
        )
        action = self.env.ref(action_xmlid)
        return action.report_action(self, data={"labels": payloads})
