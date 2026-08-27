/** @odoo-module **/

import { Component, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DdmhCameraBarcodeField extends Component {
    static template = "doorandoor_mobile_hanger.DdmhCameraBarcodeField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        autoAction: { type: String, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.reader = useRef("reader");
        this.state = useState({
            active: false,
            starting: false,
            error: "",
            status: "",
            inputValue: this.props.record.data[this.props.name] || "",
        });
        this.scanner = null;
        this.acceptingResult = false;
        onWillUnmount(() => void this.stopCamera());
    }

    get value() {
        return this.state.inputValue || "";
    }

    get readerId() {
        return `ddmh_reader_${String(this.props.record.id || "new").replace(/[^a-zA-Z0-9_-]/g, "_")}`;
    }

    async onInput(event) {
        this.state.inputValue = event.target.value;
        await this.props.record.update({ [this.props.name]: this.state.inputValue });
    }

    async startCamera() {
        if (this.state.active || this.state.starting) return;
        this.state.error = "";
        this.state.status = "";
        if (!window.isSecureContext) {
            this.state.error = "La cámara requiere una conexión HTTPS segura.";
            return;
        }
        if (!navigator.mediaDevices?.getUserMedia) {
            this.state.error = "Este navegador no permite acceder a la cámara.";
            return;
        }
        this.state.starting = true;
        this.state.active = true;
        this.acceptingResult = true;
        await Promise.resolve();
        await new Promise((resolve) => requestAnimationFrame(resolve));
        try {
            const library = window.__Html5QrcodeLibrary__;
            if (!library?.Html5Qrcode || !library?.Html5QrcodeSupportedFormats) {
                throw new Error("No se pudo cargar el lector móvil integrado.");
            }
            if (!this.reader.el?.id) {
                throw new Error("El área de lectura no está disponible.");
            }
            const formats = library.Html5QrcodeSupportedFormats;
            this.scanner = new library.Html5Qrcode(this.reader.el.id, {
                formatsToSupport: [formats.CODE_128, formats.QR_CODE],
                useBarCodeDetectorIfSupported: true,
                verbose: false,
            });
            await this.scanner.start(
                { facingMode: "environment" },
                {
                    fps: 10,
                    aspectRatio: 1.7777778,
                    disableFlip: true,
                    qrbox: (width, height) => ({
                        width: Math.max(240, Math.min(560, Math.floor(width * 0.92))),
                        height: Math.max(100, Math.min(220, Math.floor(height * 0.42))),
                    }),
                    videoConstraints: {
                        facingMode: { ideal: "environment" },
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                    },
                },
                (decodedText) => void this.onScanSuccess(decodedText),
                () => {},
            );
            try {
                const capabilities = this.scanner.getRunningTrackCapabilities?.() || {};
                const advanced = {};
                if (Array.isArray(capabilities.focusMode) && capabilities.focusMode.includes("continuous")) {
                    advanced.focusMode = "continuous";
                }
                if (capabilities.zoom?.max > capabilities.zoom?.min) {
                    advanced.zoom = Math.min(capabilities.zoom.max, Math.max(capabilities.zoom.min, 1.5));
                }
                if (Object.keys(advanced).length) {
                    await this.scanner.applyVideoConstraints({ advanced: [advanced] });
                }
            } catch {
                // Some Android camera drivers expose capabilities but reject
                // changing them. Scanning continues with their defaults.
            }
            this.state.status = "Acerque el Code128 al cuadro horizontal hasta verlo enfocado";
        } catch (error) {
            await this.stopCamera();
            if (error?.name === "NotAllowedError" || String(error).includes("Permission")) {
                this.state.error = "Permiso de cámara denegado. Autorice la cámara para este sitio.";
            } else if (error?.name === "NotFoundError") {
                this.state.error = "No se encontró una cámara disponible en el dispositivo.";
            } else {
                this.state.error = `No se pudo iniciar el lector: ${error?.message || error}`;
            }
        } finally {
            this.state.starting = false;
        }
    }

    async onScanSuccess(decodedText) {
        const value = (decodedText || "").trim();
        if (!value || !this.acceptingResult) return;
        this.acceptingResult = false;
        this.state.inputValue = value;
        await this.props.record.update({ [this.props.name]: value });
        await this.stopCamera();
        this.notification.add(`Código leído: ${value}`, {
            title: "Escaneo completado",
            type: "success",
        });
        await this._runAutoAction();
    }

    async registerTypedCode() {
        this.state.error = "";
        const value = this.state.inputValue.trim();
        if (!value) {
            this.state.error = "Escanee o escriba un barcode antes de registrarlo.";
            return;
        }
        await this.props.record.update({ [this.props.name]: value });
        await this._runAutoAction(value);
    }

    async _runAutoAction(explicitValue = null) {
        const method = this.props.autoAction;
        if (!method) return;
        const record = this.props.record;
        if (!record.resId) {
            this.state.error = "Guarde el registro antes de usar el escaneo automático.";
            return;
        }
        try {
            const scannedValue = (explicitValue || this.state.inputValue || "").trim();
            if (!scannedValue) {
                this.state.error = "No se recibió el código leído. Intente nuevamente.";
                return;
            }
            // Send the decoded barcode in the same RPC that records the count.
            // Saving the complete form first caused a mobile race where the
            // server action received an empty barcode_input.
            await this.orm.call(record.resModel, method, [[record.resId], scannedValue]);
            setTimeout(
                () => this.action.doAction({ type: "ir.actions.client", tag: "reload" }),
                0,
            );
        } catch (error) {
            this.state.error = error?.data?.message || error?.message || "No se pudo registrar la lectura.";
        }
    }

    async stopCamera() {
        this.acceptingResult = false;
        if (this.scanner) {
            try {
                if (this.scanner.isScanning) await this.scanner.stop();
                this.scanner.clear();
            } catch {
                // The camera can already be stopped during view destruction.
            }
            this.scanner = null;
        }
        this.state.active = false;
        this.state.status = "";
    }

}

registry.category("fields").add("ddmh_camera_barcode", {
    component: DdmhCameraBarcodeField,
    supportedTypes: ["char"],
    extractProps: ({ options }) => ({ autoAction: options.auto_action }),
});
