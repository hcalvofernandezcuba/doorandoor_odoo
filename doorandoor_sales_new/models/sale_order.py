from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "doorandoor.document.barcode.mixin"]
    _description = "Sales Order"

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
            ("po", "PO"),
            ("invoiced", "Facturada"),
        ],
        string="Flow Stage",
        default="quotation",
        tracking=True,
        copy=False,
    )
    ddsn_po_first_flow = fields.Boolean(
        string="Flujo PO antes de factura",
        default=True,
        copy=False,
        index=True,
        help="La Orden de Venta se emite como PO desde la prefactura y la factura fiscal se crea automáticamente al liquidar la entrega.",
    )
    ddsn_po_issued_at = fields.Datetime(
        string="PO emitido el",
        copy=False,
        readonly=True,
        tracking=True,
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
        for order in self:
            order.order_line.filtered(
                lambda line: not line.display_type and line.product_id
            ).with_context(ddsn_automatic_pricing=True)._ddsn_apply_automatic_bonus()
        for order in self:
            order._ddsn_prepare_office_stock_requests()
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

    def _ddsn_prepare_office_stock_requests(self):
        """Keep the sale at its office and request replenishment for shortages."""
        Request = self.env["ddsn.stock.transfer.request"]
        for order in self:
            warehouse = order.warehouse_id
            if not warehouse:
                continue
            for line in order.order_line.filtered(lambda item: not item.display_type and item.product_id):
                if line.ddsn_supply_warehouse_id != warehouse:
                    line.ddsn_supply_warehouse_id = warehouse
                product, required_qty, transformed = line._ddsn_get_stock_control_product()
                if not product or not product.is_storable or required_qty <= 0:
                    continue
                available = product.with_company(order.company_id).with_context(
                    location=warehouse.lot_stock_id.id
                ).qty_available
                if not transformed:
                    available -= line._ddsn_get_committed_qty_for_display(warehouse=warehouse)
                    available -= line._ddsn_get_reserved_qty_for_display(warehouse=warehouse)
                shortage = max(required_qty - available, 0.0)
                if not shortage:
                    continue
                existing = Request.search([
                    ("sale_line_id", "=", line.id), ("state", "not in", ("done", "cancel"))
                ], limit=1)
                if existing:
                    continue
                request = Request.create({
                    "sale_order_id": order.id, "sale_line_id": line.id,
                    "product_id": product.id, "quantity": shortage,
                    "destination_warehouse_id": warehouse.id,
                    "company_id": order.company_id.id, "requested_by_id": self.env.user.id,
                })
                order.message_post(body=_(
                    "Solicitud logística %(request)s creada: %(qty).2f de %(product)s hacia %(warehouse)s. "
                    "Logística decidirá el almacén de origen."
                ) % {"request": request.name, "qty": shortage, "product": product.display_name, "warehouse": warehouse.display_name})

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

    def action_ddsn_print_po(self):
        self.ensure_one()
        preinvoice = self.ddsn_preinvoice_move_id
        if (
            not self.ddsn_po_first_flow
            or not preinvoice
            or preinvoice.ddsn_preinvoice_state != "confirmed"
        ):
            raise ValidationError(_("Confirme la prefactura antes de emitir el PO."))
        if not self.ddsn_po_issued_at:
            self.write({"ddsn_po_issued_at": fields.Datetime.now(), "ddsn_flow_stage": "po"})
            self.message_post(body=_("PO emitido desde la prefactura %s.") % preinvoice.ddsn_preinvoice_number)
        return self.env.ref("doorandoor_sales_new.action_report_ddsn_po").report_action(self)

    def _create_invoices(self, grouped=False, final=False, date=None):
        blocked_orders = self.filtered("ddsn_po_first_flow")
        if blocked_orders and not self.env.context.get("ddsn_invoice_after_delivery"):
            raise ValidationError(
                _("No puede crear la factura en esta etapa. En el flujo PO la factura se genera después de liquidar la entrega.")
            )
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def _ddsn_create_invoice_after_full_delivery(self):
        """Create and post the fiscal invoice once a PO is fully delivered."""
        for order in self.filtered("ddsn_po_first_flow"):
            # The hook runs inside stock.move._action_done. Discard the sale
            # line cache so Odoo reads the quantities just completed by stock.
            order.order_line.invalidate_recordset(["qty_delivered", "qty_to_invoice"])
            fiscal_invoices = (order.invoice_ids | order.ddsn_invoice_move_id).filtered(
                lambda move: move.move_type == "out_invoice"
                and move.state != "cancel"
                and not move.ddsn_is_preinvoice
            )
            if fiscal_invoices:
                continue
            product_lines = order.order_line.filtered(
                lambda line: not line.display_type and line.product_id
            )
            if not product_lines or any(
                float_compare(
                    line.qty_delivered,
                    line.product_uom_qty,
                    precision_rounding=line.product_uom.rounding,
                ) < 0
                for line in product_lines
            ):
                continue
            preinvoice = order.ddsn_preinvoice_move_id
            if not preinvoice or preinvoice.ddsn_preinvoice_state != "confirmed":
                raise ValidationError(
                    _("El PO %s no tiene una prefactura confirmada para generar la factura fiscal.")
                    % order.name
                )
            preinvoice.with_context(
                ddsn_invoice_after_delivery=True
            ).action_ddsn_create_invoice_from_preinvoice()
            invoice = preinvoice.ddsn_created_invoice_id
            if not invoice:
                raise ValidationError(
                    _("No fue posible generar la factura fiscal después de completar la entrega del PO %s.")
                    % order.name
                )
            order.ddsn_invoice_move_id = invoice.id
            order.ddsn_flow_stage = "invoiced"
            if preinvoice:
                preinvoice.write(
                    {
                        "ddsn_created_invoice_id": invoice.id,
                        "ddsn_reservation_expires_at": False,
                    }
                )
            invoice.write(
                {
                    "ddsn_source_preinvoice_id": preinvoice.id,
                    "sale_order_id": order.id,
                }
            )
            invoice.action_post()
            order.message_post(
                body=_("Entrega liquidada. Se creó y contabilizó automáticamente la factura %s.")
                % invoice.name
            )
            order._ddsn_broadcast_document_update("invoice_created_after_delivery")
        return True

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
                "ddsn_bonus_percent": line.ddsn_bonus_percent,
                "ddsn_bonus_source": line.ddsn_bonus_source,
                "ddsn_bonus_rule_reference": line.ddsn_bonus_rule_reference,
                "ddsn_bonus_authorized_by_id": line.ddsn_bonus_authorized_by_id.id,
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
        return self.env["account.move"].with_context(ddsn_automatic_pricing=True).create(move_vals)

    def _ddsn_open_preinvoice(self, preinvoice):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action["res_id"] = preinvoice.id
        action["views"] = [(False, "form")]
        action["view_mode"] = "form"
        return action

    def write(self, vals):
        if (
            "pricelist_id" in vals
            and not self.env.context.get("ddsn_automatic_pricing")
            and not self.env.user.has_group("base.group_system")
        ):
            changed_orders = self.filtered(
                lambda order: order.order_line
                and order.pricelist_id.id != vals.get("pricelist_id")
            )
            if changed_orders:
                raise ValidationError(
                    _("Solo un administrador de Ajustes puede cambiar la lista de precios después de agregar productos.")
                )
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

    def action_ddsn_admin_set_draft(self):
        """Safely reopen a confirmed sale without bypassing downstream documents.

        DoorAndDoor confirms quotations without native procurement, but the
        confirmation may create pending inter-warehouse replenishment requests.
        Only those still pending are cancelled automatically.  Once another
        operational or fiscal document exists, support must resolve that
        document first instead of silently breaking its traceability.
        """
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Solo Administración/Ajustes puede devolver una venta a borrador.")
            )
        Request = self.env["ddsn.stock.transfer.request"].sudo()
        for order in self:
            if order.state not in ("sale", "done", "sent", "cancel"):
                continue
            active_invoices = order.invoice_ids.filtered(lambda move: move.state != "cancel")
            if active_invoices:
                raise ValidationError(
                    _(
                        "No puede devolver %(sale)s a borrador porque tiene documentos de "
                        "facturación activos: %(documents)s. Cancélelos o reviértalos primero."
                    )
                    % {
                        "sale": order.name,
                        "documents": ", ".join(active_invoices.mapped("name")),
                    }
                )
            active_pickings = order.picking_ids.filtered(lambda picking: picking.state != "cancel")
            if active_pickings:
                raise ValidationError(
                    _(
                        "No puede devolver %(sale)s a borrador porque tiene operaciones de "
                        "inventario activas: %(documents)s. Cancélelas o termínelas primero."
                    )
                    % {
                        "sale": order.name,
                        "documents": ", ".join(active_pickings.mapped("name")),
                    }
                )
            requests = Request.search([
                ("sale_order_id", "=", order.id),
                ("state", "not in", ("done", "cancel")),
            ])
            processed_requests = requests.filtered(
                lambda request: request.state != "pending" or request.picking_id
            )
            if processed_requests:
                raise ValidationError(
                    _(
                        "No puede devolver %(sale)s a borrador porque las solicitudes "
                        "logísticas %(requests)s ya generaron una operación."
                    )
                    % {
                        "sale": order.name,
                        "requests": ", ".join(processed_requests.mapped("name")),
                    }
                )
            request_names = requests.mapped("name")
            if requests:
                requests.write({"state": "cancel"})
                for request in requests:
                    request.message_post(
                        body=_(
                            "Solicitud cancelada automáticamente al devolver la venta %(sale)s "
                            "a borrador por %(user)s."
                        )
                        % {"sale": order.name, "user": self.env.user.display_name}
                    )
            previous_state = order.state
            order.write(
                {
                    "state": "draft",
                    "signature": False,
                    "signed_by": False,
                    "signed_on": False,
                }
            )
            order.message_post(
                body=_(
                    "Venta devuelta de %(previous)s a borrador por %(user)s "
                    "(Administración/Ajustes). Solicitudes logísticas pendientes canceladas: %(requests)s."
                )
                % {
                    "previous": previous_state,
                    "user": self.env.user.display_name,
                    "requests": ", ".join(request_names) or _("ninguna"),
                }
            )
        self._ddsn_broadcast_document_update("sale_reopened")
        return True
