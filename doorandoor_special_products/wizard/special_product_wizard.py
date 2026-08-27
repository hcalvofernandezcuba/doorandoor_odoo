from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SpecialProductWizard(models.TransientModel):
    _name = "ddsp.special.product.wizard"
    _description = "Crear producto transformado desde documento comercial"

    invoice_line_id = fields.Many2one("account.move.line", readonly=True)
    sale_order_line_id = fields.Many2one("sale.order.line", readonly=True)
    base_product_id = fields.Many2one("product.product", required=True, readonly=True)
    name = fields.Char(string="Nombre del producto transformado", required=True)
    default_code = fields.Char(string="Referencia interna", readonly=True)
    # Compatibilidad con vistas/sesiones cargadas antes de 18.0.1.1.2.
    # No se muestra ni participa en la nomenclatura de los nuevos especiales.
    length = fields.Float(string="Largo historico", readonly=True)
    width = fields.Float(string="Ancho transformado")
    height = fields.Float(string="Alto transformado")
    available_attribute_ids = fields.Many2many(
        "product.attribute", compute="_compute_available_attribute_ids"
    )
    special_attribute_id = fields.Many2one(
        "product.attribute",
        string="Atributo a modificar",
        domain="[('id', 'in', available_attribute_ids)]",
    )
    special_value = fields.Char(string="Valor transformado")
    special_notes = fields.Text(string="Especificaciones de transformacion", required=True)
    production_instructions = fields.Text(string="Instrucciones de fabricacion", required=True)
    price_unit = fields.Monetary(string="Precio de venta", required=True)
    currency_id = fields.Many2one(
        "res.currency", compute="_compute_document_values", readonly=True
    )
    base_bom_id = fields.Many2one(
        "mrp.bom",
        string="LDM base",
        domain="[('product_tmpl_id', '=', base_product_tmpl_id), ('active', '=', True)]",
    )
    base_product_tmpl_id = fields.Many2one(related="base_product_id.product_tmpl_id", readonly=True)
    copy_base_operations = fields.Boolean(
        string="Copiar operaciones de la LDM base", default=True
    )
    component_line_ids = fields.One2many(
        "ddsp.special.product.wizard.line", "wizard_id", string="Componentes de la nueva LDM"
    )

    def _ddsp_configured_variant_price(self):
        """Return the base variant price maintained by Administration."""
        self.ensure_one()
        product = self.base_product_id
        if not product:
            return 0.0
        return product.product_tmpl_id.list_price + (
            product.ddpc_variant_extra_price
            if "ddpc_variant_extra_price" in product._fields
            else 0.0
        )

    @api.depends("base_product_id.product_tmpl_id.attribute_line_ids.attribute_id")
    def _compute_available_attribute_ids(self):
        for wizard in self:
            wizard.available_attribute_ids = (
                wizard.base_product_id.product_tmpl_id.attribute_line_ids.attribute_id
            )

    @api.depends("invoice_line_id.currency_id", "sale_order_line_id.currency_id")
    def _compute_document_values(self):
        for wizard in self:
            wizard.currency_id = (
                wizard.invoice_line_id.currency_id
                or wizard.sale_order_line_id.currency_id
            )

    @staticmethod
    def _ddsp_format_measure(value):
        return f"{value:g}"

    def _ddsp_build_special_name(self):
        self.ensure_one()
        base_name = self.base_product_id.product_tmpl_id.name or self.base_product_id.display_name
        if self.special_attribute_id and self.special_value:
            return _("%s Transformado %s: %s") % (
                base_name,
                self.special_attribute_id.display_name,
                self.special_value.strip(),
            )
        if self.width and self.height:
            dimensions = "x".join(
                self._ddsp_format_measure(value)
                for value in (self.width, self.height)
            )
            return _("%s Transformado %s") % (base_name, dimensions)
        return _("%s Transformado %s") % (base_name, self.default_code or "")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        invoice_line = self.env["account.move.line"].browse(
            values.get("invoice_line_id") or self.env.context.get("default_invoice_line_id")
        ).exists()
        sale_line = self.env["sale.order.line"].browse(
            values.get("sale_order_line_id")
            or self.env.context.get("default_sale_order_line_id")
        ).exists()
        document_line = invoice_line or sale_line
        if not document_line:
            return values
        product = document_line.product_id
        code = self.env["ir.sequence"].next_by_code("ddsp.special.product") or "ESP"
        values.update(
            {
                "invoice_line_id": invoice_line.id,
                "sale_order_line_id": sale_line.id,
                "base_product_id": product.id,
                "name": _("%s Transformado %s") % (product.product_tmpl_id.name, code),
                "default_code": code,
                "price_unit": (
                    product.product_tmpl_id.list_price
                    + (
                        product.ddpc_variant_extra_price
                        if "ddpc_variant_extra_price" in product._fields
                        else 0.0
                    )
                ),
                "base_bom_id": False,
                "component_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "product_uom_id": product.uom_id.id,
                        },
                    )
                ],
            }
        )
        return values

    @api.onchange(
        "width",
        "height",
        "special_attribute_id",
        "special_value",
        "base_product_id",
        "default_code",
    )
    def _onchange_special_dimensions_name(self):
        if self.base_product_id:
            self.name = self._ddsp_build_special_name()

    @api.onchange("base_bom_id")
    def _onchange_base_bom_id(self):
        self.component_line_ids = [(5, 0, 0)] + [
            (0, 0, {"product_id": line.product_id.id, "product_qty": line.product_qty, "product_uom_id": line.product_uom_id.id})
            for line in self.base_bom_id.bom_line_ids
        ]

    def action_create_special_product(self):
        self.ensure_one()
        invoice_line = self.invoice_line_id
        sale_line = self.sale_order_line_id
        if bool(invoice_line) == bool(sale_line):
            raise UserError(_("El producto transformado debe pertenecer a una sola linea comercial."))
        if invoice_line and (
            invoice_line.move_id.state != "draft"
            or invoice_line.move_id.move_type != "out_invoice"
        ):
            raise UserError(_("La factura debe permanecer en borrador mientras se crea el producto transformado."))
        if sale_line and sale_line.order_id.state not in ("draft", "sent"):
            raise UserError(_("La cotizacion debe permanecer abierta mientras se crea el producto transformado."))
        if not self.special_attribute_id or not (self.special_value or "").strip():
            raise UserError(_("Selecciona el atributo que cambia y escribe su valor transformado."))
        if self.component_line_ids.filtered(lambda component: component.product_qty <= 0):
            raise UserError(_("Todos los componentes deben tener una cantidad mayor que cero."))
        dimensions = (self.width, self.height)
        if any(dimensions) and not all(value > 0 for value in dimensions):
            raise UserError(
                _("Para usar medidas en el nombre debes completar Ancho y Alto con valores mayores que cero.")
            )
        final_name = self._ddsp_build_special_name()
        # Recalculate on the server so a salesperson cannot inject a manual
        # price by modifying the wizard request in the browser.
        configured_price = self._ddsp_configured_variant_price()
        company = (
            invoice_line.move_id.company_id
            if invoice_line
            else sale_line.order_id.company_id
        )

        base_template = self.base_product_id.product_tmpl_id
        if not base_template.ddsp_allow_special or base_template.ddsp_is_special:
            raise UserError(
                _("El producto %s no permite crear productos transformados.")
                % base_template.display_name
            )
        if not base_template.is_storable:
            raise UserError(_("El producto base debe ser almacenable para crear una transformacion."))
        template_vals = {
            "name": final_name,
            "default_code": self.default_code,
            "barcode": self.env["product.template"]._ddsp_next_special_barcode(),
            "type": base_template.type,
            "is_storable": True,
            "categ_id": base_template.categ_id.id,
            "uom_id": base_template.uom_id.id,
            "uom_po_id": base_template.uom_po_id.id,
            "list_price": configured_price,
            "standard_price": base_template.standard_price,
            "sale_ok": True,
            "purchase_ok": False,
            "route_ids": [(6, 0, base_template.route_ids.ids)],
            "taxes_id": [(6, 0, base_template.taxes_id.ids)],
            "supplier_taxes_id": [(6, 0, base_template.supplier_taxes_id.ids)],
            "company_id": company.id,
            "ddsp_is_special": True,
            "ddsp_product_kind": "transformed",
            "ddsp_allow_special": False,
            "ddsp_manufacturing_family": base_template.ddsp_manufacturing_family,
            "ddsp_base_product_tmpl_id": base_template.id,
            "ddsp_origin_invoice_id": invoice_line.move_id.id if invoice_line else False,
            "ddsp_origin_invoice_line_id": invoice_line.id if invoice_line else False,
            "ddsp_origin_sale_order_id": sale_line.order_id.id if sale_line else False,
            "ddsp_origin_sale_order_line_id": sale_line.id if sale_line else False,
            "ddsp_special_attribute_id": self.special_attribute_id.id,
            "ddsp_special_value": self.special_value.strip(),
            "ddsp_width": self.width,
            "ddsp_height": self.height,
            "ddsp_special_notes": self.special_notes,
            "ddsp_production_instructions": self.production_instructions,
            "ddsp_bom_state": "draft",
        }
        template = self.env["product.template"].sudo().create(template_vals)
        product = template.product_variant_id
        bom_vals = {
            "product_tmpl_id": template.id,
            "product_id": product.id,
            "product_qty": 1.0,
            "product_uom_id": template.uom_id.id,
            "company_id": company.id,
            "type": "normal",
            "bom_line_ids": [
                (0, 0, {"product_id": component.product_id.id, "product_qty": component.product_qty, "product_uom_id": component.product_uom_id.id})
                for component in self.component_line_ids
            ],
        }
        self.env["mrp.bom"].sudo().create(bom_vals)
        template._ddsp_validate_special_bom(require_production_user=False)
        document_line = invoice_line or sale_line
        document_line.with_context(ddsn_automatic_pricing=True).write(
            {"product_id": product.id, "name": final_name, "price_unit": configured_price}
        )
        if invoice_line and invoice_line.generated_sale_line_id:
            invoice_line.generated_sale_line_id.with_context(ddsn_automatic_pricing=True).write(
                {
                    "product_id": product.id,
                    "name": final_name,
                    "price_unit": configured_price,
                }
            )
        document = invoice_line.move_id if invoice_line else sale_line.order_id
        document.message_post(
            body=_("Se creo el producto transformado %s con su LDM validada automaticamente.") % template.display_name
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Producto transformado"),
            "res_model": "product.template",
            "res_id": template.id,
            "view_mode": "form",
            "target": "current",
        }


class SpecialProductWizardLine(models.TransientModel):
    _name = "ddsp.special.product.wizard.line"
    _description = "Componente de LDM transformada"

    wizard_id = fields.Many2one("ddsp.special.product.wizard", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Componente", required=True)
    product_qty = fields.Float(string="Cantidad", required=True, default=1.0)
    product_uom_id = fields.Many2one("uom.uom", string="Unidad", required=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
