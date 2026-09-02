/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const ddpcRecordUpdateService = {
    dependencies: ["bus_service"],

    start(env, { bus_service: busService }) {
        let reloadTimer;
        busService.subscribe("record_update", (payload) => {
            if (payload.model !== "stock.picking") {
                return;
            }
            browser.clearTimeout(reloadTimer);
            reloadTimer = browser.setTimeout(() => browser.location.reload(), 1200);
        });
    },
};

registry.category("services").add("ddpc_record_update", ddpcRecordUpdateService);
