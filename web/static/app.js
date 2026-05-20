// qrecog front-end. Vanilla JS, no framework.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const fmtMs = (ms) => {
  const s = ms / 1000;
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(2).padStart(5, "0")}`;
};
const fmtSec = (ms) => `${(ms / 1000).toFixed(2)} s`;
const escHtml = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------------------------------------------------------------------- state
const state = {
  reciters: [],
  selected: null,        // reciter id
  results: null,         // current loaded payload
  tab: "drifts",
  filter: "",
  evtSource: null,
  runActive: false,
  lastSeq: 0,
  audioPlayingRow: null, // DOM row currently playing
};

// ---------------------------------------------------------------------- API
const api = {
  reciters:   ()      => fetch("/api/reciters").then(r => r.json()),
  results:    (rid)   => fetch(`/api/reciters/${rid}/results`).then(r => r.json()),
  startRun:   (rid)   => fetch(`/api/reciters/${rid}/run`, { method: "POST" }).then(r => r.json()),
  runState:   (rid)   => fetch(`/api/reciters/${rid}/run/state`).then(r => r.json()),
  verse:      (rid, s, v) => fetch(`/api/reciters/${rid}/verse/${s}/${v}`).then(r => r.ok ? r.json() : null),
};
const verseCache = new Map();
const cachedVerse = async (rid, s, v) => {
  const key = `${rid}/${s}/${v}`;
  if (verseCache.has(key)) return verseCache.get(key);
  const data = await api.verse(rid, s, v);
  verseCache.set(key, data);
  return data;
};

// ============================================================== left rail
async function loadReciters() {
  state.reciters = await api.reciters();
  renderReciters();
  // auto-select the first cached reciter (or 161 if none cached)
  const def = state.reciters.find(r => r.has_diffs)
            ?? state.reciters.find(r => r.has_verify)
            ?? state.reciters[0];
  if (def) selectReciter(def.reciter_id);
}

function renderReciters() {
  const ul = $("#reciter-list");
  ul.innerHTML = "";
  for (const r of state.reciters) {
    const cached = r.has_diffs || r.has_verify;
    const li = document.createElement("li");
    li.className = "reciter";
    li.dataset.rid = r.reciter_id;
    li.dataset.cached = cached;
    if (state.selected === r.reciter_id) li.classList.add("active");
    li.innerHTML = `
      <span class="r-name">${escHtml(r.name)}</span>
      <span class="r-id">id ${r.reciter_id}</span>
      <span class="r-bar"><span style="width:${r.completeness_pct}%"></span></span>
      <span class="r-meta">
        <span>${r.has_diffs ? "✓ pipeline" : (r.has_verify ? "verify only" : "no cache")}</span>
        <span class="pct">${r.completeness_pct.toFixed(0)}%</span>
      </span>`;
    li.addEventListener("click", () => selectReciter(r.reciter_id));
    ul.appendChild(li);
  }
}

function selectReciter(rid) {
  state.selected = rid;
  $$(".reciter").forEach(el => el.classList.toggle("active",
    Number(el.dataset.rid) === rid));
  loadResults(rid);
  attachLogStream(rid);  // attach to existing run if any
}

// ============================================================== results
async function loadResults(rid) {
  const data = await api.results(rid);
  state.results = data;
  $("#empty-state").hidden = true;
  $("#headline").hidden = false;
  $("#resultswrap").hidden = false;
  $("#logwrap").hidden = false;
  renderHeadline(data);
  renderResults();
}

function renderHeadline(d) {
  $("#hl-name").textContent = d.reciter_name ?? "—";
  $("#hl-id").textContent   = `reciter id ${d.reciter_id}`;
  if (!d.cached) {
    $("#hl-shifts").textContent = "—";
    $("#hl-drifts").textContent = "—";
    $("#hl-surahs").textContent = "—";
    $("#hl-clean").textContent = "—";
    $("#count-shifts").textContent = 0;
    $("#count-drifts").textContent = 0;
    return;
  }
  $("#hl-shifts").textContent = d.headline.n_shifts;
  $("#hl-drifts").textContent = d.headline.n_drifts;
  $("#hl-surahs").textContent = d.headline.n_surahs_affected;
  $("#hl-clean").textContent  = d.headline.n_surahs_clean;
  $("#count-shifts").textContent = d.shifts.length;
  $("#count-drifts").textContent = d.drifts.length;
}

function severity(absMs) {
  if (absMs >= 1500) return 3;
  if (absMs >= 700)  return 2;
  if (absMs >= 300)  return 1;
  return 0;
}

function renderResults() {
  const r = state.results;
  const out = $("#results");
  out.innerHTML = "";
  if (!r || !r.cached) {
    out.innerHTML = `
      <div class="empty-inner" style="padding:36px;text-align:center">
        <p class="muted">No cached pipeline output for this reciter.<br />
        Press <b>Run analysis</b> to start a fresh end-to-end run.</p>
      </div>`;
    return;
  }
  const list = state.tab === "drifts" ? r.drifts : r.shifts;
  const f = state.filter.trim().toLowerCase();
  const filtered = !f ? list : list.filter(item => {
    const hay = `${item.surah}:${item.verse} ${item.surah_name}`.toLowerCase();
    return hay.includes(f);
  });
  if (!filtered.length) {
    out.innerHTML = `<div class="empty-inner" style="padding:36px;text-align:center">
      <p class="muted">No ${state.tab} match the current filter.</p></div>`;
    return;
  }
  const frag = document.createDocumentFragment();
  for (const item of filtered) {
    frag.appendChild(state.tab === "drifts" ? rowDrift(item) : rowShift(item));
  }
  out.appendChild(frag);
}

function rowDrift(d) {
  const wrap = document.createElement("div");
  wrap.className = "row-wrap";
  const dirClass = d.direction === "EARLY" ? "row-early" : "row-late";
  const row = document.createElement("div");
  row.className = `row ${dirClass}`;
  row.dataset.severity = severity(d.abs_delta_ms);
  row.innerHTML = `
    <span class="severity"></span>
    <div class="delta-cell">
      <span class="delta-num">${d.delta_ms > 0 ? "+" : ""}${fmtSec(d.delta_ms)}</span>
      <span class="delta-label">${d.direction}</span>
    </div>
    <div class="body">
      <div class="verseline">
        <span class="chev">▸</span>
        <a href="${d.verse_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">
          ${d.surah}:${d.verse}</a>
        <span class="surah-name">${escHtml(d.surah_name)}</span>
      </div>
      <div class="meta">
        old <b>${fmtMs(d.old_to_ms)}</b> → new <b>${fmtMs(d.new_to_ms)}</b>
        · ${d.direction === "EARLY"
          ? "API flips <b>before</b> voice ends"
          : "API flips <b>after</b> voice ends"}
      </div>
    </div>
    <div class="actions">
      <button class="iconbtn play" title="Play disputed span" ${!d.audio_url ? "disabled" : ""}>
        <svg class="ico"><use href="#ico-play" /></svg>
      </button>
      <a class="iconbtn" href="${d.verse_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Open on quran.com">
        <svg class="ico"><use href="#ico-link" /></svg>
      </a>
    </div>`;
  wrap.appendChild(row);
  const details = document.createElement("div");
  details.className = "row-details";
  wrap.appendChild(details);

  const ensureOpen = () => {
    if (wrap.classList.contains("open")) return;
    wrap.classList.add("open");
    row.querySelector(".chev").textContent = "▾";
    if (!details.dataset.loaded) {
      details.innerHTML = `<div class="loading">loading verse…</div>`;
      details.dataset.loaded = "loading";
      buildBoundaryReader(d).then(reader => {
        details.innerHTML = "";
        if (reader) details.appendChild(reader);
        else details.innerHTML = `<div class="loading muted">verse text not cached for this reciter</div>`;
        details.dataset.loaded = "1";
        if (state.audioPlayingRow === row) startHighlightLoop(details);
      });
    }
  };
  const toggle = () => {
    if (wrap.classList.contains("open")) {
      wrap.classList.remove("open");
      row.querySelector(".chev").textContent = "▸";
    } else {
      ensureOpen();
    }
  };
  row.querySelector(".body").addEventListener("click", toggle);
  row.querySelector(".play").addEventListener("click", (e) => {
    e.stopPropagation();
    ensureOpen();
    playSpan(d.audio_url, row, details);
  });
  return wrap;
}

function rowShift(s) {
  const wrap = document.createElement("div");
  wrap.className = "row-wrap";
  const row = document.createElement("div");
  row.className = "row row-shift";
  row.dataset.severity = s.best_sim >= 0.9 ? 3 : s.best_sim >= 0.8 ? 2 : 1;
  row.innerHTML = `
    <span class="severity"></span>
    <div class="delta-cell">
      <span class="delta-num">${s.offset > 0 ? "+" : ""}${s.offset}</span>
      <span class="delta-label">verse ${s.offset > 0 ? "ahead" : "behind"}</span>
    </div>
    <div class="body">
      <div class="verseline">
        <span class="chev">▸</span>
        <a href="${s.claimed_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">
          ${s.surah}:${s.verse}</a>
        <span class="surah-name">${escHtml(s.surah_name)}</span>
        <span class="muted">→ actually</span>
        <a href="${s.actual_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">
          ${s.surah}:${s.actual_verse}</a>
      </div>
      <div class="meta">
        sim vs claimed <b>${s.sim_self.toFixed(2)}</b> · vs actual <b>${s.best_sim.toFixed(2)}</b>
        · span ${fmtMs(s.api_from_ms)}–${fmtMs(s.api_to_ms)}
      </div>
      ${s.transcribed ? `<div class="arabic-line" title="${escHtml(s.transcribed)}">${escHtml(s.transcribed)}</div>` : ""}
    </div>
    <div class="actions">
      <button class="iconbtn play" title="Play disputed span" ${!s.audio_url ? "disabled" : ""}>
        <svg class="ico"><use href="#ico-play" /></svg>
      </button>
      <a class="iconbtn" href="${s.claimed_url}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Open claimed verse">
        <svg class="ico"><use href="#ico-link" /></svg>
      </a>
    </div>`;
  wrap.appendChild(row);
  const details = document.createElement("div");
  details.className = "row-details";
  wrap.appendChild(details);

  const ensureOpen = () => {
    if (wrap.classList.contains("open")) return;
    wrap.classList.add("open");
    row.querySelector(".chev").textContent = "▾";
    if (!details.dataset.loaded) {
      details.innerHTML = `<div class="loading">loading verses…</div>`;
      details.dataset.loaded = "loading";
      buildShiftReader(s).then(reader => {
        details.innerHTML = "";
        if (reader) details.appendChild(reader);
        else details.innerHTML = `<div class="loading muted">verse text not cached for this reciter</div>`;
        details.dataset.loaded = "1";
        if (state.audioPlayingRow === row) startHighlightLoop(details);
      });
    }
  };
  const toggle = () => {
    if (wrap.classList.contains("open")) {
      wrap.classList.remove("open");
      row.querySelector(".chev").textContent = "▸";
    } else {
      ensureOpen();
    }
  };
  row.querySelector(".body").addEventListener("click", toggle);
  row.querySelector(".play").addEventListener("click", (e) => {
    e.stopPropagation();
    ensureOpen();
    playSpan(s.audio_url, row, details);
  });
  return wrap;
}

// ============================================================== inline reader
// tone -> { badge symbol, badge text, badge class }
const TONE_BADGE = {
  "claimed":         { sym: "✗", text: "FAULTY annotation",     cls: "bad"  },
  "actual":          { sym: "✓", text: "CORRECTED annotation",  cls: "good" },
  "boundary-before": { sym: "↔", text: "boundary verse",        cls: "info" },
  "boundary-after":  { sym: "↔", text: "next verse",            cls: "info" },
};

function renderVerseCard(v, label, tone) {
  const card = document.createElement("div");
  card.className = `verse-card tone-${tone}`;
  card.dataset.surah = v.surah;
  card.dataset.verse = v.verse;
  const wordsHtml = v.words.map(w => {
    const ts = (w.start_ms != null) ? `data-from="${w.start_ms}" data-to="${w.end_ms}"` : "";
    return `<span class="w" ${ts}>${escHtml(w.text)}</span>`;
  }).join(" ");
  const trWords = v.translation ? v.translation.split(/\s+/).filter(Boolean) : [];
  const trHtml = trWords.length
    ? trWords.map(w => `<span class="tw">${escHtml(w)}</span>`).join(" ")
    : "";
  const b = TONE_BADGE[tone] || { sym: "·", text: "", cls: "info" };
  card.innerHTML = `
    <div class="verse-card-head">
      <span class="vc-badge badge-${b.cls}" title="${escHtml(b.text)}">
        <span class="vc-sym">${b.sym}</span>${escHtml(b.text)}
      </span>
      <span class="vc-key">${v.verse_key}</span>
      ${v.verse_from_ms != null ? `<span class="vc-time">${fmtMs(v.verse_from_ms)} – ${fmtMs(v.verse_to_ms)}</span>` : ""}
    </div>
    <div class="vc-sublabel">${escHtml(label)}</div>
    <div class="arabic">${wordsHtml}</div>
    ${trHtml ? `<div class="translation" title="English alignment is approximate (per-word translations not available from the API)">${trHtml}</div>` : ""}`;
  return card;
}

async function buildShiftReader(s) {
  const [claimed, actual] = await Promise.all([
    cachedVerse(state.selected, s.surah, s.verse),
    cachedVerse(state.selected, s.surah, s.actual_verse),
  ]);
  if (!claimed && !actual) return null;
  const wrap = document.createElement("div");
  wrap.className = "reader reader-shift";
  if (claimed) wrap.appendChild(renderVerseCard(claimed,
    `API claims verse ${s.surah}:${s.verse}`, "claimed"));
  if (actual)  wrap.appendChild(renderVerseCard(actual,
    `Audio actually contains ${s.surah}:${s.actual_verse}`, "actual"));
  const note = document.createElement("div");
  note.className = "reader-note";
  note.innerHTML = `<span class="muted">Press ▶ on the row to play the disputed span.
    The <span style="color:var(--rose)">rose-glowing</span> card is the
    <b>FAULTY</b> annotation the API currently serves; the
    <span style="color:var(--sage)">sage-glowing</span> card is the
    <b>CORRECTED</b> verse the audio actually contains. Watch which one
    tracks the recitation in real time.</span>`;
  wrap.appendChild(note);
  return wrap;
}

async function buildBoundaryReader(d) {
  // Show verse N and verse N+1; the boundary in question is between them.
  const [a, b] = await Promise.all([
    cachedVerse(state.selected, d.surah, d.verse),
    cachedVerse(state.selected, d.surah, d.verse + 1),
  ]);
  if (!a && !b) return null;
  const wrap = document.createElement("div");
  wrap.className = "reader reader-drift";
  if (a) wrap.appendChild(renderVerseCard(a,
    `Verse ${d.surah}:${d.verse} (boundary at end)`, "boundary-before"));
  if (b) wrap.appendChild(renderVerseCard(b,
    `Verse ${d.surah}:${d.verse + 1}`, "boundary-after"));
  const note = document.createElement("div");
  note.className = "reader-note";
  note.innerHTML = `<span class="muted">Old verse-end: <b>${fmtMs(d.old_to_ms)}</b>
    · New verse-end: <b>${fmtMs(d.new_to_ms)}</b> · drift <b>${d.delta_ms > 0 ? "+" : ""}${fmtSec(d.delta_ms)}</b>
    (${d.direction}). Press ▶ to hear ~3 s around the boundary; the active word
    lights up so you can see exactly where the API truncates.</span>`;
  wrap.appendChild(note);
  return wrap;
}

// ============================================================== audio
let _hlRaf = null;
function clearHighlights() {
  $$(".verse-card .w.active, .verse-card .tw.active").forEach(el => el.classList.remove("active"));
  $$(".verse-card .w.passed, .verse-card .tw.passed").forEach(el => el.classList.remove("passed"));
  $$(".verse-card.playing").forEach(el => el.classList.remove("playing"));
}
function startHighlightLoop(detailsRoot) {
  const audio = $("#audio");
  const cards = $$(".verse-card", detailsRoot);
  // Pre-build per-card data: arabic word ranges + translation word handles.
  const cardData = cards.map(card => ({
    card,
    arWords: $$(".w[data-from]", card).map(el => ({
      el, from: Number(el.dataset.from), to: Number(el.dataset.to),
    })),
    trWords: $$(".tw", card),
  }));
  cancelAnimationFrame(_hlRaf);
  const tick = () => {
    const tMs = audio.currentTime * 1000;
    for (const cd of cardData) {
      const ws = cd.arWords;
      if (!ws.length) { cd.card.classList.remove("playing"); continue; }
      let activeIdx = -1;
      for (let i = 0; i < ws.length; i++) {
        if (tMs >= ws[i].from && tMs < ws[i].to) { activeIdx = i; break; }
        if (tMs >= ws[i].from) activeIdx = i;
      }
      // Arabic: active = current word, passed = words before it.
      ws.forEach((w, i) => {
        const on   = i === activeIdx;
        const past = i < activeIdx;
        if (on   !== w.el.classList.contains("active")) w.el.classList.toggle("active", on);
        if (past !== w.el.classList.contains("passed")) w.el.classList.toggle("passed", past);
      });
      // English: proportional mapping from arabic word index -> translation index.
      // We highlight the slice of english words that *align* with the active arabic word.
      const tr = cd.trWords;
      if (tr.length && activeIdx >= 0) {
        const lo = Math.floor((activeIdx       / ws.length) * tr.length);
        const hi = Math.max(lo + 1,
                  Math.ceil(((activeIdx + 1) / ws.length) * tr.length));
        tr.forEach((el, i) => {
          const on   = i >= lo && i < hi;
          const past = i < lo;
          if (on   !== el.classList.contains("active")) el.classList.toggle("active", on);
          if (past !== el.classList.contains("passed")) el.classList.toggle("passed", past);
        });
      } else if (tr.length) {
        tr.forEach(el => el.classList.remove("active", "passed"));
      }
      cd.card.classList.toggle("playing", activeIdx >= 0);
    }
    if (!audio.paused) _hlRaf = requestAnimationFrame(tick);
  };
  _hlRaf = requestAnimationFrame(tick);
}

function playSpan(url, row, detailsRoot) {
  if (!url) { console.warn("playSpan: empty url"); return; }
  const audio = $("#audio");
  if (state.audioPlayingRow && state.audioPlayingRow !== row) {
    state.audioPlayingRow.querySelector(".play").classList.remove("playing");
  }
  cancelAnimationFrame(_hlRaf);
  clearHighlights();

  const m = url.match(/#t=([\d.]+),([\d.]+)$/);
  const base = m ? url.split("#")[0] : url;
  const start = m ? parseFloat(m[1]) : 0;
  const end   = m ? parseFloat(m[2]) : null;

  // Mark playing immediately so the user sees feedback.
  row.querySelector(".play").classList.add("playing");
  state.audioPlayingRow = row;

  // Remove any previous timeupdate stopper.
  if (state._stopper) {
    audio.removeEventListener("timeupdate", state._stopper);
    state._stopper = null;
  }

  const startPlayback = () => {
    try { audio.currentTime = start; } catch (e) { console.warn("seek failed", e); }
    audio.play().then(() => {
      if (detailsRoot) startHighlightLoop(detailsRoot);
    }).catch(err => {
      console.error("audio.play() rejected:", err);
      row.querySelector(".play").classList.remove("playing");
      state.audioPlayingRow = null;
    });
    if (end !== null) {
      const stopper = () => {
        if (audio.currentTime >= end) {
          audio.pause();
          row.querySelector(".play").classList.remove("playing");
          cancelAnimationFrame(_hlRaf);
          clearHighlights();
          audio.removeEventListener("timeupdate", stopper);
          state._stopper = null;
          if (state.audioPlayingRow === row) state.audioPlayingRow = null;
        }
      };
      state._stopper = stopper;
      audio.addEventListener("timeupdate", stopper);
    }
  };

  // If src already matches and we have metadata, start synchronously
  // (keeps the user-gesture chain alive on Chrome/Edge).
  if (audio.src === base && audio.readyState >= 1) {
    startPlayback();
  } else {
    audio.src = base;
    audio.addEventListener("loadedmetadata", startPlayback, { once: true });
    audio.addEventListener("error", function onErr() {
      console.error("audio failed to load:", audio.error);
      row.querySelector(".play").classList.remove("playing");
      state.audioPlayingRow = null;
      audio.removeEventListener("error", onErr);
    }, { once: true });
    audio.load();
  }
}

// ============================================================== tabs / filter
$$(".tab").forEach(t => t.addEventListener("click", () => {
  $$(".tab").forEach(x => x.classList.toggle("active", x === t));
  state.tab = t.dataset.tab;
  renderResults();
}));
$("#filter").addEventListener("input", (e) => {
  state.filter = e.target.value;
  renderResults();
});

// ============================================================== run + log
$("#btn-run").addEventListener("click", async () => {
  if (!state.selected) return;
  $("#btn-run").disabled = true;
  await api.startRun(state.selected);
  attachLogStream(state.selected);
  $("#btn-run").disabled = false;
});

function setRunStatus(label, cls) {
  const el = $("#run-status");
  el.textContent = label;
  el.className = `run-pill ${cls}`;
}

function attachLogStream(rid) {
  if (state.evtSource) {
    try { state.evtSource.close(); } catch {}
    state.evtSource = null;
  }
  $("#log").innerHTML = "";
  state.lastSeq = 0;
  setRunStatus("checking…", "idle");
  $("#progress-pill").hidden = true;

  // Probe state first to set initial pill
  api.runState(rid).then(s => {
    if (!s.exists) { setRunStatus("idle", "idle"); return; }
    if (s.running) setRunStatus("running", "running");
    else setRunStatus(s.return_code === 0 ? "ok" : "error",
                      s.return_code === 0 ? "ok" : "err");
  });

  const src = new EventSource(`/api/reciters/${rid}/stream`);
  state.evtSource = src;
  src.onmessage = (ev) => {
    const rec = JSON.parse(ev.data);
    state.lastSeq = rec.seq;
    appendLog(rec);
    setRunStatus("running", "running");
    maybeUpdateProgress(rec.line);
  };
  src.addEventListener("done", (ev) => {
    const d = JSON.parse(ev.data);
    setRunStatus(d.return_code === 0 ? "completed" : "error",
                 d.return_code === 0 ? "ok" : "err");
    src.close();
    // Refresh sidebar + results since cache may have grown
    loadReciters().then(() => {
      $$(".reciter").forEach(el => el.classList.toggle("active",
        Number(el.dataset.rid) === rid));
      loadResults(rid);
    });
  });
  src.addEventListener("idle", () => setRunStatus("idle", "idle"));
  src.onerror = () => { /* keep open; browser will retry */ };
}

function appendLog(rec) {
  const log = $("#log");
  const wasAtBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  const cls = /error|traceback|fail/i.test(rec.line) ? "lerr"
             : /surah|verse|saved|wrote|complete/i.test(rec.line) ? "lhi" : "";
  const line = document.createElement("div");
  line.innerHTML = `<span class="lseq">${String(rec.seq).padStart(4, "0")}</span><span class="${cls}">${escHtml(rec.line)}</span>`;
  log.appendChild(line);
  if (wasAtBottom) {
    log.scrollTop = log.scrollHeight;
    $("#btn-jump").hidden = true;
  } else {
    $("#btn-jump").hidden = false;
  }
}
$("#btn-jump").addEventListener("click", () => {
  $("#log").scrollTop = $("#log").scrollHeight;
  $("#btn-jump").hidden = true;
});

// Best-effort progress parser for lines like "[surah 12/114]" or
// "surah 12 done" -- updates the progress bar.
function maybeUpdateProgress(line) {
  const m = line.match(/surah\s*(\d+)\s*(?:\/|of)\s*(\d+)/i)
         || line.match(/\[(\d+)\s*\/\s*114\]/);
  if (!m) return;
  const cur = Number(m[1]), total = Number(m[2] || 114);
  const pct = Math.min(100, Math.round(100 * cur / total));
  $("#progress-pill").hidden = false;
  $("#progress-fill").style.width = `${pct}%`;
  $("#progress-text").textContent = `${cur}/${total}`;
}

// ============================================================== keyboard
document.addEventListener("keydown", (e) => {
  if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
  if (e.key === "/") { e.preventDefault(); $("#filter").focus(); return; }
  if (e.key === "r") { e.preventDefault(); $("#btn-run").click(); return; }
  if (e.key === "j" || e.key === "k") {
    e.preventDefault();
    const ids = state.reciters.map(r => r.reciter_id);
    if (!ids.length) return;
    const cur = ids.indexOf(state.selected);
    const next = e.key === "j"
      ? Math.min(ids.length - 1, cur + 1)
      : Math.max(0, cur - 1);
    selectReciter(ids[next]);
  }
});

// ============================================================== boot
loadReciters().catch(err => {
  console.error(err);
  document.body.innerHTML = `<pre style="color:#c97a3a;padding:24px">${escHtml(String(err))}</pre>`;
});
