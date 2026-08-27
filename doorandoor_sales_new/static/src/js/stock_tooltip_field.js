/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DdsnStockTooltipField extends Component {
    static template = "doorandoor_sales_new.DdsnStockTooltipField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ open: false, loading: false, text: "" });
    }

    get fallbackText() {
        return this.props.record.data[this.props.name] || "Sin información de existencias";
    }

    async loadStock() {
        this.state.loading = true;
        this.state.text = this.fallbackText;
        const record = this.props.record;
        if (record.resId) {
            try {
                this.state.text = await this.orm.call(
                    record.resModel,
                    "ddsn_get_live_warehouse_stock_tooltip",
                    [[record.resId]]
                );
            } catch {
                this.state.text = this.fallbackText;
            }
        }
        this.state.loading = false;
        return this.state.text;
    }

    async onMouseEnter() {
        this.state.open = true;
        await this.loadStock();
    }

    onMouseLeave() {
        this.state.open = false;
    }

    async onClick() {
        const text = await this.loadStock();
        this.notification.add(text, {
            title: "Existencias por almacén",
            type: "info",
        });
    }
}

registry.category("fields").add("ddsn_stock_tooltip", {
    component: DdsnStockTooltipField,
    supportedTypes: ["char"],
});
