/* global window, document, fetch */
(function () {
    "use strict";
    const body = document.querySelector(".ddpc-display");
    if (!body) { return; }
    const escape = (value) => String(value || "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]));
    const money = (value, currency) => new Intl.NumberFormat("en-US", {style:"currency", currency: currency.name || "USD"}).format(value || 0);
    const percent = (value) => new Intl.NumberFormat("es-US", {maximumFractionDigits: 4}).format(Number(value || 0));
    let promotionKey = "", promotionIndex = 0, promotionNextAt = 0, promotionData = null, renderedPromotionKey = "";
    function renderPromotion(data) {
        promotionData = data;
        const promotions = document.querySelector("#ddpc-promotions");
        const list = data.promotions || [];
        const key = JSON.stringify(list.map((item) => [item.name, item.city, item.media_type, item.image, item.video, item.seconds, item.conditions]));
        if (!list.length) { promotions.innerHTML = '<div class="ddpc-empty">Gracias por su compra</div>'; renderedPromotionKey = "empty"; return; }
        if (key !== promotionKey) { promotionKey = key; promotionIndex = 0; promotionNextAt = 0; renderedPromotionKey = ""; }
        const now = Date.now();
        if (now >= promotionNextAt) {
            const promo = list[promotionIndex % list.length];
            promotionNextAt = now + Math.max(3, Number(promo.seconds || 10)) * 1000;
            promotionIndex = (promotionIndex + 1) % list.length;
        }
        const promo = list[(promotionIndex + list.length - 1) % list.length];
        const currentKey = `${key}:${promotionIndex}:${promo.city || "Door&Door"}`;
        // Do not rebuild a video element on each refresh: rebuilding restarts
        // playback and makes the customer see only its first frames.
        if (currentKey === renderedPromotionKey) { return; }
        renderedPromotionKey = currentKey;
        const media = promo.media_type === "video" && promo.video
            ? `<video autoplay muted playsinline loop><source src="data:${escape(promo.video_mimetype || 'video/mp4')};base64,${promo.video}"/></video>`
            : `<img src="data:image/png;base64,${promo.image}" alt="${escape(promo.name)}"/>`;
        promotions.innerHTML = `<article class="ddpc-promotion"><div class="ddpc-promotion-city">${escape(promo.city || 'Door&Door')}</div>${media}<div class="ddpc-promotion-copy"><h2>${escape(promo.name)}</h2>${promo.conditions ? `<p>${escape(promo.conditions)}</p>` : ""}</div></article>`;
    }
    function render(data) {
        const promotions = document.querySelector("#ddpc-promotions");
        if (data.mode === "promotion") {
            document.body.classList.add("ddpc-promotion-mode");
            promotions.classList.remove("d-none");
            renderPromotion(data);
            return;
        }
        document.body.classList.remove("ddpc-promotion-mode");
        promotions.classList.add("d-none");
        const currency = data.currency;
        document.querySelector("#ddpc-lines").innerHTML = data.lines.length ? data.lines.map((line) => `
            <article class="ddpc-line"><div class="ddpc-line-product">${line.image ? `<img src="data:image/png;base64,${line.image}" alt=""/>` : ""}<span>${escape(line.name)}</span></div><span>${line.quantity}</span><span>${money(line.unit_price, currency)}</span><span class="ddpc-line-total">${money(line.subtotal, currency)}</span></article>`).join("") : '<div class="ddpc-empty">Esperando productos…</div>';
        document.querySelector("#ddpc-last-product").innerHTML = data.last_product.name ? `${data.last_product.image ? `<img src="data:image/png;base64,${data.last_product.image}" alt=""/>` : ""}<div class="ddpc-last-product-name">${escape(data.last_product.name)}</div>` : '<div class="ddpc-empty">El último producto aparecerá aquí.</div>';
        const state = document.querySelector("#ddpc-payment-state"); state.textContent = data.payment_state.label; state.className = `ddpc-payment-state ${data.payment_state.code}`;
        document.querySelector("#ddpc-payment-detail").textContent = data.payment_state.detail || "";
        document.querySelector("#ddpc-untaxed").textContent = money(data.totals.untaxed, currency);
        document.querySelector("#ddpc-tax-label").textContent = data.totals.tax_rate ? `Impuesto sobre ventas (${percent(data.totals.tax_rate)}%)` : "Impuesto sobre ventas";
        document.querySelector("#ddpc-tax").textContent = money(data.totals.tax, currency);
        const partial = data.totals.payment_plan === "partial";
        document.body.classList.toggle("ddpc-partial-payment", partial);
        const paymentRow = document.querySelector("#ddpc-payment-due-row"); paymentRow.classList.toggle("d-none", !partial);
        document.querySelector("#ddpc-payment-due").textContent = money(data.totals.payment_due, currency);
        const feeRow = document.querySelector("#ddpc-fee-row"); feeRow.classList.toggle("d-none", !data.totals.fee);
        document.querySelector("#ddpc-fee-label").textContent = `Cargo por pago con tarjeta (${percent(data.totals.fee_rate)}%)`;
        document.querySelector("#ddpc-fee").textContent = money(data.totals.fee, currency);
        document.querySelector("#ddpc-total").textContent = money(data.totals.total, currency);
        const cardTotalRow = document.querySelector("#ddpc-card-total-row"); cardTotalRow.classList.toggle("d-none", !data.totals.fee);
        document.querySelector("#ddpc-card-total").textContent = money(data.totals.card_total, currency);
        const pendingRow = document.querySelector("#ddpc-payment-pending-row"); pendingRow.classList.toggle("d-none", !partial);
        document.querySelector("#ddpc-payment-pending").textContent = money(data.totals.payment_pending, currency);
    }
    function refresh() { fetch(body.dataset.url, {cache:"no-store"}).then((res) => { if (!res.ok) { throw new Error("expired"); } return res.json(); }).then(render).catch(() => { document.body.innerHTML = '<main class="ddpc-empty">Esta pantalla de cliente ya no está disponible.</main>'; }); }
    // Keep the customer display visually in step with persisted sale changes.
    // The POS-grade event channel will replace this compatibility polling path.
    refresh(); window.setInterval(refresh, 1000); window.setInterval(() => { if (document.body.classList.contains("ddpc-promotion-mode") && promotionData) { renderPromotion(promotionData); } }, 250);
}());
