from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class DdpcVariantSelector(models.TransientModel):
    _name = "ddpc.variant.selector"
    _description = "Configurador guiado DoorAndDoor"

    # Compatibilidad con especificaciones de vista que hayan quedado en la
    # cache del cliente desde la presentacion experimental anterior. El campo
    # ya no controla la vista definitiva, pero mantenerlo evita que web_read
    # falle mientras esas pestañas se renuevan.
    layout_mode = fields.Selection(
        [("visual", "Visual"), ("compact", "Compacta")],
        default="visual",
        readonly=True,
    )
    move_line_id = fields.Many2one("account.move.line", required=True, readonly=True)
    product_template_id = fields.Many2one(
        "product.template", string="Producto", required=True
    )
    selection_mode = fields.Selection(
        [("guided", "Armar producto"), ("custom", "Crear medida/valor personalizado")],
        string="Accion",
        default="guided",
        required=True,
    )
    product_image = fields.Image(related="product_template_id.image_128", readonly=True)
    quantity = fields.Float(string="Cantidad", required=True, default=1.0)
    option_line_ids = fields.One2many(
        "ddpc.variant.selector.option", "wizard_id", string="Opciones disponibles"
    )
    attribute_selection_line_ids = fields.One2many(
        "ddpc.variant.selector.attribute",
        "wizard_id",
        string="Atributos de variante",
    )
    variant_id = fields.Many2one(
        "product.product", string="Variante resultante", readonly=True
    )
    variant_preview_name = fields.Char(
        string="Variante resultante", compute="_compute_preview", readonly=True
    )
    available_attribute_ids = fields.Many2many(
        "product.attribute", compute="_compute_available_attribute_ids"
    )
    custom_attribute_id = fields.Many2one(
        "product.attribute",
        string="Atributo a modificar",
        domain="[('id', 'in', available_attribute_ids)]",
    )
    custom_value = fields.Char(string="Nuevo valor")
    custom_default_code = fields.Char(string="Referencia interna")
    custom_extra_price = fields.Float(string="Precio adicional", digits="Product Price")
    variant_extra_price = fields.Float(
        string="Adicional de variante", compute="_compute_preview", readonly=True
    )
    configured_price = fields.Float(
        string="Precio configurado", compute="_compute_preview", readonly=True
    )
    configured_total = fields.Float(
        string="Total", compute="_compute_preview", readonly=True
    )
    selection_summary = fields.Text(
        string="Configuracion seleccionada", compute="_compute_preview", readonly=True
    )

    @api.depends("product_template_id.attribute_line_ids.attribute_id")
    def _compute_available_attribute_ids(self):
        for wizard in self:
            wizard.available_attribute_ids = wizard.product_template_id.attribute_line_ids.attribute_id.filtered(
                lambda attribute: attribute.create_variant != "no_variant"
            )

    @api.depends(
        "product_template_id.list_price",
        "selection_mode",
        "option_line_ids.selected",
        "attribute_selection_line_ids.selected_template_value_id",
        "custom_attribute_id",
        "custom_value",
        "custom_extra_price",
        "quantity",
    )
    def _compute_preview(self):
        for wizard in self:
            selected_options = wizard.option_line_ids.filtered("selected")
            selected_attributes = wizard.attribute_selection_line_ids.filtered(
                "selected_template_value_id"
            )
            summary_lines = [
                "%s: %s"
                % (
                    line.attribute_id.display_name,
                    line.selected_template_value_id.product_attribute_value_id.display_name,
                )
                for line in selected_attributes
            ] + [
                "%s: %s" % (option.attribute_id.display_name, option.value_id.display_name)
                for option in selected_options
            ]
            wizard.selection_summary = "\n".join(summary_lines)
            variant = False
            if wizard.product_template_id and wizard.selection_mode == "guided":
                combination = selected_attributes.mapped("selected_template_value_id")
                required_lines = wizard.product_template_id.attribute_line_ids.filtered(
                    lambda line: line.active
                    and line.attribute_id.create_variant != "no_variant"
                )
                selected_line_ids = selected_attributes.mapped("attribute_line_id").ids
                missing_lines = required_lines.filtered(
                    lambda line: line.id not in selected_line_ids
                )
                if not missing_lines:
                    variant = wizard.product_template_id._get_variant_for_combination(combination)
            # `_get_variant_for_combination` busca también con active_test=False
            # para permitir reutilizar combinaciones archivadas al aplicar. No
            # se debe enviar una variante archivada en un Many2one del wizard:
            # web_read no puede resolver su display_name con el contexto activo
            # y termina en KeyError. La reactivación se realiza exclusivamente
            # en `_ddpc_get_guided_variant`.
            wizard.variant_id = False
            if variant and variant.active:
                wizard.variant_preview_name = variant.display_name
            elif variant:
                wizard.variant_preview_name = _(
                    "Combinacion archivada: se reactivara al confirmar"
                )
            elif wizard.product_template_id and wizard.selection_mode == "guided" and missing_lines:
                wizard.variant_preview_name = _("Falta seleccionar: %s") % ", ".join(
                    missing_lines.mapped("attribute_id.display_name")
                )
            else:
                wizard.variant_preview_name = _("Combinacion nueva")
            extra = (
                wizard.custom_extra_price
                if wizard.selection_mode == "custom"
                else variant.ddpc_variant_extra_price if variant else 0.0
            )
            wizard.variant_extra_price = extra
            wizard.configured_price = wizard.product_template_id.list_price + extra
            wizard.configured_total = wizard.configured_price * wizard.quantity

    def _ddpc_option_commands(self, template):
        commands = [Command.clear()]
        for attribute_line in template.attribute_line_ids.filtered(
            lambda line: line.active and line.attribute_id.create_variant == "no_variant"
        ):
            for template_value in attribute_line.product_template_value_ids.filtered("ptav_active"):
                commands.append(
                    Command.create(
                        {
                            "attribute_id": attribute_line.attribute_id.id,
                            "template_value_id": template_value.id,
                            "creates_variant": False,
                            # El configurador debe comenzar limpio. El producto
                            # provisional de la linea no representa una decision
                            # comercial del vendedor.
                            "selected": False,
                        }
                    )
                )
        return commands

    def _ddpc_attribute_commands(self, template):
        return [Command.clear()] + [
            Command.create({"attribute_line_id": attribute_line.id})
            for attribute_line in template.attribute_line_ids.filtered(
                lambda line: line.active and line.attribute_id.create_variant != "no_variant"
            )
        ]

    def _ddpc_load_options(self):
        for wizard in self:
            wizard.option_line_ids = wizard._ddpc_option_commands(
                wizard.product_template_id
            )
            wizard.attribute_selection_line_ids = wizard._ddpc_attribute_commands(
                wizard.product_template_id
            )
            if wizard.move_line_id.quantity:
                wizard.quantity = wizard.move_line_id.quantity

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        self._ddpc_load_options()

    def _ddpc_selected_combination(self, excluded_attribute=False):
        self.ensure_one()
        selected_lines = self.attribute_selection_line_ids.filtered(
            lambda line: line.attribute_id != excluded_attribute
        )
        required_lines = self.product_template_id.attribute_line_ids.filtered(
            lambda line: line.active
            and line.attribute_id.create_variant != "no_variant"
            and line.attribute_id != excluded_attribute
        )
        errors = []
        for attribute_line in required_lines:
            selection_line = selected_lines.filtered(
                lambda line: line.attribute_id == attribute_line.attribute_id
            )
            if len(selection_line) != 1 or not selection_line.selected_template_value_id:
                errors.append(attribute_line.attribute_id.display_name)
        if errors:
            raise UserError(
                _("Seleccione exactamente una opcion para: %s.") % ", ".join(errors)
            )
        return selected_lines.mapped("selected_template_value_id")

    def _ddpc_get_guided_variant(self):
        self.ensure_one()
        template = self.product_template_id.sudo()
        combination = self._ddpc_selected_combination()
        variant = template._get_variant_for_combination(combination)
        if variant:
            if not variant.active:
                variant.active = True
            return variant
        variant = template._create_product_variant(combination, log_warning=True)
        if not variant:
            raise UserError(
                _("La combinacion seleccionada no existe y la configuracion del producto no permite crearla dinamicamente.")
            )
        return variant

    def _create_or_reactivate_custom_variant(self):
        self.ensure_one()
        value_name = (self.custom_value or "").strip()
        if not self.custom_attribute_id or not value_name:
            raise UserError(_("Seleccione el atributo y escriba el nuevo valor personalizado."))
        template = self.product_template_id.sudo()
        attribute_line = template.attribute_line_ids.filtered(
            lambda item: item.attribute_id == self.custom_attribute_id
        )[:1]
        if not attribute_line:
            raise UserError(_("El atributo seleccionado no pertenece a este producto."))

        attribute_value = self.env["product.attribute.value"].sudo().search(
            [
                ("attribute_id", "=", self.custom_attribute_id.id),
                ("name", "=ilike", value_name),
            ],
            limit=1,
        )
        if not attribute_value:
            attribute_value = self.env["product.attribute.value"].sudo().create(
                {"attribute_id": self.custom_attribute_id.id, "name": value_name}
            )

        template_value = attribute_line.product_template_value_ids.filtered(
            lambda item: item.product_attribute_value_id == attribute_value
        )[:1]
        attribute_line.with_context(update_product_template_attribute_values=False).write(
            {"value_ids": [Command.link(attribute_value.id)]}
        )
        if template_value:
            if not template_value.ptav_active:
                template_value.ptav_active = True
        else:
            template_value = self.env["product.template.attribute.value"].sudo().create(
                {
                    "attribute_line_id": attribute_line.id,
                    "product_attribute_value_id": attribute_value.id,
                }
            )

        combination = self._ddpc_selected_combination(
            excluded_attribute=self.custom_attribute_id
        ) | template_value
        variant = template._get_variant_for_combination(combination)
        if variant:
            if not variant.active:
                variant.active = True
        else:
            variant = self.env["product.product"].sudo().create(
                template._prepare_variant_values(combination)
            )
        variant.write(
            {
                "ddpc_is_custom_variant": True,
                "ddpc_custom_attribute_value_id": attribute_value.id,
                "ddpc_origin_invoice_id": self.move_line_id.move_id.id,
                "ddpc_variant_extra_price": self.custom_extra_price,
                "default_code": self.custom_default_code or variant.default_code,
                "ddpc_archive_after_date": False,
            }
        )
        return variant

    def action_apply_variant(self):
        self.ensure_one()
        line = self.move_line_id
        if not line:
            raise UserError(_("La linea de factura ya no esta disponible."))
        if line.move_id.state != "draft":
            raise UserError(_("Solo puede configurar variantes en facturas en borrador."))

        variant = (
            self._create_or_reactivate_custom_variant()
            if self.selection_mode == "custom"
            else self._ddpc_get_guided_variant()
        )
        self._ddpc_apply_variant_to_line(variant)
        return {"type": "ir.actions.act_window_close"}

    def _ddpc_apply_variant_to_line(self, variant):
        self.ensure_one()
        line = self.move_line_id
        informational_values = self.option_line_ids.filtered(
            lambda option: option.selected and not option.creates_variant
        ).mapped("template_value_id")
        description = variant.get_product_multiline_description_sale() or variant.display_name
        if informational_values:
            description += "\n" + _("Opciones: %s") % ", ".join(
                informational_values.mapped("display_name")
            )
        line.write(
            {
                "product_id": variant.id,
                "name": description,
                "quantity": self.quantity,
                "ddpc_selected_option_value_ids": [Command.set(informational_values.ids)],
            }
        )
        line._ddpc_apply_variant_price()
        return line


class DdpcVariantSelectorOption(models.TransientModel):
    _name = "ddpc.variant.selector.option"
    _description = "Opcion del configurador guiado"
    _order = "attribute_id, template_value_id"

    wizard_id = fields.Many2one(
        "ddpc.variant.selector", required=True, ondelete="cascade"
    )
    attribute_id = fields.Many2one("product.attribute", string="Atributo", readonly=True)
    template_value_id = fields.Many2one(
        "product.template.attribute.value", string="Valor", required=True, readonly=True
    )
    value_id = fields.Many2one(
        related="template_value_id.product_attribute_value_id", string="Opcion"
    )
    creates_variant = fields.Boolean(string="Define variante", readonly=True)
    selected = fields.Boolean(string="Seleccionar")


class DdpcVariantSelectorAttribute(models.TransientModel):
    _name = "ddpc.variant.selector.attribute"
    _description = "Atributo del configurador guiado"
    _order = "attribute_line_id"

    wizard_id = fields.Many2one(
        "ddpc.variant.selector", required=True, ondelete="cascade"
    )
    attribute_line_id = fields.Many2one(
        "product.template.attribute.line", required=True, readonly=True
    )
    attribute_id = fields.Many2one(
        related="attribute_line_id.attribute_id", string="Atributo", readonly=True
    )
    available_template_value_ids = fields.Many2many(
        "product.template.attribute.value",
        string="Valores disponibles",
        compute="_compute_available_template_value_ids",
        readonly=True,
    )
    selected_template_value_id = fields.Many2one(
        "product.template.attribute.value",
        string="Valor",
        domain="[('id', 'in', available_template_value_ids)]",
    )

    @api.depends(
        "attribute_line_id",
        "attribute_line_id.product_template_value_ids",
        "attribute_line_id.product_template_value_ids.ptav_active",
    )
    def _compute_available_template_value_ids(self):
        for line in self:
            line.available_template_value_ids = (
                line.attribute_line_id.product_template_value_ids.filtered("ptav_active")
            )
