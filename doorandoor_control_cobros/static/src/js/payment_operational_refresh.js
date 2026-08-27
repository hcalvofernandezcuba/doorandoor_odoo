/** @odoo-module **/

import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const CHANNEL = "doorandoor.payment.operations";
const INVOICE_POLL_INTERVAL = 10000;
const INVOICE_STATE_FIELDS = [
    "write_date",
    "payment_state",
    "amount_residual",
    "ddc_collection_state",
    "ddc_payment_review_state",
    "ddc_total_reported",
    "ddc_total_validated",
    "ddc_total_pending",
    "ddc_balance_pending",
    "ddc_last_manual_sync_at",
];
const DOCUMENT_ACTIONS_REQUIRING_RELOAD = new Set([
    "action_confirm",
    "action_draft",
    "action_ddsn_confirm_preinvoice",
    "action_ddsn_reset_preinvoice_draft",
    "action_post",
    "button_draft",
]);

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.ddcBusService = useService("bus_service");
        this.ddcNotification = useService("notification");
        this.ddcOrm = useService("orm");
        this.ddcRefreshInProgress = false;
        this.ddcRefreshQueued = false;
        this.ddcIsDestroyed = false;
        this.ddcInvoiceSignature = null;
        this.ddcPendingRefreshWarning = false;
        this.ddcPaymentUpdateCallback = this._ddcOnPaymentUpdate.bind(this);
        this.ddcBundleChangedCallback = this._ddcOnBundleChanged.bind(this);
        this.ddcVisibilityCallback = this._ddcOnPageVisible.bind(this);
        this.ddcBusService.addChannel(CHANNEL);
        this.ddcBusService.subscribe("doorandoor_payment_update", this.ddcPaymentUpdateCallback);
        this.ddcBusService.subscribe("bundle_changed", this.ddcBundleChangedCallback);
        this.ddcInitialPollTimer = setTimeout(() => this._ddcSafeCheckInvoiceState(), 2500);
        this.ddcPollTimer = setInterval(
            () => this._ddcSafeCheckInvoiceState(),
            INVOICE_POLL_INTERVAL
        );
        document.addEventListener("visibilitychange", this.ddcVisibilityCallback);
        window.addEventListener("focus", this.ddcVisibilityCallback);
        window.addEventListener("online", this.ddcVisibilityCallback);
        onWillUnmount(() => {
            this.ddcIsDestroyed = true;
            clearTimeout(this.ddcInitialPollTimer);
            clearInterval(this.ddcPollTimer);
            document.removeEventListener("visibilitychange", this.ddcVisibilityCallback);
            window.removeEventListener("focus", this.ddcVisibilityCallback);
            window.removeEventListener("online", this.ddcVisibilityCallback);
            this.ddcBusService.unsubscribe(
                "doorandoor_payment_update",
                this.ddcPaymentUpdateCallback
            );
            this.ddcBusService.unsubscribe("bundle_changed", this.ddcBundleChangedCallback);
        });
    },

    async _ddcOnBundleChanged() {
        if (this.ddcIsDestroyed || this.ddcBundleReloadScheduled) {
            return;
        }
        const dirty = await this.model?.root?.isDirty();
        if (this.ddcIsDestroyed) {
            return;
        }
        if (dirty) {
            this.ddcNotification.add(
                _t("Hay una actualización disponible. Guarde o descarte sus cambios; la pantalla se actualizará automáticamente después."),
                { title: _t("Actualización del sistema"), type: "warning", sticky: true }
            );
            return;
        }
        this.ddcBundleReloadScheduled = true;
        setTimeout(() => {
            if (!this.ddcIsDestroyed) {
                window.location.reload();
            }
        }, 1500 + Math.floor(Math.random() * 2500));
    },

    _ddcOnPageVisible() {
        if (document.visibilityState === "visible") {
            this._ddcSafeCheckInvoiceState();
        }
    },

    async _ddcSafeCheckInvoiceState() {
        try {
            await this._ddcCheckInvoiceState();
        } catch (error) {
            if (!this.ddcIsDestroyed && error?.message !== "Component is destroyed") {
                console.warn("DoorAndDoor: no se pudo comprobar el estado de la factura", error);
            }
        }
    },

    async _ddcReadInvoiceSignature() {
        const root = this.model?.root;
        if (root?.resModel !== "account.move" || !root.resId) {
            return null;
        }
        const [state] = await this.ddcOrm.read(
            "account.move",
            [root.resId],
            INVOICE_STATE_FIELDS
        );
        return state ? JSON.stringify(state) : null;
    },

    async _ddcCheckInvoiceState() {
        if (
            this.ddcIsDestroyed ||
            this.ddcRefreshInProgress ||
            document.visibilityState !== "visible"
        ) {
            return;
        }
        const signature = await this._ddcReadInvoiceSignature();
        if (this.ddcIsDestroyed || !signature) {
            return;
        }
        const firstCheck = this.ddcInvoiceSignature === null;
        if (!firstCheck && signature === this.ddcInvoiceSignature) {
            return;
        }
        const dirty = await this.model.root.isDirty();
        if (this.ddcIsDestroyed) {
            return;
        }
        if (dirty) {
            if (!this.ddcPendingRefreshWarning) {
                this.ddcPendingRefreshWarning = true;
                this.ddcNotification.add(
                    _t("La factura recibió información nueva. Guarde o descarte sus cambios para actualizarla."),
                    { title: _t("Pago actualizado"), type: "warning", sticky: true }
                );
            }
            return;
        }
        this.ddcRefreshInProgress = true;
        try {
            const reloaded = await this._ddcReloadModelIfAlive();
            if (reloaded) {
                this.ddcInvoiceSignature = signature;
                this.ddcPendingRefreshWarning = false;
            }
        } finally {
            if (!this.ddcIsDestroyed) {
                this.ddcRefreshInProgress = false;
            }
        }
    },

    _ddcPayloadMatchesCurrentRecord(payload) {
        const root = this.model?.root;
        if (!root?.resId || !root?.resModel) {
            return false;
        }
        const mapping = {
            "sale.order": payload.sale_order_ids || [],
            "account.move": payload.invoice_ids || [],
            "account.payment": payload.payment_ids || [],
            "doorandoor.cobro.control": payload.control_ids || [],
            "res.partner": payload.partner_ids || [],
            "doorandoor.customer.credit": payload.payment_ids || [],
        };
        return (mapping[root.resModel] || []).includes(root.resId);
    },

    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        if (this.ddcIsDestroyed) {
            return;
        }
        const root = this.model?.root;
        if (
            !root?.resId ||
            !["sale.order", "account.move"].includes(root.resModel) ||
            !DOCUMENT_ACTIONS_REQUIRING_RELOAD.has(clickParams.name)
        ) {
            return;
        }
        await this._ddcReloadModelIfAlive();
    },

    async _ddcReloadModelIfAlive() {
        if (this.ddcIsDestroyed) {
            return false;
        }
        try {
            await this.model.load();
            return !this.ddcIsDestroyed;
        } catch (error) {
            // Navigation can destroy the old form while an asynchronous load
            // is still resolving.  That lifecycle cancellation is expected;
            // every other error must remain visible to the operator.
            if (this.ddcIsDestroyed || error?.message === "Component is destroyed") {
                return false;
            }
            throw error;
        }
    },

    async _ddcOnPaymentUpdate(payload) {
        if (
            this.ddcIsDestroyed ||
            !this._ddcPayloadMatchesCurrentRecord(payload)
        ) {
            return;
        }
        if (this.ddcRefreshInProgress) {
            // A total payment can arrive while the partial-payment refresh is
            // still loading. Never discard that newer event: process it as
            // soon as the current render has finished.
            this.ddcRefreshQueued = true;
            return;
        }
        const dirty = await this.model.root.isDirty();
        if (this.ddcIsDestroyed) {
            return;
        }
        if (dirty) {
            this.ddcNotification.add(
                _t("Se recibió una actualización de pago. Guarde o descarte sus cambios para actualizar esta vista."),
                { title: payload.title || _t("Información actualizada"), type: "warning", sticky: true }
            );
            return;
        }
        this.ddcRefreshInProgress = true;
        try {
            const reloaded = await this._ddcReloadModelIfAlive();
            if (!reloaded) {
                return;
            }
            // Do not capture a second server signature here. The server could
            // already contain a newer payment than the data just rendered,
            // which would make the polling loop believe the stale view is
            // current. A null signature forces one cheap confirmation cycle.
            this.ddcInvoiceSignature = null;
            this.ddcPendingRefreshWarning = false;
            this.ddcNotification.add(payload.message || _t("La información fue actualizada."), {
                title: payload.title || _t("Información actualizada"),
                type: "success",
                sticky: false,
            });
        } finally {
            if (!this.ddcIsDestroyed) {
                this.ddcRefreshInProgress = false;
                if (this.ddcRefreshQueued) {
                    this.ddcRefreshQueued = false;
                    setTimeout(() => this._ddcSafeCheckInvoiceState(), 250);
                }
            }
        }
    },
});
