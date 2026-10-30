from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCashRegister(models.Model):
    _name = "doorandoor.cash.register"
    _description = "Caja de ventas"
    _rec_name = "name"
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    office_id = fields.Many2one(
        "doorandoor.commercial.office",
        string="Oficina comercial",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        check_company=True,
        ondelete="restrict",
        help="Oficina cuyos cobros se procesan exclusivamente en esta caja.",
    )
    city_rule_id = fields.Many2one(
        "doorandoor.tax.state.rule", string="Ciudad / sucursal",
        help="Los cobros en efectivo de esta ciudad se envían a esta caja.",
    )
    cash_journal_id = fields.Many2one(
        "account.journal", required=True, check_company=True,
        domain="[('type', '=', 'cash'), ('company_id', '=', company_id)]",
        string="Diario de efectivo",
    )
    deposit_journal_id = fields.Many2one(
        "account.journal", check_company=True,
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        string="Diario bancario de depósito",
        help="Solo identifica el destino en la planilla; el módulo no crea el asiento bancario.",
    )
    cashier_ids = fields.Many2many(
        "res.users",
        string="Operadores de caja",
        domain="[('ddco_office_id', '=', office_id)]",
    )
    manager_ids = fields.Many2many(
        "res.users",
        "ddcc_cash_register_manager_rel",
        "register_id",
        "user_id",
        string="Responsables de caja",
        domain="[('ddco_office_id', '=', office_id)]",
        help="Supervisores de la caja. El rol responsable incluye el rol operador.",
    )

    @api.constrains("office_id", "company_id", "active")
    def _check_office_assignment(self):
        for register in self:
            if register.office_id and register.office_id.company_id != register.company_id:
                raise ValidationError("La caja y la oficina deben pertenecer a la misma compañía.")
            if register.active and register.office_id:
                duplicate = self.search_count([
                    ("id", "!=", register.id),
                    ("active", "=", True),
                    ("office_id", "=", register.office_id.id),
                ])
                if duplicate:
                    raise ValidationError("Solo puede existir una caja comercial activa por oficina.")

    @api.constrains("office_id", "cashier_ids", "manager_ids")
    def _check_cash_users_office(self):
        for register in self.filtered("office_id"):
            invalid = (register.cashier_ids | register.manager_ids).filtered(
                lambda user: user.ddco_office_id != register.office_id
            )
            if invalid:
                raise ValidationError(
                    "Estos usuarios no pertenecen a la oficina %s: %s"
                    % (register.office_id.display_name, ", ".join(invalid.mapped("name")))
                )

    def _sync_cash_role_groups(self, previous_users=None):
        cashier_group = self.env.ref("doorandoor_cierre_caja.group_cashier")
        manager_group = self.env.ref("doorandoor_cierre_caja.group_cash_manager")
        current_cashiers = self.mapped("cashier_ids") | self.mapped("manager_ids")
        current_managers = self.mapped("manager_ids")
        for user in (previous_users or self.env["res.users"]) - current_managers:
            still_manager = self.search_count([("manager_ids", "in", user.id)])
            if not still_manager:
                user.sudo().write({"groups_id": [(3, manager_group.id)]})
        for user in (previous_users or self.env["res.users"]) - current_cashiers:
            still_cashier = self.search_count([
                "|", ("cashier_ids", "in", user.id), ("manager_ids", "in", user.id)
            ])
            if not still_cashier:
                user.sudo().write({"groups_id": [(3, cashier_group.id)]})

        current_cashiers.sudo().write({"groups_id": [(4, cashier_group.id)]})
        current_managers.sudo().write({"groups_id": [(4, manager_group.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        registers = super().create(vals_list)
        registers._sync_cash_role_groups()
        return registers

    def write(self, vals):
        previous_users = self.mapped("cashier_ids") | self.mapped("manager_ids")
        result = super().write(vals)
        if {"cashier_ids", "manager_ids"}.intersection(vals):
            self._sync_cash_role_groups(previous_users)
        return result
