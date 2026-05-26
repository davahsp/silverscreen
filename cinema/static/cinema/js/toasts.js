(function () {
  const TOAST_EVENT = "ss:messages";
  const DEFAULT_TIMEOUT = 5000;
  const ERROR_TIMEOUT = 8000;

  function getRegion() {
    return document.querySelector("[data-toast-region]");
  }

  function normalizeMessages(payload) {
    if (Array.isArray(payload)) {
      return payload;
    }
    if (payload && Array.isArray(payload.messages)) {
      return payload.messages;
    }
    return [];
  }

  function levelClass(tags) {
    const tagList = String(tags || "").split(/\s+/);
    if (tagList.includes("error")) {
      return "error";
    }
    if (tagList.includes("warning")) {
      return "warning";
    }
    if (tagList.includes("success")) {
      return "success";
    }
    return "info";
  }

  function titleForVariant(variant) {
    if (variant === "success") {
      return "Berhasil";
    }
    if (variant === "error") {
      return "Gagal";
    }
    if (variant === "warning") {
      return "Peringatan";
    }
    return "Info";
  }

  function showToast(messageData) {
    const region = getRegion();
    if (!region || !messageData || !messageData.message) {
      return;
    }

    const variant = levelClass(messageData.tags);
    const toast = document.createElement("div");
    toast.className = `toast toast-${variant}`;
    toast.setAttribute("role", variant === "error" ? "alert" : "status");

    const stripe = document.createElement("div");
    stripe.className = "toast-stripe";
    stripe.setAttribute("aria-hidden", "true");

    const body = document.createElement("div");
    body.className = "toast-body";

    const title = document.createElement("div");
    title.className = "toast-title";
    title.textContent = messageData.title || titleForVariant(variant);

    const text = document.createElement("div");
    text.className = "toast-text";
    text.textContent = messageData.message;

    body.append(title, text);

    const close = document.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Tutup notifikasi");
    close.textContent = "x";
    close.addEventListener("click", function () {
      dismissToast(toast);
    });

    toast.append(stripe, body, close);
    region.appendChild(toast);

    window.setTimeout(function () {
      dismissToast(toast);
    }, variant === "error" ? ERROR_TIMEOUT : DEFAULT_TIMEOUT);
  }

  function dismissToast(toast) {
    if (!toast || toast.dataset.dismissed) {
      return;
    }
    toast.dataset.dismissed = "true";
    toast.classList.add("toast-exit");
    toast.addEventListener(
      "animationend",
      function () {
        toast.remove();
      },
      { once: true }
    );
  }

  function showMessages(payload) {
    normalizeMessages(payload).forEach(showToast);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const data = document.getElementById("django-messages-data");
    if (!data) {
      return;
    }
    try {
      showMessages(JSON.parse(data.textContent));
    } catch (error) {
      return;
    }
  });

  document.body.addEventListener(TOAST_EVENT, function (event) {
    showMessages(event.detail);
  });
})();
