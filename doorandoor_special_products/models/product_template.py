from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_is_zero


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddsp_is_special = fields.Boolean(string="Producto personalizado", copy=False, index=True)
    ddsp_product_kind = fields.Selection(
        [("transformed", "Transformado"), ("special", "Especial")],
        string="Tipo de producto personalizado",
        copy=False,
        index=True,
    )
    ddsp_manufacturing_family = fields.Selection(
        [("windows", "WINDOWS"), ("doors", "DOORS")],
        string="Familia de fabricacion",
        index=True,
    )
    ddsp_is_manufacturing_template = fields.Boolean(
        string="Plantilla maestra de fabricacion",
        help="Identifica un producto tecnico usado como modelo de receta para WINDOWS o DOORS.",
    )
    ddsp_template_output_name = fields.Char(
        string="Nombre comercial resultante",
        help="Nombre base usado al crear productos especiales desde esta plantilla.",
    )
    ddsp_default_special_component_id = fields.Many2one(
        "product.product",
        string="Componente automatico",
        domain="[('active', '=', True)]",
        help="Componente de la LDM minima cuando la plantilla no tiene receta.",
    )
    ddsp_default_special_component_qty = fields.Float(
        string="Cantidad automatica", default=3.0
    )
    ddsp_allow_vendor_price = fields.Boolean(
        string="Permitir precio de proveedor en Especial",
        help=(
            "Permite al comercial introducir el precio cotizado por el proveedor "
            "al crear un producto Especial desde esta plantilla."
        ),
    )
    ddsp_source_bom_template_id = fields.Many2one(
        "mrp.bom", string="LDM maestra utilizada", copy=False, readonly=True
    )

    def _ddsp_get_default_special_component(self):
        self.ensure_one()
        if self.ddsp_default_special_component_id:
            return self.ddsp_default_special_component_id
        Product = self.env["product.product"].sudo()
        component = Product.search(
            [("product_tmpl_id.name", "=ilike", "bisagras"), ("active", "=", True)],
            limit=1,
        )
        if not component:
            component = Product.search(
                [("product_tmpl_id.name", "=ilike", "bisagra"), ("active", "=", True)],
                limit=1,
            )
        if not component:
            component_template = self.env["product.template"].sudo().create(
                {
                    "name": "Bisagras para producto especial",
                    "default_code": "DD-BISAGRA-DEFAULT",
                    "type": "consu",
                    "is_storable": True,
                    "sale_ok": False,
                    "purchase_ok": True,
                }
            )
            component = component_template.product_variant_id
        return component
    ddsp_allow_special = fields.Boolean(
        string="Permitir productos transformados",
        default=True,
        help="Permite usar este producto como base para crear productos transformados desde documentos comerciales.",
    )
    ddsp_base_product_tmpl_id = fields.Many2one(
        "product.template", string="Producto base", copy=False, readonly=True
    )
    ddsp_origin_invoice_id = fields.Many2one(
        "account.move", string="Factura de origen", copy=False, readonly=True
    )
    ddsp_origin_invoice_line_id = fields.Many2one(
        "account.move.line", string="Linea de factura de origen", copy=False, readonly=True
    )
    ddsp_origin_sale_order_id = fields.Many2one(
        "sale.order", string="Cotizacion de origen", copy=False, readonly=True
    )
    ddsp_origin_sale_order_line_id = fields.Many2one(
        "sale.order.line", string="Linea de cotizacion de origen", copy=False, readonly=True
    )
    ddsp_special_attribute_id = fields.Many2one(
        "product.attribute", string="Atributo transformado", copy=False, readonly=True
    )
    ddsp_special_value = fields.Char(string="Valor transformado", copy=False, readonly=True)
    ddsp_special_changes = fields.Json(string="Cambios de transformacion", copy=False, readonly=True)
    ddsp_special_changes_display = fields.Text(
        string="Variantes transformadas", compute="_compute_ddsp_special_changes_display"
    )
    ddsp_length = fields.Float(string="Largo transformado")
    ddsp_width = fields.Float(string="Ancho transformado")
    ddsp_height = fields.Float(string="Alto transformado")
    ddsp_dimensions_display = fields.Char(
        string="Cambios de fabricacion", compute="_compute_ddsp_dimensions_display"
    )
    ddsp_special_notes = fields.Text(string="Especificaciones de transformacion")
    ddsp_production_instructions = fields.Text(string="Instrucciones de fabricacion")
    ddsp_bom_state = fields.Selection(
        [("draft", "LDM pendiente"), ("validated", "LDM validada")],
        string="Estado de LDM transformada",
        default="draft",
        copy=False,
        tracking=True,
    )
    ddsp_sale_date = fields.Date(string="Fecha de venta transformada", copy=False, readonly=True)
    ddsp_last_activity_date = fields.Date(string="Ultima actividad", copy=False, readonly=True)
    ddsp_archive_after_date = fields.Date(string="Archivar despues de", copy=False, readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if vals.get("ddsp_is_special") and not vals.get("ddsp_archive_after_date"):
                vals["ddsp_archive_after_date"] = today + timedelta(days=30)
        return super().create(vals_list)

    @api.model
    def _ddsp_next_special_barcode(self):
        """Return a unique EAN-13 in the GS1 restricted-use 29 range."""
        for _attempt in range(20):
            sequence = self.env["ir.sequence"].next_by_code(
                "ddsp.special.product.barcode"
            )
            if not sequence:
                raise UserError(_("No esta configurada la secuencia de barcode para productos especiales."))
            digits = "".join(character for character in sequence if character.isdigit())
            base = "29%s" % digits.zfill(10)[-10:]
            weighted_sum = sum(
                int(digit) * (1 if index % 2 == 0 else 3)
                for index, digit in enumerate(base)
            )
            barcode = "%s%s" % (base, (10 - weighted_sum % 10) % 10)
            if not self.search_count([("barcode", "=", barcode)]):
                return barcode
        raise UserError(_("No fue posible generar un barcode unico para el producto especial."))

    def _ddsp_get_special_report_name(self):
        self.ensure_one()
        report_name = self.name or ""
        changes = self.ddsp_special_changes or []
        configuration = ", ".join(
            "%s: %s" % (change.get("attribute_name"), change.get("value"))
            for change in changes
            if change.get("attribute_name") and change.get("value")
        )
        suffix = " [%s]" % configuration if configuration else ""
        if suffix and report_name.endswith(suffix):
            report_name = report_name[: -len(suffix)]
        code = self.default_code or self.product_variant_id.default_code
        return "[%s] %s" % (code, report_name) if code else report_name

    def _ddsp_get_special_report_attributes(self):
        self.ensure_one()
        return [
            {
                "name": change.get("attribute_name"),
                "value": change.get("value"),
            }
            for change in (self.ddsp_special_changes or [])
            if change.get("attribute_name") and change.get("value")
        ]

    def _ddsp_get_commercial_report_name(self, variant=False):
        """Return a clean product heading without variant values in parentheses."""
        self.ensure_one()
        if self.ddsp_is_special:
            report_name = self.name or ""
            if report_name.endswith("]") and " [" in report_name:
                report_name = report_name.rsplit(" [", 1)[0]
            code = (variant and variant.default_code) or self.default_code
            return "[%s] %s" % (code, report_name) if code else report_name
        code = (variant and variant.default_code) or self.default_code
        name = self.name or ""
        return "[%s] %s" % (code, name) if code else name

    def _ddsp_get_commercial_report_attributes(self, variant=False):
        """Return every attribute/value as independent report rows."""
        self.ensure_one()
        if self.ddsp_product_kind == "special" and self.ddsp_special_changes:
            return self._ddsp_get_special_report_attributes()
        variant = variant or self.product_variant_id
        return [
            {
                "name": value.attribute_id.display_name,
                "value": value.name,
            }
            for value in variant.product_template_attribute_value_ids
            if value.attribute_id and value.name
        ]

    @api.model
    def ddsp_create_special_from_configurator(
        self,
        base_product_id,
        special_changes,
        price_unit,
        special_notes,
        production_instructions,
    ):
        base_product = self.env["product.product"].browse(base_product_id).exists()
        if not base_product or not special_changes:
            raise UserError(_("Selecciona una variante base y al menos un atributo transformado."))
        base_template = base_product.product_tmpl_id
        if not base_template.ddsp_allow_special or base_template.ddsp_is_special:
            raise UserError(
                _("El producto %s no permite crear productos transformados.")
                % base_template.display_name
            )
        available_attributes = base_template.attribute_line_ids.attribute_id
        normalized_changes = []
        seen_attribute_ids = set()
        for change in special_changes:
            attribute = self.env["product.attribute"].browse(change.get("attribute_id")).exists()
            value = (change.get("value") or "").strip()
            if not attribute or attribute not in available_attributes or not value:
                raise UserError(_("Cada cambio debe tener un atributo del producto y un valor transformado."))
            if attribute.id in seen_attribute_ids:
                raise UserError(_("No puedes modificar dos veces el mismo atributo."))
            seen_attribute_ids.add(attribute.id)
            normalized_changes.append(
                {"attribute_id": attribute.id, "attribute_name": attribute.display_name, "value": value}
            )
        if not base_template.is_storable:
            raise UserError(_("El producto base debe ser almacenable para crear una transformacion."))

        company = self.env.company
        code = self.env["ir.sequence"].next_by_code("ddsp.special.product") or "ESP"
        changes_by_attribute = {
            change["attribute_id"]: change for change in normalized_changes
        }
        final_attribute_values = []
        for attribute_line in base_template.attribute_line_ids.filtered("active"):
            change = changes_by_attribute.get(attribute_line.attribute_id.id)
            if change:
                value_name = change["value"]
            else:
                selected_value = base_product.product_template_attribute_value_ids.filtered(
                    lambda value: value.attribute_line_id == attribute_line
                )[:1]
                if not selected_value:
                    continue
                value_name = selected_value.product_attribute_value_id.name
            final_attribute_values.append(
                {
                    "attribute": attribute_line.attribute_id,
                    "attribute_name": attribute_line.attribute_id.display_name,
                    "value": value_name,
                    "modified": bool(change),
                }
            )
        configuration_label = ", ".join(
            "%s: %s" % (item["attribute_name"], item["value"])
            for item in final_attribute_values
        )
        final_name = _("%s Transformado [%s]") % (base_template.name, configuration_label)
        first_change = normalized_changes[0]
        attribute_line_commands = []
        for item in final_attribute_values:
            attribute = item["attribute"]
            attribute_value = self.env["product.attribute.value"].sudo().search(
                [
                    ("attribute_id", "=", attribute.id),
                    ("name", "=ilike", item["value"]),
                ],
                limit=1,
            )
            if not attribute_value:
                attribute_value = self.env["product.attribute.value"].sudo().create(
                    {"attribute_id": attribute.id, "name": item["value"]}
                )
            attribute_line_commands.append(
                (0, 0, {"attribute_id": attribute.id, "value_ids": [(6, 0, [attribute_value.id])]})
            )
        template = self.sudo().create(
            {
                "name": final_name,
                "default_code": code,
                "barcode": self._ddsp_next_special_barcode(),
                "type": base_template.type,
                "is_storable": True,
                "categ_id": base_template.categ_id.id,
                "uom_id": base_template.uom_id.id,
                "uom_po_id": base_template.uom_po_id.id,
                "list_price": price_unit,
                "standard_price": base_template.sudo().standard_price,
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
                "ddsp_special_attribute_id": first_change["attribute_id"],
                "ddsp_special_value": first_change["value"],
                "ddsp_special_changes": normalized_changes,
                "ddsp_special_notes": special_notes,
                "ddsp_production_instructions": production_instructions,
                "ddsp_bom_state": "draft",
                "attribute_line_ids": attribute_line_commands,
            }
        )
        product = template.product_variant_id
        if not product:
            combination = template.attribute_line_ids.product_template_value_ids
            product = template._create_product_variant(combination, log_warning=True)
        if not product:
            raise UserError(
                _("No fue posible generar la variante del producto transformado. Revise la configuracion de sus atributos.")
            )
        self.env["mrp.bom"].sudo().create(
            {
                "product_tmpl_id": template.id,
                "product_id": product.id,
                "product_qty": 1.0,
                "product_uom_id": template.uom_id.id,
                "company_id": company.id,
                "type": "normal",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": base_product.id,
                            "product_qty": 1.0,
                            "product_uom_id": base_product.uom_id.id,
                        },
                    )
                ],
            }
        )
        template._ddsp_validate_special_bom(require_production_user=False)
        return {
            "product_id": product.id,
            "product_template_id": template.id,
            "display_name": product.display_name,
            "name": final_name,
            "price": price_unit,
        }

    @api.depends("ddsp_special_changes", "ddsp_special_attribute_id", "ddsp_special_value")
    def _compute_ddsp_special_changes_display(self):
        for product in self:
            changes = product.ddsp_special_changes or []
            if changes:
                product.ddsp_special_changes_display = "\n".join(
                    "%s: %s" % (change.get("attribute_name", ""), change.get("value", ""))
                    for change in changes
                )
            elif product.ddsp_special_attribute_id and product.ddsp_special_value:
                product.ddsp_special_changes_display = "%s: %s" % (
                    product.ddsp_special_attribute_id.display_name,
                    product.ddsp_special_value,
                )
            else:
                product.ddsp_special_changes_display = False

    @api.depends(
        "ddsp_special_changes",
        "ddsp_special_attribute_id",
        "ddsp_special_value",
        "ddsp_width",
        "ddsp_height",
    )
    def _compute_ddsp_dimensions_display(self):
        for product in self:
            if product.ddsp_special_changes:
                product.ddsp_dimensions_display = ", ".join(
                    "%s: %s" % (change.get("attribute_name", ""), change.get("value", ""))
                    for change in product.ddsp_special_changes
                )
            elif product.ddsp_special_attribute_id and product.ddsp_special_value:
                product.ddsp_dimensions_display = "%s: %s" % (
                    product.ddsp_special_attribute_id.display_name,
                    product.ddsp_special_value,
                )
            else:
                measures = (product.ddsp_width, product.ddsp_height)
                product.ddsp_dimensions_display = (
                    " x ".join(f"{measure:g}" for measure in measures)
                    if all(measure > 0 for measure in measures)
                    else False
                )

    def _ddsp_validate_special_bom(self, require_production_user=True):
        if require_production_user and not self.env.user.has_group("mrp.group_mrp_user"):
            raise AccessError(_("Solo un usuario de Produccion puede validar la LDM personalizada."))
        for product in self:
            if not product.ddsp_is_special:
                continue
            bom = product._ddsp_get_special_bom()
            if not bom or not bom.bom_line_ids:
                raise UserError(_("El producto personalizado debe tener una LDM con al menos un componente."))
            if bom.bom_line_ids.filtered(lambda line: line.product_qty <= 0):
                raise UserError(_("Todos los componentes de la LDM deben tener cantidades mayores que cero."))
            product.ddsp_bom_state = "validated"
            product.message_post(body=_("LDM personalizada validada por %s.") % self.env.user.display_name)
        return True

    def action_ddsp_validate_bom(self):
        return self._ddsp_validate_special_bom(require_production_user=True)

    def _ddsp_get_special_bom(self):
        self.ensure_one()
        return self.env["mrp.bom"].search(
            [
                ("product_tmpl_id", "=", self.id),
                ("company_id", "in", [False, self.company_id.id]),
                ("active", "=", True),
            ],
            order="product_id desc, sequence, id",
            limit=1,
        )

    def _ddsp_touch_activity(self, activity_date=None):
        activity_date = fields.Date.to_date(activity_date or fields.Date.context_today(self))
        special_products = self.filtered("ddsp_is_special")
        if special_products:
            # This bookkeeping is triggered when a commercial user adds a
            # special product to a quotation or invoice.  Salespeople must not
            # receive general write access to the product catalogue just to
            # update these two technical lifecycle fields.
            special_products.sudo().write(
                {
                    "ddsp_last_activity_date": activity_date,
                    "ddsp_archive_after_date": activity_date + timedelta(days=30),
                }
            )

    def _ddsp_mark_sold(self, sale_date=None):
        """Update only the technical lifecycle dates after invoice posting.

        A salesperson is allowed to post the commercial invoice but must not
        receive generic write access to ``product.template``.  Keep the
        elevation confined to the three lifecycle fields of special products.
        """
        sale_date = fields.Date.to_date(sale_date or fields.Date.context_today(self))
        special_products = self.filtered("ddsp_is_special")
        if special_products:
            special_products.sudo().write(
                {
                    "ddsp_sale_date": sale_date,
                    "ddsp_last_activity_date": sale_date,
                    "ddsp_archive_after_date": sale_date + timedelta(days=30),
                }
            )

    @api.model
    def _ddsp_archive_inactive_special_products(self):
        today = fields.Date.context_today(self)
        candidates = self.search(
            [
                ("ddsp_is_special", "=", True),
                ("active", "=", True),
                ("ddsp_archive_after_date", "!=", False),
                ("ddsp_archive_after_date", "<=", today),
            ]
        )
        archived = self.env["product.template"]
        for product in candidates:
            variants = product.with_context(active_test=False).product_variant_ids
            open_moves = self.env["stock.move"].search_count(
                [("product_id", "in", variants.ids), ("state", "not in", ("done", "cancel"))], limit=1
            )
            open_productions = self.env["mrp.production"].search_count(
                [("product_id", "in", variants.ids), ("state", "not in", ("done", "cancel"))], limit=1
            )
            has_stock = any(
                not float_is_zero(variant.qty_available, precision_rounding=variant.uom_id.rounding)
                for variant in variants
            )
            open_invoice_lines = self.env["account.move.line"].search_count(
                [
                    ("product_id", "in", variants.ids),
                    ("move_id.state", "=", "draft"),
                    ("move_id.move_type", "in", ("out_invoice", "out_refund")),
                ],
                limit=1,
            )
            open_sale_lines = self.env["sale.order.line"].search_count(
                [
                    ("product_id", "in", variants.ids),
                    ("order_id.state", "in", ("draft", "sent", "sale")),
                ],
                limit=1,
            )
            if open_moves or open_productions or has_stock or open_invoice_lines or open_sale_lines:
                continue
            product._ddsp_get_special_bom().write({"active": False})
            product.message_post(body=_("Producto personalizado archivado automaticamente por inactividad."))
            product.active = False
            archived |= product
        return len(archived)
