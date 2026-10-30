from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOperationalManualAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_group = cls.env.ref("base.group_user")
        cls.user_internal = cls.env["res.users"].create(
            {
                "name": "Test lector interno",
                "login": "test_manual_internal",
                "groups_id": [(6, 0, [cls.internal_group.id])],
            }
        )

    def test_internal_user_sees_every_published_manual(self):
        Manual = self.env["doorandoor.operational.manual"]
        manuals = Manual.with_user(self.user_internal).search([])
        self.assertEqual(
            set(manuals.mapped("code")),
            {"DD-GUIA-HIST-001", "DD-GUIA-INV-001", "DD-GUIA-ALM-001"},
        )
        self.assertTrue(all(manuals.mapped("pdf_file")))

    def test_reader_cannot_modify_manual(self):
        manual = self.env.ref(
            "doorandoor_operational_manuals.manual_historic_logistics"
        ).with_user(self.user_internal)
        with self.assertRaises(AccessError):
            manual.write({"name": "Cambio no autorizado"})
