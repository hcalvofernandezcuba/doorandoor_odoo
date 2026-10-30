from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "doorandoor.document.barcode.mixin"]

    ddsn_admin_unrestricted_print = fields.Boolean(
        string="Impresión administrativa sin restricción",
        compute="_compute_ddsn_admin_unrestricted_print",
        help="Permite mostrar e imprimir cualquier documento comercial a "
             "Administración/Ajustes sin retirar las reglas al resto de usuarios.",
    )

    @api.depends_context("uid")
    def _compute_ddsn_admin_unrestricted_print(self):
        allowed = self.env.user.has_group("base.group_system")
        for move in self:
            move.ddsn_admin_unrestricted_print = allowed

    def _ddsn_check_printable_invoice(self):
        if self.env.user.has_group("base.group_system"):
            return
        unconfirmed = self.filtered(
            lambda move: move.move_type in ("out_invoice", "out_refund")
            and not move.ddsn_is_preinvoice
            and move.state != "posted"
        )
        if unconfirmed:
            raise ValidationError(_(
                "La factura debe estar confirmada antes de imprimirse o enviarse. "
                "Las prefacturas y borradores no reciben número de factura."
            ))
        unpaid = self.filtered(
            lambda move: move.move_type in ("out_invoice", "out_refund")
            and not move.ddsn_is_preinvoice
            and move.state == "posted"
            and move.payment_state != "paid"
            and not move._ddsn_has_printable_partial_payment()
        )
        if unpaid:
            move = unpaid[0]
            validated, _required = move._ddsn_partial_print_amounts()
            raise ValidationError(_(
                "La factura solo puede imprimirse o enviarse cuando el pago esté "
                "completado o exista al menos un cobro real validado. "
                "Validado: %(validated)s. Puede consultar la "
                "Vista previa mientras permanezca pendiente."
            ) % {
                "validated": move.currency_id.format(validated),
            })

    def _ddsn_partial_print_amounts(self):
        """Return validated and former milestone amounts for compatibility.

        The commercial milestone remains useful to payment and fulfillment
        workflows.  Printing, however, is released by any positive amount
        validated by Control de Cobros; a merely reported or pending payment
        never unlocks the official document.
        """
        self.ensure_one()
        validated = getattr(self, "ddc_total_validated", 0.0) or 0.0
        if self.move_type != "out_invoice":
            return validated, self.amount_total
        required = self.currency_id.round(
            self.amount_untaxed * 0.5 + self.amount_tax
        )
        if getattr(self, "ddtp_card_payment_enabled", False):
            required += getattr(self, "ddtp_card_fee_amount", 0.0) or 0.0
            required = self.currency_id.round(required)
        return validated, required

    def _ddsn_has_printable_partial_payment(self):
        self.ensure_one()
        validated, _required = self._ddsn_partial_print_amounts()
        return (
            self.move_type == "out_invoice"
            and self.currency_id.compare_amounts(validated, 0.0) > 0
        )

    def action_ddsn_preview_invoice(self):
        """Open a non-official HTML preview without generating the PDF output."""
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund") or self.state != "posted":
            raise ValidationError(_("La vista previa está disponible solo para facturas confirmadas."))
        return {
            "type": "ir.actions.act_url",
            "url": "/report/html/account.report_invoice/%s" % self.id,
            "target": "new",
        }

    def action_print_pdf(self):
        self._ddsn_check_printable_invoice()
        return super().action_print_pdf()

    def action_invoice_sent(self):
        self._ddsn_check_printable_invoice()
        return super().action_invoice_sent()

    def action_send_and_print(self):
        self._ddsn_check_printable_invoice()
        return super().action_send_and_print()

    def _generate_and_send(self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings):
        self._ddsn_check_printable_invoice()
        return super()._generate_and_send(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
            **custom_settings,
        )

    # Explicitly track commercial reassignment on preinvoices and invoices.
    invoice_user_id = fields.Many2one(tracking=True)

    ddsn_origin_salesperson_id = fields.Many2one(
        "res.users",
        string="Comercial inicial",
        copy=True,
        readonly=True,
        tracking=True,
        help="Comercial que inició la cotización de origen.",
    )

    ddsn_document_stage = fields.Selection(
        selection=[
            ("preinvoice", "Prefactura"),
            ("invoice", "Factura"),
            ("cancelled", "Cancelada"),
        ],
        string="Document Stage",
        compute="_compute_ddsn_document_stage",
    )
    ddsn_is_preinvoice = fields.Boolean(
        string="Es prefactura",
        default=False,
        copy=False,
        index=True,
    )
    ddsn_preinvoice_state = fields.Selection(
        selection=[("draft", "Borrador"), ("confirmed", "Confirmada")],
        string="Estado de prefactura",
        copy=False,
    )
    ddsn_preinvoice_number = fields.Char(
        string="Numero de prefactura",
        copy=False,
        readonly=True,
        index=True,
    )
    ddsn_source_preinvoice_id = fields.Many2one(
        "account.move",
        string="Prefactura de origen",
        copy=False,
        readonly=True,
    )
    ddsn_created_invoice_id = fields.Many2one(
        "account.move",
        string="Factura creada",
        copy=False,
        readonly=True,
    )
    ddsn_po_first_flow = fields.Boolean(
        string="Flujo PO antes de factura",
        related="sale_order_id.ddsn_po_first_flow",
        readonly=True,
    )
    ddsn_supply_transfer_ids = fields.One2many(
        "stock.picking",
        "ddsn_supply_invoice_id",
        string="Traslados de abastecimiento",
        copy=False,
    )
    ddsn_supply_transfer_count = fields.Integer(
        string="Traslados internos",
        compute="_compute_ddsn_supply_transfer_count",
    )

    release_state = fields.Selection(
        selection=[
            ("not_ready", "Not Ready"),
            ("partially_released", "Partially Released"),
            ("released", "Released"),
            ("delivered", "Delivered"),
        ],
        string="Release State",
        default="not_ready",
        tracking=True,
        copy=False,
    )

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Generated Sale Order",
        copy=False,
        readonly=True,
    )

    fulfillment_line_ids = fields.One2many(
        "doorandoor.fulfillment.line",
        "move_id",
        string="Fulfillment Lines",
        copy=False,
    )

    fulfillment_line_count = fields.Integer(
        string="Fulfillment Line Count",
        compute="_compute_fulfillment_counts",
    )

    payment_release_log_ids = fields.One2many(
        "doorandoor.payment.release.log",
        "move_id",
        string="Payment Release Logs",
        copy=False,
    )

    payment_release_log_count = fields.Integer(
        string="Payment Release Log Count",
        compute="_compute_fulfillment_counts",
    )

    picking_count = fields.Integer(
        string="Picking Count",
        compute="_compute_fulfillment_counts",
    )

    mrp_production_count = fields.Integer(
        string="Production Count",
        compute="_compute_fulfillment_counts",
    )
    pickup_order_ids = fields.One2many(
        "doorandoor.pickup.order",
        "move_id",
        string="Pickup Orders",
        copy=False,
    )
    pickup_order_count = fields.Integer(
        string="Pickup Order Count",
        compute="_compute_fulfillment_counts",
    )
    ddsn_reservation_expires_at = fields.Datetime(
        string="Preinvoice Reservation Expires At",
        copy=False,
        readonly=True,
    )
    ddsn_reservation_active = fields.Boolean(
        string="Preinvoice Reservation Active",
        compute="_compute_ddsn_reservation_status",
    )
    ddsn_reservation_status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("expired", "Expired"),
            ("released", "Released"),
        ],
        string="Preinvoice Reservation Status",
        compute="_compute_ddsn_reservation_status",
    )
    ddsn_shipping_address_summary = fields.Text(
        string="Delivery Address Summary",
        compute="_compute_ddsn_shipping_address_summary",
    )

    def _ddsn_get_salesperson_history(self):
        """Return commercial reassignments from the document chatter."""
        self.ensure_one()
        names = []

        def append_name(name):
            name = (name or "").strip()
            if name and (not names or names[-1] != name):
                names.append(name)

        if self.sale_order_id:
            for salesperson_name in self.sale_order_id._ddsn_get_salesperson_history():
                append_name(salesperson_name)

        tracking_values = self.env["mail.tracking.value"].sudo().search(
            [
                ("mail_message_id", "in", self.message_ids.ids),
                ("field_id.name", "=", "invoice_user_id"),
                ("field_id.model", "=", "account.move"),
            ],
            order="id asc",
        )
        for tracking in tracking_values:
            append_name(tracking.old_value_char)
            append_name(tracking.new_value_char)
        if not names:
            origin = (
                self.ddsn_origin_salesperson_id
                or self.sale_order_id.ddsn_origin_salesperson_id
            )
            if origin and origin != self.env.ref("base.user_root"):
                append_name(origin.name)
        append_name((self.invoice_user_id or self.create_uid).name)
        return names

    payment_release_policy = fields.Selection(
        selection=[
            ("prorated", "Prorated"),
            ("sequential_line", "Sequential by Line"),
            ("priority", "Sequential by Priority"),
            ("manual", "Manual"),
        ],
        string="Payment Release Policy",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.payment_release_policy", "sequential_line"
        ),
        required=True,
        copy=True,
    )

    fulfillment_route_policy = fields.Selection(
        selection=[
            ("by_stock", "By Stock Availability"),
            ("by_product_route", "By Product Route"),
            ("by_product_type", "By Product Type"),
            ("force_mrp", "Force Manufacturing"),
            ("force_stock", "Force Stock"),
            ("manual", "Manual"),
        ],
        string="Fulfillment Route Policy",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.fulfillment_route_policy", "by_stock"
        ),
        required=True,
        copy=True,
    )

    partial_stock_policy = fields.Selection(
        selection=[
            ("split_stock_mrp", "Deliver Stock and Manufacture Rest"),
            ("all_mrp", "Manufacture All"),
            ("wait_full_stock", "Wait Full Stock"),
            ("reserve_partial", "Reserve Partial"),
            ("manual", "Manual"),
        ],
        string="Partial Stock Policy",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.partial_stock_policy", "split_stock_mrp"
        ),
        required=True,
        copy=True,
    )

    picking_creation_policy = fields.Selection(
        selection=[
            ("per_payment", "One Picking per Payment"),
            ("group_by_invoice", "Grouped by Invoice"),
            ("manual_release", "Manual Release"),
        ],
        string="Picking Creation Policy",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.picking_creation_policy", "per_payment"
        ),
        required=True,
        copy=True,
    )

    mrp_creation_policy = fields.Selection(
        selection=[
            ("per_line", "One MO per Released Line"),
            ("group_by_product", "Group by Product"),
            ("manual_release", "Manual Release"),
        ],
        string="Manufacturing Creation Policy",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.mrp_creation_policy", "per_line"
        ),
        required=True,
        copy=True,
    )

    @api.depends("fulfillment_line_ids", "fulfillment_line_ids.picking_id", "fulfillment_line_ids.mrp_production_id")
    def _compute_fulfillment_counts(self):
        for move in self:
            fulfillment_lines = move.fulfillment_line_ids
            move.fulfillment_line_count = len(fulfillment_lines)
            move.picking_count = len(fulfillment_lines.mapped("picking_id"))
            move.mrp_production_count = len(fulfillment_lines.mapped("mrp_production_id"))
            move.payment_release_log_count = len(move.payment_release_log_ids)
            move.pickup_order_count = len(move.pickup_order_ids)

    @api.depends("ddsn_supply_transfer_ids", "ddsn_supply_transfer_ids.state")
    def _compute_ddsn_supply_transfer_count(self):
        for move in self:
            move.ddsn_supply_transfer_count = len(move.ddsn_supply_transfer_ids)

    def action_view_ddsn_supply_transfers(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action["domain"] = [("id", "in", self.ddsn_supply_transfer_ids.ids)]
        action["context"] = {"create": False}
        if len(self.ddsn_supply_transfer_ids) == 1:
            action.update(
                {
                    "res_id": self.ddsn_supply_transfer_ids.id,
                    "views": [(False, "form")],
                    "view_mode": "form",
                }
            )
        return action

    def action_ddsn_change_supply_warehouse(self):
        self.ensure_one()
        if self.move_type != "out_invoice" or self.state != "draft":
            raise ValidationError(
                _("El almacén proveedor solo puede cambiarse antes de confirmar la factura.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Cambiar almacén proveedor"),
            "res_model": "ddsn.supply.warehouse.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "default_move_line_id": self.invoice_line_ids.filtered(
                    lambda line: line.display_type in (False, "product") and line.product_id
                )[:1].id,
            },
        }

    @api.depends("state", "move_type", "ddsn_is_preinvoice")
    def _compute_ddsn_document_stage(self):
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                move.ddsn_document_stage = False
            elif move.ddsn_is_preinvoice:
                move.ddsn_document_stage = "preinvoice"
            elif move.state == "cancel":
                move.ddsn_document_stage = "cancelled"
            elif move.state == "posted":
                move.ddsn_document_stage = "invoice"
            else:
                move.ddsn_document_stage = "preinvoice"

    @api.depends("state", "move_type", "ddsn_reservation_expires_at")
    def _compute_ddsn_reservation_status(self):
        now = fields.Datetime.now()
        for move in self:
            if move.state == "posted" or move.state == "cancel" or move.move_type != "out_invoice":
                move.ddsn_reservation_active = False
                move.ddsn_reservation_status = "released"
            elif move.state == "draft" and move.ddsn_reservation_expires_at and move.ddsn_reservation_expires_at > now:
                move.ddsn_reservation_active = True
                move.ddsn_reservation_status = "active"
            elif move.state == "draft" and move.ddsn_reservation_expires_at:
                move.ddsn_reservation_active = False
                move.ddsn_reservation_status = "expired"
            else:
                move.ddsn_reservation_active = False
                move.ddsn_reservation_status = "released"

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
        for move in self:
            partner = move.partner_shipping_id
            if not partner:
                move.ddsn_shipping_address_summary = False
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
            move.ddsn_shipping_address_summary = "\n".join(part for part in parts if part)

    @api.model_create_multi
    def create(self, vals_list):
        # The fiscal number is a legal, one-way value.  A client-side form may
        # send ``name`` while the document is still a draft, but that value
        # must never become the posted invoice number or its sequence prefix.
        normalized_vals_list = []
        for vals in vals_list:
            values = dict(vals)
            move_type = values.get("move_type") or self.env.context.get("default_move_type")
            if move_type == "out_invoice":
                values["name"] = "/"
                values.pop("sequence_prefix", None)
                values.pop("sequence_number", None)
            normalized_vals_list.append(values)
        return super().create(normalized_vals_list)

    def write(self, vals):
        if (
            "name" in vals
            and not self.env.context.get("ddsn_assigning_invoice_sequence")
            and self.filtered(lambda move: move.move_type == "out_invoice")
        ):
            raise ValidationError(_(
                "El número de una factura es asignado exclusivamente por Odoo al confirmarla y no puede editarse."
            ))
        previous_salespeople = (
            {move.id: move.invoice_user_id for move in self}
            if "invoice_user_id" in vals
            else {}
        )
        protected_commercial_fields = {
            "partner_id",
            "partner_shipping_id",
            "invoice_date",
            "invoice_date_due",
            "date",
            "currency_id",
            "journal_id",
            "invoice_payment_term_id",
            "invoice_user_id",
            "fiscal_position_id",
            "invoice_line_ids",
            "narration",
            "ref",
            "payment_reference",
        }
        if protected_commercial_fields.intersection(vals) and self.filtered(
            lambda move: move.is_invoice(include_receipts=True)
            and (
                move.state in ("posted", "cancel")
                or (move.ddsn_is_preinvoice and move.ddsn_preinvoice_state == "confirmed")
            )
        ):
            raise ValidationError(
                _("No se puede editar una factura confirmada. "
                  "Un administrador de Ajustes debe devolverla a borrador antes de modificarla.")
            )
        if vals.get("state") in ("posted", "cancel"):
            vals.setdefault("ddsn_reservation_expires_at", False)
        result = super().write(vals)
        if previous_salespeople:
            tracked_field = self.env["ir.model.fields"].sudo().search(
                [("model", "=", "account.move"), ("name", "=", "invoice_user_id")],
                limit=1,
            )
            for move in self:
                previous = previous_salespeople[move.id]
                current = move.invoice_user_id
                if previous == current:
                    continue
                message = move.message_post(
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

    def button_draft(self):
        protected_moves = self.filtered(lambda move: move.is_invoice(include_receipts=True))
        if protected_moves and not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Solo un administrador con acceso a Ajustes puede devolver una factura a borrador.")
            )
        result = super().button_draft()
        protected_moves._ddsn_broadcast_document_update("invoice_reopened")
        return result

    def action_ddsn_confirm_preinvoice(self):
        for move in self:
            if not move.ddsn_is_preinvoice or move.state != "draft":
                raise ValidationError(_("Solo una prefactura en borrador puede confirmarse."))
            if move.ddsn_preinvoice_state == "confirmed":
                continue
            number = move.ddsn_preinvoice_number or self.env["ir.sequence"].next_by_code(
                "doorandoor.preinvoice"
            )
            if not number:
                raise ValidationError(_("No se pudo obtener el numero de prefactura."))
            move._ddsn_validate_and_lock_supply_reservations()
            move.write(
                {
                    "ddsn_preinvoice_number": number,
                    "ddsn_preinvoice_state": "confirmed",
                    "ddsn_reservation_expires_at": fields.Datetime.now()
                    + timedelta(hours=move._ddsn_get_reservation_window_hours()),
                }
            )
            if move.sale_order_id:
                move.sale_order_id.write(
                    {"ddsn_flow_stage": "preinvoice"}
                )
        self._ddsn_broadcast_document_update("preinvoice_confirmed")
        return True

    def action_ddsn_reset_preinvoice_draft(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Solo un administrador con acceso a Ajustes puede reabrir una prefactura.")
            )
        reopened = self.filtered(
            lambda move: move.ddsn_is_preinvoice
            and move.ddsn_preinvoice_state == "confirmed"
            and not move.ddsn_created_invoice_id
        )
        reopened.write(
            {
                "ddsn_preinvoice_state": "draft",
                "ddsn_reservation_expires_at": False,
            }
        )
        reopened._ddsn_broadcast_document_update("preinvoice_reopened")
        return True

    def action_ddsn_create_invoice_from_preinvoice(self):
        self.ensure_one()
        if not self.ddsn_is_preinvoice or self.ddsn_preinvoice_state != "confirmed":
            raise ValidationError(_("La prefactura debe estar confirmada antes de crear la factura."))
        if self.ddsn_created_invoice_id:
            return self.ddsn_created_invoice_id._ddsn_open_as_invoice()
        invoice = self.with_context(ddsn_automatic_pricing=True).copy(
            default={
                "name": "/",
                "state": "draft",
                "ddsn_is_preinvoice": False,
                "ddsn_preinvoice_state": False,
                "ddsn_preinvoice_number": False,
                # Transfer the virtual promise to the draft fiscal invoice.
                # The stock move itself is created only after full payment.
                "ddsn_reservation_expires_at": self.ddsn_reservation_expires_at,
                "ddsn_source_preinvoice_id": self.id,
                "ddsn_created_invoice_id": False,
                "sale_order_id": self.sale_order_id.id,
            }
        )
        # account.move.line.generated_sale_line_id is intentionally copy=False.
        # Rebuild the commercial trace explicitly so that the selected source
        # warehouse and any later controlled change remain attached to the
        # same product line through quotation, preinvoice and invoice.
        source_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product") and line.product_id
        )
        target_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product") and line.product_id
        )
        for source_line, target_line in zip(source_lines, target_lines):
            target_line.write(
                {
                    "generated_sale_line_id": source_line.generated_sale_line_id.id,
                    "ddsn_supply_warehouse_id": (
                        source_line.ddsn_supply_warehouse_id
                        or self.sale_order_id.warehouse_id
                    ).id,
                }
            )
        self.ddsn_created_invoice_id = invoice.id
        if self.sale_order_id:
            self.sale_order_id.ddsn_invoice_move_id = invoice.id
        # The invoice now owns the virtual promise. The original prefactura
        # must stop discounting the same quantity from availability.
        self.ddsn_reservation_expires_at = False
        (self | invoice)._ddsn_broadcast_document_update("invoice_created")
        return invoice._ddsn_open_as_invoice()

    def action_ddsn_print_po(self):
        self.ensure_one()
        if not self.ddsn_is_preinvoice or self.ddsn_preinvoice_state != "confirmed":
            raise ValidationError(_("Confirme la prefactura antes de emitir el PO."))
        if not self.sale_order_id:
            raise ValidationError(_("La prefactura no tiene una Orden de Venta vinculada."))
        return self.sale_order_id.action_ddsn_print_po()

    def action_ddsn_open_po_delivery(self):
        self.ensure_one()
        if not self.ddsn_is_preinvoice or not self.ddsn_po_first_flow:
            raise ValidationError(_("Esta acción corresponde únicamente al flujo PO."))
        if not self.sale_order_id:
            raise ValidationError(_("La prefactura no tiene una Orden de Venta vinculada."))
        return self.sale_order_id.action_open_delivery()

    def _ddsn_effective_supply_warehouse(self, line):
        self.ensure_one()
        return line.ddsn_supply_warehouse_id or self.sale_order_id.warehouse_id

    def _ddsn_reserved_supply_qty(self, product, warehouse):
        """Virtual quantity already promised by other confirmed preinvoices."""
        self.ensure_one()
        candidates = self.search(
            [
                ("id", "!=", self.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("company_id", "=", self.company_id.id),
                ("ddsn_is_preinvoice", "=", True),
                ("ddsn_preinvoice_state", "=", "confirmed"),
                ("ddsn_reservation_expires_at", ">", fields.Datetime.now()),
            ]
        )
        reserved = 0.0
        for candidate in candidates:
            for line in candidate.invoice_line_ids.filtered(
                lambda item: item.display_type in (False, "product") and item.product_id
            ):
                controlled_product, required_qty, _transformed = line._ddsn_get_stock_control_product()
                source = candidate._ddsn_effective_supply_warehouse(line)
                if controlled_product == product and source == warehouse:
                    reserved += required_qty
        return reserved

    def _ddsn_committed_supply_qty(self, product, warehouse):
        """Posted but undelivered quantities that still consume this stock."""
        self.ensure_one()
        committed = 0.0
        invoices = self.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", self.company_id.id),
            ]
        )
        for invoice in invoices:
            for line in invoice.invoice_line_ids.filtered(
                lambda item: item.display_type in (False, "product") and item.product_id
            ):
                controlled_product, required_qty, _transformed = line._ddsn_get_stock_control_product()
                source = invoice._ddsn_effective_supply_warehouse(line)
                if controlled_product != product or source != warehouse:
                    continue
                if line.ddsn_supply_transfer_id.state == "done":
                    # Once received, the source stock has physically decreased
                    # and must not be discounted a second time.
                    continue
                if line.fulfillment_line_id:
                    ratio = (
                        line.fulfillment_line_id.qty_pending_delivery
                        / (line.fulfillment_line_id.qty_invoiced or 1.0)
                    )
                    required_qty *= max(min(ratio, 1.0), 0.0)
                committed += required_qty
        return committed

    def _ddsn_validate_and_lock_supply_reservations(self):
        """Atomically validate source availability before confirming a preinvoice."""
        self.ensure_one()
        requested = {}
        locations = self.env["stock.location"]
        products = self.env["product.product"]
        for line in self.invoice_line_ids.filtered(
            lambda item: item.display_type in (False, "product") and item.product_id
        ):
            product, required_qty, _transformed = line._ddsn_get_stock_control_product()
            warehouse = self._ddsn_effective_supply_warehouse(line)
            if not product or not product.is_storable or required_qty <= 0:
                continue
            if not warehouse or warehouse.company_id != self.company_id or not warehouse.lot_stock_id:
                raise ValidationError(
                    _("Debe seleccionar un almacén proveedor válido para %s.") % line.product_id.display_name
                )
            key = (warehouse, product)
            requested[key] = requested.get(key, 0.0) + required_qty
            products |= product
            locations |= self.env["stock.location"].search(
                [("id", "child_of", warehouse.lot_stock_id.id)]
            )

        if products and locations:
            self.env.cr.execute(
                """
                    SELECT id
                      FROM stock_quant
                     WHERE product_id = ANY(%s)
                       AND location_id = ANY(%s)
                     FOR UPDATE
                """,
                [products.ids, locations.ids],
            )

        shortages = []
        for (warehouse, product), required_qty in requested.items():
            physical = product.with_company(self.company_id).with_context(
                location=warehouse.lot_stock_id.id
            ).qty_available
            available = (
                physical
                - self._ddsn_reserved_supply_qty(product, warehouse)
                - self._ddsn_committed_supply_qty(product, warehouse)
            )
            if float_compare(
                required_qty,
                available,
                precision_rounding=product.uom_id.rounding,
            ) > 0:
                shortages.append(
                    _("%(product)s en %(warehouse)s: requerido %(required).2f, disponible %(available).2f")
                    % {
                        "product": product.display_name,
                        "warehouse": warehouse.display_name,
                        "required": required_qty,
                        "available": max(available, 0.0),
                    }
                )
        if shortages:
            self.message_post(
                body=_(
                    "La prefactura continúa con faltantes de inventario. "
                    "Logística deberá abastecer estas cantidades:<br/>%s"
                )
                % "<br/>".join(shortages),
                subtype_xmlid="mail.mt_note",
            )
        return True

    def _ddsn_create_supply_transfers_from_preinvoice(self, preinvoice):
        """Convert paid alternate-warehouse promises into internal pickings."""
        self.ensure_one()
        target = self.sale_order_id.warehouse_id
        if not target or not target.lot_stock_id:
            return self.env["stock.picking"]

        grouped = {}
        for line in self.invoice_line_ids.filtered(
            lambda item: item.display_type in (False, "product") and item.product_id
        ):
            source = self._ddsn_effective_supply_warehouse(line)
            product, required_qty, _transformed = line._ddsn_get_stock_control_product()
            if (
                not source
                or source == target
                or not product
                or not product.is_storable
                or required_qty <= 0
            ):
                continue
            bucket = grouped.setdefault(source, {"lines": [], "products": {}})
            bucket["lines"].append(line)
            bucket["products"][product] = bucket["products"].get(product, 0.0) + required_qty

        Picking = self.env["stock.picking"].sudo()
        created = Picking.browse()
        for source, payload in grouped.items():
            existing = Picking.search(
                [
                    ("ddsn_supply_invoice_id", "=", self.id),
                    ("ddsn_supply_source_warehouse_id", "=", source.id),
                    ("ddsn_supply_destination_warehouse_id", "=", target.id),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )
            if existing:
                for line in payload["lines"]:
                    line.ddsn_supply_transfer_id = existing.id
                created |= existing
                continue
            picking_type = source.int_type_id
            if not picking_type:
                raise ValidationError(
                    _("El almacén %s no tiene un tipo de operación para traslados internos.")
                    % source.display_name
                )
            picking_vals = {
                    "picking_type_id": picking_type.id,
                    "location_id": source.lot_stock_id.id,
                    "location_dest_id": target.lot_stock_id.id,
                    "origin": "%s / PO %s" % (preinvoice.ddsn_preinvoice_number, self.sale_order_id.name),
                    "ddsn_supply_invoice_id": self.id,
                    "ddsn_supply_sale_order_id": self.sale_order_id.id,
                    "ddsn_supply_preinvoice_id": preinvoice.id,
                    "ddsn_supply_source_warehouse_id": source.id,
                    "ddsn_supply_destination_warehouse_id": target.id,
                    "move_ids": [
                        (
                            0,
                            0,
                            {
                                "name": _("Abastecimiento para %s") % (self.name or preinvoice.ddsn_preinvoice_number),
                                "product_id": product.id,
                                "product_uom_qty": qty,
                                "product_uom": product.uom_id.id,
                                "location_id": source.lot_stock_id.id,
                                "location_dest_id": target.lot_stock_id.id,
                            },
                        )
                        for product, qty in payload["products"].items()
                    ],
                }
            picking = Picking.create(picking_vals)
            picking.action_confirm()
            picking.action_assign()
            for line in payload["lines"]:
                line.ddsn_supply_transfer_id = picking.id
            picking.message_post(
                body=_(
                    "Traslado solicitado automáticamente por el PO %(po)s desde la "
                    "prefactura %(preinvoice)s. Usuario solicitante: %(user)s."
                )
                % {
                    "po": self.sale_order_id.name,
                    "preinvoice": preinvoice.ddsn_preinvoice_number,
                    "user": self.env.user.display_name,
                },
                subtype_xmlid="mail.mt_note",
            )
            created |= picking
        return created

    def _ddsn_supply_ready_for_customer_dispatch(self):
        """Create transfers at full payment and wait for physical reception.

        A cross-warehouse dispatch being done only means that the merchandise
        reached transit. The customer delivery must remain blocked until the
        linked destination receipt is also done.
        """
        self.ensure_one()
        alternate_lines = self.invoice_line_ids.filtered(
            lambda line: line.product_id
            and line.display_type in (False, "product")
            and self._ddsn_effective_supply_warehouse(line)
            and self._ddsn_effective_supply_warehouse(line) != self.sale_order_id.warehouse_id
        )
        if not alternate_lines:
            return True
        if not self._ddsn_is_fully_paid():
            return False
        preinvoice = self.ddsn_source_preinvoice_id
        self._ddsn_create_supply_transfers_from_preinvoice(preinvoice)
        transfers = self.ddsn_supply_transfer_ids.filtered(lambda picking: picking.state != "cancel")
        if not transfers:
            return False
        # A receipt validated in this same transaction may still be cached as
        # ``waiting`` through the dispatch relation.  Refresh both sides before
        # deciding whether the customer delivery can be released.
        transfers.invalidate_recordset(["state", "ddpc_transfer_receipt_picking_id"])
        receipts = transfers.mapped("ddpc_transfer_receipt_picking_id")
        receipts.invalidate_recordset(["state"])
        for dispatch in transfers:
            if dispatch.state != "done":
                return False
            if "ddpc_transfer_receipt_picking_id" not in dispatch._fields:
                continue
            receipt = dispatch.ddpc_transfer_receipt_picking_id
            if not receipt or receipt.state != "done":
                return False
        return True

    def _ddsn_cancel_open_supply_transfers(self):
        open_transfers = self.mapped("ddsn_supply_transfer_ids").filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        if open_transfers:
            open_transfers.action_cancel()
        return True

    def button_cancel(self):
        self._ddsn_cancel_open_supply_transfers()
        return super().button_cancel()

    def unlink(self):
        self._ddsn_cancel_open_supply_transfers()
        return super().unlink()

    def _ddsn_broadcast_document_update(self, reason="updated"):
        """Notify clean invoice/preinvoice forms after the transaction commits."""
        for move in self:
            self.env["bus.bus"]._sendone(
                "doorandoor.payment.operations",
                "doorandoor_payment_update",
                {
                    "reason": reason,
                    "sale_order_ids": move.sale_order_id.ids,
                    "invoice_ids": move.ids,
                    "payment_ids": [],
                    "control_ids": [],
                    "partner_ids": move.partner_id.commercial_partner_id.ids,
                    "title": _("Documento actualizado"),
                    "message": _("La prefactura o factura cambió de estado."),
                },
            )

    def _ddsn_open_as_invoice(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action.update({"res_id": self.id, "views": [(False, "form")], "view_mode": "form"})
        return action

    def action_view_generated_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        if self.sale_order_id:
            action["res_id"] = self.sale_order_id.id
            action["views"] = [(False, "form")]
            action["view_mode"] = "form"
        else:
            action["domain"] = [("id", "=", 0)]
        return action

    def action_view_fulfillment_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "doorandoor_sales_new.action_doorandoor_fulfillment_line"
        )
        action["domain"] = [("move_id", "=", self.id)]
        action["context"] = {"default_move_id": self.id}
        return action

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        pickings = self.fulfillment_line_ids.mapped("picking_id")
        if len(pickings) == 1:
            action["res_id"] = pickings.id
            action["views"] = [(False, "form")]
            action["view_mode"] = "form"
        else:
            action["domain"] = [("id", "in", pickings.ids)]
        return action

    def action_view_mrp_productions(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_action")
        productions = self.fulfillment_line_ids.mapped("mrp_production_id")
        if len(productions) == 1:
            action["res_id"] = productions.id
            action["views"] = [(False, "form")]
            action["view_mode"] = "form"
        else:
            action["domain"] = [("id", "in", productions.ids)]
        return action

    def action_view_pickup_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "doorandoor_sales_new.action_doorandoor_pickup_order"
        )
        pickup_orders = self.pickup_order_ids
        if len(pickup_orders) == 1:
            action["res_id"] = pickup_orders.id
            action["views"] = [(False, "form")]
            action["view_mode"] = "form"
        else:
            action["domain"] = [("id", "in", pickup_orders.ids)]
        action["context"] = {"default_move_id": self.id}
        return action

    def action_create_pickup_orders(self):
        self._ddsn_ensure_pickup_orders()
        return self.action_view_pickup_orders()

    def action_sync_fulfillment(self):
        self._ddsn_create_sale_orders_and_fulfillment()
        self._ddsn_sync_release_from_payments()
        return True

    def action_ddsn_renew_preinvoice_reservation(self):
        for move in self:
            if (
                move.move_type != "out_invoice"
                or move.state != "draft"
                or not move.ddsn_is_preinvoice
                or move.ddsn_preinvoice_state != "confirmed"
            ):
                continue
            if move.sale_order_id and move.partner_id.commercial_partner_id != move.sale_order_id.partner_id.commercial_partner_id:
                continue
            move.ddsn_reservation_expires_at = fields.Datetime.now() + timedelta(
                hours=move._ddsn_get_reservation_window_hours()
            )
        return True

    def action_post(self):
        if self.filtered("ddsn_is_preinvoice"):
            raise ValidationError(
                _("Una prefactura no se contabiliza. Confirme la prefactura y use Crear factura.")
            )
        fiscal_invoices = self.filtered(
            lambda move: move.move_type == "out_invoice" and move.sale_order_id
        )
        # A linked fiscal invoice must never enter payment/fulfillment while
        # its commercial order remains technically in draft.  Confirmation
        # deliberately keeps procurement disabled: delivery is still created
        # only by the fully-paid invoice flow.
        fiscal_invoices.mapped("sale_order_id")._ddsn_confirm_for_fiscal_invoice()
        # ``create`` and ``write`` already prevent users from injecting an
        # invoice number in a new draft.  Do not reset ``name`` here: Odoo
        # intentionally keeps the fiscal number when a posted invoice is
        # reopened, and that same number must be reused on reposting.  Resetting
        # every draft to '/' consumed another journal sequence and changed the
        # identity of corrected, already-paid invoices.
        # Flujo nativo: liberar reserva y confirmar factura de forma estándar
        self.filtered("ddsn_reservation_expires_at").write({"ddsn_reservation_expires_at": False})
        result = super(AccountMove, self.with_context(ddsn_assigning_invoice_sequence=True)).action_post()
        
        # Procesar cumplimiento solo para facturas con orden de venta
        self._ddsn_create_sale_orders_and_fulfillment()
        
        # Actualizar trazabilidad en la orden de venta si existe
        for move in self.filtered("sale_order_id"):
            move.sale_order_id.write(
                {
                    "ddsn_invoice_move_id": move.id,
                    "ddsn_flow_stage": "invoiced",
                }
            )
        self._ddsn_broadcast_document_update("invoice_posted")
        return result

    def _ddsn_get_reservation_window_hours(self):
        param_value = self.env["ir.config_parameter"].sudo().get_param(
            "doorandoor_sales_new.preinvoice_reservation_hours",
            "24",
        )
        try:
            return max(int(param_value), 1)
        except (TypeError, ValueError):
            return 24

    def _ddsn_get_preinvoice_cleanup_window_hours(self):
        # Lost preinvoices should not remain forever in the draft invoice list.
        return max(self._ddsn_get_reservation_window_hours() * 2, 48)

    def _ddsn_has_active_reservation(self):
        self.ensure_one()
        return bool(
            self.move_type == "out_invoice"
            and self.state == "draft"
            and self.ddsn_reservation_expires_at
            and self.ddsn_reservation_expires_at > fields.Datetime.now()
        )

    def _ddsn_get_committed_qty_for_product(self, product, warehouse=False):
        self.ensure_one()
        if not product or self.move_type != "out_invoice" or self.state != "posted":
            return 0.0

        committed_qty = 0.0
        for invoice_line in self.invoice_line_ids.filtered(
            lambda line: line.product_id == product and line.display_type in (False, "product")
        ):
            pending_qty = invoice_line.quantity
            if invoice_line.fulfillment_line_id:
                pending_qty = max(
                    invoice_line.fulfillment_line_id.qty_invoiced - invoice_line.fulfillment_line_id.qty_delivered,
                    0.0,
                )
            if pending_qty <= 0:
                continue

            # This is an aggregate stock calculation over every posted
            # invoice.  A salesperson restricted to their own quotations must
            # not fail merely because another seller owns the generated sale
            # order of one of those invoices.  Read only the warehouse needed
            # by the calculation with technical privileges; the originating
            # order itself remains protected by its normal record rules.
            reservation_warehouse = self.sudo().sale_order_id.warehouse_id
            if warehouse and reservation_warehouse and reservation_warehouse != warehouse:
                continue
            committed_qty += pending_qty
        return committed_qty

    @api.model
    def _ddsn_release_expired_preinvoice_reservations(self):
        now = fields.Datetime.now()
        expired_moves = self.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("ddsn_is_preinvoice", "=", True),
                ("ddsn_preinvoice_state", "=", "confirmed"),
                ("ddsn_reservation_expires_at", "!=", False),
                ("ddsn_reservation_expires_at", "<=", now),
            ]
        )
        expired_moves.write({"ddsn_reservation_expires_at": False})
        # El primer cron posterior a medianoche elimina los borradores del dia
        # anterior. Las prefacturas confirmadas nunca se eliminan: solo vence
        # su reserva a las 24 horas.
        cleanup_cutoff = datetime.combine(fields.Date.context_today(self), time.min)
        obsolete_preinvoices = self.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
                ("ddsn_is_preinvoice", "=", True),
                ("ddsn_preinvoice_state", "=", "draft"),
                ("create_date", "!=", False),
                ("create_date", "<=", cleanup_cutoff),
            ]
        )
        for move in obsolete_preinvoices.filtered("sale_order_id"):
            move.sale_order_id.write(
                {
                    "ddsn_flow_stage": "quotation",
                    "ddsn_preinvoice_move_id": False,
                }
            )
        obsolete_count = len(obsolete_preinvoices)
        if obsolete_preinvoices:
            obsolete_preinvoices.unlink()
        return len(expired_moves) + obsolete_count

    def _ddsn_create_sale_orders_and_fulfillment(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.state != "posted":
                continue
            product_lines = move._ddsn_get_invoice_product_lines()
            if not product_lines:
                continue
            
            # Si ya existe una orden de venta (del flujo nativo cotización->orden->factura)
            if move.sale_order_id:
                move._ddsn_link_invoice_lines_to_sale_order_lines(product_lines)
                move._ddsn_sync_existing_fulfillment_lines(product_lines)
                continue

            # Si no existe orden de venta, crear una (caso de factura directa)
            sale_order = move._ddsn_create_sale_order_from_invoice(product_lines)
            move.sale_order_id = sale_order.id
            move._ddsn_create_fulfillment_lines(sale_order, product_lines)

    def _ddsn_get_invoice_product_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product") and line.product_id and line.quantity
        )

    def _ddsn_prepare_sale_order_vals(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id or self.partner_id
        return {
            "partner_id": partner.id,
            "partner_invoice_id": self.partner_id.id,
            "partner_shipping_id": self.partner_shipping_id.id or self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "origin": self.name or self.ref or self.payment_reference,
            "client_order_ref": self.ref or self.payment_reference or self.name,
            "note": self.narration,
            "date_order": fields.Datetime.now(),
        }

    def _ddsn_create_sale_order_from_invoice(self, product_lines):
        self.ensure_one()
        sale_order = self.env["sale.order"].with_context(ddsn_assign_number_immediately=True).create(
            self._ddsn_prepare_sale_order_vals()
        )
        sale_lines = self.env["sale.order.line"]

        for invoice_line in product_lines:
            sale_line = self.env["sale.order.line"].create(
                self._ddsn_prepare_sale_line_vals(sale_order, invoice_line)
            )
            invoice_line.generated_sale_line_id = sale_line.id
            sale_lines |= sale_line

        sale_order.order_line = [(6, 0, sale_lines.ids)]
        return sale_order

    def _ddsn_prepare_sale_line_vals(self, sale_order, invoice_line):
        self.ensure_one()
        product = invoice_line.product_id
        return {
            "order_id": sale_order.id,
            "product_id": product.id,
            "name": invoice_line.name or product.display_name,
            "product_uom_qty": invoice_line.quantity,
            "product_uom": invoice_line.product_uom_id.id or product.uom_id.id,
            "price_unit": invoice_line.price_unit,
            "discount": invoice_line.discount,
            "tax_id": [(6, 0, invoice_line.tax_ids.ids)],
            "ddsn_supply_warehouse_id": (
                invoice_line.ddsn_supply_warehouse_id or sale_order.warehouse_id
            ).id,
        }

    def _ddsn_get_pickup_candidate_lines(self):
        self.ensure_one()
        return self.fulfillment_line_ids.filtered(
            lambda line: line.product_id
            and line.picking_id
            and line.picking_id.state != "cancel"
            and line._ddsn_get_qty_ready_for_pickup() > 0.0
        )

    def _ddsn_prepare_pickup_order_vals(self, picking, warehouse):
        self.ensure_one()
        state = "ready" if picking.state in ("assigned", "done") else "pending"
        return {
            "move_id": self.id,
            "picking_id": picking.id,
            "warehouse_id": warehouse.id if warehouse else False,
            "state": state,
        }

    def _ddsn_prepare_pickup_order_line_vals(self, order, fulfillment_line):
        self.ensure_one()
        qty = fulfillment_line._ddsn_get_qty_ready_for_pickup()
        unit_amount = 0.0
        if fulfillment_line.qty_invoiced:
            unit_amount = fulfillment_line.amount_total / fulfillment_line.qty_invoiced
        return {
            "pickup_order_id": order.id,
            "fulfillment_line_id": fulfillment_line.id,
            "product_uom_qty": qty,
            "qty_delivered": 0.0,
            "amount_total": unit_amount * qty,
        }

    def _ddsn_ensure_pickup_orders(self):
        pickup_order_model = self.env["doorandoor.pickup.order"]
        pickup_line_model = self.env["doorandoor.pickup.order.line"]
        for move in self:
            candidates = move._ddsn_get_pickup_candidate_lines()
            grouped_lines = {}
            for line in candidates:
                picking = line.picking_id
                warehouse = picking.picking_type_id.warehouse_id
                key = (picking.id, warehouse.id if warehouse else False)
                grouped_lines.setdefault(key, self.env["doorandoor.fulfillment.line"])
                grouped_lines[key] |= line

            for (picking_id, warehouse_id), lines in grouped_lines.items():
                existing_order = move.pickup_order_ids.filtered(
                    lambda order: order.picking_id.id == picking_id and order.state not in ("delivered", "cancelled")
                )[:1]
                if existing_order:
                    existing_fulfillment_ids = existing_order.pickup_line_ids.mapped("fulfillment_line_id").ids
                    missing_lines = lines.filtered(lambda line: line.id not in existing_fulfillment_ids)
                    for fulfillment_line in missing_lines:
                        pickup_line_model.create(
                            move._ddsn_prepare_pickup_order_line_vals(existing_order, fulfillment_line)
                        )
                    existing_order._ddsn_sync_state_from_operation()
                    continue

                picking = self.env["stock.picking"].browse(picking_id)
                warehouse = self.env["stock.warehouse"].browse(warehouse_id) if warehouse_id else False
                order = pickup_order_model.create(move._ddsn_prepare_pickup_order_vals(picking, warehouse))
                for fulfillment_line in lines:
                    pickup_line_model.create(move._ddsn_prepare_pickup_order_line_vals(order, fulfillment_line))
                order._ddsn_sync_state_from_operation()
        return True

    def _ddsn_create_fulfillment_lines(self, sale_order, product_lines):
        self.ensure_one()
        for invoice_line in product_lines:
            sale_line = invoice_line.generated_sale_line_id
            fulfillment_line = self.env["doorandoor.fulfillment.line"].create(
                {
                    "move_id": self.id,
                    "move_line_id": invoice_line.id,
                    "sale_order_id": sale_order.id,
                    "sale_line_id": sale_line.id if sale_line else False,
                    "qty_invoiced": invoice_line.quantity,
                    "qty_pending_payment": invoice_line.quantity,
                    "qty_pending_delivery": invoice_line.quantity,
                    "amount_total": invoice_line.price_total,
                }
            )
            invoice_line.fulfillment_line_id = fulfillment_line.id
        self._ddsn_sync_release_from_payments()

    def _ddsn_sync_existing_fulfillment_lines(self, product_lines):
        self.ensure_one()
        existing_lines = self.fulfillment_line_ids.mapped("move_line_id")
        missing_lines = product_lines - existing_lines
        if not missing_lines:
            return

        for invoice_line in missing_lines:
            sale_line = invoice_line.generated_sale_line_id
            fulfillment_line = self.env["doorandoor.fulfillment.line"].create(
                {
                    "move_id": self.id,
                    "move_line_id": invoice_line.id,
                    "sale_order_id": self.sale_order_id.id,
                    "sale_line_id": sale_line.id if sale_line else False,
                    "qty_invoiced": invoice_line.quantity,
                    "qty_pending_payment": invoice_line.quantity,
                    "qty_pending_delivery": invoice_line.quantity,
                    "amount_total": invoice_line.price_total,
                }
            )
            invoice_line.fulfillment_line_id = fulfillment_line.id
        self._ddsn_sync_release_from_payments()

    def _ddsn_link_invoice_lines_to_sale_order_lines(self, product_lines):
        self.ensure_one()
        sale_order = self.sale_order_id
        if not sale_order:
            return

        used_sale_lines = self.invoice_line_ids.mapped("generated_sale_line_id")
        for invoice_line in product_lines.filtered(lambda line: not line.generated_sale_line_id):
            candidate_line = sale_order.order_line.filtered(
                lambda sale_line: sale_line.product_id == invoice_line.product_id and sale_line not in used_sale_lines
            )[:1]
            if not candidate_line:
                candidate_line = sale_order.order_line.filtered(
                    lambda sale_line: sale_line.product_id == invoice_line.product_id
                )[:1]
            if candidate_line:
                invoice_line.generated_sale_line_id = candidate_line.id
                used_sale_lines |= candidate_line

    def _ddsn_sync_release_from_payments(self):
        for move in self:
            if move.move_type != "out_invoice" or move.state != "posted" or not move.fulfillment_line_ids:
                continue

            # The internal sale order can be generated after ``action_post``
            # has already started.  Confirm it here as the last defensive
            # boundary before any paid quantity creates stock/MRP documents.
            # Procurement remains disabled; deliveries are still released
            # exclusively by the invoice payment rules below.
            move._ddsn_confirm_linked_sales_for_fulfillment()

            if move.payment_release_policy == "manual":
                move._ddsn_set_release_state()
                continue

            total_amount = abs(move.amount_total)
            paid_amount = max(total_amount - abs(move.amount_residual), 0.0)
            # Operational payment control can validate and release the sale
            # before the bank/cash entry is finally reconciled in Accounting.
            # Keep that audited release amount when a later warehouse event
            # (such as the destination receipt) resumes fulfillment.
            latest_release = move.payment_release_log_ids.sorted(
                key=lambda log: log.write_date or log.create_date
            )[-1:]
            if latest_release:
                paid_amount = max(
                    paid_amount,
                    min(abs(latest_release.amount_applied), total_amount),
                )
            currency = move.currency_id

            if not total_amount or currency.is_zero(total_amount):
                move._ddsn_set_release_state()
                continue

            if move.payment_release_policy == "prorated":
                move._ddsn_apply_prorated_release(paid_amount, total_amount)
            else:
                move._ddsn_apply_sequential_release(paid_amount)

            move._ddsn_create_or_update_release_log(paid_amount)
            if move._ddsn_supply_ready_for_customer_dispatch():
                move._ddsn_sync_stock_fulfillment_documents()
                move._ddsn_sync_mrp_fulfillment_documents()
                move._ddsn_ensure_pickup_orders()
            move._ddsn_set_release_state()

    def _ddsn_apply_release_for_amount(self, paid_amount):
        for move in self:
            total_amount = abs(move.amount_total)
            if move.payment_release_policy == "manual" or not move.fulfillment_line_ids:
                move._ddsn_set_release_state()
                continue

            move._ddsn_confirm_linked_sales_for_fulfillment()

            if move.payment_release_policy == "prorated":
                move._ddsn_apply_prorated_release(paid_amount, total_amount)
            else:
                move._ddsn_apply_sequential_release(paid_amount)

            move._ddsn_create_or_update_release_log(paid_amount)
            if move._ddsn_supply_ready_for_customer_dispatch():
                move._ddsn_sync_stock_fulfillment_documents()
                move._ddsn_sync_mrp_fulfillment_documents()
                move._ddsn_ensure_pickup_orders()
            move._ddsn_set_release_state()

    def _ddsn_confirm_linked_sales_for_fulfillment(self):
        """Ensure every sale used by fulfillment is technically confirmed."""
        fiscal_moves = self.filtered(
            lambda move: move.move_type == "out_invoice" and move.state == "posted"
        )
        sale_orders = fiscal_moves.mapped("sale_order_id")
        sale_orders |= fiscal_moves.mapped("fulfillment_line_ids.sale_order_id")
        sale_orders._ddsn_confirm_for_fiscal_invoice()
        return True

    def _ddsn_apply_prorated_release(self, paid_amount, total_amount):
        self.ensure_one()
        ratio = min(max(paid_amount / total_amount, 0.0), 1.0)
        for line in self.fulfillment_line_ids:
            qty_released = min(line.qty_invoiced * ratio, line.qty_invoiced)
            amount_released = min(line.amount_total * ratio, line.amount_total)
            route = self._ddsn_get_line_route(line, qty_released)
            line.write(
                {
                    "qty_released": qty_released,
                    "qty_pending_payment": max(line.qty_invoiced - qty_released, 0.0),
                    "qty_pending_delivery": max(line.qty_invoiced - line.qty_delivered, 0.0),
                    "amount_released": amount_released,
                    "state": "pending_payment" if qty_released <= 0 else route,
                }
            )

    def _ddsn_apply_sequential_release(self, paid_amount):
        self.ensure_one()
        remaining_amount = paid_amount

        ordered_lines = self.fulfillment_line_ids.sorted(
            key=lambda line: (
                getattr(line.product_id, "default_code", "") or "",
                line.id,
            )
        )
        if self.payment_release_policy == "sequential_line":
            ordered_lines = self.fulfillment_line_ids.sorted(key=lambda line: line.id)

        for line in ordered_lines:
            line_amount = abs(line.amount_total)
            qty_released = 0.0
            amount_released = 0.0

            if remaining_amount > 0 and line_amount > 0:
                amount_released = min(remaining_amount, line_amount)
                ratio = amount_released / line_amount
                qty_released = min(line.qty_invoiced * ratio, line.qty_invoiced)
                remaining_amount -= amount_released

            route = self._ddsn_get_line_route(line, qty_released)

            line.write(
                {
                    "qty_released": qty_released,
                    "qty_pending_payment": max(line.qty_invoiced - qty_released, 0.0),
                    "qty_pending_delivery": max(line.qty_invoiced - line.qty_delivered, 0.0),
                    "amount_released": amount_released,
                    "state": "pending_payment" if qty_released <= 0 else route,
                }
            )

    def _ddsn_get_line_route(self, line, qty_released):
        self.ensure_one()
        if qty_released <= 0:
            return "pending_payment"

        policy = self.fulfillment_route_policy
        product = line.product_id

        if policy == "force_mrp":
            return "ready_mrp"
        if policy == "force_stock":
            return "ready_stock"
        if policy == "by_product_type":
            return "ready_mrp" if product.type == "product" else "ready_stock"
        if policy == "by_product_route":
            route_names = {
                (route.name or "").strip().lower()
                for route in (product.route_ids | product.categ_id.total_route_ids)
            }
            if any("manufact" in route_name for route_name in route_names):
                return "ready_mrp"
            return "ready_stock"

        return "ready_stock"

    def _ddsn_sync_stock_fulfillment_documents(self):
        for move in self:
            if not move._ddsn_is_fully_paid():
                continue

            stock_lines = move.fulfillment_line_ids.filtered(
                lambda line: line.state == "ready_stock" and line.qty_released > line.qty_sent_stock
            )
            if not stock_lines:
                continue

            picking = move._ddsn_get_or_create_out_picking()
            for line in stock_lines:
                qty_to_send = max(line.qty_released - line.qty_sent_stock, 0.0)
                if qty_to_send <= 0:
                    continue

                move._ddsn_create_stock_move_from_fulfillment_line(picking, line, qty_to_send)
                line.write(
                    {
                        "picking_id": picking.id,
                        "qty_sent_stock": line.qty_sent_stock + qty_to_send,
                        "state": "in_process",
                    }
                )

            if picking.state == "draft":
                picking.action_confirm()
            if picking.state in ("confirmed", "waiting", "assigned"):
                picking.action_assign()

    def _ddsn_sync_mrp_fulfillment_documents(self):
        for move in self:
            mrp_lines = move.fulfillment_line_ids.filtered(
                lambda line: line.state == "ready_mrp" and line.qty_released > line.qty_sent_mrp
            )
            for line in mrp_lines:
                qty_to_manufacture = max(line.qty_released - line.qty_sent_mrp, 0.0)
                if qty_to_manufacture <= 0:
                    continue

                production = move._ddsn_get_or_create_mrp_production(line, qty_to_manufacture)
                if not production:
                    continue

                line.write(
                    {
                        "mrp_production_id": production.id,
                        "qty_sent_mrp": line.qty_sent_mrp + qty_to_manufacture,
                        "state": "in_process",
                    }
                )

    def _ddsn_sync_finished_mrp_to_outgoing_picking(self, fulfillment_line):
        self.ensure_one()
        if not self._ddsn_is_fully_paid():
            return False

        qty_to_send = max(fulfillment_line.qty_sent_mrp - fulfillment_line.qty_sent_stock, 0.0)
        if qty_to_send <= 0:
            return False

        picking = self._ddsn_get_or_create_out_picking()
        self._ddsn_create_stock_move_from_fulfillment_line(picking, fulfillment_line, qty_to_send)
        fulfillment_line.write(
            {
                "picking_id": picking.id,
                "qty_sent_stock": fulfillment_line.qty_sent_stock + qty_to_send,
                "state": "in_process",
            }
        )
        if picking.state == "draft":
            picking.action_confirm()
        if picking.state in ("confirmed", "waiting", "assigned"):
            picking.action_assign()
        self._ddsn_ensure_pickup_orders()
        return picking

    def _ddsn_get_or_create_out_picking(self):
        self.ensure_one()
        open_pickings = self.fulfillment_line_ids.mapped("picking_id").filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        if open_pickings and self.picking_creation_policy != "per_payment":
            return open_pickings[0]

        if open_pickings and self.picking_creation_policy == "per_payment":
            latest_log = self.payment_release_log_ids.sorted(key=lambda log: log.write_date or log.create_date)[-1:]
            if latest_log:
                same_log_picking = open_pickings.filtered(
                    lambda picking: (picking.origin or "").startswith(f"{self.name} | Release {latest_log.id}")
                )
                if same_log_picking:
                    return same_log_picking[0]

        existing_sale_picking = self._ddsn_find_reusable_sale_picking()
        if existing_sale_picking:
            return existing_sale_picking

        picking_type = self._ddsn_get_outgoing_picking_type()
        location_dest = self.partner_shipping_id.property_stock_customer
        if not location_dest:
            location_dest = self.env.ref("stock.stock_location_customers", raise_if_not_found=False)
        return self.env["stock.picking"].with_context(default_move_type=False).create(
            {
                "partner_id": self.partner_shipping_id.id or self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": location_dest.id if location_dest else False,
                "origin": self._ddsn_get_picking_origin_label(),
                "company_id": self.company_id.id,
                "move_type": "direct",
            }
        )

    def _ddsn_find_reusable_sale_picking(self):
        self.ensure_one()
        sale_order = self.sale_order_id
        if not sale_order:
            return False

        picking_domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "not in", ("done", "cancel")),
            ("company_id", "=", self.company_id.id),
        ]

        if "sale_id" in self.env["stock.picking"]._fields:
            picking_domain.append(("sale_id", "=", sale_order.id))
        else:
            picking_domain.append(("origin", "=", sale_order.name))

        candidate_pickings = self.env["stock.picking"].search(picking_domain, order="create_date desc, id desc")
        if not candidate_pickings:
            return False

        sale_line_ids = set(sale_order.order_line.ids)
        if not sale_line_ids:
            return candidate_pickings[0]

        for picking in candidate_pickings:
            move_sale_line_ids = set(picking.move_ids.sale_line_id.ids)
            if not move_sale_line_ids or move_sale_line_ids.intersection(sale_line_ids):
                return picking

        return candidate_pickings[0]

    def _ddsn_get_picking_origin_label(self):
        self.ensure_one()
        latest_log = self.payment_release_log_ids.sorted(key=lambda log: log.write_date or log.create_date)[-1:]
        if self.picking_creation_policy == "per_payment" and latest_log:
            return f"{self.name} | Release {latest_log.id}"
        return self.name or self.ref or self.payment_reference

    def _ddsn_is_fully_paid(self):
        self.ensure_one()
        total_amount = abs(self.amount_total)
        residual_amount = abs(self.amount_residual)
        currency = self.currency_id
        if not total_amount or currency.is_zero(total_amount):
            return True
        if currency.is_zero(residual_amount):
            return True

        latest_log = self.payment_release_log_ids.sorted(key=lambda log: log.write_date or log.create_date)[-1:]
        if latest_log and latest_log.amount_applied >= total_amount:
            return True

        return False

    def _ddsn_get_outgoing_picking_type(self):
        self.ensure_one()
        warehouse = self.sale_order_id.warehouse_id or self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)],
            limit=1,
        )
        return warehouse.out_type_id

    def _ddsn_create_stock_move_from_fulfillment_line(self, picking, line, qty_to_send):
        self.ensure_one()
        sale_line = line.sale_line_id
        existing_move = self.env["stock.move"]
        if sale_line:
            existing_move = self.env["stock.move"].search(
                [
                    ("picking_id", "=", picking.id),
                    ("sale_line_id", "=", sale_line.id),
                    ("product_id", "=", line.product_id.id),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )
        if existing_move:
            existing_move.write({"product_uom_qty": existing_move.product_uom_qty + qty_to_send})
            return existing_move

        self.env["stock.move"].create(
            {
                "name": line.product_id.display_name,
                "picking_id": picking.id,
                "company_id": self.company_id.id,
                "product_id": line.product_id.id,
                "product_uom_qty": qty_to_send,
                "product_uom": line.move_line_id.product_uom_id.id or line.product_id.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "sale_line_id": line.sale_line_id.id,
                "origin": picking.origin,
            }
        )

    def _ddsn_get_or_create_mrp_production(self, line, qty_to_manufacture):
        self.ensure_one()
        if self.mrp_creation_policy == "manual_release":
            return False

        bom = self._ddsn_get_bom_for_product(line.product_id)
        if not bom:
            return False

        if self.mrp_creation_policy == "group_by_product":
            existing_production = self.fulfillment_line_ids.mapped("mrp_production_id").filtered(
                lambda production: production.state not in ("done", "cancel") and production.product_id == line.product_id
            )[:1]
            if existing_production:
                existing_production.write(
                    {
                        "product_qty": existing_production.product_qty + qty_to_manufacture,
                        "origin": self._ddsn_get_mrp_origin_label(line),
                    }
                )
                if existing_production.state == "draft":
                    existing_production.action_confirm()
                return existing_production

        production = self.env["mrp.production"].create(
            self._ddsn_prepare_mrp_production_vals(line, qty_to_manufacture, bom)
        )
        if production.state == "draft":
            production.action_confirm()
        return production

    def _ddsn_get_bom_for_product(self, product):
        self.ensure_one()
        bom = self.env["mrp.bom"].search(
            [
                "|",
                ("product_id", "=", product.id),
                "&",
                ("product_id", "=", False),
                ("product_tmpl_id", "=", product.product_tmpl_id.id),
            ],
            order="product_id desc, sequence, id",
            limit=1,
        )
        return bom

    def _ddsn_prepare_mrp_production_vals(self, line, qty_to_manufacture, bom):
        self.ensure_one()
        locations = self._ddsn_get_mrp_locations(bom)
        return {
            "product_id": line.product_id.id,
            "product_tmpl_id": line.product_id.product_tmpl_id.id,
            "product_qty": qty_to_manufacture,
            "product_uom_id": line.move_line_id.product_uom_id.id or line.product_id.uom_id.id,
            "bom_id": bom.id,
            "origin": self._ddsn_get_mrp_origin_label(line),
            "company_id": self.company_id.id,
            "date_start": fields.Datetime.now(),
            "location_src_id": locations["location_src_id"],
            "location_dest_id": locations["location_dest_id"],
        }

    def _ddsn_get_mrp_origin_label(self, line):
        self.ensure_one()
        return f"{self.name} | {line.product_id.display_name}"

    def _ddsn_get_mrp_locations(self, bom):
        self.ensure_one()
        warehouse = self.sale_order_id.warehouse_id or self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)],
            limit=1,
        )
        location_src = bom.picking_type_id.default_location_src_id.id
        location_dest = bom.picking_type_id.default_location_dest_id.id
        if not location_src and warehouse:
            location_src = warehouse.lot_stock_id.id
        if not location_dest and warehouse:
            location_dest = warehouse.lot_stock_id.id
        return {
            "location_src_id": location_src,
            "location_dest_id": location_dest,
        }

    def _ddsn_create_or_update_release_log(self, paid_amount):
        self.ensure_one()
        if self.payment_release_policy == "manual":
            return

        release_log_model = self.env["doorandoor.payment.release.log"].sudo()
        release_log = self.payment_release_log_ids[:1].sudo()
        values = {
            "move_id": self.id,
            "sale_order_id": self.sale_order_id.id,
            "amount_applied": paid_amount,
            "policy_used": self.payment_release_policy,
            "notes": "Actualizacion automatica de liberacion por conciliacion contable.",
        }
        if release_log:
            release_log.write(values)
        else:
            release_log_model.create(values)

    def _ddsn_set_release_state(self):
        for move in self:
            if not move.fulfillment_line_ids:
                move.release_state = "not_ready"
                continue

            released_lines = move.fulfillment_line_ids.filtered(lambda line: line.qty_released > 0)
            pending_payment_lines = move.fulfillment_line_ids.filtered(lambda line: line.qty_pending_payment > 0)
            pending_delivery_lines = move.fulfillment_line_ids.filtered(
                lambda line: line.qty_released > 0 and line.qty_pending_delivery > 0
            )

            if not released_lines:
                move.release_state = "not_ready"
            elif pending_payment_lines:
                move.release_state = "partially_released"
            elif pending_delivery_lines:
                move.release_state = "released"
            else:
                move.release_state = "delivered"
