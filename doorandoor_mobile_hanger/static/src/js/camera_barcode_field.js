/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DdmhCameraBarcodeField extends Component {
    static template = "doorandoor_mobile_hanger.DdmhCameraBarcodeField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        autoAction: { type: String, optional: true },
        continuous: { type: Boolean, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.reader = useRef("reader");
        this.input = useRef("input");
        this.state = useState({
            active: false,
            starting: false,
            error: "",
            status: "",
            inputValue: this.props.record.data[this.props.name] || "",
            busy: false,
            lastProduct: "",
            lastBarcode: "",
            lastQty: 0,
            totalScans: 0,
        });
        this.scanner = null;
        this.acceptingResult = false;
        this.cameraArmed = true;
        this.noCodeFrames = 0;
        this.lastCameraCode = "";
        this.hangerStartedAt = 0;
        this.hangerSubmitTimer = null;
        this.serverAttempted = false;
        this.focusTimers = [];
        onMounted(() => {
            if ((this.props.continuous || this.props.autoAction) && !this.props.readonly) {
                // A physical Hanger works as a keyboard wedge: without an
                // active input its shot never reaches OWL nor the server.
                // Odoo can move focus again while mounting the dialog, so
                // recover it after the initial render as well.
                requestAnimationFrame(() => this._focusScannerInput());
                this.focusTimers.push(setTimeout(() => this._focusScannerInput(), 250));
                this.focusTimers.push(setTimeout(() => this._focusScannerInput(), 800));
            }
        });
        onWillUnmount(() => {
            clearTimeout(this.hangerSubmitTimer);
            for (const timer of this.focusTimers) clearTimeout(timer);
            void this._logNoInputIfNeeded();
            void this.stopCamera();
        });
    }

    _focusScannerInput() {
        if (!this.props.readonly && this.input.el && document.activeElement !== this.input.el) {
            this.input.el.focus({ preventScroll: true });
        }
    }

    get value() {
        return this.state.inputValue || "";
    }

    get readerId() {
        return `ddmh_reader_${String(this.props.record.id || "new").replace(/[^a-zA-Z0-9_-]/g, "_")}`;
    }

    async onInput(event) {
        const previousValue = this.state.inputValue || "";
        const nextValue = event.target.value || "";
        const now = performance.now();
        this.state.inputValue = nextValue;
        if (!this.props.autoAction) {
            await this.props.record.update({ [this.props.name]: nextValue });
            return;
        }
        if (!nextValue || !nextValue.startsWith(previousValue)) {
            this.hangerStartedAt = now;
        } else if (!previousValue) {
            this.hangerStartedAt = now;
        }
        clearTimeout(this.hangerSubmitTimer);
        // Zebra/DataWedge can inject a complete barcode without emitting Enter.
        // A short, fast burst is a scanner shot; normal human typing remains manual.
        if (nextValue.trim().length >= 4) {
            this.hangerSubmitTimer = setTimeout(() => {
                const elapsed = performance.now() - this.hangerStartedAt;
                const isDocumentLauncher =
                    this.props.record.resModel === "doorandoor.hanger.document.scan";
                // Some Hanger keyboard wedges inject long document references
                // more slowly than product barcodes. On the dedicated document
                // launcher, the pause itself marks the end of the shot; do not
                // discard it because the complete injection exceeded 1.2 s.
                if ((isDocumentLauncher || this.props.continuous || elapsed <= 1200) && !this.state.busy) {
                    void this.registerTypedCode(nextValue);
                }
            }, this.props.record.resModel === "doorandoor.hanger.document.scan" ? 300 : 160);
        }
    }

    async onKeydown(event) {
        if (!["Enter", "Tab"].includes(event.key) && event.code !== "NumpadEnter") return;
        event.preventDefault();
        event.stopPropagation();
        await this.registerTypedCode(this.state.inputValue);
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
        this.cameraArmed = true;
        this.noCodeFrames = 0;
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
                () => {
                    this.noCodeFrames += 1;
                    if (this.noCodeFrames >= 3) this.cameraArmed = true;
                },
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
        if (!value || !this.acceptingResult || this.state.busy) return;
        if (this.props.continuous && value === this.lastCameraCode && !this.cameraArmed) return;
        this.lastCameraCode = value;
        this.cameraArmed = false;
        this.noCodeFrames = 0;
        if (this.props.continuous) {
            this.state.inputValue = value;
            const result = await this._runAutoAction(value);
            if (result) await this._showContinuousResult(result, value);
            return;
        }
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

    async registerTypedCode(explicitValue = null) {
        clearTimeout(this.hangerSubmitTimer);
        this.state.error = "";
        const value = (
            typeof explicitValue === "string" ? explicitValue : this.state.inputValue || ""
        ).trim();
        if (!value) {
            this.state.error = "Escanee o escriba un barcode antes de registrarlo.";
            return;
        }
        const result = await this._runAutoAction(value);
        if (this.props.continuous && result) {
            await this._showContinuousResult(result, value);
            requestAnimationFrame(() => this.input.el?.focus());
        }
    }

    async _showContinuousResult(result, fallbackBarcode) {
        this.state.lastProduct = result.product_name || "Producto registrado";
        this.state.lastBarcode = result.barcode || fallbackBarcode;
        this.state.lastQty = result.counted_qty ?? this.state.lastQty;
        this.state.totalScans += 1;
        const countComplete = Boolean(
            result.expected_qty && result.counted_qty >= result.expected_qty
        );
        this.state.status = countComplete
            ? "Conteo completo. Envíe la operación a validar."
            : "Lectura guardada. Listo para el siguiente disparo.";
        this.state.inputValue = "";
        if (this.input.el) this.input.el.value = "";
        await this.props.record.update({ [this.props.name]: false });
        if (countComplete && this.state.active) {
            await this.stopCamera();
            this.state.status = "Conteo completo. Envíe la operación a validar.";
        }
        // A positive physical acknowledgement must only happen after the
        // server accepted and persisted the reading. 80 ms was imperceptible
        // on several Android/Zebra devices, so use one clear confirmation.
        if (navigator.vibrate) navigator.vibrate(180);
    }

    async _runAutoAction(explicitValue = null) {
        const method = this.props.autoAction;
        if (!method) return;
        const record = this.props.record;
        if (this.state.busy) return null;
        this.state.busy = true;
        this.state.error = "";
        const scannedValue = (explicitValue || this.state.inputValue || "").trim();
        try {
            if (!scannedValue) {
                this.state.error = "No se recibió el código leído. Intente nuevamente.";
                return;
            }
            // Send the decoded barcode in the same RPC that records the count.
            // Saving the complete form first caused a mobile race where the
            // server action received an empty barcode_input.
            if (record.resModel === "doorandoor.hanger.document.scan") {
                const result = await this.orm.call(
                    record.resModel,
                    "ddmh_open_scanned_operation",
                    [scannedValue],
                );
                setTimeout(() => this.action.doAction(result), 0);
                return result || {};
            }
            const recordId = record.resId;
            if (!recordId) {
                this.state.error = "Guarde el registro antes de usar el escaneo automático.";
                return null;
            }
            this.serverAttempted = true;
            const result = await this.orm.call(
                record.resModel,
                method,
                [[recordId], scannedValue],
            );
            // Product reads return a compact count payload and remain on the
            // continuous receiver. A document read returns an Odoo action and
            // must navigate even while the same field is in continuous mode.
            if (result?.type) {
                setTimeout(() => this.action.doAction(result), 0);
            } else if (!this.props.continuous) {
                setTimeout(() => this.action.doAction(
                    { type: "ir.actions.client", tag: "reload" }
                ), 0);
            }
            return result || {};
        } catch (error) {
            this.state.error = error?.data?.message || error?.message || "No se pudo registrar la lectura.";
            const looksLikeDocument = (
                /^(https?:\/\/|DD-PICK-\d+$)/i.test(scannedValue)
                || scannedValue.includes("/")
            );
            if (
                ["ddsl.stock.receipt.scan.wizard", "inventory.count.session"].includes(record.resModel)
                && !looksLikeDocument
            ) {
                const picking = record.data.picking_id;
                const sourceId = record.resModel === "inventory.count.session"
                    ? record.resId
                    : picking?.resId || picking?.id || (Array.isArray(picking) ? picking[0] : picking);
                if (sourceId) {
                    try {
                        await this.orm.call(
                            "ddmh.hanger.scan.event",
                            record.resModel === "inventory.count.session"
                                ? "log_count_session_attempt"
                                : "log_client_attempt",
                            [sourceId, explicitValue || this.state.inputValue || "", "rejected", this.state.error],
                        );
                    } catch {
                        // Monitoring must never hide the original scan result.
                    }
                }
            }
            return null;
        } finally {
            this.state.busy = false;
        }
    }

    async _logNoInputIfNeeded() {
        const record = this.props.record;
        if (
            this.serverAttempted
            || !["ddsl.stock.receipt.scan.wizard", "inventory.count.session"].includes(record.resModel)
            || !record.resId
        ) return;
        const picking = record.data.picking_id;
        const sourceId = record.resModel === "inventory.count.session"
            ? record.resId
            : picking?.resId || picking?.id || (Array.isArray(picking) ? picking[0] : picking);
        if (!sourceId) return;
        try {
            await this.orm.call(
                "ddmh.hanger.scan.event",
                record.resModel === "inventory.count.session"
                    ? "log_count_session_attempt"
                    : "log_client_attempt",
                [sourceId, "", "no_input", "La pantalla se cerró sin recibir ninguna lectura del Hanger."],
            );
        } catch {
            // Monitoring must never block navigation away from the scanner.
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
    extractProps: ({ options }) => ({
        autoAction: options.auto_action,
        continuous: Boolean(options.continuous),
    }),
});
