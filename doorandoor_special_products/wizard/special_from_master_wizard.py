from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DdspSpecialFromMasterWizard(models.TransientModel):
    _name = "ddsp.special.from.master.wizard"
    _description = "Crear producto especial desde plantilla maestra"

    sale_order_id = fields.Many2one("sale.order", readonly=True)
    move_id = fields.Many2one("account.move", readonly=True)
    master_template_id = fields.Many2one(
        "product.template",
        string="Plantilla maestra",
        required=True,
        domain="[('ddsp_is_manufacturing_template', '=', True), ('active', '=', True)]",
    )
    master_bom_id = fields.Many2one(
        "mrp.bom",
        string="LDM maestra",
        domain="[('product_tmpl_id', '=', master_template_id), ('active', '=', True)]",
    )
    base_variant_id = fields.Many2one(
        "product.product",
        string="Configuración base",
        domain="[('product_tmpl_id', '=', master_template_id), ('active', '=', True)]",
        help="Variante de referencia cuyos atributos se conservarán salvo los marcados para modificar.",
    )
    attribute_line_ids = fields.One2many(
        "ddsp.special.from.master.attribute", "wizard_id", string="Variantes nuevas"
    )
    component_line_ids = fields.One2many(
        "ddsp.special.from.master.component", "wizard_id", string="Componentes de la receta"
    )
    operation_line_ids = fields.One2many(
        "ddsp.special.from.master.operation", "wizard_id", string="Operaciones de la receta"
    )
    quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    price_unit = fields.Monetary(string="Precio unitario", required=True)
    currency_id = fields.Many2one("res.currency", compute="_compute_document_data")
    company_id = fields.Many2one("res.company", compute="_compute_document_data")
    special_notes = fields.Text(string="Especificaciones del producto", required=True)
    production_instructions = fields.Text(
        string="Instrucciones de fabricacion", required=True
    )

    def _ddsp_configured_variant_price(self):
        """Return the commercial price configured by Administration."""
        self.ensure_one()
        variant = self.base_variant_id
        template = self.master_template_id or variant.product_tmpl_id
        if not template:
            return 0.0
        return template.list_price + (
            variant.ddpc_variant_extra_price
            if variant and "ddpc_variant_extra_price" in variant._fields
            else 0.0
        )

    @api.depends("sale_order_id", "move_id")
    def _compute_document_data(self):
        for wizard in self:
            document = wizard.sale_order_id or wizard.move_id
            wizard.currency_id = document.currency_id
            wizard.company_id = document.company_id

    @api.onchange("master_template_id")
    def _onchange_master_template_id(self):
        self.attribute_line_ids = [(5, 0, 0)]
        self.component_line_ids = [(5, 0, 0)]
        self.operation_line_ids = [(5, 0, 0)]
        self.master_bom_id = False
        self.base_variant_id = False
        if not self.master_template_id:
            return
        self.master_bom_id = self.env["mrp.bom"].search(
            [
                ("product_tmpl_id", "=", self.master_template_id.id),
                ("active", "=", True),
                ("company_id", "in", [False, self.company_id.id]),
            ],
            order="sequence, id",
            limit=1,
        )
        self.base_variant_id = self.master_template_id.product_variant_ids.filtered("active")[:1]
        self.price_unit = self._ddsp_configured_variant_price()
        self._ddsp_load_base_attributes()
        self._ddsp_load_recipe()

    @api.onchange("base_variant_id")
    def _onchange_base_variant_id(self):
        self.price_unit = self._ddsp_configured_variant_price()
        self._ddsp_load_base_attributes()

    @api.onchange("master_bom_id")
    def _onchange_master_bom_id(self):
        self._ddsp_load_recipe()

    def _ddsp_load_base_attributes(self):
        if not self.master_template_id:
            self.attribute_line_ids = [(5, 0, 0)]
            return
        selected_by_attribute = {}
        if self.base_variant_id:
            selected_by_attribute = {
                value.attribute_id.id: value.name
                for value in self.base_variant_id.product_template_attribute_value_ids
            }
        self.attribute_line_ids = [(5, 0, 0)] + [
            (
                0,
                0,
                {
                    "attribute_id": line.attribute_id.id,
                    "base_value": selected_by_attribute.get(line.attribute_id.id)
                    or line.value_ids[:1].name
                    or "",
                    "modify": False,
                    "value": "",
                },
            )
            for line in self.master_template_id.attribute_line_ids.filtered("active")
        ]

    def _ddsp_load_recipe(self):
        self.component_line_ids = [(5, 0, 0)]
        self.operation_line_ids = [(5, 0, 0)]
        if not self.master_bom_id:
            return
        self.operation_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "include": True,
                "source_operation_id": operation.id,
                "name": operation.name,
                "workcenter_id": operation.workcenter_id.id,
                "time_cycle_manual": operation.time_cycle_manual,
            })
            for operation in self.master_bom_id.operation_ids.filtered("active")
        ]
        self.component_line_ids = [(5, 0, 0)] + [
            (0, 0, {
                "include": True,
                "source_bom_line_id": line.id,
                "product_id": line.product_id.id,
                "product_qty": line.product_qty,
                "product_uom_id": line.product_uom_id.id,
                "source_operation_id": line.operation_id.id,
            })
            for line in self.master_bom_id.bom_line_ids
        ]

    def _ddsp_validate(self):
        self.ensure_one()
        if bool(self.sale_order_id) == bool(self.move_id):
            raise UserError(_("El producto especial debe pertenecer a un solo documento comercial."))
        if self.sale_order_id and self.sale_order_id.state not in ("draft", "sent"):
            raise UserError(_("La cotizacion debe permanecer abierta."))
        if self.move_id and (
            self.move_id.state != "draft" or self.move_id.move_type != "out_invoice"
        ):
            raise UserError(_("La prefactura o factura debe permanecer en borrador."))
        if not self.master_template_id.ddsp_is_manufacturing_template:
            raise UserError(_("Seleccione una plantilla maestra WINDOWS o DOORS."))
        if self.master_bom_id and self.master_bom_id.product_tmpl_id != self.master_template_id:
            raise UserError(_("La LDM seleccionada no pertenece a la plantilla maestra."))
        if not self.attribute_line_ids:
            raise UserError(
                _("Agregue al menos un atributo y escriba su nuevo valor para el producto especial.")
            )
        invalid_attribute = self.attribute_line_ids.filtered(
            lambda line: bool(line.attribute_id) == bool((line.new_attribute_name or "").strip())
        )
        if invalid_attribute:
            raise UserError(
                _(
                    "En cada fila seleccione un atributo existente o escriba uno nuevo, "
                    "pero no ambas opciones."
                )
            )
        attribute_names = [
            (line.attribute_id.name or line.new_attribute_name).strip().casefold()
            for line in self.attribute_line_ids
        ]
        if len(attribute_names) != len(set(attribute_names)):
            raise UserError(_("Cada atributo puede agregarse una sola vez al producto especial."))
        missing = self.attribute_line_ids.filtered(lambda line: not line.result_value)
        if missing:
            raise UserError(
                _("Complete el valor base o el nuevo valor de: %s")
                % ", ".join(missing.mapped("attribute_display_name"))
            )
        missing_modified = self.attribute_line_ids.filtered(
            lambda line: line.modify and not (line.value or "").strip()
        )
        if missing_modified:
            raise UserError(_("Todo atributo marcado para modificar necesita un nuevo valor."))
        invalid_components = self.component_line_ids.filtered(
            lambda line: line.include and (not line.product_id or line.product_qty <= 0)
        )
        if invalid_components:
            raise UserError(_("Los componentes incluidos deben tener producto y cantidad mayor que cero."))
        if self.master_bom_id and not self.component_line_ids.filtered("include"):
            raise UserError(
                _("Seleccione al menos un componente de la receta o agregue uno nuevo antes de crear el Especial.")
            )
        if self.quantity <= 0:
            raise UserError(_("La cantidad debe ser mayor que cero."))

    def action_create_special_product(self):
        self.ensure_one()
        self._ddsp_validate()
        # Never trust a price received from the browser. Sales users only
        # select the variant; Administration configures its commercial price.
        configured_price = self._ddsp_configured_variant_price()
        master = self.master_template_id
        code = self.env["ir.sequence"].next_by_code("ddsp.special.product") or "ESP"
        changes = []
        for line in self.attribute_line_ids:
            attribute = line.attribute_id
            if not attribute:
                attribute_name = line.new_attribute_name.strip()
                attribute = self.env["product.attribute"].sudo().search(
                    [("name", "=ilike", attribute_name)], limit=1
                )
                if not attribute:
                    attribute = self.env["product.attribute"].sudo().create(
                        {"name": attribute_name, "create_variant": "always"}
                    )
            changes.append(
                {
                    "attribute_id": attribute.id,
                    "attribute_name": attribute.display_name,
                    "value": line.result_value,
                    "modified": line.modify,
                }
            )
        configuration = ", ".join(
            "%s: %s" % (change["attribute_name"], change["value"])
            for change in changes
        )
        base_name = master.ddsp_template_output_name or master.name
        final_name = _("%s Especial [%s]") % (base_name, configuration)
        attribute_commands = []
        for change in changes:
            attribute = self.env["product.attribute"].browse(change["attribute_id"])
            value = self.env["product.attribute.value"].sudo().search(
                [
                    ("attribute_id", "=", attribute.id),
                    ("name", "=ilike", change["value"]),
                ],
                limit=1,
            )
            if not value:
                value = self.env["product.attribute.value"].sudo().create(
                    {"attribute_id": attribute.id, "name": change["value"]}
                )
            attribute_commands.append(
                (0, 0, {"attribute_id": attribute.id, "value_ids": [(6, 0, value.ids)]})
            )
        template = self.env["product.template"].sudo().create(
            {
                "name": final_name,
                "default_code": code,
                "barcode": self.env["product.template"]._ddsp_next_special_barcode(),
                "type": master.type,
                "is_storable": True,
                "categ_id": master.categ_id.id,
                "uom_id": master.uom_id.id,
                "uom_po_id": master.uom_po_id.id,
                "list_price": configured_price,
                "standard_price": master.standard_price,
                "sale_ok": True,
                "purchase_ok": False,
                "route_ids": [(6, 0, master.route_ids.ids)],
                "taxes_id": [(6, 0, master.taxes_id.ids)],
                "supplier_taxes_id": [(6, 0, master.supplier_taxes_id.ids)],
                "company_id": self.company_id.id,
                "ddsp_is_special": True,
                "ddsp_product_kind": "special",
                "ddsp_allow_special": False,
                "ddsp_manufacturing_family": master.ddsp_manufacturing_family,
                "ddsp_base_product_tmpl_id": master.id,
                "ddsp_source_bom_template_id": self.master_bom_id.id or False,
                "ddsp_special_attribute_id": changes[0]["attribute_id"],
                "ddsp_special_value": changes[0]["value"],
                "ddsp_special_changes": changes,
                "ddsp_special_notes": self.special_notes,
                "ddsp_production_instructions": self.production_instructions,
                "ddsp_bom_state": "draft",
                "attribute_line_ids": attribute_commands,
            }
        )
        product = template.product_variant_id
        if not product:
            product = template._create_product_variant(
                template.attribute_line_ids.product_template_value_ids,
                log_warning=True,
            )
        if not product:
            raise UserError(_("No fue posible crear la variante del producto especial."))
        bom_values = {
                "product_tmpl_id": template.id,
                "product_id": product.id,
                "product_qty": 1.0,
                "product_uom_id": template.uom_id.id,
                "company_id": self.company_id.id,
                "type": "normal",
                "code": "%s-MASTER" % code,
                "active": True,
            }
        bom = self.env["mrp.bom"].sudo().create(bom_values)
        operation_map = {}
        for operation_line in self.operation_line_ids.filtered("include"):
            source = operation_line.source_operation_id
            operation = source.sudo().copy({
                "bom_id": bom.id,
                "name": operation_line.name,
                "workcenter_id": operation_line.workcenter_id.id,
                "time_cycle_manual": operation_line.time_cycle_manual,
                "blocked_by_operation_ids": [(5, 0, 0)],
                "bom_product_template_attribute_value_ids": [(5, 0, 0)],
            })
            operation_map[source.id] = operation
        for component_line in self.component_line_ids.filtered("include"):
            source = component_line.source_bom_line_id
            vals = {
                "bom_id": bom.id,
                "product_id": component_line.product_id.id,
                "product_qty": component_line.product_qty,
                "product_uom_id": component_line.product_uom_id.id,
                "operation_id": operation_map.get(component_line.source_operation_id.id, False).id
                if operation_map.get(component_line.source_operation_id.id) else False,
                "bom_product_template_attribute_value_ids": [(5, 0, 0)],
            }
            if source:
                source.sudo().copy(vals)
            else:
                self.env["mrp.bom.line"].sudo().create(vals)
        if not self.master_bom_id and not bom.bom_line_ids:
            component = master._ddsp_get_default_special_component()
            component_qty = master.ddsp_default_special_component_qty or 3.0
            bom.sudo().write(
                {
                    "bom_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": component.id,
                                "product_qty": component_qty,
                                "product_uom_id": component.uom_id.id,
                            },
                        )
                    ]
                }
            )
        if self.master_bom_id:
            bom._ddsp_apply_manufacturing_rules(changes)
        template._ddsp_validate_special_bom(require_production_user=False)
        line_vals = {
            "product_id": product.id,
            "name": final_name,
            "price_unit": configured_price,
        }
        if self.sale_order_id:
            line = self.env["sale.order.line"].create(
                {
                    **line_vals,
                    "order_id": self.sale_order_id.id,
                    "product_uom_qty": self.quantity,
                    "product_uom": product.uom_id.id,
                    "tax_id": [(6, 0, product.taxes_id.filtered(
                        lambda tax: not tax.company_id or tax.company_id == self.company_id
                    ).ids)],
                }
            )
            template.sudo().write(
                {
                    "ddsp_origin_sale_order_id": self.sale_order_id.id,
                    "ddsp_origin_sale_order_line_id": line.id,
                }
            )
        else:
            line = self.env["account.move.line"].create(
                {
                    **line_vals,
                    "move_id": self.move_id.id,
                    "quantity": self.quantity,
                    "product_uom_id": product.uom_id.id,
                    "tax_ids": [(6, 0, product.taxes_id.filtered(
                        lambda tax: not tax.company_id or tax.company_id == self.company_id
                    ).ids)],
                }
            )
            template.sudo().write(
                {
                    "ddsp_origin_invoice_id": self.move_id.id,
                    "ddsp_origin_invoice_line_id": line.id,
                }
            )
        return {"type": "ir.actions.act_window_close"}


class DdspSpecialFromMasterAttribute(models.TransientModel):
    _name = "ddsp.special.from.master.attribute"
    _description = "Valor nuevo de variante para producto especial"
    _order = "id"

    wizard_id = fields.Many2one(
        "ddsp.special.from.master.wizard", required=True, ondelete="cascade"
    )
    attribute_id = fields.Many2one("product.attribute", string="Atributo existente")
    new_attribute_name = fields.Char(string="Atributo nuevo")
    base_value = fields.Char(string="Valor base", readonly=True)
    modify = fields.Boolean(string="Modificar")
    value = fields.Char(string="Nuevo valor")
    result_value = fields.Char(string="Valor resultante", compute="_compute_result_value")
    attribute_display_name = fields.Char(compute="_compute_result_value")

    @api.depends("attribute_id", "new_attribute_name", "base_value", "modify", "value")
    def _compute_result_value(self):
        for line in self:
            line.attribute_display_name = line.attribute_id.display_name or line.new_attribute_name
            line.result_value = (
                (line.value or "").strip()
                if line.modify or not (line.base_value or "").strip()
                else (line.base_value or "").strip()
            )

    @api.onchange("new_attribute_name")
    def _onchange_new_attribute_name(self):
        if self.new_attribute_name and not self.attribute_id:
            self.modify = True


class DdspSpecialFromMasterComponent(models.TransientModel):
    _name = "ddsp.special.from.master.component"
    _description = "Componente seleccionable de LDM especial"
    _order = "id"

    wizard_id = fields.Many2one("ddsp.special.from.master.wizard", required=True, ondelete="cascade")
    include = fields.Boolean(string="Conservar", default=True)
    source_bom_line_id = fields.Many2one("mrp.bom.line", readonly=True)
    product_id = fields.Many2one("product.product", string="Componente", required=True)
    product_qty = fields.Float(string="Cantidad", default=1.0, required=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", required=True)
    source_operation_id = fields.Many2one("mrp.routing.workcenter", string="Operación de origen", readonly=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id


class DdspSpecialFromMasterOperation(models.TransientModel):
    _name = "ddsp.special.from.master.operation"
    _description = "Operación seleccionable de LDM especial"
    _order = "id"

    wizard_id = fields.Many2one("ddsp.special.from.master.wizard", required=True, ondelete="cascade")
    include = fields.Boolean(string="Conservar", default=True)
    source_operation_id = fields.Many2one("mrp.routing.workcenter", readonly=True)
    name = fields.Char(string="Operación", required=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro de trabajo", required=True)
    time_cycle_manual = fields.Float(string="Duración manual", required=True)
