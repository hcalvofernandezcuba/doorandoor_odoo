import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorandoorLabelLocator(models.TransientModel):
    _name = "doorandoor.label.locator"
    _description = "Localizador global de labels"

    query = fields.Text(
        string="Labels",
        required=True,
        help="Escriba un label o pegue varios separados por espacios, comas o líneas.",
    )
    line_ids = fields.One2many(
        "doorandoor.label.locator.line", "wizard_id", string="Resultados", readonly=True,
    )
    found_count = fields.Integer(string="Encontrados", compute="_compute_counts")
    missing_labels = fields.Text(string="No encontrados", readonly=True)

    @api.depends("line_ids")
    def _compute_counts(self):
        for wizard in self:
            wizard.found_count = len(wizard.line_ids)

    def _requested_codes(self):
        self.ensure_one()
        return list(dict.fromkeys(
            item.strip() for item in re.split(r"[\s,;]+", self.query or "") if item.strip()
        ))

    def action_search(self):
        self.ensure_one()
        codes = self._requested_codes()
        if not codes:
            raise UserError(_("Indique al menos un número de label."))
        if len(codes) > 500:
            raise UserError(_("Puede consultar hasta 500 labels en una búsqueda."))

        allowed = self.env["inventory.serial.label.batch"]._ddic_allowed_warehouses()
        lookup_codes = list(dict.fromkeys(
            value
            for code in codes
            for value in ([code, code.zfill(8)] if code.isdigit() else [code])
        ))
        serials = self.env["inventory.unit.serial"].search([
            ("code", "in", lookup_codes),
            "|",
            ("current_warehouse_id", "in", allowed.ids),
            ("current_batch_id.warehouse_id", "in", allowed.ids),
        ])
        found = {serial.code: serial for serial in serials}
        resolved = {
            code: found.get(code) or (found.get(code.zfill(8)) if code.isdigit() else False)
            for code in codes
        }
        self.line_ids = [(5, 0, 0)] + [
            (0, 0, self.env["doorandoor.label.locator.line"]._values_from_serial(resolved[code]))
            for code in codes if resolved[code]
        ]
        self.missing_labels = ", ".join(code for code in codes if not resolved[code])
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class DoorandoorLabelLocatorLine(models.TransientModel):
    _name = "doorandoor.label.locator.line"
    _description = "Resultado del localizador de labels"
    _order = "code, id"

    wizard_id = fields.Many2one("doorandoor.label.locator", required=True, ondelete="cascade")
    serial_id = fields.Many2one("inventory.unit.serial", required=True, readonly=True)
    code = fields.Char(string="Label", readonly=True)
    product_id = fields.Many2one("product.product", string="ITEM", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén actual", readonly=True)
    batch_id = fields.Many2one("inventory.serial.label.batch", string="Lote actual", readonly=True)
    position_id = fields.Many2one(
        "doorandoor.warehouse.map.position", string="Posición física", readonly=True,
    )
    location_id = fields.Many2one("stock.location", string="Ubicación operativa", readonly=True)
    status = fields.Selection([
        ("available", "Disponible"),
        ("reserved", "Reservado"),
        ("predispatch", "Predespacho"),
        ("transit", "En tránsito"),
        ("delivered", "Entregado / cliente"),
        ("pending", "Pendiente de cargar"),
        ("inactive", "Inactivo"),
    ], string="Estado", readonly=True)
    picking_id = fields.Many2one("stock.picking", string="Operación reservada", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Factura", readonly=True)
    reserved_by_id = fields.Many2one("res.users", string="Reservado por", readonly=True)
    reserved_at = fields.Datetime(string="Reservado el", readonly=True)

    @api.model
    def _values_from_serial(self, serial):
        location = serial.current_location_id
        if not serial.active:
            status = "inactive"
        elif serial.reserved_picking_id:
            status = "reserved"
        elif location.ddic_is_predispatch or location.ddic_is_predispatch_root:
            status = "predispatch"
        elif location.usage == "transit":
            status = "transit"
        elif location.usage == "customer":
            status = "delivered"
        elif serial.inventory_loaded:
            status = "available"
        else:
            status = "pending"
        batch = serial.current_batch_id
        return {
            "serial_id": serial.id,
            "code": serial.code,
            "product_id": serial.product_id.id,
            "warehouse_id": serial.current_warehouse_id.id,
            "batch_id": batch.id,
            "position_id": batch._ddwm_resolved_position().id if batch else False,
            "location_id": location.id,
            "status": status,
            "picking_id": serial.reserved_picking_id.id,
            "invoice_id": serial.reserved_invoice_id.id,
            "reserved_by_id": serial.reserved_by_id.id,
            "reserved_at": serial.reserved_at,
        }

    def action_open_map(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "doorandoor_warehouse_map.dashboard",
            "name": _("Mapa del almacén"),
            "params": {"warehouse_id": self.warehouse_id.id, "label_code": self.code},
        }
