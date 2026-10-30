import base64

from odoo import http
from odoo.http import request
from werkzeug.utils import secure_filename


class DoorAndDoorOperationalManualCenter(http.Controller):

    def _ensure_internal_user(self):
        user = request.env.user
        return bool(user and not user._is_public() and not user.share)

    @http.route(
        "/guias-operativas",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def operational_manual_center(self, area=None, **kwargs):
        if not self._ensure_internal_user():
            return request.not_found()
        domain = [("state", "=", "published"), ("active", "=", True)]
        if area:
            domain.append(("area", "=", area))
        manuals = request.env["doorandoor.operational.manual"].search(
            domain, order="sequence, area, name"
        )
        areas = request.env["doorandoor.operational.manual"]._fields["area"].selection
        return request.render(
            "doorandoor_operational_manuals.operational_manual_center",
            {
                "manuals": manuals,
                "areas": areas,
                "area_labels": dict(areas),
                "selected_area": area or "",
            },
        )

    @http.route(
        "/guias-operativas/<int:manual_id>/pdf",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def operational_manual_pdf(self, manual_id, download=0, **kwargs):
        if not self._ensure_internal_user():
            return request.not_found()
        manual = request.env["doorandoor.operational.manual"].browse(manual_id).exists()
        if not manual:
            return request.not_found()
        manual.check_access_rights("read")
        manual.check_access_rule("read")
        if manual.state != "published" or not manual.active or not manual.pdf_file:
            return request.not_found()
        filename = secure_filename(manual.pdf_filename or "%s.pdf" % manual.code)
        disposition = "attachment" if str(download) == "1" else "inline"
        return request.make_response(
            base64.b64decode(manual.pdf_file),
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", '%s; filename="%s"' % (disposition, filename)),
                ("Cache-Control", "private, no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
