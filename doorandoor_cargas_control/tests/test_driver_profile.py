from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDriverProfile(TransactionCase):

    def test_quick_create_driver_without_odoo_user(self):
        profile_id, display_name = self.env[
            "doorandoor.driver.profile"
        ].name_create("Yordanis Rodrigues")
        profile = self.env["doorandoor.driver.profile"].browse(profile_id)

        self.assertEqual(profile.name, "Yordanis Rodrigues")
        self.assertEqual(display_name, "Yordanis Rodrigues")
        self.assertFalse(profile.user_id)

    def test_user_link_supplies_default_driver_name(self):
        profile = self.env["doorandoor.driver.profile"].create({
            "user_id": self.env.user.id,
        })

        self.assertEqual(profile.name, self.env.user.name)
