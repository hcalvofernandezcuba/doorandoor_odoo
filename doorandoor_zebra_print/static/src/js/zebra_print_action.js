/** @odoo-module **/

import { registry } from "@web/core/registry";

// Browser Print issues its local TLS certificate for `localhost`. Using the
// numeric loopback address causes a certificate-name mismatch on macOS.
const SERVICE_URLS = [
    "https://localhost:9101/",
    "https://127.0.0.1:9101/",
    "http://localhost:9100/",
    "http://127.0.0.1:9100/",
];

async function request(path, options = {}) {
    let lastError;
    for (const baseUrl of SERVICE_URLS) {
        if (window.location.protocol === "https:" && baseUrl.startsWith("http:")) {
            continue;
        }
        try {
            const response = await fetch(baseUrl + path, {
                cache: "no-store",
                ...options,
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response;
        } catch (error) {
            lastError = error;
        }
    }
    throw lastError || new Error("Zebra Browser Print no está disponible.");
}

async function getDefaultPrinter() {
    const response = await request("default?type=printer");
    const printer = await response.json();
    if (!printer || (!printer.uid && !printer.name)) {
        throw new Error("No existe una impresora Zebra predeterminada en este equipo.");
    }
    return printer;
}

async function sendToPrinter(printer, zpl) {
    await request("write", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: printer, data: zpl }),
    });
}

registry.category("actions").add("doorandoor_zebra_print.print", async (env, action) => {
    const params = action.params || {};
    try {
        const printer = await getDefaultPrinter();
        await sendToPrinter(printer, params.zpl || "");
        env.services.notification.add(
            `${params.label_count || 0} etiqueta(s) ${params.format_name || ""} enviada(s) a ${printer.name || "Zebra"}.`,
            { title: "Impresión Zebra aceptada", type: "success", sticky: false }
        );
    } catch (error) {
        env.services.notification.add(
            "No se pudo comunicar con Zebra Browser Print. Compruebe que esté instalado y abierto; después visite https://localhost:9101 y autorice su certificado local. Confirme también que la ZD421 sea el dispositivo predeterminado en Browser Print. " +
                (error.message || ""),
            { title: "Impresión Zebra no enviada", type: "danger", sticky: true }
        );
    }
    return { type: "ir.actions.act_window_close" };
});
