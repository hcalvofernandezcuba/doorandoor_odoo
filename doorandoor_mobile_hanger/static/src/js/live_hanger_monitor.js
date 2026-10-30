/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class DdmhLiveListController extends ListController {
    setup() {
        super.setup();
        this.busService = useService("bus_service");
        this.reloadTimer = null;
        this.onHangerEvent = () => {
            browser.clearTimeout(this.reloadTimer);
            this.reloadTimer = browser.setTimeout(() => this.model.load(), 150);
        };
        this.busService.subscribe("ddmh_hanger_event", this.onHangerEvent);
        onWillUnmount(() => {
            browser.clearTimeout(this.reloadTimer);
            this.busService.unsubscribe("ddmh_hanger_event", this.onHangerEvent);
        });
    }
}

class DdmhLiveFormController extends FormController {
    setup() {
        super.setup();
        this.busService = useService("bus_service");
        this.reloadTimer = null;
        this.onHangerEvent = (payload) => {
            const root = this.model.root;
            if (payload.source_model !== root.resModel || payload.source_res_id !== root.resId) {
                return;
            }
            browser.clearTimeout(this.reloadTimer);
            this.reloadTimer = browser.setTimeout(() => this.model.load(), 150);
        };
        this.busService.subscribe("ddmh_hanger_event", this.onHangerEvent);
        onWillUnmount(() => {
            browser.clearTimeout(this.reloadTimer);
            this.busService.unsubscribe("ddmh_hanger_event", this.onHangerEvent);
        });
    }
}

registry.category("views").add("ddmh_live_monitor_list", {
    ...listView,
    Controller: DdmhLiveListController,
});
registry.category("views").add("ddmh_live_monitor_form", {
    ...formView,
    Controller: DdmhLiveFormController,
});
