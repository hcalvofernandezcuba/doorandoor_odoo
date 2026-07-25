from odoo import api, fields, models
from odoo.exceptions import UserError


class DdpcVariantSelector(models.TransientModel):
    _name = "ddpc.variant.selector"
    _description = "DoorAndDoor Variant Selector"

    move_line_id = fields.Many2one("account.move.line", required=True, readonly=True)
    product_template_id = fields.Many2one("product.template", string="Product Template", required=True)
    variant_id = fields.Many2one(
        "product.product",
        string="Variant",
        required=True,
        domain="[('product_tmpl_id', '=', product_template_id)]",
    )
    variant_extra_price = fields.Float(
        string="Variant Extra",
        related="variant_id.ddpc_variant_extra_price",
        readonly=True,
    )
    configured_price = fields.Float(
        string="Configured Price",
        compute="_compute_configured_price",
        readonly=True,
    )

    @api.depends("product_template_id.list_price", "variant_id.ddpc_variant_extra_price")
    def _compute_configured_price(self):
        for wizard in self:
            wizard.configured_price = wizard.product_template_id.list_price + wizard.variant_id.ddpc_variant_extra_price

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        for wizard in self:
            if wizard.variant_id and wizard.variant_id.product_tmpl_id != wizard.product_template_id:
                wizard.variant_id = False
            if not wizard.variant_id and wizard.product_template_id.product_variant_count == 1:
                wizard.variant_id = wizard.product_template_id.product_variant_id

    def action_apply_variant(self):
        self.ensure_one()
        line = self.move_line_id
        if not line:
            raise UserError("The invoice line is no longer available.")
        if line.move_id.state != "draft":
            raise UserError("You can only configure variants on draft invoices.")

        line.product_id = self.variant_id
        line._ddpc_apply_variant_price()
        line.name = self.variant_id.get_product_multiline_description_sale() or self.variant_id.display_name
        return {"type": "ir.actions.act_window_close"}
