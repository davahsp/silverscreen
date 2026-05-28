(function () {
  "use strict";

  const MODES = ["default", "success", "warning", "danger", "neutral"];
  const HTMX_REQUEST_ATTRS = "[hx-get],[hx-post],[hx-put],[hx-patch],[hx-delete]";
  const GUARD = "ssConfirmPassed";

  const DEFAULTS = {
    mode: "default",
    title: "Konfirmasi",
    message: "Apakah Anda yakin?",
    confirmLabel: "Ya",
    cancelLabel: "Batal",
  };

  let root = null;
  let elements = null;
  let activeReject = null;
  let previousFocus = null;

  function normalizeMode(value) {
    const mode = String(value || "").trim().toLowerCase();
    return MODES.includes(mode) ? mode : DEFAULTS.mode;
  }

  // Reads the declarative data-confirm-* options off a triggering element.
  function optionsFromElement(el) {
    if (!el || !el.dataset) {
      return {};
    }
    const data = el.dataset;
    const options = {};
    if (data.confirmMode) options.mode = data.confirmMode;
    if (data.confirmTitle) options.title = data.confirmTitle;
    if (data.confirmMessage) options.message = data.confirmMessage;
    else if (data.confirm) options.message = data.confirm;
    if (data.confirmYes) options.confirmLabel = data.confirmYes;
    if (data.confirmNo) options.cancelLabel = data.confirmNo;
    return options;
  }

  function buildRoot() {
    if (root) {
      return;
    }
    root = document.createElement("div");
    root.className = "ss-confirm-backdrop";
    root.setAttribute("hidden", "");
    root.innerHTML =
      '<div class="ss-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="ss-confirm-title" aria-describedby="ss-confirm-message">' +
      '<div class="ss-confirm-stripe" aria-hidden="true"></div>' +
      '<div class="ss-confirm-body">' +
      '<h2 class="ss-confirm-title" id="ss-confirm-title"></h2>' +
      '<p class="ss-confirm-message" id="ss-confirm-message"></p>' +
      "</div>" +
      '<div class="ss-confirm-actions">' +
      '<button type="button" class="button button-secondary ss-confirm-cancel"></button>' +
      '<button type="button" class="button ss-confirm-accept"></button>' +
      "</div>" +
      "</div>";

    elements = {
      dialog: root.querySelector(".ss-confirm-dialog"),
      title: root.querySelector(".ss-confirm-title"),
      message: root.querySelector(".ss-confirm-message"),
      accept: root.querySelector(".ss-confirm-accept"),
      cancel: root.querySelector(".ss-confirm-cancel"),
    };

    elements.accept.addEventListener("click", function () {
      settle(true);
    });
    elements.cancel.addEventListener("click", function () {
      settle(false);
    });
    root.addEventListener("mousedown", function (event) {
      if (event.target === root) {
        settle(false);
      }
    });
    document.addEventListener("keydown", function (event) {
      if (root.hasAttribute("hidden")) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        settle(false);
      } else if (event.key === "Tab") {
        trapFocus(event);
      }
    });

    document.body.appendChild(root);
  }

  function trapFocus(event) {
    const focusable = [elements.cancel, elements.accept];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function open(rawOptions) {
    buildRoot();
    // Resolve any pending dialog as cancelled before opening a new one.
    if (activeReject) {
      settle(false);
    }

    const options = Object.assign({}, DEFAULTS, rawOptions || {});
    const mode = normalizeMode(options.mode);

    elements.dialog.setAttribute("data-mode", mode);
    elements.title.textContent = options.title;
    elements.message.textContent = options.message;
    elements.accept.textContent = options.confirmLabel;
    elements.cancel.textContent = options.cancelLabel;
    elements.accept.className = "button ss-confirm-accept button-" + acceptVariant(mode);

    previousFocus = document.activeElement;
    root.removeAttribute("hidden");
    // Force a reflow so the enter transition runs.
    void root.offsetWidth;
    root.classList.add("ss-confirm-open");
    window.requestAnimationFrame(function () {
      elements.accept.focus();
    });

    return new Promise(function (resolve) {
      activeReject = function (result) {
        resolve(result);
      };
    });
  }

  function acceptVariant(mode) {
    if (mode === "danger") return "danger";
    if (mode === "success") return "success";
    if (mode === "warning") return "warning";
    if (mode === "neutral") return "secondary";
    return "primary";
  }

  function settle(result) {
    if (!activeReject) {
      return;
    }
    const resolve = activeReject;
    activeReject = null;
    root.classList.remove("ss-confirm-open");
    root.setAttribute("hidden", "");
    if (previousFocus && typeof previousFocus.focus === "function") {
      previousFocus.focus();
    }
    previousFocus = null;
    resolve(result);
  }

  // ---- Declarative wiring -------------------------------------------------

  function triggerFor(el) {
    return el && el.closest ? el.closest("[data-confirm],[data-confirm-message]") : null;
  }

  function isHtmxElement(el) {
    return !!(el && el.matches && el.matches(HTMX_REQUEST_ATTRS));
  }

  // Restore any checkbox/radio toggles to their server-rendered state after a
  // cancelled confirmation (covers onchange-submit toggle switches).
  function revertControls(form) {
    if (!form) {
      return;
    }
    form.querySelectorAll("input[type=checkbox],input[type=radio]").forEach(function (input) {
      input.checked = input.defaultChecked;
    });
  }

  // A toggle may only need confirmation in one direction (e.g. deactivating).
  function gatePasses(trigger) {
    const when = trigger.dataset ? trigger.dataset.confirmWhen : null;
    if (!when) {
      return true;
    }
    const checkbox = trigger.matches("input[type=checkbox]")
      ? trigger
      : trigger.querySelector("input[type=checkbox]");
    if (!checkbox) {
      return true;
    }
    if (when === "checked") return checkbox.checked;
    if (when === "unchecked") return !checkbox.checked;
    return true;
  }

  function onSubmit(event) {
    const form = event.target;
    if (form[GUARD]) {
      form[GUARD] = false;
      return;
    }
    const trigger = triggerFor(form) || form.querySelector("[data-confirm],[data-confirm-message]");
    if (!trigger || isHtmxElement(form)) {
      return;
    }
    if (!gatePasses(trigger)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const submitter = event.submitter || null;
    open(optionsFromElement(trigger)).then(function (ok) {
      if (!ok) {
        revertControls(form);
        return;
      }
      form[GUARD] = true;
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit(submitter);
      } else {
        form.submit();
      }
    });
  }

  function onClick(event) {
    const link = event.target.closest ? event.target.closest("a[href]") : null;
    if (!link) {
      return;
    }
    const trigger = triggerFor(link);
    if (!trigger || trigger !== link || isHtmxElement(link)) {
      return;
    }
    if (link[GUARD]) {
      link[GUARD] = false;
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const href = link.href;
    const target = link.target;
    open(optionsFromElement(trigger)).then(function (ok) {
      if (!ok) {
        return;
      }
      if (target === "_blank") {
        window.open(href, "_blank");
      } else {
        window.location.assign(href);
      }
    });
  }

  // Toggle switches submit via inline onchange + form.submit(), which never
  // fires a submit event. Intercept in capture phase so we run before the
  // inline handler, and stop propagation to suppress it until confirmed.
  function onChange(event) {
    const el = event.target;
    if (!el.matches || !el.matches("input[type=checkbox][data-confirm],input[type=radio][data-confirm]")) {
      return;
    }
    if (!gatePasses(el)) {
      return;
    }
    event.stopPropagation();
    const form = el.form;
    open(optionsFromElement(el)).then(function (ok) {
      if (!ok) {
        el.checked = el.defaultChecked;
        return;
      }
      if (form) {
        // form.submit() bypasses the submit event, avoiding a second prompt.
        form.submit();
      }
    });
  }

  // HTMX fires htmx:confirm for every request; intercept only when the element
  // issuing the request opts in directly. Ancestor data-confirm (e.g. a form
  // wrapping unrelated hx-get controls) must not leak onto child requests.
  function onHtmxConfirm(event) {
    const detail = event.detail;
    const elt = detail.elt;
    const optedIn = elt && elt.hasAttribute &&
      (elt.hasAttribute("data-confirm") || elt.hasAttribute("data-confirm-message"));
    if (!optedIn) {
      return;
    }
    const trigger = elt;
    event.preventDefault();
    const options = optionsFromElement(trigger);
    if (!options.message && detail.question) {
      options.message = detail.question;
    }
    open(options).then(function (ok) {
      if (ok) {
        detail.issueRequest(true);
      }
    });
  }

  document.addEventListener("submit", onSubmit, true);
  document.addEventListener("change", onChange, true);
  document.addEventListener("click", onClick, true);
  document.body.addEventListener("htmx:confirm", onHtmxConfirm);

  window.SSConfirm = { open: open };
})();
