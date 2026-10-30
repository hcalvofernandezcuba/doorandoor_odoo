/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const randomKey = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;

registry.category("services").add("server_monitor_user_tracker", {
    start() {
        let sessionKey = localStorage.getItem("dd_server_monitor_session");
        if (!sessionKey) {
            sessionKey = randomKey();
            localStorage.setItem("dd_server_monitor_session", sessionKey);
        }
        let tabKey = sessionStorage.getItem("dd_server_monitor_tab");
        if (!tabKey) {
            tabKey = randomKey();
            sessionStorage.setItem("dd_server_monitor_tab", tabKey);
        }
        const beat = () => rpc("/server_monitor/users/heartbeat", {
            session_key: sessionKey,
            tab_key: tabKey,
            path: `${window.location.pathname}${window.location.hash}`,
        }).catch(() => {});
        beat();
        const timer = window.setInterval(beat, 20000);
        return { stop: () => window.clearInterval(timer) };
    },
});
