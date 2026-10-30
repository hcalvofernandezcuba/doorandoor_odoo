/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebsitePreview } from "@website/client_actions/website_preview/website_preview";

/*
 * Firefox can finish loading the main Website iframe before Odoo's hidden
 * fallback iframe has a contentDocument.  Odoo then tries to clear that
 * missing document and aborts the whole Website client action.  The fallback
 * is visual only, so ignoring this one transient cleanup race is safe.
 */
patch(WebsitePreview.prototype, {
    _onPageLoaded() {
        try {
            return super._onPageLoaded(...arguments);
        } catch (error) {
            const fallbackDocument = this.iframefallback.el?.contentDocument;
            const isFallbackRace = error instanceof TypeError
                && error.message.includes("replaceChildren")
                && !fallbackDocument;
            if (!isFallbackRace) {
                throw error;
            }
        }
    },
});
