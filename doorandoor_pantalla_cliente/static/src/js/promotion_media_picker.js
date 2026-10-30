/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";

/**
 * Reuses Website's media-library dialog instead of accepting a local path in
 * the editable list.  The selected attachment is copied server-side into the
 * promotion binary field, which is what the public customer screen consumes.
 */
class PromotionMediaPicker extends Component {
    static template = xml`
        <div class="d-flex flex-column gap-2">
            <div class="text-muted" t-if="!props.record.resId">
                Guarde primero la promoción para seleccionar o subir el archivo.
            </div>
            <button class="btn btn-primary align-self-start" type="button"
                    t-att-disabled="!props.record.resId"
                    t-on-click="openMediaDialog">
                <i class="fa fa-folder-open me-1"/>
                <t t-if="props.record.data.media_type === 'video'">Seleccionar o subir video</t>
                <t t-else="">Seleccionar o subir imagen</t>
            </button>
            <div class="text-muted small">
                La biblioteca de Website guarda el archivo en Odoo; no se almacenan rutas del equipo.
            </div>
        </div>`;
    static props = { record: Object };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    _attachmentIdFromElement(element) {
        const source = element?.getAttribute(element?.tagName === "A" ? "href" : "src") || "";
        const match = source.match(/\/web\/(?:content|image)(?:\/ir\.attachment)?\/(\d+)/);
        return match && Number(match[1]);
    }

    openMediaDialog() {
        const record = this.props.record;
        if (!record.resId) {
            this.notification.add("Guarde primero la promoción.", { type: "warning" });
            return;
        }
        const mediaType = record.data.media_type || "image";
        this.dialog.add(MediaDialog, {
            resModel: record.resModel,
            resId: record.resId,
            onlyImages: mediaType === "image",
            noImages: mediaType === "video",
            noIcons: true,
            noVideos: true,
            noDocuments: mediaType === "image",
            save: async (element) => {
                const attachmentId = this._attachmentIdFromElement(element);
                if (!attachmentId) {
                    this.notification.add("No se pudo identificar el archivo seleccionado.", { type: "danger" });
                    return;
                }
                await this.orm.call(record.resModel, "ddpc_set_media_from_attachment", [
                    [record.resId], attachmentId, mediaType,
                ]);
                await record.load();
                this.notification.add("Archivo guardado en la promoción.", { type: "success" });
            },
        });
    }
}

registry.category("view_widgets").add("ddpc_promotion_media_picker", {
    component: PromotionMediaPicker,
});
