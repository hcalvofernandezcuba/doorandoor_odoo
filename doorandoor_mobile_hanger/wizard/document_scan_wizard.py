import re
from urllib.parse import parse_qs, unquote, urlparse

from odoo import _, fields, models
from odoo.exceptions import UserError


class DoorAndDoorHangerDocumentScan(models.TransientModel):
    _name = "doorandoor.hanger.document.scan"
    _description = "Escanear operación con móvil o hanger"

    scan_code = fields.Char(
        string="Código de la operación",
        required=True,
        help="Escanee el Code128, escriba la referencia o pegue el contenido del QR.",
    )

    def _ddmh_extract_picking_id(self, code):
        decoded = unquote((code or "").strip())
        if not decoded:
            return False

        if decoded.lower().startswith(("http://", "https://")):
            parsed = urlparse(decoded)
            fragment = parse_qs(parsed.fragment)
            model = (fragment.get("model") or [""])[0]
            record_id = (fragment.get("id") or [""])[0]
            if model == "stock.picking" and record_id.isdigit():
                return int(record_id)

        match = re.fullmatch(r"DD-PICK-(\d+)", decoded, flags=re.IGNORECASE)
        return int(match.group(1)) if match else False

    def action_open_operation(self):
        self.ensure_one()
        code = (self.scan_code or "").strip()
        picking_id = self._ddmh_extract_picking_id(code)
        Picking = self.env["stock.picking"]
        if picking_id:
            picking = Picking.browse(picking_id).exists()
        else:
            picking = Picking.search([("name", "=ilike", code)], limit=2)

        if not picking:
            raise UserError(
                _("No se encontró una operación de almacén con el código %s.") % code
            )
        if len(picking) > 1:
            raise UserError(
                _("El código %s identifica más de una operación. Revise el documento.")
                % code
            )
        return picking.action_ddmh_open_mobile()
