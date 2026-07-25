from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ddsn_quote_registered = fields.Boolean(
        string="Registered Quote",
        default=False,
        copy=False,
        tracking=True,
    )
    ddsn_quote_list_visible = fields.Boolean(
        string="Visible in Quotations List",
        compute="_compute_ddsn_quote_list_visible",
        store=True,
        index=True,
    )
    ddsn_flow_stage = fields.Selection(
        [
            ("quotation", "Cotización"),
            ("preinvoice", "Prefactura"),
            ("invoiced", "Facturada"),
        ],
        string="Flow Stage",
        default="quotation",
        tracking=True,
        copy=False,
    )
    ddsn_preinvoice_move_id = fields.Many2one(
        "account.move",
        string="Current Preinvoice",
        copy=False,
        readonly=True,
    )
    ddsn_invoice_move_id = fields.Many2one(
        "account.move",
        string="Final Invoice",
        copy=False,
        readonly=True,
    )
    ddsn_shipping_address_summary = fields.Text(
        string="Delivery Address Summary",
        compute="_compute_ddsn_shipping_address_summary",
    )

    @api.depends("ddsn_quote_registered", "name")
    def _compute_ddsn_quote_list_visible(self):
        for order in self:
            order.ddsn_quote_list_visible = bool(order.ddsn_quote_registered or ((order.name or "") != "New"))

    @api.depends(
        "partner_shipping_id",
        "partner_shipping_id.name",
        "partner_shipping_id.street",
        "partner_shipping_id.street2",
        "partner_shipping_id.city",
        "partner_shipping_id.state_id",
        "partner_shipping_id.zip",
        "partner_shipping_id.country_id",
        "partner_shipping_id.phone",
        "partner_shipping_id.mobile",
    )
    def _compute_ddsn_shipping_address_summary(self):
        for order in self:
            partner = order.partner_shipping_id
            if not partner:
                order.ddsn_shipping_address_summary = False
                continue
            parts = [
                partner.name,
                partner.street,
                partner.street2,
                partner.city,
                partner.state_id.name,
                partner.zip,
                partner.country_id.name,
                partner.phone or partner.mobile,
            ]
            order.ddsn_shipping_address_summary = "\n".join(part for part in parts if part)

    @api.model_create_multi
    def create(self, vals_list):
        sequence_code = "sale.order"
        for vals in vals_list:
            if vals.get("name") and vals["name"] != "New":
                continue
            if self.env.context.get("ddsn_assign_number_immediately"):
                vals["name"] = self.env["ir.sequence"].next_by_code(sequence_code) or "New"
                vals.setdefault("ddsn_quote_registered", True)
            else:
                vals["name"] = "New"
                vals.setdefault("ddsn_quote_registered", False)
        return super().create(vals_list)

    def action_ddsn_register_quote(self):
        for order in self:
            if order.ddsn_quote_registered:
                preinvoice = order.ddsn_preinvoice_move_id.filtered(lambda move: move.state == "draft")[:1]
                if preinvoice:
                    return order._ddsn_open_preinvoice(preinvoice)
            order._ddsn_assign_quote_number()
            preinvoice = order._ddsn_create_preinvoice()
            order.write(
                {
                    "ddsn_quote_registered": True,
                    "ddsn_flow_stage": "preinvoice",
                    "ddsn_preinvoice_move_id": preinvoice.id,
                }
            )
            return order._ddsn_open_preinvoice(preinvoice)
        return True

    def action_confirm(self):
        if self.env.context.get("ddsn_finalize_from_preinvoice"):
            self._ddsn_assign_quote_number()
            self.write({"ddsn_quote_registered": True, "ddsn_flow_stage": "invoiced"})
            return super().action_confirm()
        return self.action_ddsn_register_quote()

    def action_view_ddsn_preinvoice(self):
        self.ensure_one()
        if not self.ddsn_preinvoice_move_id:
            return False
        return self._ddsn_open_preinvoice(self.ddsn_preinvoice_move_id)

    def _ddsn_assign_quote_number(self):
        for order in self:
            if not order.name or order.name == "New":
                order.name = self.env["ir.sequence"].next_by_code("sale.order") or "New"
            order.ddsn_quote_registered = True

    @api.onchange("partner_id")
    def _onchange_partner_id_ddsn_delivery_address(self):
        for order in self.filtered("partner_id"):
            commercial_partner = order.partner_id.commercial_partner_id
            available_addresses = commercial_partner.child_ids.filtered(lambda child: child.type == "delivery")
            if order.partner_shipping_id in available_addresses:
                continue
            order.partner_shipping_id = available_addresses[:1] or order.partner_id

    def _ddsn_create_preinvoice(self):
        self.ensure_one()
        existing_preinvoice = self.ddsn_preinvoice_move_id.filtered(lambda move: move.state == "draft")[:1]
        if existing_preinvoice:
            return existing_preinvoice

        invoice_line_commands = []
        for line in self.order_line.filtered(lambda order_line: not order_line.display_type and order_line.product_uom_qty):
            line_vals = {
                "product_id": line.product_id.id,
                "name": line.name or line.product_id.display_name,
                "quantity": line.product_uom_qty,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "generated_sale_line_id": line.id,
                "tax_ids": [(6, 0, line.tax_id.ids)],
            }
            if "sale_line_ids" in self.env["account.move.line"]._fields:
                line_vals["sale_line_ids"] = [(6, 0, [line.id])]
            invoice_line_commands.append((0, 0, line_vals))

        move_vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_invoice_id.id or self.partner_id.id,
            "partner_shipping_id": self.partner_shipping_id.id or self.partner_id.id,
            "invoice_origin": self.name,
            "ref": self.name,
            "payment_reference": self.name,
            "invoice_user_id": self.user_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_line_ids": invoice_line_commands,
            "sale_order_id": self.id,
        }
        return self.env["account.move"].create(move_vals)

    def _ddsn_open_preinvoice(self, preinvoice):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action["res_id"] = preinvoice.id
        action["views"] = [(False, "form")]
        action["view_mode"] = "form"
        return action
