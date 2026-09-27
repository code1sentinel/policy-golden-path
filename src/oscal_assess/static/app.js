"use strict";

// All user and file content is rendered with textContent, never innerHTML.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const KIND_LABELS = {
  "implementation": "Implementation statement",
  "risk-statement": "Risk statement",
  "recommendation": "Recommendation",
};
const BADGE_LABELS = {
  "implementation": "Implementation",
  "risk-statement": "Risk",
  "recommendation": "Recommendation",
};
const TEXT_LABELS = {
  "implementation": "Implementation statement",
  "risk-statement": "Risk statement",
  "recommendation": "Recommendation",
};
const CRITERION_LABELS = {
  policy_intent: "Policy intent",
  root_cause: "Root cause",
};

const EXAMPLES = {
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
};

const state = {
  engine: "heuristic",
  files: [],        // {name, size, content}
  catalog: null,    // {name, content}
  policy: null,
  batch: null,      // last batch response
};

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

async function post(body) {
  const res = await fetch("/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, engine: state.engine }),
  });
  let data = null;
  try { data = await res.json(); } catch { /* fall through */ }
  if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);
  return data;
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
  try { localStorage.setItem("oscal-assess-tab", tab.id); } catch { /* storage unavailable */ }
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
  try { saved = localStorage.getItem("oscal-assess-tab"); } catch { /* storage unavailable */ }
  if (saved && $(`#${saved}`)) selectTab($(`#${saved}`));
}

// ---------------------------------------------------------------- rendering an assessment

function criteriaList(criteria) {
  if (!criteria.length) return el("p", { class: "none", text: "No criteria returned." });
  return el("ul", { class: "criteria" }, criteria.map((c) =>
    el("li", { class: "criterion" },
      el("span", { class: "criterion__name", text: human(c.name) }),
      bar(c.score),
      el("span", { class: "criterion__pct", text: pct(c.score) }),
      c.note ? el("span", { class: "criterion__note", text: c.note }) : null,
    )));
}

function improvementsList(items) {
  if (!items.length) return el("p", { class: "none", text: "No areas for improvement found." });
  return el("ul", { class: "improvements" }, items.map((i) => el("li", { text: i })));
}

function renderSingle(a) {
  const box = $("#single-result");
  box.replaceChildren(
    el("p", { class: "verdict__kind", text: KIND_LABELS[a.kind] }),
    el("p", { class: "verdict__score" },
      el("span", { class: "verdict__pct", text: pct(a.confidence) }),
      el("span", { class: "verdict__label", text: "confidence" })),
    bar(a.confidence, "bar--large"),
    el("h3", { text: `Areas for improvement (${a.improvements.length})` }),
    improvementsList(a.improvements),
    el("h3", { text: "Criteria" }),
    criteriaList(a.criteria),
    el("p", { class: "rationale", text: `${a.rationale} Engine: ${a.engine}.` }),
  );
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
      $("#single-result").replaceChildren(el("p", { class: "placeholder", text: "Enter a statement and select Assess." }));
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
    busy($("#single-submit"), "Assessing…", async () => {
      const data = await post({ mode: "single", item });
      renderSingle(data.assessments[0]);
    });
  });
}

// ---------------------------------------------------------------- batch upload

async function readFile(file) {
  return { name: file.name, size: file.size, content: await file.text() };
}

function updateBatchButton() {
  const n = state.files.length;
  const btn = $("#batch-submit");
  btn.disabled = n === 0;
  btn.textContent = n ? `Assess ${plural(n, "file")}` : "Assess";
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
  const accepted = Array.from(fileList).filter((f) => /\.(json|csv)$/i.test(f.name));
  const skipped = fileList.length - accepted.length;
  for (const f of accepted) {
    const existing = state.files.findIndex((x) => x.name === f.name);
    const read = await readFile(f);
    if (existing >= 0) state.files[existing] = read; else state.files.push(read);
  }
  renderFileList();
  showError(skipped ? `${plural(skipped, "file")} skipped: only .json and .csv files can be assessed.` : "");
}

function renderTiles(summary) {
  const tiles = Object.entries(summary.by_kind).map(([kind, k]) =>
    el("div", { class: "tile" },
      el("p", { class: "tile__label", text: `${KIND_LABELS[kind]}s` }),
      el("p", { class: "tile__value" }, pct(k.average_confidence), el("small", { text: "average confidence" })),
      bar(k.average_confidence),
      el("p", { class: "tile__meta", text: `${plural(k.count, "item")}, ${k.with_improvements} with areas for improvement` })));
  $("#tiles").replaceChildren(...tiles);
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
  $(".result__count", node).textContent = a.improvements.length
    ? plural(a.improvements.length, "improvement") : "No improvements";

  // Build the details only when first opened: large batches stay fast.
  node.addEventListener("toggle", () => {
    const body = $(".result__body", node);
    if (!node.open || body.childElementCount) return;
    body.append(
      el("div", {}, el("h3", { text: "Areas for improvement" }), improvementsList(a.improvements)),
      el("div", {}, el("h3", { text: "Criteria" }), criteriaList(a.criteria)),
      el("div", { class: "full" }, el("h3", { text: "Text assessed" }), el("pre", { class: "quote", text: a.text || "(empty)" })),
      el("p", { class: "rationale full", text: `${a.rationale} Engine: ${a.engine}.` }),
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
  const header = ["file", "kind", "item", "control_id", "confidence", "improvement_count", "improvements", "rationale", "text"];
  const lines = [header.join(",")];
  for (const a of assessments) {
    lines.push([a.file, a.kind, a.item, a.control_id, Math.round(a.confidence * 100), a.improvements.length,
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
    busy(e.currentTarget, "Assessing…", async () => {
      const strip = (f) => f && { name: f.name, content: f.content };
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
      if (kind === "csv") download(`oscal-assess-${stamp}.csv`, toCsv(data.assessments), "text/csv");
      if (kind === "json") download(`oscal-assess-${stamp}.json`, JSON.stringify(
        { summary: data.summary, files: data.files, assessments: data.assessments }, null, 2), "application/json");
      if (kind === "md") download(`oscal-assess-${stamp}.md`, data.markdown, "text/markdown");
    });
  }
}

// ---------------------------------------------------------------- start

async function initConfig() {
  const select = $("#engine");
  select.addEventListener("change", () => { state.engine = select.value; });
  try {
    const res = await fetch("/api/config");
    const config = await res.json();
    $("#version").textContent = `Version ${config.version}.`;
    if (config.engines.includes("claude")) {
      select.append(el("option", { value: "claude", text: `Claude (${config.claude_model})` }));
    }
  } catch {
    showError("Could not reach the oscal-assess server. Is oscal-assess-web still running?");
  }
}

initTabs();
initSingle();
initBatch();
initConfig();
