from odoo import api, fields, models


class ProductLabelWizard(models.TransientModel):
    _name = "ddsl.product.label.wizard"
    _description = "DoorAndDoor Product Label Wizard"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    quantity = fields.Integer(string="Labels Quantity", default=1, required=True)
    label_format = fields.Selection(
        [("small", "Almacén — Zebra 3×1"), ("large", "Entrega — Zebra 4×6")],
        string="Tamaño de etiqueta", default="small", required=True,
    )
    product_label_code = fields.Char(
        related="product_tmpl_id.ddsl_product_label_code",
        string="Codigo de producto para label",
        readonly=False,
        help="Puedes escribir aqui el codigo comercial que debe aparecer en el label.",
    )
    effective_label_code = fields.Char(
        string="Codigo que se imprimira",
        compute="_compute_effective_label_code",
    )
    uses_automatic_label_code = fields.Boolean(
        compute="_compute_effective_label_code",
    )

    @api.depends(
        "product_tmpl_id",
        "product_label_code",
        "product_tmpl_id.default_code",
        "product_tmpl_id.barcode",
        "product_tmpl_id.product_variant_ids.default_code",
        "product_tmpl_id.product_variant_ids.barcode",
    )
    def _compute_effective_label_code(self):
        for wizard in self:
            product = wizard.product_tmpl_id
            wizard.effective_label_code = product.ddsl_get_product_label_code() if product else False
            wizard.uses_automatic_label_code = bool(product and not wizard.product_label_code)

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        product_tmpl_id = self.env.context.get("default_product_tmpl_id")
        if product_tmpl_id:
            values["product_tmpl_id"] = product_tmpl_id
        if "warehouse_id" in field_list or not values.get("warehouse_id"):
            warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", self.env.company.id)],
                limit=1,
            )
            if warehouse:
                values["warehouse_id"] = warehouse.id
        return values

    def _prepare_label_payloads(self):
        self.ensure_one()
        product = self.product_tmpl_id
        product_code = self.effective_label_code or product.ddsl_get_product_label_code()

        label_data = {
            "product_name": product.display_name or product.name or "",
            "warehouse_name": self.warehouse_id.display_name or "",
            "label_model": product.ddsl_label_model or "",
            "label_design": product.ddsl_label_design or "",
            "label_size": product.ddsl_label_size or "",
            "label_swing": product.ddsl_label_swing or "",
            "label_hinge": product.ddsl_label_hinge or "",
            "product_code": product_code,
            "barcode_src": product.product_variant_id.ddsl_get_label_barcode_src(product_code),
        }
        return [dict(label_data) for _index in range(max(self.quantity, 1))]

    def action_print_labels(self):
        self.ensure_one()
        payloads = self._prepare_label_payloads()
        action_xmlid = (
            "doorandoor_stock_labels.action_report_ddsl_product_labels"
            if self.label_format == "large"
            else "doorandoor_stock_labels.action_report_ddsl_product_labels_small"
        )
        action = self.env.ref(action_xmlid)
        return action.report_action(self, data={"labels": payloads})
