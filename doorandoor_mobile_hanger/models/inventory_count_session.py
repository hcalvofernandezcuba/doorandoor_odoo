from odoo import _, fields, models


class InventorySerialClaim(models.Model):
    _inherit = "inventory.serial.claim"

    ddmh_serial_code = fields.Char(
        string="Label",
        related="serial_id.code",
        readonly=True,
    )


class InventoryCountSession(models.Model):
    _inherit = "inventory.count.session"

    ddmh_scan_event_ids = fields.One2many(
        "ddmh.hanger.scan.event", "count_session_id",
        string="Eventos Hanger", readonly=True,
    )

    def action_scan(self, scanned_barcode=None):
        """Persist accepted IC shots; rejected attempts use the fallback RPC."""
        self.ensure_one()
        code = (scanned_barcode or self.barcode_input or "").strip()
        result = super().action_scan(scanned_barcode)
        serial = self.env["inventory.unit.serial"].search([
            ("code", "=", code), ("active", "=", True),
        ], limit=1)
        product = serial.product_id or self.last_scanned_product_id
        self.env["ddmh.hanger.scan.event"].sudo().create({
            "count_session_id": self.id,
            "user_id": self.env.user.id,
            "code": code,
            "serial_id": serial.id or False,
            "product_id": product.id or False,
            "status": "accepted",
            "message": _("Lectura aceptada y acumulada en la sesión IC."),
        })
        return result

    def action_ddmh_reload_mobile(self):
        self.ensure_one()
        self._ddic_check_location_access(self.location_id)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ddmh_reload_monitor(self):
        """Refresh data without falling back to the operational IC form."""
        self.ensure_one()
        self._ddic_check_location_access(self.location_id)
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "view_id": self.env.ref(
                "doorandoor_mobile_hanger.view_inventory_count_session_form_ddmh_monitor"
            ).id,
            "target": "current",
        }
