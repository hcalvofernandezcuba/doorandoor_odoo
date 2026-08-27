from odoo import _, api, fields, models
from odoo.exceptions import UserError


MAX_LABELS_PER_PDF = 50


class ProductLabelWizard(models.TransientModel):
    _inherit = "ddsl.product.label.wizard"

    label_scope = fields.Selection(
        [
            ("variants", "Variantes"),
            ("product", "Producto"),
            ("product_variants", "Producto y variantes"),
        ],
        string="Labels a imprimir",
        default="variants",
        required=True,
    )
    variant_ids = fields.Many2many(
        "product.product",
        string="Variantes asociadas a imprimir",
        domain="[('product_tmpl_id', '=', product_tmpl_id), ('active', '=', True)]",
        help=(
            "Active variants associated with this product. All are selected "
            "automatically; remove only those whose labels should not be printed."
        ),
    )
    selected_variant_count = fields.Integer(
        string="Variantes seleccionadas",
        compute="_compute_batch_information",
    )
    batch_number = fields.Integer(
        string="Lote a imprimir",
        default=1,
        required=True,
        help="Número de lote del PDF que se desea generar.",
    )
    total_batches = fields.Integer(
        string="Total de lotes",
        compute="_compute_batch_information",
    )
    batch_information = fields.Char(
        string="Resumen de impresión",
        compute="_compute_batch_information",
    )

    @api.depends("variant_ids", "quantity", "label_scope", "batch_number")
    def _compute_batch_information(self):
        for wizard in self:
            selected_count = len(wizard.variant_ids)
            wizard.selected_variant_count = selected_count
            copies = max(wizard.quantity or 1, 1)
            reserved_labels = copies if wizard.label_scope == "product_variants" else 0
            available_labels = max(MAX_LABELS_PER_PDF - reserved_labels, 1)
            variants_per_batch = max(available_labels // copies, 1)
            total_batches = (
                (selected_count + variants_per_batch - 1) // variants_per_batch
                if selected_count and wizard.label_scope != "product" else 1
            )
            wizard.total_batches = total_batches
            current_batch = max(wizard.batch_number or 1, 1)
            start = (current_batch - 1) * variants_per_batch + 1 if selected_count else 0
            end = min(current_batch * variants_per_batch, selected_count)
            wizard.batch_information = _(
                "%s variant(s) selected · batch %s of %s · variants %s–%s · "
                "maximum %s labels per PDF"
            ) % (
                selected_count,
                current_batch,
                total_batches,
                start,
                end,
                MAX_LABELS_PER_PDF,
            )

    @api.onchange("variant_ids", "quantity", "label_scope")
    def _onchange_reset_batch_number(self):
        self.batch_number = 1

    def _get_associated_variants(self, product_tmpl_id):
        return self.env["product.product"].search([
            ("product_tmpl_id", "=", product_tmpl_id),
            ("active", "=", True),
        ], order="default_code, id")

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        product_tmpl_id = values.get("product_tmpl_id") or self.env.context.get(
            "default_product_tmpl_id"
        )
        if product_tmpl_id and "variant_ids" in field_list:
            variants = self._get_associated_variants(product_tmpl_id)
            values["variant_ids"] = [(6, 0, variants.ids)]
        return values

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_variants(self):
        self.variant_ids = (
            self._get_associated_variants(self.product_tmpl_id.id)
            if self.product_tmpl_id else False
        )

    @api.onchange("label_scope")
    def _onchange_label_scope_variants(self):
        if (
            self.label_scope in ("variants", "product_variants")
            and self.product_tmpl_id
            and not self.variant_ids
        ):
            self.variant_ids = self._get_associated_variants(self.product_tmpl_id.id)

    def _reopen_label_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Labels de productos"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_select_all_variants(self):
        self.ensure_one()
        self.variant_ids = self._get_associated_variants(self.product_tmpl_id.id)
        self.batch_number = 1
        return self._reopen_label_wizard()

    def action_clear_variants(self):
        self.ensure_one()
        self.variant_ids = False
        self.batch_number = 1
        return self._reopen_label_wizard()

    def _get_variant_batch(self):
        self.ensure_one()
        if not self.variant_ids:
            raise UserError(_("Select at least one product variant to print its label."))
        copies = self.quantity or 0
        if copies <= 0:
            raise UserError(_("Labels Quantity must be greater than zero."))
        if copies > MAX_LABELS_PER_PDF:
            raise UserError(_(
                "A maximum of %s copies can be generated in one PDF."
            ) % MAX_LABELS_PER_PDF)
        reserved_labels = copies if self.label_scope == "product_variants" else 0
        variants_per_batch = max(
            (MAX_LABELS_PER_PDF - reserved_labels) // copies,
            1,
        )
        variants = self.variant_ids.sorted(lambda variant: (
            variant.default_code or "", variant.id
        ))
        total_batches = (len(variants) + variants_per_batch - 1) // variants_per_batch
        if self.batch_number < 1 or self.batch_number > total_batches:
            raise UserError(_(
                "Batch number must be between 1 and %s for the current selection."
            ) % total_batches)
        start = (self.batch_number - 1) * variants_per_batch
        return variants[start:start + variants_per_batch]

    def _prepare_variant_label_payloads(self):
        self.ensure_one()
        payloads = []
        template = self.product_tmpl_id
        for variant in self._get_variant_batch():
            # This physical label is also the inventory-counting key. Persist a
            # unique barcode on the exact variant instead of printing a fallback
            # reference that the counting session cannot resolve afterwards.
            if not variant.barcode:
                variant.barcode = variant._doorandoor_next_product_barcode()
            variant_code = variant.barcode
            attribute_lines = [
                {
                    "name": value.attribute_id.display_name or "",
                    "value": value.name or "",
                }
                for value in variant.product_template_attribute_value_ids
            ]
            label_data = {
                "product_name": template.display_name or template.name or "",
                "warehouse_name": self.warehouse_id.display_name or "",
                "variant_name": variant.display_name or variant.name or "",
                "variant_attributes": attribute_lines,
                "is_variant_label": True,
                "label_model": template.ddsl_label_model or "",
                "label_design": template.ddsl_label_design or "",
                "label_size": template.ddsl_label_size or "",
                "label_swing": template.ddsl_label_swing or "",
                "label_hinge": template.ddsl_label_hinge or "",
                "product_code": variant_code,
                "barcode_src": variant.ddsl_get_label_barcode_src(variant_code),
            }
            payloads.extend(
                dict(label_data) for _index in range(max(self.quantity, 1))
            )
        return payloads

    def _prepare_label_payloads(self):
        self.ensure_one()
        if (self.quantity or 0) <= 0:
            raise UserError(_("Labels Quantity must be greater than zero."))
        if self.quantity > MAX_LABELS_PER_PDF:
            raise UserError(_(
                "A maximum of %s labels can be generated in one PDF."
            ) % MAX_LABELS_PER_PDF)
        payloads = []
        if self.label_scope == "product" or (
            self.label_scope == "product_variants" and self.batch_number == 1
        ):
            product_payloads = super()._prepare_label_payloads()
            for payload in product_payloads:
                payload["is_template_label"] = True
                if self.product_tmpl_id.product_variant_count > 1:
                    payload["inventory_warning"] = _(
                        "PRODUCT TEMPLATE - NOT FOR INVENTORY COUNT"
                    )
            payloads.extend(product_payloads)
        if self.label_scope in ("variants", "product_variants"):
            payloads.extend(self._prepare_variant_label_payloads())
        return payloads
