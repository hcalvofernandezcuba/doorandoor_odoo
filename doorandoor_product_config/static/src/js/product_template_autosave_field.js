/** @odoo-module **/

import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    Many2OneField,
    many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";

function noVariantValueIds(product) {
    return product.attribute_lines
        .filter((line) => line.create_variant === "no_variant")
        .flatMap((line) => line.selected_attribute_value_ids);
}

async function applyInvoiceProduct(record, product) {
    await record.update({
        ddpc_product_template_id: [product.product_tmpl_id, product.display_name],
        product_id: [product.id, product.display_name],
        quantity: product.quantity,
        price_unit: parseFloat(product.price),
        ddpc_selected_option_value_ids: [x2ManyCommands.set(noVariantValueIds(product))],
    });
}

export class DdpcProductTemplateAutosaveField extends Many2OneField {
    setup() {
        super.setup();
        this.ddpcDialog = useService("dialog");
        this.ddpcOpeningConfigurator = false;
    }

    async updateRecord(value) {
        // Preserve the selected template before Odoo runs the invoice-line
        // onchange.  The line has no variant yet, so the computed/inverse
        // field can be cleared during that onchange.
        const productTemplateId = Array.isArray(value)
            ? value[0]
            : (value?.resId || value?.id || value);
        await super.updateRecord(value);
        if (productTemplateId && !this.ddpcOpeningConfigurator) {
            this._ddpcOpenConfigurator(productTemplateId);
        }
    }

    _ddpcOpenConfigurator(productTemplateId) {
        const lineRecord = this.props.record;
        const rootRecord = lineRecord.model.root;
        this.ddpcOpeningConfigurator = true;
        const line = lineRecord.data;
        const root = rootRecord.data;
        this.ddpcDialog.add(ProductConfiguratorDialog, {
            productTemplateId,
            ptavIds: [],
            customPtavs: [],
            quantity: line.quantity || 1,
            productUOMId: line.product_uom_id?.[0],
            companyId: root.company_id?.[0],
            currencyId: root.currency_id?.[0],
            soDate: root.invoice_date?.toISO?.() || new Date().toISOString(),
            save: async (mainProduct, optionalProducts) => {
                try {
                    await applyInvoiceProduct(lineRecord, mainProduct);
                    for (const product of optionalProducts) {
                        const optionalLine = await root.invoice_line_ids.addNewRecord({
                            position: "bottom",
                            mode: "readonly",
                        });
                        await applyInvoiceProduct(optionalLine, product);
                    }
                    await rootRecord.save();
                    root.invoice_line_ids.leaveEditMode();
                } finally {
                    this.ddpcOpeningConfigurator = false;
                }
            },
            discard: async () => {
                try {
                    await lineRecord.update({
                        ddpc_product_template_id: false,
                        product_id: false,
                    });
                } finally {
                    this.ddpcOpeningConfigurator = false;
                }
            },
        });
    }
}

export const ddpcProductTemplateAutosaveField = {
    ...many2OneField,
    component: DdpcProductTemplateAutosaveField,
};

registry
    .category("fields")
    .add("ddpc_product_template_autosave", ddpcProductTemplateAutosaveField);
