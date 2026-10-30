from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class InventoryCountVariantSelector(models.TransientModel):
    _name = "inventory.count.variant.selector"
    _description = "Guided Product Selector for Inventory Count"

    session_id = fields.Many2one(
        "inventory.count.session", required=True, readonly=True, ondelete="cascade"
    )
    location_id = fields.Many2one(related="session_id.location_id", readonly=True)
    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        domain="[('is_storable', '=', True), ('active', '=', True)]",
    )
    product_image = fields.Image(related="product_template_id.image_128", readonly=True)
    attribute_line_ids = fields.One2many(
        "inventory.count.variant.selector.attribute", "wizard_id", string="Attributes"
    )
    variant_id = fields.Many2one(
        "product.product", string="Technical Variant", compute="_compute_preview"
    )
    variant_preview = fields.Char(
        string="Resulting Variant", compute="_compute_preview"
    )
    selection_summary = fields.Text(
        string="Selected Configuration", compute="_compute_preview"
    )
    expected_qty = fields.Float(
        string="Current Stock", compute="_compute_preview",
        digits="Product Unit of Measure",
    )
    counted_qty = fields.Float(
        string="Counted Quantity", required=True, digits="Product Unit of Measure"
    )
    currency_id = fields.Many2one(related="session_id.company_id.currency_id", readonly=True)
    cost_price = fields.Monetary(
        string="Unit Cost",
        currency_field="currency_id",
        groups="base.group_system",
    )
    sale_price = fields.Monetary(
        string="Final Sale Price",
        currency_field="currency_id",
        groups="base.group_system",
    )
    generate_barcode = fields.Boolean(string="Generate Barcode", default=True)

    @api.constrains("cost_price", "sale_price")
    def _check_nonnegative_prices(self):
        for wizard in self:
            if wizard.cost_price < 0 or wizard.sale_price < 0:
                raise ValidationError(_("Cost and sale prices cannot be negative."))

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        self._load_attribute_lines()
        self.cost_price = self.product_template_id.standard_price
        self.sale_price = self.product_template_id.list_price

    @api.onchange("attribute_line_ids.selected_template_value_id")
    def _onchange_selected_variant_prices(self):
        for wizard in self:
            combination, missing = wizard._selected_combination()
            if missing:
                continue
            variant = wizard.product_template_id._get_variant_for_combination(combination)
            if not variant:
                continue
            existing_line = wizard.session_id.line_ids.filtered(
                lambda line: line.product_id == variant
                and not line.lot_id and not line.package_id and not line.owner_id
            )[:1]
            if existing_line and existing_line.price_configured:
                wizard.cost_price = existing_line.cost_price
                wizard.sale_price = existing_line.sale_price
            else:
                wizard.cost_price = variant.with_company(
                    wizard.session_id.company_id
                ).standard_price
                wizard.sale_price = (
                    variant.product_tmpl_id.list_price
                    + variant.ddpc_variant_extra_price
                )

    def _load_attribute_lines(self):
        for wizard in self:
            wizard.attribute_line_ids = [Command.clear()] + [
                Command.create({"attribute_line_id": line.id})
                for line in wizard.product_template_id.attribute_line_ids.filtered(
                    lambda item: item.active
                )
            ]

    def _selected_combination(self, raise_if_incomplete=False):
        self.ensure_one()
        selected = self.attribute_line_ids.filtered("selected_template_value_id")
        required = self.product_template_id.attribute_line_ids.filtered(
            lambda line: line.active
        )
        selected_line_ids = selected.mapped("attribute_line_id").ids
        missing = required.filtered(lambda line: line.id not in selected_line_ids)
        if missing and raise_if_incomplete:
            raise ValidationError(
                _("Select one value for: %s.")
                % ", ".join(missing.mapped("attribute_id.display_name"))
            )
        return selected.mapped("selected_template_value_id"), missing

    @api.depends(
        "session_id.location_id",
        "product_template_id",
        "attribute_line_ids.selected_template_value_id",
    )
    def _compute_preview(self):
        for wizard in self:
            wizard.variant_id = False
            wizard.variant_preview = False
            wizard.selection_summary = False
            wizard.expected_qty = 0.0
            if not wizard.product_template_id:
                continue
            combination, missing = wizard._selected_combination()
            wizard.selection_summary = "\n".join(
                "%s: %s" % (
                    line.attribute_id.display_name,
                    line.selected_template_value_id.product_attribute_value_id.display_name,
                )
                for line in wizard.attribute_line_ids.filtered(
                    "selected_template_value_id"
                )
            )
            if missing:
                wizard.variant_preview = _("Missing: %s") % ", ".join(
                    missing.mapped("attribute_id.display_name")
                )
                continue
            variant = wizard.product_template_id._get_variant_for_combination(combination)
            if variant and variant.active:
                wizard.variant_id = variant
                wizard.variant_preview = variant.display_name
                wizard.expected_qty = self.env["stock.quant"]._get_available_quantity(
                    variant, wizard.location_id
                )
            else:
                wizard.variant_preview = _("New inventory variant")

    def _get_or_create_variant(self):
        self.ensure_one()
        combination, unused = self._selected_combination(raise_if_incomplete=True)
        non_variant_attributes = self.attribute_line_ids.filtered(
            lambda line: line.attribute_id.create_variant == "no_variant"
        ).mapped("attribute_id")
        if non_variant_attributes:
            raise UserError(_(
                "These attributes are configured as 'Never' and therefore do not "
                "identify separate inventory items: %s. Change their variant "
                "creation mode to 'Dynamically' before performing the count."
            ) % ", ".join(non_variant_attributes.mapped("display_name")))
        template = self.product_template_id.sudo()
        variant = template._get_variant_for_combination(combination)
        if variant:
            if not variant.active:
                variant.active = True
            return variant
        variant = template._create_product_variant(combination, log_warning=True)
        if not variant:
            raise UserError(_(
                "This combination does not exist and its attributes do not permit "
                "creating it dynamically."
            ))
        return variant

    def _add_count_line(self):
        self.ensure_one()
        if self.session_id.state != "counting":
            raise UserError(_("The count session is no longer in progress."))
        if self.counted_qty < 0:
            raise ValidationError(_("The counted quantity cannot be negative."))
        variant = self._get_or_create_variant()
        if not variant.is_storable:
            raise UserError(_("Only storable products can be added to inventory."))
        lines = self.session_id.line_ids.filtered(
            lambda line: line.product_id == variant
            and not line.lot_id and not line.package_id and not line.owner_id
        )
        if len(lines) > 1:
            raise UserError(_("This variant occurs on multiple untracked count lines."))
        if lines:
            line = lines
        else:
            expected = self.env["stock.quant"]._get_available_quantity(
                variant, self.session_id.location_id
            )
            line = self.env["inventory.count.line"].create({
                "session_id": self.session_id.id,
                "product_id": variant.id,
                "expected_qty": expected,
            })
        line_values = {
            "counted_qty": self.counted_qty,
            "is_counted": True,
        }
        line.write(line_values)
        if self.generate_barcode and not variant.barcode:
            variant.action_generate_doorandoor_barcode()
        return variant

    def action_add_and_close(self):
        self._add_count_line()
        return {"type": "ir.actions.act_window_close"}

    def action_add_and_continue(self):
        variant = self._add_count_line()
        return {
            "type": "ir.actions.act_window",
            "name": _("Add Configured Product"),
            "res_model": self._name,
            "view_mode": "form",
            "view_id": self.env.ref(
                "doorandoor_inventory_variant_count.view_inventory_count_variant_selector_form"
            ).id,
            "target": "new",
            "context": {
                "default_session_id": self.session_id.id,
                "ddpc_last_added": variant.display_name,
            },
        }


class InventoryCountVariantSelectorAttribute(models.TransientModel):
    _name = "inventory.count.variant.selector.attribute"
    _description = "Inventory Selector Attribute"
    _order = "attribute_line_id"

    wizard_id = fields.Many2one(
        "inventory.count.variant.selector", required=True, ondelete="cascade"
    )
    attribute_line_id = fields.Many2one(
        "product.template.attribute.line", required=True, readonly=True
    )
    attribute_id = fields.Many2one(
        related="attribute_line_id.attribute_id", string="Attribute", readonly=True
    )
    available_template_value_ids = fields.Many2many(
        "product.template.attribute.value",
        compute="_compute_available_template_value_ids",
    )
    selected_template_value_id = fields.Many2one(
        "product.template.attribute.value",
        string="Value",
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
