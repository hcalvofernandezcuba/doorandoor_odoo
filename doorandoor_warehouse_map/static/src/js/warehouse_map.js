/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DoorAndDoorWarehouseMap extends Component {
    static template = "doorandoor_warehouse_map.WarehouseMap";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            warehouses: [],
            selectedWarehouseId: false,
            zones: [],
            summary: {},
            selected: null,
            viewMode: "classic",
            productQuery: "",
            productResults: [],
            productSearching: false,
            productSearchOpen: false,
        });
        this.productSearchTimer = null;
        this.productSearchRequest = 0;
        onWillStart(async () => {
            const params = this.props.action?.params || {};
            await this.loadMap(params.warehouse_id || false);
            if (params.label_code) {
                this.state.productQuery = params.label_code;
                await this.searchProducts();
                if (this.state.productResults.length) {
                    await this.locateProduct(this.state.productResults[0]);
                }
            }
        });
    }

    async loadMap(warehouseId = false) {
        this.state.loading = true;
        try {
            const payload = await this.orm.call(
                "inventory.serial.label.batch",
                "ddwm_map_payload",
                [warehouseId || false]
            );
            this.state.warehouses = payload.warehouses;
            this.state.selectedWarehouseId = payload.selected_warehouse_id;
            this.state.zones = payload.zones;
            this.state.summary = payload.summary;
            this.state.selected = null;
        } catch (error) {
            this.notification.add(
                error.message || "No fue posible cargar el mapa del almacén.",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    onWarehouseChange(event) {
        this.state.productResults = [];
        this.state.productSearchOpen = false;
        this.loadMap(Number(event.target.value));
    }

    onProductSearchInput(event) {
        const query = event.target.value;
        this.state.productQuery = query;
        clearTimeout(this.productSearchTimer);
        if (query.trim().length < 2) {
            this.state.productResults = [];
            this.state.productSearchOpen = false;
            this.state.productSearching = false;
            return;
        }
        this.state.productSearchOpen = true;
        this.productSearchTimer = setTimeout(() => this.searchProducts(), 250);
    }

    async searchProducts() {
        const query = this.state.productQuery.trim();
        if (query.length < 2) {
            return;
        }
        const requestId = ++this.productSearchRequest;
        this.state.productSearching = true;
        try {
            // The map search is deliberately scoped to the warehouse currently
            // displayed. Delivery workflows can reuse the backend method with
            // another explicit warehouse when their operation requires it.
            const results = await this.orm.call(
                "inventory.serial.label.batch",
                "ddwm_find_product_locations",
                [query, this.state.selectedWarehouseId, 30]
            );
            if (requestId === this.productSearchRequest) {
                this.state.productResults = results;
                this.state.productSearchOpen = true;
            }
        } catch (error) {
            this.notification.add(
                error.message || "No fue posible buscar el producto.",
                { type: "danger" }
            );
        } finally {
            if (requestId === this.productSearchRequest) {
                this.state.productSearching = false;
            }
        }
    }

    async locateProduct(result) {
        this.state.productSearchOpen = false;
        await this.loadMap(result.warehouse_id);
        let found = null;
        let foundZone = null;
        for (const zone of this.state.zones) {
            for (const quadrant of zone.horizontal_positions) {
                found = quadrant.items.find((item) => item.key === result.map_key);
                if (found) {
                    foundZone = zone.name;
                    break;
                }
            }
            if (found) {
                break;
            }
        }
        if (!found) {
            this.notification.add(
                "El producto existe, pero su posición no está disponible en el mapa.",
                { type: "warning" }
            );
            return;
        }
        this.state.selected = found;
        setTimeout(() => {
            let target = document.querySelector(
                `[data-ddwm-key="${result.map_key}"]`
            );
            if (!target && this.state.viewMode === "top") {
                target = Array.from(document.querySelectorAll("[data-ddwm-zone][data-ddwm-horizontal]"))
                    .find((element) => (
                        element.dataset.ddwmZone === foundZone
                        && element.dataset.ddwmHorizontal === found.horizontal_position
                    ));
            }
            target?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
            target?.focus({ preventScroll: true });
        }, 0);
    }

    selectPosition(item) {
        this.state.selected = item;
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    openBatch() {
        if (!this.state.selected?.batch_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "inventory.serial.label.batch",
            res_id: this.state.selected.batch_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openBatchMovements() {
        if (!this.state.selected?.batch_id) {
            return;
        }
        const action = await this.orm.call(
            "inventory.serial.label.batch",
            "action_ddwm_open_document_movements",
            [[this.state.selected.batch_id]]
        );
        await this.action.doAction(action);
    }

    openMovementDocument(document) {
        if (!document?.id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.picking",
            res_id: document.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPhysicalPosition() {
        if (!this.state.selected?.position_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "doorandoor.warehouse.map.position",
            res_id: this.state.selected.position_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSession() {
        if (!this.state.selected?.session_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "inventory.count.session",
            res_id: this.state.selected.session_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add(
    "doorandoor_warehouse_map.dashboard",
    DoorAndDoorWarehouseMap
);
