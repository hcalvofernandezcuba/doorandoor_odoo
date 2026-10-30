/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

let leafletPromise;
function loadLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (leafletPromise) return leafletPromise;
    leafletPromise = new Promise((resolve, reject) => {
        if (!document.querySelector('link[data-ddcc-leaflet="1"]')) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
            link.integrity = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
            link.crossOrigin = "";
            link.dataset.ddccLeaflet = "1";
            document.head.appendChild(link);
        }
        const script = document.createElement("script");
        script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
        script.integrity = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
        script.crossOrigin = "";
        script.onload = () => resolve(window.L);
        script.onerror = () => reject(new Error("No fue posible cargar Leaflet."));
        document.head.appendChild(script);
    });
    return leafletPromise;
}

export class DoorAndDoorLoadRouteMap extends Component {
    static template = "doorandoor_cargas_control.RouteMap";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.mapRef = useRef("map");
        this.state = useState({ loading: true, routes: [], activeCount: 0, selectedId: false, headquarters: false });
        this.routeLayers = new Map();
        onWillStart(async () => {
            try {
                await Promise.all([loadLeaflet(), this.loadRoutes()]);
            } catch (error) {
                this.notification.add(error.message || "No fue posible cargar el mapa.", { type: "danger" });
            }
        });
        onMounted(() => this.renderMap());
        onWillUnmount(() => this.map?.remove());
    }

    async loadRoutes() {
        const payload = await this.orm.call("doorandoor.load.plan", "ddcc_route_map_payload", []);
        this.state.routes = payload.routes;
        this.state.activeCount = payload.active_count;
        this.state.headquarters = payload.headquarters;
        this.state.selectedId = payload.routes[0]?.id || false;
        this.state.loading = false;
    }

    get selectedRoute() {
        return this.state.routes.find((route) => route.id === this.state.selectedId);
    }

    color(route) {
        return { ready: "#f2c94c", loading: "#ef9b22", transit: "#18a558", incident: "#d9363e", completed: "#1769aa" }[route.color_key];
    }

    renderMap() {
        if (!window.L || !this.mapRef.el) return;
        const L = window.L;
        this.map = L.map(this.mapRef.el, { zoomControl: true, minZoom: 5 }).setView([27.8, -81.7], 6);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(this.map);
        this.map.fitBounds([[24.3, -87.7], [31.1, -79.8]], { padding: [12, 12] });

        if (this.state.headquarters) {
            const hq = this.state.headquarters;
            const icon = L.divIcon({ className: "ddcc_hq_marker", html: "<strong>HQ</strong>", iconSize: [38, 38], iconAnchor: [19, 19] });
            L.marker([hq.latitude, hq.longitude], { icon, zIndexOffset: 1000 })
                .bindPopup(`<strong>Oficina Central · Doral</strong><br/>${hq.warehouse}`)
                .addTo(this.map);
        }

        for (const route of this.state.routes) {
            const coordinates = route.points.map((point) => [point.latitude, point.longitude]);
            const group = L.featureGroup().addTo(this.map);
            const line = L.polyline(coordinates, { color: this.color(route), weight: route.id === this.state.selectedId ? 7 : 5, opacity: 0.9 }).addTo(group);
            line.bindTooltip(`${route.name} · ${route.state_label}`);
            route.points.forEach((point, index) => {
                const marker = L.circleMarker([point.latitude, point.longitude], {
                    radius: route.last_checkpoint_id === point.warehouse_id ? 10 : 7,
                    color: this.color(route), fillColor: point.exact ? "#ffffff" : "#dce7ef", fillOpacity: 1, weight: 3,
                }).addTo(group);
                const role = index === 0 ? "Origen" : `Parada ${index}`;
                marker.bindPopup(`<strong>${point.warehouse}</strong><br/>${role}<br/>${point.exact ? "Coordenada verificada" : "Coordenada provisional"}`);
                if (route.next_stop_id === point.warehouse_id) marker.setStyle({ color: "#ffd43b", weight: 6 });
            });
            this.routeLayers.set(route.id, group);
        }
        window.setTimeout(() => this.map.invalidateSize(), 0);
    }

    selectRoute(route) {
        this.state.selectedId = route.id;
        for (const [id, group] of this.routeLayers) {
            group.eachLayer((layer) => {
                if (layer.setStyle && layer instanceof window.L.Polyline) layer.setStyle({ weight: id === route.id ? 7 : 5 });
            });
        }
        const selected = this.routeLayers.get(route.id);
        if (selected) this.map.fitBounds(selected.getBounds(), { padding: [45, 45], maxZoom: 10 });
    }

    showFlorida() {
        this.map.fitBounds([[24.3, -87.7], [31.1, -79.8]], { padding: [12, 12] });
    }

    openPlan(route) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "doorandoor.load.plan", res_id: route.id, views: [[false, "form"]], target: "current" });
    }
}

registry.category("actions").add("doorandoor_cargas_control.route_map", DoorAndDoorLoadRouteMap);
