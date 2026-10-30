from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoorandoorWarehouseMapPosition(models.Model):
    _name = "doorandoor.warehouse.map.position"
    _description = "Posición física del mapa de almacén"
    _order = "warehouse_id, aisle, horizontal_position, vertical_position, side, slot_number"
    _check_company_auto = True

    name = fields.Char(string="Código", compute="_compute_name", store=True, index=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        required=True,
        index=True,
        check_company=True,
        context={"ddic_authorized_warehouse_search": True},
    )
    company_id = fields.Many2one(related="warehouse_id.company_id", store=True, index=True)
    warehouse_prefix = fields.Char(
        string="Prefijo", size=2,
        help="Letra inicial del almacén. Déjelo vacío si la codificación del almacén comienza por el pasillo.",
    )
    aisle = fields.Char(string="Pasillo", required=True, index=True)
    horizontal_position = fields.Char(string="Horizontal", required=True, index=True)
    vertical_position = fields.Integer(string="Nivel", required=True, default=1, index=True)
    side = fields.Selection(
        [("C", "Completo"), ("L", "Izquierda"), ("R", "Derecha")],
        required=True, default="C", index=True,
    )
    slot_number = fields.Integer(
        string="Subdivisión", required=True, default=1,
        help="Primer producto del lado = 1 (se muestra L o R); productos adicionales = 2, 3, etc.",
    )
    custom_suffix = fields.Char(
        string="Sufijo excepcional", size=12,
        help="Solo conserva referencias históricas que aún no cumplen la guía. Debe quedar vacío en posiciones nuevas.",
    )
    status = fields.Selection(
        [("available", "Disponible"), ("reserved", "Reservado"),
         ("blocked", "Bloqueado"), ("maintenance", "Mantenimiento")],
        required=True, default="available", index=True,
    )
    capacity = fields.Integer(
        string="Capacidad estimada",
        default=33,
        help="Capacidad operativa obligatoria de DoorAndDoor: 33 ITEM.",
    )
    note = fields.Text(string="Observaciones")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("warehouse_position_unique", "unique(warehouse_id, name)",
         "Ya existe esta posición física en el almacén."),
    ]

    @api.depends("warehouse_prefix", "aisle", "horizontal_position", "vertical_position", "side", "slot_number", "custom_suffix")
    def _compute_name(self):
        for rec in self:
            prefix = (rec.warehouse_prefix or "").strip().upper()
            aisle = (rec.aisle or "").strip().upper()
            horizontal = (rec.horizontal_position or "").strip().upper()
            base = "%s%s%s%s" % (prefix, aisle, horizontal, rec.vertical_position or "")
            if rec.custom_suffix:
                base += "-" + rec.custom_suffix.strip().upper()
            elif rec.side in ("L", "R"):
                suffix = rec.side + (str(rec.slot_number) if rec.slot_number > 1 else "")
                base += "-" + suffix
            rec.name = base

    @api.constrains("vertical_position", "slot_number", "side", "capacity")
    def _check_values(self):
        for rec in self:
            if rec.vertical_position < 1:
                raise ValidationError(_("El nivel vertical debe ser mayor que cero."))
            if rec.slot_number < 1:
                raise ValidationError(_("La subdivisión debe ser mayor que cero."))
            if rec.side == "C" and rec.slot_number != 1:
                raise ValidationError(_("Una posición completa no utiliza subdivisiones numéricas."))
            if rec.custom_suffix and rec.side != "C":
                raise ValidationError(_("El sufijo excepcional no puede combinarse con los lados L/R."))
            if rec.capacity != 33:
                raise ValidationError(_("Todas las posiciones DoorAndDoor deben tener capacidad 33."))

    @api.model
    def _sync_from_existing_batches(self):
        """Create physical positions for current active batches without changing inventory."""
        Batch = self.env["inventory.serial.label.batch"].sudo()
        created = self.browse()
        known_positions = {
            (position.warehouse_id.id, position.name.upper())
            for position in self.search([])
        }
        for batch in Batch.search([("state", "=", "generated")], order="warehouse_id,name,id"):
            parts = Batch._ddwm_position_parts(batch.name)
            zone, prefix, aisle, horizontal, vertical, suffix, _order = parts
            if zone == "Otras posiciones" or not aisle or not horizontal or not vertical:
                continue
            side = suffix[0] if suffix and suffix[0] in ("L", "R") else "C"
            slot_number = int(suffix[1:]) if suffix and suffix[1:].isdigit() else 1
            custom_suffix = suffix if suffix and side == "C" else False
            reference = (batch.name or "").strip().upper()
            position_key = (batch.warehouse_id.id, reference)
            if position_key in known_positions:
                continue
            created |= self.create({
                "warehouse_id": batch.warehouse_id.id,
                "warehouse_prefix": prefix or False,
                "aisle": aisle,
                "horizontal_position": horizontal,
                "vertical_position": int(vertical),
                "side": side,
                "slot_number": slot_number,
                "custom_suffix": custom_suffix,
                "status": "available",
                "capacity": 33,
                "note": _("Creada automáticamente desde el lote existente %s.") % batch.display_name,
            })
            known_positions.add(position_key)
        return len(created)
