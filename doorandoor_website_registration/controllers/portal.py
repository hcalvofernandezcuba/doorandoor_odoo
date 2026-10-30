from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal


class DoorAndDoorCustomerPortal(CustomerPortal):
    def _get_optional_fields(self):
        return super()._get_optional_fields() + [
            "mobile",
            "ddwr_state_name",
            "ddwr_customer_type",
            "ddwr_builder_name_claim",
            "ddwr_builder_license",
            "ddwr_project_interest",
        ]

    def _get_mandatory_fields(self):
        return super()._get_mandatory_fields() + [
            "ddwr_state_name",
            "ddwr_customer_type",
        ]

    def details_form_validate(self, data, partner_creation=False):
        error, error_message = super().details_form_validate(data, partner_creation=partner_creation)
        customer_type = data.get("ddwr_customer_type")
        if customer_type not in {"individual", "builder", "builder_client"}:
            error["ddwr_customer_type"] = "error"
            error_message.append(_("Seleccione un tipo de cliente válido."))
        if customer_type == "builder_client" and not (data.get("ddwr_builder_name_claim") or "").strip():
            error["ddwr_builder_name_claim"] = "missing"
            error_message.append(_("Escriba el nombre de la constructora asociada."))
        if customer_type == "builder" and not (data.get("company_name") or "").strip():
            error["company_name"] = "missing"
            error_message.append(_("Indique el nombre de la empresa constructora."))
        return error, error_message
