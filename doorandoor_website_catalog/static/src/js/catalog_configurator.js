/** @odoo-module **/

function initCatalogConfigurator(root) {
    const variants = JSON.parse(root.dataset.variants || "[]");
    const groups = [...root.querySelectorAll(".ddwc_option_group")];
    const selection = {};
    const result = root.querySelector(".ddwc_variant_result");
    const quoteButton = document.querySelector(".ddwc_quote_button");
    const productImage = document.querySelector(".ddwc_product_image");
    const baseQuoteUrl = quoteButton?.getAttribute("href") || "/contactus";
    const productName = root.dataset.productName || "Producto";

    const matches = (variant, selected, exceptAttribute = null) =>
        Object.entries(selected).every(([attributeId, valueId]) =>
            attributeId === exceptAttribute || String(variant.v[attributeId]) === String(valueId)
        );

    function refresh() {
        groups.forEach((group) => {
            const attributeId = group.dataset.attributeId;
            group.querySelectorAll(".ddwc_option").forEach((button) => {
                const candidate = {...selection, [attributeId]: button.dataset.valueId};
                button.disabled = !variants.some((variant) => matches(variant, candidate));
                button.classList.toggle("active", String(selection[attributeId]) === button.dataset.valueId);
            });
        });

        const selectedVariant = variants.find((variant) =>
            groups.every((group) => String(variant.v[group.dataset.attributeId]) === String(selection[group.dataset.attributeId]))
        );
        if (selectedVariant) {
            const selectedValues = groups.map((group) =>
                group.querySelector(".ddwc_option.active")?.textContent.trim()
            ).filter(Boolean);
            const variantName = `${productName} (${selectedValues.join(", ")})`;
            const code = selectedVariant.c ? ` · ${selectedVariant.c}` : "";
            result.textContent = `Configuración disponible: ${variantName}${code}`;
            if (quoteButton) {
                const separator = baseQuoteUrl.includes("?") ? "&" : "?";
                quoteButton.href = `${baseQuoteUrl}${separator}variant_id=${selectedVariant.i}&variant=${encodeURIComponent(variantName)}`;
                quoteButton.classList.remove("disabled");
                quoteButton.setAttribute("aria-disabled", "false");
            }
            if (productImage) {
                productImage.src = `/web/image/product.product/${selectedVariant.i}/image_1920`;
            }
        } else {
            result.textContent = "Seleccione las opciones para identificar el producto.";
            if (quoteButton) {
                quoteButton.href = baseQuoteUrl;
                quoteButton.classList.add("disabled");
                quoteButton.setAttribute("aria-disabled", "true");
            }
        }
    }

    groups.forEach((group) => {
        group.addEventListener("click", (event) => {
            const button = event.target.closest(".ddwc_option");
            if (!button || button.disabled) return;
            const attributeId = group.dataset.attributeId;
            selection[attributeId] = button.dataset.valueId;
            group.querySelector(".ddwc_selected_value").textContent = button.textContent.trim();

            let clearFollowing = false;
            groups.forEach((candidateGroup) => {
                if (candidateGroup === group) {
                    clearFollowing = true;
                    return;
                }
                if (clearFollowing) {
                    delete selection[candidateGroup.dataset.attributeId];
                    candidateGroup.querySelector(".ddwc_selected_value").textContent = "Seleccione una opción";
                }
            });
            refresh();
        });
    });

    refresh();
}

function startCatalogConfigurators() {
    document.querySelectorAll(".ddwc_configurator").forEach(initCatalogConfigurator);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startCatalogConfigurators, {once: true});
} else {
    startCatalogConfigurators();
}
