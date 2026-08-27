from odoo import _, models
from odoo.exceptions import AccessError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ddmh_check_mobile_warehouse_access(self):
        """Apply a clear warehouse check in addition to the native record rules."""
        manager = self.env.user.has_group("doorandoor_process_control.group_ddpc_manager")
        system = self.env.user.has_group("base.group_system")
        operator = self.env.user.has_group(
            "doorandoor_process_control.group_ddpc_warehouse_operator"
        )
        if manager or system or not operator:
            return True

        allowed = self.env.user.ddpc_warehouse_ids
        if not allowed:
            raise AccessError(
                _("Su usuario no tiene almacenes operativos asignados.")
            )
        for picking in self:
            warehouses = picking.ddpc_source_warehouse_id | picking.ddpc_dest_warehouse_id
            if not (warehouses & allowed):
                raise AccessError(
                    _("La operación %(operation)s no pertenece a uno de sus almacenes.")
                    % {"operation": picking.display_name}
                )
        return True

    def action_ddmh_open_mobile(self):
        self.ensure_one()
        self.check_access_rights("read")
        self.check_access_rule("read")
        self._ddmh_check_mobile_warehouse_access()
        action = self.env.ref("doorandoor_mobile_hanger.action_ddmh_mobile_picking").read()[0]
        action.update({"res_id": self.id, "target": "current"})
        return action

    def action_ddmh_open_full_operation(self):
        self.ensure_one()
        self._ddmh_check_mobile_warehouse_access()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "stock.picking",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def _ddsn_get_barcode_backend_url(self):
        """Make picking QR codes open the dedicated mobile operation view."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        action = self.env.ref(
            "doorandoor_mobile_hanger.action_ddmh_mobile_picking",
            raise_if_not_found=False,
        )
        action_part = f"action={action.id}&" if action else ""
        return (
            f"{base_url}/web#{action_part}id={self.id}"
            "&model=stock.picking&view_type=form"
        )
