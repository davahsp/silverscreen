(function () {
  const wizard = document.querySelector("[data-showtime-wizard]");
  const dataNode = document.getElementById("scheduler-wizard-data");
  if (!wizard || !dataNode) return;

  const data = JSON.parse(dataNode.textContent);
  const fields = {
    movie: document.getElementById("id_movie"),
    studio: document.getElementById("id_studio"),
    startAt: document.getElementById("id_start_at"),
    price: document.getElementById("id_price"),
  };

  const state = {
    step: 1,
    movieId: fields.movie ? fields.movie.value : "",
    studioId: fields.studio ? fields.studio.value : "",
    date: data.today,
    startMin: null,
    calYear: Number(data.today.slice(0, 4)),
    calMonth: Number(data.today.slice(5, 7)) - 1,
    hoverStudioId: null,
    hoverMin: null,
  };

  if (fields.startAt && fields.startAt.value) {
    const startValue = fields.startAt.value;
    state.date = startValue.slice(0, 10) || state.date;
    state.startMin = timeToMinutes(startValue.slice(11, 16));
    state.calYear = Number(state.date.slice(0, 4));
    state.calMonth = Number(state.date.slice(5, 7)) - 1;
  }

  const monthNames = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
  ];
  const themeColors = {
    Drama: "#4c1d95",
    "Sci-Fi": "#1e3a8a",
    Horror: "#7f1d1d",
    Family: "#14532d",
    Documentary: "#713f12",
    Action: "#7c2d12",
    Romance: "#831843",
  };

  const stepButtons = Array.from(wizard.querySelectorAll("[data-step-target]"));
  const panels = Array.from(wizard.querySelectorAll("[data-step-panel]"));
  const calendarTitle = wizard.querySelector("[data-calendar-title]");
  const calendarGrid = wizard.querySelector("[data-calendar-grid]");
  const timelineRows = wizard.querySelector("[data-timeline-rows]");
  const summary = wizard.querySelector("[data-scheduler-summary]");
  const pastTimeMessage = wizard.querySelector("[data-past-time-message]");
  const submit = wizard.querySelector("[data-submit-showtime]");

  wizard.querySelectorAll(".scheduler-movie-card").forEach((card) => {
    const color = themeColors[card.dataset.theme] || "#1a1410";
    card.style.setProperty("--scheduler-movie-bg", color);
    card.addEventListener("click", () => {
      state.movieId = card.dataset.movieId;
      state.studioId = "";
      state.startMin = null;
      syncFields();
      setStep(2);
    });
  });

  wizard.querySelector("[data-calendar-prev]").addEventListener("click", () => {
    if (state.calMonth === 0) {
      state.calMonth = 11;
      state.calYear -= 1;
    } else {
      state.calMonth -= 1;
    }
    render();
  });

  wizard.querySelector("[data-calendar-next]").addEventListener("click", () => {
    if (state.calMonth === 11) {
      state.calMonth = 0;
      state.calYear += 1;
    } else {
      state.calMonth += 1;
    }
    render();
  });

  wizard.querySelectorAll("[data-change-step]").forEach((button) => {
    button.addEventListener("click", () => setStep(Number(button.dataset.changeStep)));
  });

  if (fields.price) {
    fields.price.addEventListener("input", updateConfirmMessage);
  }

  stepButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = Number(button.dataset.stepTarget);
      if (target === 2 && !currentMovie()) return;
      if (target === 3 && !currentMovie()) return;
      setStep(target);
    });
  });

  function setStep(step) {
    if (step > 1 && !currentMovie()) step = 1;
    state.step = step;
    render();
  }

  function currentMovie() {
    return data.movies.find((movie) => String(movie.id) === String(state.movieId));
  }

  function currentStudio() {
    return data.studios.find((studio) => String(studio.id) === String(state.studioId));
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function minutesToTime(minutes) {
    const normalized = ((minutes % 1440) + 1440) % 1440;
    return `${pad2(Math.floor(normalized / 60))}:${pad2(normalized % 60)}`;
  }

  function timeToMinutes(value) {
    if (!value || !value.includes(":")) return null;
    const parts = value.split(":").map(Number);
    return parts[0] * 60 + parts[1];
  }

  function rupiah(value) {
    return `Rp${Number(value || 0).toLocaleString("id-ID")}`;
  }

  function buildConfirmMessage() {
    const movie = currentMovie();
    const studio = currentStudio();
    if (!movie || !studio || state.startMin === null) {
      return "Jam tayang akan dibuat untuk slot yang dipilih. Pastikan film, studio, jam tayang, dan harga sudah benar.";
    }
    const endMin = state.startMin + movie.runtime_minutes;
    const price = fields.price && fields.price.value ? rupiah(fields.price.value) : "harga belum diisi";
    return [
      `Buat jam tayang ${movie.title}`,
      `di ${studio.name} (${studio.studio_type})`,
      `pada ${state.date} pukul ${minutesToTime(state.startMin)}-${minutesToTime(endMin)}`,
      `dengan harga tiket ${price}?`,
    ].join(" ");
  }

  function updateConfirmMessage() {
    wizard.dataset.confirmMessage = buildConfirmMessage();
  }

  function localDateKey(date) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  }

  function localMinutes(date) {
    return date.getHours() * 60 + date.getMinutes();
  }

  function isTodaySelected() {
    return state.date === data.now.slice(0, 10);
  }

  function isPastStart(startMin) {
    return isTodaySelected() && startMin < timeToMinutes(data.now.slice(11, 16));
  }

  function showtimeStartDate(showtime) {
    return new Date(showtime.start_at);
  }

  function showtimeEndDate(showtime) {
    return new Date(showtime.end_at);
  }

  function showtimesForTimeline(studioId) {
    return data.showtimes
      .filter((showtime) => String(showtime.studio_id) === String(studioId))
      .filter((showtime) => localDateKey(showtimeStartDate(showtime)) === state.date);
  }

  function hasConflict(studioId, startMin) {
    const movie = currentMovie();
    if (!movie || !studioId || startMin === null) return false;
    const start = new Date(`${state.date}T${minutesToTime(startMin)}:00`);
    const end = new Date(start.getTime() + movie.runtime_minutes * 60000);
    return data.showtimes
      .filter((showtime) => String(showtime.studio_id) === String(studioId))
      .some((showtime) => start < showtimeEndDate(showtime) && end > showtimeStartDate(showtime));
  }

  function syncFields() {
    if (fields.movie) fields.movie.value = state.movieId || "";
    if (fields.studio) fields.studio.value = state.studioId || "";
    if (fields.startAt) {
      fields.startAt.value = state.startMin === null ? "" : `${state.date}T${minutesToTime(state.startMin)}`;
    }
  }

  function selectDate(date) {
    state.date = date;
    state.calYear = Number(date.slice(0, 4));
    state.calMonth = Number(date.slice(5, 7)) - 1;
    state.studioId = "";
    state.startMin = null;
    hidePastTimeMessage();
    syncFields();
    setStep(3);
  }

  function selectTimelineSlot(studio, event) {
    const movie = currentMovie();
    if (!movie) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const raw = Math.round((pct * 1440) / 15) * 15;
    const startMin = Math.min(raw, Math.max(0, 1440 - movie.runtime_minutes));
    if (isPastStart(startMin)) {
      showPastTimeMessage();
      return;
    }
    hidePastTimeMessage();
    state.studioId = String(studio.id);
    state.startMin = startMin;
    if (fields.price && !fields.price.value) fields.price.value = studio.base_price;
    syncFields();
    render();
  }

  function showPastTimeMessage() {
    if (!pastTimeMessage) return;
    pastTimeMessage.hidden = false;
  }

  function hidePastTimeMessage() {
    if (!pastTimeMessage) return;
    pastTimeMessage.hidden = true;
  }

  function renderStepper() {
    stepButtons.forEach((button) => {
      const step = Number(button.dataset.stepTarget);
      button.classList.toggle("is-active", step === state.step);
      button.classList.toggle("is-complete", step < state.step);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-active", Number(panel.dataset.stepPanel) === state.step);
    });
  }

  function renderCalendar() {
    calendarTitle.textContent = `${monthNames[state.calMonth]} ${state.calYear}`;
    calendarGrid.innerHTML = "";
    const firstDay = (new Date(state.calYear, state.calMonth, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(state.calYear, state.calMonth + 1, 0).getDate();
    const prevDays = new Date(state.calYear, state.calMonth, 0).getDate();
    const items = [];
    for (let index = firstDay - 1; index >= 0; index -= 1) {
      items.push({ label: prevDays - index, current: false });
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      items.push({
        label: day,
        current: true,
        date: `${state.calYear}-${pad2(state.calMonth + 1)}-${pad2(day)}`,
      });
    }
    while (items.length % 7) items.push({ label: items.length, current: false });

    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = item.label;
      button.className = "scheduler-calendar-day";
      if (!item.current) button.classList.add("is-outside");
      if (item.date === data.today) button.classList.add("is-today");
      if (item.date === state.date) button.classList.add("is-selected");
      if (!item.current || item.date < data.today) {
        button.disabled = true;
      } else {
        button.addEventListener("click", () => selectDate(item.date));
      }
      calendarGrid.appendChild(button);
    });
  }

  function renderMovieSelection() {
    const movie = currentMovie();
    wizard.querySelectorAll(".scheduler-movie-card").forEach((card) => {
      card.classList.toggle("is-selected", String(card.dataset.movieId) === String(state.movieId));
    });
    const title = wizard.querySelector("[data-selected-movie-title]");
    const meta = wizard.querySelector("[data-selected-movie-meta]");
    const media = wizard.querySelector("[data-selected-movie-media]");
    const chip = wizard.querySelector("[data-chip-movie]");
    if (movie) {
      title.textContent = movie.title;
      meta.textContent = `${movie.theme} · ${movie.runtime_minutes} mnt · ${movie.age_rating_display}`;
      chip.textContent = movie.title;
      media.innerHTML = "";
      media.classList.toggle("has-image", Boolean(movie.main_picture_url));
      if (movie.main_picture_url) {
        const image = document.createElement("img");
        image.src = movie.main_picture_url;
        image.alt = "";
        media.appendChild(image);
      }
    } else {
      title.textContent = "Pilih film dahulu";
      meta.textContent = "";
      chip.textContent = "Film";
      media.innerHTML = "";
      media.classList.remove("has-image");
    }
    wizard.querySelector("[data-chip-date]").textContent = state.date;
  }

  function renderTimeline() {
    const movie = currentMovie();
    timelineRows.innerHTML = "";
    data.studios.forEach((studio) => {
      const row = document.createElement("div");
      row.className = "scheduler-timeline-row";

      const label = document.createElement("div");
      label.className = "scheduler-timeline-label";
      label.innerHTML = `<strong>${studio.name}</strong><span>${studio.studio_type} · ${rupiah(studio.base_price)}</span>`;

      const track = document.createElement("button");
      track.type = "button";
      track.className = "scheduler-timeline-track";
      if (String(studio.id) === String(state.studioId)) track.classList.add("is-selected");
      track.addEventListener("click", (event) => selectTimelineSlot(studio, event));
      track.addEventListener("mousemove", (event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        state.hoverStudioId = String(studio.id);
        state.hoverMin = Math.round((pct * 1440) / 15) * 15;
        renderTimeline();
      });
      track.addEventListener("mouseleave", () => {
        state.hoverStudioId = null;
        state.hoverMin = null;
        renderTimeline();
      });

      [3, 6, 9, 12, 15, 18, 21].forEach((hour) => {
        const line = document.createElement("i");
        line.className = "scheduler-hour-line";
        line.style.left = `${(hour / 24) * 100}%`;
        track.appendChild(line);
      });

      if (isTodaySelected()) {
        const past = document.createElement("span");
        past.className = "scheduler-past-zone";
        past.style.width = `${Math.min(100, (timeToMinutes(data.now.slice(11, 16)) / 1440) * 100)}%`;
        track.appendChild(past);
      }

      showtimesForTimeline(studio.id).forEach((showtime) => {
        const start = localMinutes(showtimeStartDate(showtime));
        const end = localMinutes(showtimeEndDate(showtime));
        const duration = Math.max(15, end >= start ? end - start : 1440 - start);
        const block = document.createElement("span");
        block.className = "scheduler-time-block is-booked";
        block.style.left = `${(start / 1440) * 100}%`;
        block.style.width = `${(duration / 1440) * 100}%`;
        block.textContent = showtime.movie_title;
        track.appendChild(block);
      });

      if (movie && state.hoverStudioId === String(studio.id) && String(state.studioId) !== String(studio.id)) {
        const hoverMin = Math.min(state.hoverMin, 1440 - movie.runtime_minutes);
        const ghost = document.createElement("span");
        ghost.className = "scheduler-time-block is-ghost";
        if (isPastStart(hoverMin)) ghost.classList.add("is-disabled");
        ghost.style.left = `${(hoverMin / 1440) * 100}%`;
        ghost.style.width = `${(movie.runtime_minutes / 1440) * 100}%`;
        track.appendChild(ghost);
      }

      if (movie && String(studio.id) === String(state.studioId) && state.startMin !== null) {
        const selected = document.createElement("span");
        selected.className = "scheduler-time-block is-new";
        if (hasConflict(studio.id, state.startMin)) selected.classList.add("is-conflict");
        selected.style.left = `${(state.startMin / 1440) * 100}%`;
        selected.style.width = `${(movie.runtime_minutes / 1440) * 100}%`;
        selected.textContent = `${minutesToTime(state.startMin)} - ${minutesToTime(state.startMin + movie.runtime_minutes)}`;
        track.appendChild(selected);
      }

      const capacity = document.createElement("div");
      capacity.className = "scheduler-timeline-capacity";
      capacity.innerHTML = `<strong>${studio.capacity}</strong><span>kursi</span>`;

      row.append(label, track, capacity);
      timelineRows.appendChild(row);
    });
  }

  function renderSummary() {
    const movie = currentMovie();
    const studio = currentStudio();
    const hasSelection = Boolean(movie && studio && state.startMin !== null);
    summary.hidden = !hasSelection;
    if (!hasSelection) {
      if (submit) submit.disabled = true;
      updateConfirmMessage();
      return;
    }

    const conflict = hasConflict(studio.id, state.startMin);
    const pastStart = isPastStart(state.startMin);
    const endMin = state.startMin + movie.runtime_minutes;
    wizard.querySelector("[data-summary-kicker]").textContent = `${studio.name} · ${studio.studio_type} · ${state.date}`;
    wizard.querySelector("[data-summary-start]").textContent = minutesToTime(state.startMin);
    wizard.querySelector("[data-summary-end]").textContent = minutesToTime(endMin);
    wizard.querySelector("[data-summary-meta]").textContent = `${movie.title} · ${movie.runtime_minutes} mnt · ${studio.capacity} kursi`;
    wizard.querySelector("[data-summary-conflict]").hidden = !conflict && !pastStart;
    wizard.querySelector("[data-summary-conflict]").textContent = pastStart
      ? "Jam mulai sudah lewat. Pilih slot yang masih tersedia."
      : "Waktu bertabrakan dengan showtime lain. Pilih slot kosong.";
    summary.classList.toggle("has-conflict", conflict || pastStart);
    if (submit) submit.disabled = conflict || pastStart;
    updateConfirmMessage();
  }

  function render() {
    renderStepper();
    renderCalendar();
    renderMovieSelection();
    renderTimeline();
    renderSummary();
  }

  syncFields();
  if (state.movieId && state.startMin !== null) state.step = 3;
  else if (state.movieId) state.step = 2;
  render();
})();
