/** @odoo-module **/

function updateCustomerTypeFields(root) {
    const select = root.querySelector("#customer_type, #ddwr_customer_type");
    if (!select) {
        return;
    }
    const builderFields = root.querySelectorAll(".ddwr_builder_company_fields");
    const associationFields = root.querySelectorAll(".ddwr_builder_association_fields");
    const refresh = () => {
        builderFields.forEach((element) => {
            element.style.display = select.value === "builder" ? "" : "none";
        });
        associationFields.forEach((element) => {
            element.style.display = select.value === "builder_client" ? "" : "none";
        });
    };
    select.addEventListener("change", refresh);
    refresh();
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".ddwr_signup_form, .o_portal_details").forEach(updateCustomerTypeFields);
});

