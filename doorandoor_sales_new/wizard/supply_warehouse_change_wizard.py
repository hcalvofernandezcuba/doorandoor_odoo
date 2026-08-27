from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SupplyWarehouseChangeWizard(models.TransientModel):
    _name = "ddsn.supply.warehouse.change.wizard"
    _description = "Controlled supply warehouse change"

    sale_order_id = fields.Many2one("sale.order", string="Cotización", readonly=True)
    move_id = fields.Many2one("account.move", string="Prefactura / Factura", readonly=True)
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Producto",
        domain="[('order_id', '=', sale_order_id), ('display_type', '=', False)]",
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Producto de prefactura / factura",
        domain="[('move_id', '=', move_id), ('product_id', '!=', False)]",
    )
    current_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén actual", compute="_compute_current_warehouse"
    )
    new_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Nuevo almacén proveedor",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one("res.company", compute="_compute_company")
    reason = fields.Char(string="Motivo del cambio", required=True)

    @api.depends("sale_order_id", "move_id")
    def _compute_company(self):
        for wizard in self:
            wizard.company_id = wizard.sale_order_id.company_id or wizard.move_id.company_id

    @api.depends("sale_line_id", "move_line_id")
    def _compute_current_warehouse(self):
        for wizard in self:
            line = wizard.sale_line_id or wizard.move_line_id
            document = wizard.sale_order_id or wizard.move_id
            wizard.current_warehouse_id = (
                line.ddsn_supply_warehouse_id
                or getattr(document, "warehouse_id", False)
                or document.sale_order_id.warehouse_id
            )

    @api.onchange("sale_line_id", "move_line_id")
    def _onchange_line(self):
        self.new_warehouse_id = self.current_warehouse_id

    def _get_commercial_lines(self):
        self.ensure_one()
        sale_line = self.sale_line_id or self.move_line_id.generated_sale_line_id
        move_lines = self.env["account.move.line"]
        if sale_line:
            move_lines = self.env["account.move.line"].search(
                [("generated_sale_line_id", "=", sale_line.id)]
            )
        elif self.move_line_id:
            move_lines = self.move_line_id
        return sale_line, move_lines

    def action_apply(self):
        self.ensure_one()
        if bool(self.sale_order_id) == bool(self.move_id):
            raise ValidationError(_("No se pudo determinar el documento comercial de origen."))
        if self.move_id and (self.move_id.move_type != "out_invoice" or self.move_id.state != "draft"):
            raise ValidationError(
                _("El almacén proveedor solo puede cambiarse antes de confirmar la factura.")
            )
        if self.sale_order_id.state == "cancel":
            raise ValidationError(_("No se puede cambiar el almacén de una cotización cancelada."))
        if self.new_warehouse_id.company_id != self.company_id:
            raise ValidationError(_("El almacén seleccionado pertenece a otra compañía."))

        sale_line, move_lines = self._get_commercial_lines()
        if not sale_line and not move_lines:
            raise ValidationError(_("Seleccione la línea de producto que desea cambiar."))
        if move_lines.filtered("ddsn_supply_transfer_id"):
            raise ValidationError(
                _("Ya existe un traslado para esta línea y su almacén de origen no puede cambiarse.")
            )

        old_warehouse = self.current_warehouse_id
        values = {"ddsn_supply_warehouse_id": self.new_warehouse_id.id}
        if sale_line:
            sale_line.write(values)
        move_lines.write(values)

        # Recheck the complete reservation atomically at its new warehouse.
        # Any shortage raises and rolls the whole wizard transaction back.
        reserved_moves = move_lines.mapped("move_id").filtered(
            lambda move: move.state == "draft" and move._ddsn_has_active_reservation()
        )
        for reserved_move in reserved_moves:
            reserved_move._ddsn_validate_and_lock_supply_reservations()

        documents = (move_lines.mapped("move_id") | self.move_id).filtered(lambda move: move)
        orders = (sale_line.order_id | self.sale_order_id).filtered(lambda order: order)
        body = _(
            "Almacén proveedor cambiado para %(product)s: %(old)s → %(new)s. Motivo: %(reason)s"
        ) % {
            "product": (sale_line or move_lines[:1]).product_id.display_name,
            "old": old_warehouse.display_name or _("Sin definir"),
            "new": self.new_warehouse_id.display_name,
            "reason": self.reason,
        }
        for order in orders:
            order.message_post(body=body)
        for document in documents:
            document.message_post(body=body)
        (orders.mapped("ddsn_preinvoice_move_id") | orders.mapped("ddsn_invoice_move_id") | documents)._ddsn_broadcast_document_update(
            "supply_warehouse_changed"
        )
        return {"type": "ir.actions.act_window_close"}
