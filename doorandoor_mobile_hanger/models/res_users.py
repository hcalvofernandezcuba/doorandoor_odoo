from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    ddmh_operational_role = fields.Selection(
        selection=[
            ("none", "Sin perfil Hanger"),
            ("counter", "Contador de inventario"),
            ("delivery", "Operador de entregas"),
            ("warehouse", "Almacenero"),
            ("supervisor", "Supervisor de almacén"),
        ],
        string="Perfil operativo Hanger",
        default="none",
        required=True,
        help=(
            "Plantilla funcional del dispositivo. Los permisos quedan limitados "
            "a los almacenes operativos seleccionados."
        ),
    )
    ddmh_live_scan_notifications = fields.Boolean(
        string="Recibir disparos Hanger en vivo",
        help=(
            "Muestra una notificación de Odoo por cada lectura Hanger, positiva "
            "o negativa, aunque el usuario esté trabajando fuera del monitor."
        ),
    )

    @api.constrains("ddmh_operational_role", "ddpc_warehouse_ids")
    def _check_ddmh_role_warehouses(self):
        for user in self:
            if user.ddmh_operational_role != "none" and not user.ddpc_warehouse_ids:
                raise ValidationError(_(
                    "Asigne al menos un almacén operativo antes de activar el "
                    "perfil Hanger de %(user)s."
                ) % {"user": user.display_name})

    def _ddmh_sync_operational_role_groups(self):
        """Synchronize only the four profile groups; never grant Settings."""
        profiles = {
            "counter": self.env.ref("doorandoor_mobile_hanger.group_ddmh_counter"),
            "delivery": self.env.ref("doorandoor_mobile_hanger.group_ddmh_delivery"),
            "warehouse": self.env.ref("doorandoor_mobile_hanger.group_ddmh_warehouse"),
            "supervisor": self.env.ref("doorandoor_mobile_hanger.group_ddmh_supervisor"),
        }
        profile_ids = set(group.id for group in profiles.values())
        for user in self:
            commands = [(3, group_id) for group_id in profile_ids]
            selected = profiles.get(user.ddmh_operational_role)
            if selected:
                commands.append((4, selected.id))
            user.sudo().with_context(ddmh_skip_role_sync=True).write({"groups_id": commands})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users.filtered(lambda user: user.ddmh_operational_role != "none")._ddmh_sync_operational_role_groups()
        return users

    def write(self, vals):
        result = super().write(vals)
        if "ddmh_operational_role" in vals and not self.env.context.get("ddmh_skip_role_sync"):
            self._ddmh_sync_operational_role_groups()
        return result
