from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Keep every reassignment in chatter so commercial reports can reproduce
    # the actual chain of responsibility instead of only the current owner.
    user_id = fields.Many2one(tracking=True)

    ddsn_origin_salesperson_id = fields.Many2one(
        "res.users",
        string="Comercial inicial",
        default=lambda self: self.env.user,
        copy=False,
        readonly=True,
        tracking=True,
        help="Comercial que inició la cotización. Se conserva aunque otro comercial asuma el proceso.",
    )

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

    def _ddsn_get_salesperson_history(self):
        """Return the chronological salesperson history recorded in chatter."""
        self.ensure_one()
        names = []

        def append_name(name):
            name = (name or "").strip()
            if name and (not names or names[-1] != name):
                names.append(name)

        tracking_values = self.env["mail.tracking.value"].sudo().search(
            [
                ("mail_message_id", "in", self.message_ids.ids),
                ("field_id.name", "=", "user_id"),
                ("field_id.model", "=", "sale.order"),
            ],
            order="id asc",
        )
        for tracking in tracking_values:
            append_name(tracking.old_value_char)
            append_name(tracking.new_value_char)
        if not names:
            origin = self.ddsn_origin_salesperson_id
            if origin and origin != self.env.ref("base.user_root"):
                append_name(origin.name)
        append_name((self.user_id or self.create_uid).name)
        return names

    def action_ddsn_change_supply_warehouse(self):
        self.ensure_one()
        if self.state == "cancel":
            raise ValidationError(_("No se puede cambiar el almacén de una cotización cancelada."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Cambiar almacén proveedor"),
            "res_model": "ddsn.supply.warehouse.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
                "default_sale_line_id": self.order_line.filtered(
                    lambda line: not line.display_type and line.product_id
                )[:1].id,
            },
        }

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
        force_current_salesperson = self.env.user.has_group("sales_team.group_sale_salesman") and not self.env.user.has_group(
            "sales_team.group_sale_salesman_all_leads"
        )
        for vals in vals_list:
            vals.setdefault("ddsn_origin_salesperson_id", self.env.user.id)
            if force_current_salesperson:
                vals["user_id"] = self.env.user.id
            else:
                vals.setdefault("user_id", self.env.user.id)
            # Flujo nativo: asignar número de cotización inmediatamente
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(sequence_code) or "New"
                vals.setdefault("ddsn_quote_registered", True)
        return super().create(vals_list)

    def action_ddsn_register_quote(self):
        # Paso manual: crear prefactura desde cotización confirmada SIN cambiar estado
        for order in self:
            if self.env.user.has_group("sales_team.group_sale_salesman") and not self.env.user.has_group(
                "sales_team.group_sale_salesman_all_leads"
            ) and order.user_id != self.env.user:
                order.user_id = self.env.user
            
            # Verificar si ya existe prefactura borrador
            preinvoice = order.ddsn_preinvoice_move_id.filtered("ddsn_is_preinvoice")[:1]
            if preinvoice:
                return order._ddsn_open_preinvoice(preinvoice)
            
            # Crear nueva prefactura sin cambiar el estado de la cotización
            preinvoice = order._ddsn_create_preinvoice()
            order.write(
                {
                    "ddsn_preinvoice_move_id": preinvoice.id,
                }
            )
            return order._ddsn_open_preinvoice(preinvoice)
        return True

    def action_confirm(self):
        # Flujo nativo: confirmar cotización sin crear prefactura automáticamente
        if self.env.context.get("ddsn_finalize_from_preinvoice"):
            self._ddsn_assign_quote_number()
            self.write({"ddsn_quote_registered": True, "ddsn_flow_stage": "invoiced"})
            # La confirmacion comercial no debe lanzar el picking nativo de
            # sale_stock. Los despachos se liberan exclusivamente desde la
            # factura, una vez comprobado el pago total.
            result = super(SaleOrder, self.with_context(skip_procurement=True)).action_confirm()
            self._ddsn_broadcast_document_update("sale_confirmed")
            return result
        
        # Asignar número de cotización si no tiene
        for order in self:
            if not order.ddsn_quote_registered:
                order._ddsn_assign_quote_number()
        
        # Confirmar la cotización de forma nativa
        result = super(SaleOrder, self.with_context(skip_procurement=True)).action_confirm()
        self._ddsn_broadcast_document_update("sale_confirmed")
        return result

    def _ddsn_confirm_for_fiscal_invoice(self):
        """Align the native sale state before a linked fiscal invoice posts.

        DoorAndDoor suppresses native procurement because customer deliveries
        are released by the paid invoice.  Some invoice-creation paths kept the
        functional quotation confirmed while its native ``state`` remained in
        draft.  That mismatch later blocked the paid-invoice delivery flow.
        """
        orders_to_confirm = self.filtered(lambda order: order.state in ("draft", "sent"))
        if not orders_to_confirm:
            return True
        orders_to_confirm.with_context(
            ddsn_finalize_from_preinvoice=True,
            skip_procurement=True,
        ).action_confirm()
        return True

    def _ddsn_broadcast_document_update(self, reason="updated"):
        """Refresh clean commercial forms opened in other browser sessions."""
        for order in self:
            invoices = order.ddsn_preinvoice_move_id | order.ddsn_invoice_move_id
            self.env["bus.bus"]._sendone(
                "doorandoor.payment.operations",
                "doorandoor_payment_update",
                {
                    "reason": reason,
                    "sale_order_ids": order.ids,
                    "invoice_ids": invoices.ids,
                    "payment_ids": [],
                    "control_ids": [],
                    "partner_ids": order.partner_id.commercial_partner_id.ids,
                    "title": _("Documento comercial actualizado"),
                    "message": _("La cotización o uno de sus documentos relacionados cambió de estado."),
                },
            )

    def action_view_ddsn_preinvoice(self):
        self.ensure_one()
        if not self.ddsn_preinvoice_move_id:
            return False
        return self._ddsn_open_preinvoice(self.ddsn_preinvoice_move_id)

    def _ddsn_assign_quote_number(self):
        for order in self:
            if self.env.user.has_group("sales_team.group_sale_salesman") and not self.env.user.has_group(
                "sales_team.group_sale_salesman_all_leads"
            ) and order.user_id != self.env.user:
                order.user_id = self.env.user
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
        existing_preinvoice = self.ddsn_preinvoice_move_id.filtered("ddsn_is_preinvoice")[:1]
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
                "ddsn_supply_warehouse_id": (
                    line.ddsn_supply_warehouse_id or self.warehouse_id
                ).id,
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
            "ddsn_origin_salesperson_id": (
                self.ddsn_origin_salesperson_id or self.create_uid
            ).id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_line_ids": invoice_line_commands,
            "sale_order_id": self.id,  # Vincular la orden de venta existente
            "ddsn_is_preinvoice": True,
            "ddsn_preinvoice_state": "draft",
        }
        return self.env["account.move"].create(move_vals)

    def _ddsn_open_preinvoice(self, preinvoice):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action["res_id"] = preinvoice.id
        action["views"] = [(False, "form")]
        action["view_mode"] = "form"
        return action

    def write(self, vals):
        previous_salespeople = (
            {order.id: order.user_id for order in self}
            if "user_id" in vals
            else {}
        )
        protected_commercial_fields = {
            "partner_id",
            "partner_invoice_id",
            "partner_shipping_id",
            "validity_date",
            "date_order",
            "pricelist_id",
            "payment_term_id",
            "warehouse_id",
            "user_id",
            "team_id",
            "order_line",
            "fiscal_position_id",
            "company_id",
            "currency_id",
            "client_order_ref",
        }
        if protected_commercial_fields.intersection(vals) and self.filtered(
            lambda order: order.state in ("sale", "done")
        ):
            raise ValidationError(
                _("No se puede editar una cotización confirmada. "
                  "Un administrador de Ajustes debe devolverla a borrador antes de modificarla.")
            )
        result = super().write(vals)
        if previous_salespeople:
            tracked_field = self.env["ir.model.fields"].sudo().search(
                [("model", "=", "sale.order"), ("name", "=", "user_id")],
                limit=1,
            )
            for order in self:
                previous = previous_salespeople[order.id]
                current = order.user_id
                if previous == current:
                    continue
                message = order.message_post(
                    body=_("Cambio de comercial: %(previous)s → %(current)s")
                    % {
                        "previous": previous.name or _("Sin asignar"),
                        "current": current.name or _("Sin asignar"),
                    },
                    subtype_xmlid="mail.mt_note",
                )
                if tracked_field:
                    self.env["mail.tracking.value"].sudo().create(
                        {
                            "mail_message_id": message.id,
                            "field_id": tracked_field.id,
                            "old_value_char": previous.name or "",
                            "new_value_char": current.name or "",
                        }
                    )
        return result

    def action_draft(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Solo un administrador con acceso a Ajustes puede devolver una cotización a borrador.")
            )
        result = super().action_draft()
        self._ddsn_broadcast_document_update("sale_reopened")
        return result
