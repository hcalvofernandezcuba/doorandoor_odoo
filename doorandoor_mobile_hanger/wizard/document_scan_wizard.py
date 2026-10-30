import re
from urllib.parse import parse_qs, unquote, urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DoorAndDoorHangerDocumentScan(models.TransientModel):
    _name = "doorandoor.hanger.document.scan"
    _description = "Escanear operación con móvil o hanger"

    scan_code = fields.Char(
        string="Código de la operación",
        required=True,
        help="Escanee el Code128, escriba la referencia o pegue el contenido del QR.",
    )

    @api.model
    def ddmh_is_document_code(self, code):
        """Separate operational documents from physical item labels.

        DoorAndDoor item labels are compact barcodes, while operational
        references use slashes (PICK/..., DD/OUT/..., DTP/OUT/...) or an Odoo
        URL/QR payload. The explicit DD-PICK form remains supported for older
        printed documents.
        """
        decoded = unquote((code or "").strip())
        if not decoded:
            return False
        return bool(
            decoded.lower().startswith(("http://", "https://"))
            or re.fullmatch(r"DD-PICK-\d+", decoded, flags=re.IGNORECASE)
            or "/" in decoded
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

    def _ddmh_extract_odoo_url_target(self, code):
        """Return the model and id encoded in an Odoo backend URL."""
        decoded = unquote((code or "").strip())
        if not decoded.lower().startswith(("http://", "https://")):
            return False, False

        parsed = urlparse(decoded)
        params = parse_qs(parsed.query)
        # Odoo backend links normally keep model/id in the URL fragment. Some
        # mobile QR readers move that fragment to the query string, so accept
        # both representations.
        params.update(parse_qs(parsed.fragment.lstrip("?")))
        model = (params.get("model") or [""])[0]
        record_id = (params.get("id") or [""])[0]
        if model and record_id.isdigit():
            return model, int(record_id)

        # Odoo 18 also exposes clean backend URLs such as
        # /odoo/action-797/60. Some Android scanners return this browser URL
        # instead of the legacy /web#model=...&id=... value printed in the QR.
        # Resolve the action before trusting the trailing record id so an
        # invoice or another document cannot be mistaken for a picking.
        modern = re.search(r"/odoo/action-(\d+)/(\d+)(?:/)?$", parsed.path)
        if modern:
            action = self.env["ir.actions.act_window"].sudo().browse(
                int(modern.group(1))
            ).exists()
            if action and action.res_model in (
                "stock.picking",
                "doorandoor.pickup.order",
            ):
                return action.res_model, int(modern.group(2))
        return False, False

    @api.model
    def ddmh_open_scanned_operation(self, code):
        """Resolve a document shot without persisting a transient wizard."""
        code = (code or "").strip()
        if not code:
            raise UserError(_("Escanee o escriba el código de la operación."))
        model, record_id = self._ddmh_extract_odoo_url_target(code)
        picking_id = self._ddmh_extract_picking_id(code)
        Picking = self.env["stock.picking"]
        if model == "doorandoor.pickup.order" and record_id:
            pickup = self.env["doorandoor.pickup.order"].browse(record_id).exists()
            if pickup and not pickup.picking_id:
                raise UserError(
                    _("El Pickup Order %s todavía no tiene una entrega asociada.")
                    % pickup.display_name
                )
            picking = pickup.picking_id if pickup else Picking
        elif model == "stock.picking" and record_id:
            picking = Picking.browse(record_id).exists()
        elif picking_id:
            picking = Picking.browse(picking_id).exists()
        else:
            # Operational references such as DFM/INT/00002 must be resolved
            # as stock operations before inspecting commercial documents. A
            # warehouse-only user is intentionally not allowed to read
            # account.move, which is traversed by the Pickup Order invoice
            # lookup below.
            picking = Picking.search([("name", "=ilike", code)], limit=2)
            if not picking and "/INT/" in code.upper():
                # Existing printed transfer slips remain usable after the
                # controlled INT -> TRS nomenclature migration.  This alias is
                # only a lookup fallback; record rules and warehouse checks are
                # still enforced by action_ddmh_open_mobile below.
                migrated_code = re.sub(
                    r"/INT/", "/TRS/", code, count=1, flags=re.IGNORECASE,
                )
                picking = Picking.search([
                    ("name", "=ilike", migrated_code)
                ], limit=2)
            if len(picking) > 1:
                picking = Picking
            else:
                if not picking:
                    # Sudo is restricted to resolving the document reference.
                    # The resulting picking is reopened with the real user and
                    # action_ddmh_open_mobile enforces its record rule and
                    # assigned warehouses before returning any operation data.
                    pickup = self.env["doorandoor.pickup.order"].sudo().search([
                        "|", ("name", "=ilike", code), ("move_id.name", "=ilike", code),
                    ], limit=2)
                    if len(pickup) == 1 and pickup.picking_id:
                        picking = pickup.picking_id.with_user(self.env.user)
                    elif len(pickup) > 1:
                        picking = Picking
                    else:
                        historical = self.env["doorandoor.historical.delivery"].search([
                            ("external_reference", "=ilike", code),
                        ], limit=2)
                        if len(historical) == 1 and historical.picking_id:
                            picking = historical.picking_id
                        elif len(historical) > 1:
                            picking = Picking
                        else:
                            picking = Picking.search([
                                ("origin", "ilike", code),
                            ], limit=2)

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

    def action_open_operation(self):
        self.ensure_one()
        return self.ddmh_open_scanned_operation(self.scan_code)
