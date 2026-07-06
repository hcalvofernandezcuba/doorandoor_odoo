/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

const DEFAULT_INTERVAL_MS = 3000;
const HIDDEN_INTERVAL_MULTIPLIER = 4;

export class ServerMonitorWireGuard extends Component {
    static template = "server_monitor.WireGuardMonitor";

    setup() {
        this.state = useState({
            lastUpdated: "",
            error: null,
            isFetching: false,
            available: false,
            service_status: "unknown",
            command: "",
            warning: null,
            summary: {
                interfaces: 0,
                peers: 0,
                active_peers: 0,
                rx_bytes: 0,
                tx_bytes: 0,
            },
            interfaces: [],
            peers: [],
        });
        this.intervalMs = DEFAULT_INTERVAL_MS;
        this.hiddenIntervalMs = DEFAULT_INTERVAL_MS * HIDDEN_INTERVAL_MULTIPLIER;
        this.timer = null;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        onMounted(() => {
            this.fetchMetrics();
            this.setTimer(this.getEffectiveInterval());
            document.addEventListener("visibilitychange", this.handleVisibilityChange);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            document.removeEventListener("visibilitychange", this.handleVisibilityChange);
        });
    }

    async fetchMetrics() {
        if (this.state.isFetching) {
            return;
        }
        this.state.isFetching = true;
        try {
            const data = await rpc("/server_monitor/wireguard", {});
            this.clearError();
            this.updateMetrics(data || {});
        } catch {
            this.setError("Unable to fetch WireGuard metrics. Retrying...");
        } finally {
            this.state.isFetching = false;
        }
    }

    updateMetrics(data) {
        const timestamp = data.timestamp || Date.now() / 1000;
        this.state.lastUpdated = new Date(timestamp * 1000).toLocaleTimeString();
        this.state.available = Boolean(data.available);
        this.state.service_status = data.service_status || "unknown";
        this.state.command = data.command || "";
        this.state.warning = data.warning || null;
        this.state.summary = data.summary || this.state.summary;
        this.state.interfaces = data.interfaces || [];
        this.state.peers = data.peers || [];
    }

    setError(message) {
        this.state.error = { message };
    }

    clearError() {
        this.state.error = null;
    }

    setTimer(interval) {
        if (this.timer) {
            clearInterval(this.timer);
        }
        this.timer = setInterval(() => this.fetchMetrics(), interval);
    }

    getEffectiveInterval() {
        return document.hidden ? this.hiddenIntervalMs : this.intervalMs;
    }

    handleVisibilityChange() {
        this.setTimer(this.getEffectiveInterval());
    }

    formatBytes(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        const bytes = Number(value);
        if (!Number.isFinite(bytes)) {
            return "--";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let current = bytes;
        let index = 0;
        while (current >= 1024 && index < units.length - 1) {
            current /= 1024;
            index += 1;
        }
        return `${current.toFixed(current >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
    }

    formatTimestamp(value) {
        if (!value) {
            return "--";
        }
        return new Date(value * 1000).toLocaleString();
    }

    formatBoolean(value) {
        return value ? "Yes" : "No";
    }
}

registry.category("actions").add("server_monitor.wireguard", ServerMonitorWireGuard);
