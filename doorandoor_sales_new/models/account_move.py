from datetime import timedelta

from odoo import api, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "doorandoor.document.barcode.mixin"]

    ddsn_document_stage = fields.Selection(
        selection=[
            ("preinvoice", "Prefactura"),
            ("invoice", "Factura"),
            ("cancelled", "Cancelada"),
        ],
        string="Document Stage",
        compute="_compute_ddsn_document_stage",
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

    @api.depends("state", "move_type")
    def _compute_ddsn_document_stage(self):
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                move.ddsn_document_stage = False
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

    @api.model_create_multi
    def create(self, vals_list):
        expiration_hours = self._ddsn_get_reservation_window_hours()
        now = fields.Datetime.now()
        for vals in vals_list:
            if vals.get("move_type") == "out_invoice" and not vals.get("ddsn_reservation_expires_at"):
                vals["ddsn_reservation_expires_at"] = now + timedelta(hours=expiration_hours)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("state") in ("posted", "cancel"):
            vals.setdefault("ddsn_reservation_expires_at", False)
        return super().write(vals)

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
            if move.move_type != "out_invoice" or move.state != "draft":
                continue
            if move.sale_order_id and move.partner_id.commercial_partner_id != move.sale_order_id.partner_id.commercial_partner_id:
                continue
            move.ddsn_reservation_expires_at = fields.Datetime.now() + timedelta(
                hours=move._ddsn_get_reservation_window_hours()
            )
        return True

    def action_post(self):
        self.filtered("ddsn_reservation_expires_at").write({"ddsn_reservation_expires_at": False})
        moves = self
        result = super().action_post()
        sale_orders_to_confirm = moves.mapped("sale_order_id").filtered(lambda order: order.state in ("draft", "sent"))
        if sale_orders_to_confirm:
            sale_orders_to_confirm.with_context(ddsn_finalize_from_preinvoice=True).action_confirm()
            sale_orders_to_confirm.write({"ddsn_flow_stage": "invoiced"})
        self._ddsn_create_sale_orders_and_fulfillment()
        for move in moves.filtered("sale_order_id"):
            move.sale_order_id.write(
                {
                    "ddsn_preinvoice_move_id": False,
                    "ddsn_invoice_move_id": move.id,
                    "ddsn_flow_stage": "invoiced",
                }
            )
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

    def _ddsn_has_active_reservation(self):
        self.ensure_one()
        self._compute_ddsn_reservation_status()
        return self.ddsn_reservation_active

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

            reservation_warehouse = self.sale_order_id.warehouse_id
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
                ("ddsn_reservation_expires_at", "!=", False),
                ("ddsn_reservation_expires_at", "<=", now),
            ]
        )
        expired_moves.write({"ddsn_reservation_expires_at": False})
        for move in expired_moves.filtered("sale_order_id"):
            move.sale_order_id.write(
                {
                    "ddsn_flow_stage": "quotation",
                    "ddsn_preinvoice_move_id": False,
                }
            )
        return len(expired_moves)

    def _ddsn_create_sale_orders_and_fulfillment(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.state != "posted":
                continue
            product_lines = move._ddsn_get_invoice_product_lines()
            if not product_lines:
                continue
            if move.sale_order_id:
                move._ddsn_link_invoice_lines_to_sale_order_lines(product_lines)
                move._ddsn_sync_existing_fulfillment_lines(product_lines)
                continue

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

            if move.payment_release_policy == "manual":
                move._ddsn_set_release_state()
                continue

            total_amount = abs(move.amount_total)
            paid_amount = max(total_amount - abs(move.amount_residual), 0.0)
            currency = move.currency_id

            if not total_amount or currency.is_zero(total_amount):
                move._ddsn_set_release_state()
                continue

            if move.payment_release_policy == "prorated":
                move._ddsn_apply_prorated_release(paid_amount, total_amount)
            else:
                move._ddsn_apply_sequential_release(paid_amount)

            move._ddsn_create_or_update_release_log(paid_amount)
            move._ddsn_sync_stock_fulfillment_documents()
            move._ddsn_sync_mrp_fulfillment_documents()
            move._ddsn_set_release_state()

    def _ddsn_apply_release_for_amount(self, paid_amount):
        for move in self:
            total_amount = abs(move.amount_total)
            if move.payment_release_policy == "manual" or not move.fulfillment_line_ids:
                move._ddsn_set_release_state()
                continue

            if move.payment_release_policy == "prorated":
                move._ddsn_apply_prorated_release(paid_amount, total_amount)
            else:
                move._ddsn_apply_sequential_release(paid_amount)

            move._ddsn_create_or_update_release_log(paid_amount)
            move._ddsn_sync_stock_fulfillment_documents()
            move._ddsn_sync_mrp_fulfillment_documents()
            move._ddsn_set_release_state()

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
