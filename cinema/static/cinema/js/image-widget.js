(function () {
  function findWidget(target) {
    return target.closest("[data-image-widget]");
  }

  function revokeObjectUrl(widget) {
    if (widget.dataset.objectUrl) {
      URL.revokeObjectURL(widget.dataset.objectUrl);
      delete widget.dataset.objectUrl;
    }
  }

  function setPreview(widget, filename, url, hasImage, emptyText) {
    const preview = widget.querySelector("[data-image-widget-preview]");
    const image = widget.querySelector("[data-image-widget-preview-image]");
    const previewEmpty = widget.querySelector("[data-image-widget-preview-empty]");
    const previewEmptyText = widget.querySelector("[data-image-widget-placeholder-text]");
    const empty = widget.querySelector("[data-image-widget-empty]");
    const file = widget.querySelector("[data-image-widget-file]");
    const filenameNode = widget.querySelector("[data-image-widget-filename]");
    const actionLabel = widget.querySelector("[data-image-widget-action-label]");
    const removeButton = widget.querySelector("[data-image-widget-remove]");

    if (filenameNode) filenameNode.textContent = filename || "";
    if (file) file.hidden = !filename;
    if (empty) {
      empty.hidden = Boolean(filename);
      if (emptyText) empty.textContent = emptyText;
    }
    if (preview) {
      preview.hidden = !hasImage && !filename;
      preview.classList.toggle("image-widget-stage-empty", !hasImage);
    }
    widget.classList.toggle("image-widget-has-image", hasImage);
    if (image) {
      image.hidden = !hasImage;
      image.src = hasImage ? url : "";
    }
    if (previewEmpty) {
      previewEmpty.hidden = hasImage;
    }
    if (previewEmptyText) {
      previewEmptyText.textContent = filename ? "No preview" : "Upload image";
    }
    if (actionLabel) actionLabel.textContent = filename ? "Ganti Gambar" : "Pilih Gambar";
    if (removeButton) removeButton.hidden = !filename;
  }

  function restoreInitial(widget) {
    const filename = widget.dataset.initialFilename || "";
    const url = widget.dataset.initialUrl || "";
    setPreview(widget, filename, url, Boolean(url), "None");
  }

  function showEmpty(widget) {
    setPreview(widget, "", "", false, "None");
  }

  document.addEventListener("change", function (event) {
    if (!event.target.matches("[data-image-widget-input]")) return;
    const input = event.target;
    const widget = findWidget(input);
    if (!widget) return;
    const clearInput = widget.querySelector("[data-image-widget-clear-input]");
    const file = input.files && input.files[0];
    if (clearInput) clearInput.checked = false;
    revokeObjectUrl(widget);
    if (!file) {
      restoreInitial(widget);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    widget.dataset.objectUrl = objectUrl;
    setPreview(widget, file.name, objectUrl, true, "None");
  });

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-image-widget-remove]");
    if (!button) return;
    const widget = findWidget(button);
    if (!widget) return;
    const input = widget.querySelector("[data-image-widget-input]");
    const clearInput = widget.querySelector("[data-image-widget-clear-input]");
    if (input) input.value = "";
    revokeObjectUrl(widget);
    if (widget.dataset.initialFilename && clearInput) {
      clearInput.checked = true;
    } else if (clearInput) {
      clearInput.checked = false;
    }
    showEmpty(widget);
  });
})();
