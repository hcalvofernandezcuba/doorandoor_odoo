from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelpdeskLocalResponsible(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        warehouses = cls.env["stock.warehouse"].search([
            ("company_id", "=", company.id),
        ], limit=2)
        if len(warehouses) < 2:
            warehouses |= cls.env["stock.warehouse"].create({
                "name": "Helpdesk Local B",
                "code": "HLB",
                "company_id": company.id,
            })
        cls.warehouse_a, cls.warehouse_b = warehouses[:2]
        group = cls.env.ref("doorandoor_helpdesk.group_ddhd_local_responsible")
        cls.local_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Responsable local Helpdesk",
            "login": "helpdesk.local@example.test",
            "company_id": company.id,
            "company_ids": [Command.set(company.ids)],
            "groups_id": [Command.set((cls.env.ref("base.group_user") | group).ids)],
            "ddpc_warehouse_ids": [Command.set(cls.warehouse_a.ids)],
        })
        ticket_model = cls.env["doorandoor.helpdesk.ticket"].sudo()
        cls.ticket_a = ticket_model.create({
            "title": "Caso del almacen autorizado",
            "description": "Debe ser visible para el responsable local.",
            "requester_id": cls.env.user.id,
            "warehouse_id": cls.warehouse_a.id,
            "affected_area": "inventory",
        })
        cls.ticket_b = ticket_model.create({
            "title": "Caso de otro almacen",
            "description": "No debe ser visible para el responsable local.",
            "requester_id": cls.env.user.id,
            "warehouse_id": cls.warehouse_b.id,
            "affected_area": "inventory",
        })
        cls.own_ticket = ticket_model.create({
            "title": "Caso propio sin sede",
            "description": "El originador conserva acceso a su ticket.",
            "requester_id": cls.local_user.id,
            "office_id": False,
            "warehouse_id": False,
            "affected_area": "access",
        })

    def test_local_scope_combines_warehouse_and_own_ticket(self):
        visible = self.env["doorandoor.helpdesk.ticket"].with_user(
            self.local_user
        ).search([])
        self.assertIn(self.ticket_a, visible)
        self.assertIn(self.own_ticket, visible)
        self.assertNotIn(self.ticket_b, visible)

    def test_local_role_does_not_grant_technical_state_changes(self):
        with self.assertRaises(UserError):
            self.ticket_a.with_user(self.local_user).action_start_analysis()
