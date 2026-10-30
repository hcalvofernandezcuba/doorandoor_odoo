from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request


class DoorAndDoorPolicyAcceptanceController(http.Controller):

    @http.route("/terminos-y-condiciones", type="http", auth="public", website=True, sitemap=True)
    def official_terms_and_conditions(self, **kwargs):
        policy = request.env["doorandoor.policy.document"].sudo().get_current_policy()
        language = "es" if kwargs.get("lang") == "es" else "en"
        pdf_url = policy.pdf_url_es if language == "es" and policy.pdf_url_es else policy.pdf_url
        return request.render(
            "doorandoor_policy_acceptance.official_terms_and_conditions",
            {"policy": policy, "document_language": language, "document_pdf_url": pdf_url},
        )

    def _find_acceptance(self, token):
        return request.env["doorandoor.policy.acceptance"].sudo().search(
            [("access_token", "=", token)], limit=1
        )

    @http.route("/politicas/firmar/<string:token>", type="http", auth="public", website=True, sitemap=False)
    def policy_signature(self, token, **kwargs):
        acceptance = self._find_acceptance(token)
        if not acceptance:
            return request.not_found()
        language = "es" if kwargs.get("lang") == "es" else "en"
        pdf_url = acceptance.policy_id.pdf_url_es if language == "es" and acceptance.policy_id.pdf_url_es else acceptance.policy_id.pdf_url
        return request.render("doorandoor_policy_acceptance.policy_signature_page", {
            "acceptance": acceptance,
            "policy": acceptance.policy_id,
            "document_language": language,
            "document_pdf_url": pdf_url,
            "error": False,
        })

    @http.route(
        "/politicas/firmar/<string:token>/aceptar",
        type="http", auth="public", website=True, methods=["POST"], csrf=True, sitemap=False
    )
    def policy_signature_accept(self, token, signer_name=None, accepted=None, document_language="en", **kwargs):
        acceptance = self._find_acceptance(token)
        if not acceptance:
            return request.not_found()
        error = False
        if not accepted:
            error = _("Debe marcar la casilla de aceptación para continuar.")
        else:
            forwarded = request.httprequest.headers.get("X-Forwarded-For", "")
            ip_address = (forwarded.split(",")[0].strip() if forwarded else request.httprequest.remote_addr)
            try:
                acceptance._accept(
                    signer_name,
                    ip_address=ip_address,
                    user_agent=request.httprequest.headers.get("User-Agent", ""),
                    document_language=document_language,
                )
            except ValidationError as exc:
                error = exc.args[0]
        if error:
            return request.render("doorandoor_policy_acceptance.policy_signature_page", {
                "acceptance": acceptance,
                "policy": acceptance.policy_id,
                "document_language": document_language,
                "document_pdf_url": acceptance.policy_id.pdf_url_es if document_language == "es" and acceptance.policy_id.pdf_url_es else acceptance.policy_id.pdf_url,
                "error": error,
            })
        return request.render("doorandoor_policy_acceptance.policy_signature_success", {
            "acceptance": acceptance,
            "policy": acceptance.policy_id,
        })
