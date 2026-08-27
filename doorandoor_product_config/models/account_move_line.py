from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ddpc_product_template_id = fields.Many2one(
        "product.template",
        string="Producto",
        compute="_compute_ddpc_product_template_id",
        inverse="_inverse_ddpc_product_template_id",
        store=True,
        readonly=False,
        domain="[('sale_ok', '=', True)]",
        help="Seleccione el modelo del producto; la variante se define con Armar producto.",
    )
    ddpc_configurator_token = fields.Char(
        string="Token del configurador",
        default=lambda self: uuid4().hex,
        copy=False,
        readonly=True,
        index=True,
    )

    ddpc_selected_option_value_ids = fields.Many2many(
        "product.template.attribute.value",
        "ddpc_move_line_option_rel",
        "move_line_id",
        "template_value_id",
        string="Opciones configuradas",
        copy=True,
        readonly=True,
    )

    ddpc_base_price = fields.Float(
        string="Base Price",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )
    ddpc_variant_extra_price = fields.Float(
        string="Variant Extra",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )
    ddpc_configured_price_unit = fields.Float(
        string="Configured Price",
        digits="Product Price",
        compute="_compute_ddpc_pricing",
        readonly=True,
    )

    @api.depends("product_id.product_tmpl_id")
    def _compute_ddpc_product_template_id(self):
        for line in self:
            line.ddpc_product_template_id = line.product_id.product_tmpl_id

    def _inverse_ddpc_product_template_id(self):
        for line in self:
            template = line.ddpc_product_template_id
            # La plantilla solo abre el configurador. No colocar una variante
            # provisional aqui: hacerlo dispara onchanges y el calculo de stock
            # antes de que el vendedor confirme la combinacion definitiva.
            if not template or (line.product_id and line.product_id.product_tmpl_id != template):
                line.product_id = False

    @api.onchange("ddpc_product_template_id")
    def _onchange_ddpc_product_template_id(self):
        for line in self:
            if line.ddpc_product_template_id and not line.ddpc_configurator_token:
                line.ddpc_configurator_token = uuid4().hex
        self._inverse_ddpc_product_template_id()

    @api.depends("product_id", "product_id.product_tmpl_id.list_price", "product_id.ddpc_variant_extra_price")
    def _compute_ddpc_pricing(self):
        for line in self:
            if not line.product_id:
                line.ddpc_base_price = 0.0
                line.ddpc_variant_extra_price = 0.0
                line.ddpc_configured_price_unit = 0.0
                continue

            base_price = line._ddpc_get_base_price()
            extra_price = line.product_id.ddpc_variant_extra_price
            line.ddpc_base_price = base_price
            line.ddpc_variant_extra_price = extra_price
            line.ddpc_configured_price_unit = base_price + extra_price

    def _ddpc_is_customer_invoice_line(self):
        self.ensure_one()
        return (
            self.move_id
            and self.move_id.move_type in ("out_invoice", "out_refund")
            and self.display_type in (False, "product")
            and self.product_id
        )

    def _ddpc_get_base_price(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return 0.0
        return product.product_tmpl_id.list_price

    def _ddpc_apply_variant_price(self):
        for line in self:
            if not line._ddpc_is_customer_invoice_line():
                continue
            line.with_context(ddsn_automatic_pricing=True).price_unit = (
                line._ddpc_get_base_price() + line.product_id.ddpc_variant_extra_price
            )

    def action_open_ddpc_variant_selector(self):
        self.ensure_one()
        if not self.move_id or self.move_id.move_type not in ("out_invoice", "out_refund"):
            return False

        product_template = self.ddpc_product_template_id or self.product_id.product_tmpl_id
        if not product_template:
            raise UserError(_("Seleccione primero el producto que desea armar."))

        wizard = self.env["ddpc.variant.selector"].create(
            {
                "move_line_id": self.id,
                "product_template_id": product_template.id,
                "variant_id": self.product_id.id or product_template.product_variant_id.id,
            }
        )
        wizard._ddpc_load_options()
        return {
            "type": "ir.actions.act_window",
            "name": _("Armar producto"),
            "res_model": "ddpc.variant.selector",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    @api.model
    def action_open_ddpc_variant_selector_by_token(self, move_id, token):
        if not move_id or not token:
            raise UserError(_("No se pudo identificar la linea guardada para configurar."))
        line = self.search(
            [("move_id", "=", move_id), ("ddpc_configurator_token", "=", token)],
            order="id desc",
            limit=1,
        )
        if not line:
            raise UserError(_("La linea no fue guardada. Revise los campos obligatorios de la prefactura."))
        return line.action_open_ddpc_variant_selector()

    @api.onchange("product_id")
    def _onchange_product_id_ddpc_variant_price(self):
        self._ddpc_apply_variant_price()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ddpc_apply_variant_price()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if "product_id" in vals:
            self._ddpc_apply_variant_price()
        return result
