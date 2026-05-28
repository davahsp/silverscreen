(() => {
  const builders = document.querySelectorAll("[data-studio-layout]");
  if (!builders.length) return;

  const rowLabel = (index) => {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    let value = index + 1;
    let label = "";
    while (value > 0) {
      value -= 1;
      label = letters[value % letters.length] + label;
      value = Math.floor(value / letters.length);
    }
    return label;
  };

  builders.forEach((builder) => {
    const form = builder.closest("[data-studio-layout-form]");
    const grid = builder.querySelector("[data-seat-grid]");
    const rowsInput = form.querySelector("[data-layout-rows]");
    const colsInput = form.querySelector("[data-layout-cols]");
    const sizeDisplay = form.querySelector("[data-layout-size]");
    const capacityDisplay = form.querySelector("[data-layout-capacity]");
    if (!form || !grid || !rowsInput || !colsInput) return;

    const readState = () => {
      const rows = Math.max(parseInt(rowsInput.value, 10) || 10, 1);
      const cols = Math.max(parseInt(colsInput.value, 10) || 15, 1);
      const inputs = Array.from(grid.querySelectorAll("[data-seat-cell-input]"));
      return Array.from({ length: rows }, (_row, y) =>
        Array.from({ length: cols }, (_col, x) => inputs[y * cols + x]?.checked ?? true)
      );
    };

    let cells = readState();

    const updateSummary = () => {
      const rows = cells.length;
      const cols = cells[0]?.length || 0;
      const capacity = cells.flat().filter(Boolean).length;
      if (sizeDisplay) sizeDisplay.textContent = `${rows} x ${cols}`;
      if (capacityDisplay) capacityDisplay.textContent = String(capacity);
    };

    const render = () => {
      rowsInput.value = cells.length;
      colsInput.value = cells[0]?.length || 1;
      grid.style.setProperty("--studio-seat-cols", colsInput.value);
      grid.replaceChildren();

      const corner = document.createElement("span");
      corner.className = "studio-worksheet-corner";
      corner.setAttribute("aria-hidden", "true");
      grid.append(corner);

      cells[0].forEach((_checked, x) => {
        const button = document.createElement("button");
        button.className = "studio-delete-control studio-delete-col";
        button.type = "button";
        button.dataset.deleteCol = String(x);
        button.title = `Hapus kolom ${x + 1}`;
        button.setAttribute("aria-label", `Hapus kolom ${x + 1}`);
        button.disabled = cells[0].length <= 1;
        button.textContent = "x";
        grid.append(button);
      });

      cells.forEach((row, y) => {
        const rowButton = document.createElement("button");
        rowButton.className = "studio-delete-control studio-delete-row";
        rowButton.type = "button";
        rowButton.dataset.deleteRow = String(y);
        rowButton.title = `Hapus baris ${y + 1}`;
        rowButton.setAttribute("aria-label", `Hapus baris ${y + 1}`);
        rowButton.disabled = cells.length <= 1;
        rowButton.textContent = "x";
        grid.append(rowButton);

        row.forEach((checked, x) => {
          const input = document.createElement("input");
          input.type = "checkbox";
          input.name = "seat_cells";
          input.value = `${y},${x}`;
          input.checked = checked;
          input.dataset.seatCellInput = "";

          const labelText = document.createElement("span");
          labelText.className = "seat";
          labelText.dataset.seatCellLabel = "";
          labelText.textContent = `${rowLabel(y)}${x + 1}`;

          const choice = document.createElement("label");
          choice.className = "seat-choice studio-seat-choice";
          choice.dataset.seatCell = "";
          choice.append(input, labelText);
          grid.append(choice);
        });
      });
      updateSummary();
    };

    builder.addEventListener("click", (event) => {
      const rowButton = event.target.closest("[data-add-row]");
      const colButton = event.target.closest("[data-add-col]");
      const deleteRowButton = event.target.closest("[data-delete-row]");
      const deleteColButton = event.target.closest("[data-delete-col]");
      if (!rowButton && !colButton && !deleteRowButton && !deleteColButton) return;

      cells = readState();
      if (rowButton) {
        const newRow = Array.from({ length: cells[0]?.length || 1 }, () => true);
        if (rowButton.dataset.addRow === "start") {
          cells.unshift(newRow);
        } else {
          cells.push(newRow);
        }
      }
      if (colButton) {
        cells = cells.map((row) => {
          const nextRow = [...row];
          if (colButton.dataset.addCol === "start") {
            nextRow.unshift(true);
          } else {
            nextRow.push(true);
          }
          return nextRow;
        });
      }
      if (deleteRowButton && cells.length > 1) {
        cells.splice(Number(deleteRowButton.dataset.deleteRow), 1);
      }
      if (deleteColButton && cells[0]?.length > 1) {
        const colIndex = Number(deleteColButton.dataset.deleteCol);
        cells = cells.map((row) => row.filter((_checked, x) => x !== colIndex));
      }
      render();
    });

    grid.addEventListener("change", (event) => {
      if (!event.target.matches("[data-seat-cell-input]")) return;
      cells = readState();
      updateSummary();
    });

    form.addEventListener("submit", () => {
      cells = readState();
      render();
    });

    render();
  });
})();
