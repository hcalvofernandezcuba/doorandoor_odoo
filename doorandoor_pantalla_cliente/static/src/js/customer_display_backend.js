/** @odoo-module **/

import { Component, onMounted, onWillUnmount, onWillUpdateProps, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

/*
 * This widget is deliberately injected only in account.move and sale.order
 * views.  It does not patch Odoo's global FormController, so Website and the
 * rest of the backend remain completely isolated from this integration.
 */
class CustomerDisplayLifecycle extends Component {
    static template = xml`<span class="d-none"/>`;
    // View widgets receive the form readonly state from Odoo automatically.
    // Declare it even though this lifecycle-only component does not use it;
    // otherwise Owl rejects the complete invoice/sale form at render time.
    static props = {
        record: Object,
        model: String,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        onMounted(() => this._notify("/pantalla-cliente/session/activate"));
        this._heartbeat = window.setInterval(() => this._notify("/pantalla-cliente/session/heartbeat"), 1000);
        onWillUpdateProps((nextProps) => {
            // Navigating with Odoo's previous/next arrows can keep the form
            // mounted.  Notify the persistent screen of that new record too.
            if (nextProps.record.resId && nextProps.record.resId !== this.props.record.resId) {
                this._notify("/pantalla-cliente/session/activate", nextProps);
            }
        });
        onWillUnmount(() => {
            window.clearInterval(this._heartbeat);
            if (!this.props.record.resId) {
                return;
            }
            this._notify("/pantalla-cliente/document/leave");
        });
    }

    _notify(url, props = this.props) {
        const { record, model } = props;
        fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ model, record_id: record.resId }),
        });
    }
}

registry.category("view_widgets").add("ddpc_customer_display_lifecycle", {
    component: CustomerDisplayLifecycle,
    extractProps: ({ attrs }) => ({ model: attrs.model }),
});
