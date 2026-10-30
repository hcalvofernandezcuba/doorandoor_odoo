/* global window, document, fetch */
(function () {
    "use strict";
    const body = document.querySelector(".ddpc-display");
    const alert = document.querySelector("#ddpa-policy-alert");
    const link = document.querySelector("#ddpa-policy-link");
    const message = document.querySelector("#ddpa-policy-message");
    if (!body || !alert || !link || !message) { return; }

    function refreshPolicy() {
        fetch(body.dataset.url, {cache: "no-store"})
            .then((response) => response.ok ? response.json() : Promise.reject())
            .then((data) => {
                const policy = data.mode === "document" ? data.policy_acceptance : null;
                const pending = policy && !policy.accepted && policy.url;
                alert.classList.toggle("d-none", !pending);
                if (!pending) { return; }
                link.href = policy.url;
                message.textContent = policy.email
                    ? `Se envió el enlace a ${policy.email}. También puede aceptarlo ahora en esta pantalla.`
                    : "Este cliente no tiene email. Puede revisar y aceptar las políticas ahora en esta pantalla.";
            })
            .catch(() => alert.classList.add("d-none"));
    }
    refreshPolicy();
    window.setInterval(refreshPolicy, 1000);
}());
