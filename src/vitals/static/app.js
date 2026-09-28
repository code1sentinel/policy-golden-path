"use strict";

// All user and file content is rendered with textContent, never innerHTML.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const KIND_LABELS = {
  "control-statement": "Control statement",
  "implementation": "Implementation statement",
  "risk-statement": "Risk statement",
  "recommendation": "Recommendation",
  "identified-risk": "Identified risk",
};
const BADGE_LABELS = {
  "control-statement": "Control",
  "implementation": "Implementation",
  "risk-statement": "Risk",
  "recommendation": "Recommendation",
  "identified-risk": "Identified risk",
};
const TEXT_LABELS = {
  "control-statement": "Control statement",
  "implementation": "Implementation statement",
  "risk-statement": "Risk statement",
  "recommendation": "Recommendation",
  "identified-risk": "Identified risk",
};
const CRITERION_LABELS = {
  policy_intent: "Policy intent",
  root_cause: "Root cause",
};

const EXAMPLES = {
  "control-statement": {
    control_id: "ac-2", statement_id: "ac-2_smt.j",
    text: "The IAM team should review Okta accounts regularly.",
    requirement: "j. Review accounts for compliance with account management requirements [Assignment: frequency of account review];",
    policy_intent: "User access is reviewed at least every 90 days, and access no longer needed is removed within 5 business days.",
  },
  "implementation": {
    control_id: "ac-2", statement_id: "ac-2_smt.j",
    text: "Accounts are reviewed periodically as needed to make sure they are still appropriate.",
    requirement: "j. Review accounts for compliance with account management requirements [Assignment: frequency of account review];",
    policy_intent: "User access is reviewed at a frequency commensurate with the risk of the access, with privileged and payment access reviewed most often. Review records are retained for at least 12 months.",
  },
  "risk-statement": {
    control_id: "au-6", title: "Audit review gaps",
    text: "Audit logs are not always reviewed which could be a risk to the organization. The team should review logs more regularly.",
    requirement: "Review and analyze system audit records for indications of inappropriate or unusual activity.",
    likelihood: "", impact: "low",
  },
  "recommendation": {
    control_id: "ac-2", title: "Automate leaver deprovisioning",
    text: "Integrate Workday with Okta so that a termination disables the user's Okta account and removes the payment approver role automatically within 4 hours. Verify closure by re-sampling 60 accounts.",
    risk_statement: "14 of 60 sampled Okta accounts belonged to leavers because HR leaver notifications are processed manually by the IAM team.",
    risk: "high", owner: "IAM team lead", deadline: "",
  },
  "identified-risk": {
    title: "R-07 Ransomware",
    text: "Ransomware delivered by phishing could encrypt the finance file servers and their online backups, halting payments processing for several days.",
    treatments: "Backup policy: Critical systems are backed up at a frequency commensurate with their criticality.\nEmail security standard: Inbound email is filtered for malicious attachments and links, and staff complete phishing awareness training annually.\nAccess policy: User access is reviewed quarterly.",
    likelihood: "high", impact: "very high",
  },
};

const state = {
  files: [],        // {name, size, content}
  catalog: null,    // {name, content}
  policy: null,
  batch: null,      // last batch response
  guides: null,     // best-practice guides from /api/guides
};

const STATUS_LABELS = { "adopted": "Adopted", "partly": "Partly adopted", "not-yet": "Not yet adopted" };

// ---------------------------------------------------------------- helpers

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

const pct = (x) => `${Math.round(x * 100)}%`;
const human = (name) => CRITERION_LABELS[name] || name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, " ");
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const size = (bytes) => bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;

function bar(value, extra = "") {
  const b = el("span", { class: `bar ${extra}`.trim(), role: "img", "aria-label": `${pct(value)} confidence` });
  const fill = el("span", { class: "bar__fill" });
  fill.style.width = pct(Math.max(0, Math.min(1, value)));
  b.append(fill);
  return b;
}

function showError(message) {
  const box = $("#error");
  box.textContent = message || "";
  box.hidden = !message;
  if (message) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// ---------------------------------------------------------------- backends
//
// The same page runs in two ways. Served by `vitals-web`, it calls the local server.
// Built for GitHub Pages (data-mode="browser"), it runs Vitals's Python in the browser
// with Pyodide, so files are checked on this device and never uploaded.

const BROWSER = document.documentElement.dataset.mode === "browser";

const serverBackend = {
  async config() { return (await fetch("api/config")).json(); },
  async guides() { return (await fetch("api/guides")).json(); },
  async assess(body) {
    const res = await fetch("api/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let data = null;
    try { data = await res.json(); } catch { /* fall through */ }
    if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);
    return data;
  },
};

let python = null;  // a promise of Vitals's API running in Pyodide, started once

function startPython() {
  if (!python) {
    python = (async () => {
      const { loadPyodide } = await import("./pyodide/pyodide.mjs");
      const pyodide = await loadPyodide({ indexURL: new URL("pyodide/", location.href).href });
      const archive = await (await fetch("vitals.zip")).arrayBuffer();
      pyodide.unpackArchive(archive, "zip", { extractDir: "/home/pyodide/vitals-src" });
      pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/vitals-src')");
      return pyodide.pyimport("vitals.api");
    })();
    python.catch(() => { python = null; });  // allow a retry after a failed load
  }
  return python;
}

const browserBackend = {
  async config() { return (await fetch("config.json")).json(); },
  async guides() { return (await fetch("guides.json")).json(); },
  async assess(body) {
    const api = await startPython();
    pythonReady = true;
    const data = JSON.parse(api.handle(JSON.stringify(body)));
    if (data.error) throw new Error(data.error);
    return data;
  },
};

const backend = BROWSER ? browserBackend : serverBackend;

let pythonReady = false;

async function post(body) {
  if (BROWSER && !pythonReady) setLoading(true);
  try {
    return await backend.assess(body);
  } finally {
    setLoading(false);
  }
}

function setLoading(on) {
  const note = $("#loading");
  if (note) note.hidden = !on;
}

async function busy(button, label, work) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  showError("");
  try {
    await work();
  } catch (err) {
    showError(err.message);
  } finally {
    button.textContent = original;
    button.disabled = false;
    if (button.id === "batch-submit") updateBatchButton();
  }
}

// ---------------------------------------------------------------- tabs

function selectTab(tab) {
  for (const t of $$(".tab")) {
    const on = t === tab;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    $(`#${t.getAttribute("aria-controls")}`).hidden = !on;
  }
  try { localStorage.setItem("vitals-tab", tab.id); } catch { /* storage unavailable */ }
}

function initTabs() {
  const tabs = $$(".tab");
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      selectTab(next);
      next.focus();
    });
  });
  let saved = null;
  try { saved = localStorage.getItem("vitals-tab"); } catch { /* storage unavailable */ }
  if (saved && $(`#${saved}`)) selectTab($(`#${saved}`));
}

// ---------------------------------------------------------------- rendering an assessment

function guideFor(kind, name) {
  return state.guides?.guides?.[kind]?.practices?.[name] || null;
}

function statusPill(status) {
  return el("span", { class: `status status--${status}`, text: STATUS_LABELS[status] || status });
}

// The best-practice checklist: each criterion as a practice, with how to adopt it when it is not adopted yet.
function practiceList(criteria, kind) {
  if (!criteria.length) return el("p", { class: "none", text: "No best practices scored." });
  return el("ul", { class: "criteria" }, criteria.map((c) => {
    const guide = guideFor(kind, c.name);
    return el("li", { class: "criterion" },
      el("span", { class: "criterion__name" }, statusPill(c.status), el("span", { text: c.practice || human(c.name) })),
      bar(c.score),
      el("span", { class: "criterion__pct", text: pct(c.score) }),
      c.note ? el("span", { class: "criterion__note", text: c.note }) : null,
      guide && c.status !== "adopted"
        ? el("span", { class: "criterion__how" }, el("strong", { text: "How to adopt: " }), guide.how)
        : null,
    );
  }));
}

function adoptedLine(p) {
  return `${p.adopted} of ${plural(p.total, "best practice")} adopted` + (p.partly ? `, ${p.partly} partly` : "");
}

function improvementsList(items) {
  if (!items.length) return el("p", { class: "none", text: "No areas for improvement found." });
  return el("ul", { class: "improvements" }, items.map((i) => el("li", { text: i })));
}

function renderSingle(a) {
  const box = $("#single-result");
  box.replaceChildren(...[
    el("p", { class: "verdict__kind", text: KIND_LABELS[a.kind] }),
    el("p", { class: "verdict__score" },
      el("span", { class: "verdict__pct", text: pct(a.confidence) }),
      el("span", { class: "verdict__label", text: "confidence" })),
    bar(a.confidence, "bar--large"),
    el("p", { class: "verdict__practices", text: adoptedLine(a.practices) }),
    el("h3", { text: `Areas for improvement (${a.improvements.length})` }),
    improvementsList(a.improvements),
    a.treatments ? el("h3", { text: `Treatments (${a.treatments.length})` }) : null,
    a.treatments ? treatmentList(a.treatments) : null,
    a.fair_cam ? fairCamView(a.fair_cam) : null,
    el("h3", { text: "Best practices" }),
    practiceList(a.criteria, a.kind),
    el("p", { class: "rationale", text: a.rationale }),
  ].filter(Boolean));
}

// FAIR-CAM (prototype): which job each treatment does for the loss scenario. Shown alongside the score, not in it.
const FAIR_CAM_GROUPS = [
  ["Loss event controls", [["avoid", "Avoid"], ["deter", "Deter"], ["resist", "Resist"], ["detect", "Detect"],
    ["respond", "Respond"], ["limit", "Limit loss"]]],
  ["Variance management", [["variance", "Keep controls working"]]],
  ["Decision support", [["decision", "Policies and standards"]]],
];

function fairCamView(fc) {
  const groups = FAIR_CAM_GROUPS.map(([title, cells]) =>
    el("div", { class: "fc__group" },
      el("p", { class: "fc__title", text: title }),
      el("div", { class: "fc__cells" }, cells.map(([key, label]) => {
        const labels = fc.map[key] || [];
        return el("div", { class: `fc__cell${labels.length ? "" : " is-empty"}` },
          el("span", { class: "fc__name", text: label }),
          el("span", { class: "fc__items", text: labels.length ? labels.join(", ") : "none" }));
      }))));
  return el("section", { class: "fc", "aria-label": "FAIR-CAM view" },
    el("h3", {}, "FAIR-CAM view ", el("span", { class: "chip", text: "prototype" })),
    el("p", { class: "fc__lead", text: "What each treatment does for the loss scenario, after the FAIR Controls Analytics Model. Shown alongside the score, not part of it." }),
    ...groups,
    fc.gaps.length
      ? el("ul", { class: "improvements fc__gaps" }, fc.gaps.map((g) => el("li", { text: g })))
      : el("p", { class: "none", text: "No FAIR-CAM gaps found." }));
}

function treatmentList(items) {
  if (!items.length) return el("p", { class: "none", text: "No policy intent or control is linked to this risk." });
  return el("ul", { class: "treatments" }, items.map((t) =>
    el("li", { class: `treatment${t.relevant ? "" : " is-unlinked"}` },
      el("div", { class: "treatment__head" }, t.label,
        t.relevant ? t.types.map((k) => el("span", { class: "chip", text: k })) : el("span", { class: "chip", text: "no link found" })),
      el("div", { class: "treatment__why", text: [t.policy_intent, t.control_statement].filter(Boolean).join(" · ") }),
      t.relevant ? el("div", { class: "treatment__why", text: t.why }) : null)));
}

// ---------------------------------------------------------------- single input

function currentKind() {
  return $("input[name=kind]:checked").value;
}

function applyKind() {
  const kind = currentKind();
  $("#text-label").textContent = TEXT_LABELS[kind];
  for (const node of $$("[data-for]")) {
    node.hidden = !node.dataset.for.split(" ").includes(kind);
  }
}

function initSingle() {
  const form = $("#single-form");
  for (const r of $$("input[name=kind]")) r.addEventListener("change", applyKind);
  applyKind();

  form.addEventListener("reset", () => {
    setTimeout(() => {
      applyKind();
      $("#single-result").replaceChildren(el("p", { class: "placeholder", text: "Enter a statement and select Run health check." }));
      showError("");
    });
  });

  $("#single-example").addEventListener("click", () => {
    const kind = currentKind();
    for (const input of $$("input:not([type=radio]), textarea, select", form)) input.value = "";
    for (const [name, value] of Object.entries(EXAMPLES[kind])) {
      const field = form.elements.namedItem(name);
      if (field) field.value = value;
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const kind = currentKind();
    const item = { kind };
    for (const node of $$("input:not([type=radio]), textarea, select", form)) {
      const holder = node.closest("[data-for]");
      if (holder && holder.hidden) continue;  // only send fields that apply to this kind
      if (node.name && node.value.trim()) item[node.name] = node.value.trim();
    }
    if (!item.text) {
      showError(`Enter the ${TEXT_LABELS[kind].toLowerCase()} to assess.`);
      form.elements.namedItem("text").focus();
      return;
    }
    busy($("#single-submit"), "Checking…", async () => {
      const data = await post({ mode: "single", item });
      renderSingle(data.assessments[0]);
    });
  });
}

// ---------------------------------------------------------------- batch upload

const WORKBOOK = /\.xlsx$/i;

function toBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

// Text files are sent as text; an Excel workbook is binary, so it is sent base64-encoded.
async function readFile(file) {
  if (WORKBOOK.test(file.name)) {
    return { name: file.name, size: file.size, content_base64: toBase64(await file.arrayBuffer()) };
  }
  return { name: file.name, size: file.size, content: await file.text() };
}

function updateBatchButton() {
  const n = state.files.length;
  const btn = $("#batch-submit");
  btn.disabled = n === 0;
  btn.textContent = n ? `Check ${plural(n, "file")}` : "Run health check";
}

function renderFileList() {
  const list = $("#file-list");
  list.replaceChildren(...state.files.map((f, i) =>
    el("li", {},
      el("span", { class: "name", text: f.name, title: f.name }),
      el("span", { class: "size", text: size(f.size) }),
      (() => {
        const b = el("button", { type: "button", "aria-label": `Remove ${f.name}`, text: "×" });
        b.addEventListener("click", () => { state.files.splice(i, 1); renderFileList(); });
        return b;
      })())));
  updateBatchButton();
}

async function addFiles(fileList) {
  const accepted = Array.from(fileList).filter((f) => /\.(json|csv|xlsx)$/i.test(f.name));
  const skipped = fileList.length - accepted.length;
  for (const f of accepted) {
    const existing = state.files.findIndex((x) => x.name === f.name);
    const read = await readFile(f);
    if (existing >= 0) state.files[existing] = read; else state.files.push(read);
  }
  renderFileList();
  showError(skipped ? `${plural(skipped, "file")} skipped: only .csv, .xlsx and .json files can be assessed (save an old .xls workbook as .xlsx).` : "");
}

function renderTiles(summary) {
  const tiles = Object.entries(summary.by_kind).map(([kind, k]) =>
    el("div", { class: "tile" },
      el("p", { class: "tile__label", text: `${KIND_LABELS[kind]}s` }),
      el("p", { class: "tile__value" }, pct(k.average_confidence), el("small", { text: "average confidence" })),
      bar(k.average_confidence),
      el("p", { class: "tile__meta", text: `${plural(k.count, "item")}, ${k.practices_adopted} of ${k.practices_total} best practices adopted, ${k.with_improvements} with areas for improvement` })));
  $("#tiles").replaceChildren(...tiles);
}

function renderByFile(assessments) {
  const files = new Map();
  for (const a of assessments) {
    const f = files.get(a.file) || { items: 0, conf: 0, adopted: 0, total: 0, improving: 0 };
    f.items += 1;
    f.conf += a.confidence;
    f.adopted += a.practices.adopted;
    f.total += a.practices.total;
    f.improving += a.improvements.length ? 1 : 0;
    files.set(a.file, f);
  }
  $("#by-file").replaceChildren(...Array.from(files, ([name, f]) => {
    const avg = f.conf / f.items;
    const share = f.total ? f.adopted / f.total : 0;
    return el("tr", {},
      el("th", { scope: "row", text: name }),
      el("td", { text: String(f.items) }),
      el("td", {}, el("span", { class: "cell-score" }, bar(avg), el("span", { text: pct(avg) }))),
      el("td", {}, el("span", { class: "cell-score" }, bar(share), el("span", { text: `${f.adopted}/${f.total}` }))),
      el("td", { text: String(f.improving) }));
  }));
}

function renderFileStatus(files) {
  $("#file-status").replaceChildren(...files.map((f) =>
    el("li", { class: f.error ? "is-error" : "" },
      f.error ? `${f.name}: ${f.error}` : `${f.name}: ${plural(f.count, "item")} assessed`)));
}

function resultRow(a, index) {
  const node = $("#result-tpl").content.firstElementChild.cloneNode(true);
  const badge = $(".badge", node);
  badge.dataset.kind = a.kind;
  badge.textContent = BADGE_LABELS[a.kind];
  badge.title = KIND_LABELS[a.kind];
  $(".result__title", node).textContent = a.item;
  $(".result__title", node).title = a.item;
  $(".result__file", node).textContent = a.file;
  $(".bar__fill", node).style.width = pct(a.confidence);
  $(".bar", node).setAttribute("aria-label", `${pct(a.confidence)} confidence`);
  $(".score__pct", node).textContent = pct(a.confidence);
  $(".result__count", node).textContent = `${a.practices.adopted}/${a.practices.total} adopted`
    + (a.improvements.length ? ` · ${a.improvements.length} to improve` : "");

  // Build the details only when first opened: large batches stay fast.
  node.addEventListener("toggle", () => {
    const body = $(".result__body", node);
    if (!node.open || body.childElementCount) return;
    body.append(
      el("div", {}, el("h3", { text: "Areas for improvement" }), improvementsList(a.improvements)),
      el("div", {}, el("h3", { text: "Best practices" }), practiceList(a.criteria, a.kind)),
      a.treatments ? el("div", { class: "full" }, el("h3", { text: "Treatments" }), treatmentList(a.treatments)) : null,
      a.fair_cam ? el("div", { class: "full" }, fairCamView(a.fair_cam)) : null,
      el("div", { class: "full" }, el("h3", { text: "Text assessed" }), el("pre", { class: "quote", text: a.text || "(empty)" })),
      el("p", { class: "rationale full", text: a.rationale }),
    );
  });
  node.dataset.index = index;
  return node;
}

function renderResults() {
  const data = state.batch;
  if (!data) return;
  const kind = $("#filter-kind").value;
  const q = $("#filter-text").value.trim().toLowerCase();
  const sort = $("#sort").value;

  let rows = data.assessments.map((a, i) => ({ a, i }));
  if (kind) rows = rows.filter(({ a }) => a.kind === kind);
  if (q) rows = rows.filter(({ a }) =>
    [a.item, a.file, a.control_id, a.title, a.text].some((v) => v && String(v).toLowerCase().includes(q)));
  const by = {
    doc: (x, y) => x.i - y.i,
    low: (x, y) => x.a.confidence - y.a.confidence || x.i - y.i,
    high: (x, y) => y.a.confidence - x.a.confidence || x.i - y.i,
    most: (x, y) => y.a.improvements.length - x.a.improvements.length || x.i - y.i,
  }[sort];
  rows.sort(by);

  $("#shown").textContent = `Showing ${rows.length} of ${plural(data.assessments.length, "item")}.`;
  $("#results").replaceChildren(...rows.map(({ a, i }) => resultRow(a, i)));
}

function renderBatch(data) {
  state.batch = data;
  $("#batch-results").hidden = false;
  renderFileStatus(data.files);
  renderTiles(data.summary);
  renderByFile(data.assessments);
  const kinds = Object.keys(data.summary.by_kind);
  $("#filter-kind").replaceChildren(
    el("option", { value: "", text: "All kinds" }),
    ...kinds.map((k) => el("option", { value: k, text: `${KIND_LABELS[k]}s` })));
  renderResults();
  $("#batch-results").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- downloads

function csvCell(value) {
  let s = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;  // stop spreadsheets treating text as a formula
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(assessments) {
  const header = ["file", "kind", "item", "control_id", "confidence", "practices_adopted", "practices_total",
    "improvement_count", "improvements", "rationale", "text"];
  const lines = [header.join(",")];
  for (const a of assessments) {
    lines.push([a.file, a.kind, a.item, a.control_id, Math.round(a.confidence * 100), a.practices.adopted,
      a.practices.total, a.improvements.length,
      a.improvements.join(" | "), a.rationale, a.text].map(csvCell).join(","));
  }
  return lines.join("\r\n") + "\r\n";
}

function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------------------------------------------------------- batch wiring

function initBatch() {
  const drop = $("#drop");
  const input = $("#batch-files");
  input.addEventListener("change", async () => { await addFiles(input.files); input.value = ""; });
  for (const ev of ["dragenter", "dragover"]) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("is-over"); });
  for (const ev of ["dragleave", "drop"]) drop.addEventListener(ev, () => drop.classList.remove("is-over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); addFiles(e.dataTransfer.files); });

  $("#batch-catalog").addEventListener("change", async (e) => {
    state.catalog = e.target.files[0] ? await readFile(e.target.files[0]) : null;
  });
  $("#batch-policy").addEventListener("change", async (e) => {
    state.policy = e.target.files[0] ? await readFile(e.target.files[0]) : null;
  });

  $("#batch-submit").addEventListener("click", (e) => {
    busy(e.currentTarget, "Checking…", async () => {
      const strip = (f) => f && (f.content_base64 !== undefined
        ? { name: f.name, content_base64: f.content_base64 }
        : { name: f.name, content: f.content });
      const data = await post({
        mode: "batch",
        documents: state.files.map(strip),
        catalog: strip(state.catalog),
        policy: strip(state.policy),
      });
      renderBatch(data);
    });
  });

  for (const id of ["#filter-kind", "#sort"]) $(id).addEventListener("change", renderResults);
  $("#filter-text").addEventListener("input", renderResults);

  for (const b of $$("[data-download]")) {
    b.addEventListener("click", () => {
      const data = state.batch;
      if (!data) return;
      const stamp = new Date().toISOString().slice(0, 10);
      const kind = b.dataset.download;
      if (kind === "csv") download(`vitals-${stamp}.csv`, toCsv(data.assessments), "text/csv");
      if (kind === "json") download(`vitals-${stamp}.json`, JSON.stringify(
        { summary: data.summary, files: data.files, assessments: data.assessments }, null, 2), "application/json");
      if (kind === "md") download(`vitals-${stamp}.md`, data.markdown, "text/markdown");
    });
  }
}

// ---------------------------------------------------------------- start

// ---------------------------------------------------------------- guides (awareness)

function renderGuide(kind) {
  for (const b of $$("[data-guide]")) b.setAttribute("aria-pressed", String(b.dataset.guide === kind));
  const guide = state.guides?.guides?.[kind];
  if (!guide) return;
  $("#guide-summary").textContent = guide.summary;
  const seen = new Set();
  const cards = [];
  for (const [name, p] of Object.entries(guide.practices)) {
    if (seen.has(p.title)) continue;  // aliases (mechanism / specificity) share one card
    seen.add(p.title);
    cards.push(el("article", { class: "guide", id: `guide-${kind}-${name}` },
      el("h3", { text: p.title }),
      el("p", { class: "guide__why", text: p.why }),
      el("p", { class: "guide__how" }, el("strong", { text: "How to adopt: " }), p.how),
      el("div", { class: "guide__examples" },
        el("figure", { class: "example example--weak" },
          el("figcaption", { text: "Weak" }), el("blockquote", { text: p.weak })),
        el("figure", { class: "example example--strong" },
          el("figcaption", { text: "Strong" }), el("blockquote", { text: p.strong })))));
  }
  $("#guide-list").replaceChildren(...cards);
}

async function initGuides() {
  for (const b of $$("[data-guide]")) b.addEventListener("click", () => renderGuide(b.dataset.guide));
  for (const b of $$("[data-goto]")) b.addEventListener("click", () => {
    const tab = $(`#${b.dataset.goto}`);
    selectTab(tab);
    tab.focus();
  });
  try {
    state.guides = await backend.guides();
    $("#adopted-at").textContent = pct(state.guides.adopted);
    $("#partly-at").textContent = pct(state.guides.partly);
    renderGuide("control-statement");
  } catch { /* the rest of the page works without guides */ }
}

async function initConfig() {
  try {
    const config = await backend.config();
    $("#version").textContent = `Version ${config.version}.`;
  } catch {
    showError(BROWSER ? "Could not load Vitals. Check your connection and reload the page."
      : "Could not reach the Vitals server. Is vitals-web still running?");
  }
}

if (BROWSER) {
  for (const n of $$("[data-browser-only]")) n.hidden = false;
  // Start loading Python in the background once the page is idle, so the first check is quick.
  const warm = () => startPython().then(() => { pythonReady = true; }, () => {});
  if ("requestIdleCallback" in window) requestIdleCallback(warm, { timeout: 2000 }); else setTimeout(warm, 500);
}

initTabs();
initGuides();
initSingle();
initBatch();
initConfig();
