from odoo import http
from odoo.http import request


class DoorAndDoorLegalPages(http.Controller):
    @http.route("/terminos-y-condiciones", type="http", auth="public", website=True, sitemap=True)
    def terms_and_conditions(self, **kwargs):
        return request.render("doorandoor_website_registration.terms_and_conditions")

    @http.route("/politica-de-privacidad", type="http", auth="public", website=True, sitemap=True)
    def privacy_policy(self, **kwargs):
        return request.render("doorandoor_website_registration.privacy_policy")
