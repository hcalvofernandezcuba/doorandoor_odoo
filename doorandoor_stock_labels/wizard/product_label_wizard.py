from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        product_code = product.ddsl_product_label_code or product.default_code or product.barcode
        if not product_code:
            raise UserError(
                _("El producto %s debe tener un Codigo de producto para imprimir su label.") % product.display_name
            )

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
        action = self.env.ref("doorandoor_stock_labels.action_report_ddsl_product_labels")
        return action.report_action(self, data={"labels": payloads})
