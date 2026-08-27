/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useSubEnv } from "@odoo/owl";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";

patch(ProductConfiguratorDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.ddspOrm = useService("orm");
        this.ddspNotification = useService("notification");
        Object.assign(this.state, {
            ddspDeclareSpecial: false,
            ddspAllowSpecial: false,
            ddspBaseProductId: false,
            ddspSpecialChanges: Object.fromEntries(
                this.ddspAvailableAttributes.map((attribute) => [
                    attribute.id,
                    { selected: false, value: "" },
                ])
            ),
            ddspSpecialNotes: "",
            ddspProductionInstructions: "",
        });
        useSubEnv({
            ddspIsSpecial: () => this.state.ddspDeclareSpecial,
        });
        onWillStart(async () => {
            const [template] = await this.ddspOrm.read(
                "product.template",
                [this.props.productTemplateId],
                ["ddsp_allow_special", "ddsp_is_special"]
            );
            this.state.ddspAllowSpecial = Boolean(
                template?.ddsp_allow_special && !template?.ddsp_is_special
            );
        });
    },

    async ddspToggleSpecial(ev) {
        if (!this.state.ddspAllowSpecial) {
            this.state.ddspDeclareSpecial = false;
            return;
        }
        this.state.ddspDeclareSpecial = ev.target.checked;
        const mainProduct = this.state.products.find(
            (product) => product.product_tmpl_id === this.env.mainProductTmplId
        );
        if (!mainProduct) {
            return;
        }
        if (this.state.ddspDeclareSpecial) {
            // Conservar la variante física que se desmontará como componente de
            // la LDM, pero limpiar el selector normal para que sus valores no se
            // confundan con los valores excepcionales escritos por el vendedor.
            if (
                !mainProduct.id &&
                this._isPossibleCombination(mainProduct) &&
                mainProduct.attribute_lines.some((line) => line.create_variant === "dynamic")
            ) {
                mainProduct.id = parseInt(await this._createProduct(mainProduct));
            }
            this.state.ddspBaseProductId = mainProduct.id;
            for (const line of mainProduct.attribute_lines) {
                line.selected_attribute_value_ids = [];
                line.customValue = "";
            }
        }
    },

    get ddspAvailableAttributes() {
        const mainProduct = this.state.products.find(
            (product) => product.product_tmpl_id === this.env.mainProductTmplId
        );
        const attributes = (mainProduct?.attribute_lines || []).map((line) => line.attribute);
        if (this.state.ddspSpecialChanges) {
            for (const attribute of attributes) {
                if (!this.state.ddspSpecialChanges[attribute.id]) {
                    this.state.ddspSpecialChanges[attribute.id] = {
                        selected: false,
                        value: "",
                    };
                }
            }
        }
        return attributes;
    },

    async onConfirm(options) {
        if (!this.state.ddspDeclareSpecial) {
            return super.onConfirm(options);
        }
        const specialChanges = this.ddspAvailableAttributes
            .filter((attribute) => this.state.ddspSpecialChanges[attribute.id]?.selected)
            .map((attribute) => ({
                attribute_id: attribute.id,
                value: this.state.ddspSpecialChanges[attribute.id].value.trim(),
            }));
        if (
            !this.state.ddspBaseProductId ||
            !specialChanges.length ||
            specialChanges.some((change) => !change.value) ||
            !this.state.ddspSpecialNotes.trim() ||
            !this.state.ddspProductionInstructions.trim()
        ) {
            this.ddspNotification.add(
                _t("Seleccione uno o varios atributos y complete el valor transformado de cada uno, las especificaciones y las instrucciones de fabricación."),
                { type: "warning" }
            );
            return;
        }
        const mainProduct = this.state.products.find(
            (product) => product.product_tmpl_id === this.env.mainProductTmplId
        );
        const optionalProducts = this.state.products.filter(
            (product) => product !== mainProduct
        );
        const special = await this.ddspOrm.call(
            "product.template",
            "ddsp_create_special_from_configurator",
            [
                this.state.ddspBaseProductId || mainProduct.id,
                specialChanges,
                parseFloat(mainProduct.price),
                this.state.ddspSpecialNotes,
                this.state.ddspProductionInstructions,
            ]
        );
        mainProduct.id = special.product_id;
        mainProduct.product_tmpl_id = special.product_template_id;
        mainProduct.display_name = special.display_name;
        mainProduct.price = special.price;
        await this.props.save(
            mainProduct,
            optionalProducts,
            options
        );
        this.props.close();
    },
});
