(function () {
    "use strict";
    const root = document.querySelector(".ddcl-checkout"); if (!root) return;
    const error = document.getElementById("ddcl-card-error"), submit = document.getElementById("ddcl-submit"), form = document.getElementById("ddcl-payment-form");
    const fail = (message) => {
        const text = String(message || "");
        error.textContent = /(^|\s)402\s+Payment Required/i.test(text)
            ? "Tarjeta rechazada. No se realizó ningún cargo."
            : (text || "No fue posible validar la tarjeta.");
    };
    if (!window.Clover) { fail("No se pudo cargar el formulario seguro de Clover. Revise su conexión e inténtelo nuevamente."); return; }
    const clover = new window.Clover(root.dataset.publicToken, { merchantId: root.dataset.merchantId }), elements = clover.elements(), style = { input: { fontSize: "16px", color: "#1f2937" } };
    [["CARD_NUMBER", "#ddcl-card-number"], ["CARD_DATE", "#ddcl-card-date"], ["CARD_CVV", "#ddcl-card-cvv"], ["CARD_POSTAL_CODE", "#ddcl-card-postal"]].forEach(([type, selector]) => { const field = elements.create(type, style); field.mount(selector); field.addEventListener("change", (event) => { if (event && event.error) fail(event.error); }); });
    form.addEventListener("submit", async (event) => { event.preventDefault(); error.textContent = ""; submit.disabled = true; submit.textContent = "Procesando…"; try { const result = await clover.createToken(); if (result.errors || !result.token) { fail(Object.values(result.errors || {error: "Clover no pudo tokenizar la tarjeta."}).join(" ")); return; } const response = await fetch(root.dataset.chargeUrl || "/payment/clover/charge", { method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}, body: new URLSearchParams({operation_id: root.dataset.operationId, source: result.token, csrf_token: root.dataset.csrfToken}), credentials: "same-origin" }); const payload = await response.json(); if (!payload.ok) { fail(payload.error); return; } window.location.assign(payload.redirect_url || root.dataset.returnUrl); } catch (exception) { fail("No se pudo completar el cobro. No reintente si ve una operación en revisión."); } finally { submit.disabled = false; submit.textContent = "Cobrar con tarjeta"; } });
})();
