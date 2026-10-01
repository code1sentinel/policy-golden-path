"use strict";

// Codify web app. All user and file content is rendered with textContent, never innerHTML.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const TYPE_LABELS = {
  "requirement": "Requirement", "scope": "Scope", "definition": "Definition", "role": "Role",
  "exception": "Exception", "not-a-control": "Not a control",
};
const STATUS_LABELS = { draft: "Draft", reviewed: "Reviewed", accepted: "Accepted" };
const READY = 0.8;  // drafts at or above this score can be selected for review in bulk
const SAVE_KEY = "codify:project";

const state = {
  project: null,       // {uuid, title, source, clauses: [...], controls: [...]}
  scores: {},          // control id -> {confidence, improvements}
  selected: null,      // {control: id} or {clause: id}
  filter: "all",
  checked: new Set(),  // control ids ticked for a bulk action
  guide: null,
  config: null,
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
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

const pct = (x) => `${Math.round(x * 100)}%`;
const plural = (n, word, many = word + "s") => `${n} ${n === 1 ? word : many}`;

function showError(message) {
  const box = $("#error");
  box.textContent = message || "";
  box.hidden = !message;
  if (message) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// Fill a node, leaving out the parts that are not there (null, false).
function put(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
}

function debounce(fn, ms) {
  let timer = null;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// ---------------------------------------------------------------- backends
//
// Served by `codify-web`, the page calls the local server. Built for GitHub Pages (data-mode="browser"),
// it runs Codify's Python in the browser with Pyodide, so the policy never leaves this device.

const BROWSER = document.documentElement.dataset.mode === "browser";

const serverBackend = {
  async config() { return (await fetch("api/config")).json(); },
  async guide() { return (await fetch("api/guide")).json(); },
  async call(body) {
    const res = await fetch("api", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    let data = null;
    try { data = await res.json(); } catch { /* fall through */ }
    if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);
    return data;
  },
};

let python = null;  // a promise of Codify's API running in Pyodide, started once

function startPython() {
  if (!python) {
    python = (async () => {
      const { loadPyodide } = await import("./pyodide/pyodide.mjs");
      const pyodide = await loadPyodide({ indexURL: new URL("pyodide/", location.href).href });
      const archive = await (await fetch("codify.zip")).arrayBuffer();
      pyodide.unpackArchive(archive, "zip", { extractDir: "/home/pyodide/codify-src" });
      pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/codify-src')");
      return pyodide.pyimport("codify.api");
    })();
    python.catch(() => { python = null; });  // allow a retry after a failed load
  }
  return python;
}

let pythonReady = false;

const browserBackend = {
  async config() { return (await fetch("config.json")).json(); },
  async guide() { return (await fetch("guide.json")).json(); },
  async call(body) {
    const api = await startPython();
    pythonReady = true;
    const data = JSON.parse(api.handle(JSON.stringify(body)));
    if (data.error) throw new Error(data.error);
    return data;
  },
};

const backend = BROWSER ? browserBackend : serverBackend;

async function call(body) {
  if (BROWSER && !pythonReady) $("#loading").hidden = false;
  try {
    return await backend.call(body);
  } finally {
    $("#loading").hidden = true;
  }
}

async function busy(button, label, work) {
  const original = button ? button.textContent : "";
  if (button) { button.disabled = true; button.textContent = label; }
  showError("");
  try {
    await work();
  } catch (err) {
    showError(err.message);
  } finally {
    if (button) { button.textContent = original; button.disabled = false; }
  }
}

// ---------------------------------------------------------------- saving in this browser

function saveLocal() {
  if (!state.project) return;
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify({ project: state.project, scores: state.scores, saved: new Date().toISOString() }));
  } catch { /* storage full or unavailable: the OSCAL file is the real save */ }
}
const saveSoon = debounce(saveLocal, 600);

function loadLocal() {
  try {
    const data = JSON.parse(localStorage.getItem(SAVE_KEY) || "null");
    return data && data.project && Array.isArray(data.project.controls) ? data : null;
  } catch { return null; }
}

function clearLocal() {
  try { localStorage.removeItem(SAVE_KEY); } catch { /* ignore */ }
}

// ---------------------------------------------------------------- views

function showView(view) {
  for (const b of $$("[data-view]")) b.setAttribute("aria-pressed", String(b.dataset.view === view));
  $("#guide").hidden = view !== "guide";
  $("#start").hidden = view !== "work" || !!state.project;
  $("#work").hidden = view !== "work" || !state.project;
  if (view === "work" && !state.project) renderResume();
}

function renderResume() {
  const saved = loadLocal();
  $("#resume").hidden = !saved;
  if (!saved) return;
  $("#resume-title").textContent = saved.project.title || "Untitled policy";
  const when = new Date(saved.saved);
  $("#resume-when").textContent = isNaN(when) ? "" : `(saved ${when.toLocaleString()})`;
}

// ---------------------------------------------------------------- opening a project

function openProject(data) {
  state.project = data.project;
  state.scores = data.scores || {};
  state.checked.clear();
  state.filter = "all";
  const first = state.project.controls.find((c) => c.status === "draft") || state.project.controls[0];
  state.selected = first ? { control: first.id } : null;
  for (const b of $$("[data-filter]")) b.setAttribute("aria-pressed", String(b.dataset.filter === "all"));
  saveLocal();
  showView("work");
  render();
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    const binary = /\.(docx|xlsx|doc|xls)$/i.test(file.name);
    reader.onload = () => {
      if (!binary) return resolve({ name: file.name, content: reader.result });
      const bytes = new Uint8Array(reader.result);
      let s = "";
      for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      resolve({ name: file.name, content_base64: btoa(s) });
    };
    reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
    if (binary) reader.readAsArrayBuffer(file); else reader.readAsText(file);
  });
}

async function openFile(file) {
  if (file.size > 20 * 1024 * 1024) return showError(`${file.name} is larger than 20 MB.`);
  await busy(null, "", async () => openProject(await call({ action: "open", ...(await readFile(file)) })));
}

// ---------------------------------------------------------------- lookups

const clauseById = (id) => state.project.clauses.find((c) => c.id === id);
const controlById = (id) => state.project.controls.find((c) => c.id === id);
const controlsOf = (clauseId) => state.project.controls.filter((c) => c.clause === clauseId);
const scoreOf = (id) => (state.scores[id] ? state.scores[id].confidence : null);

function matches(control) {
  const f = state.filter;
  if (f === "all") return true;
  if (f === "low") return (scoreOf(control.id) ?? 0) < READY;
  return control.status === f;
}

function visibleControls() {
  if (state.filter === "other") return [];
  return state.project.controls.filter(matches);
}

// ---------------------------------------------------------------- rendering

function render() {
  renderHead();
  renderList();
  renderEditor();
  renderBulk();
}

function renderHead() {
  const p = state.project;
  const n = (t) => p.clauses.filter((c) => c.type === t).length;
  const dup = p.clauses.filter((c) => c.duplicate_of).length;
  const context = n("scope") + n("definition") + n("role") + n("exception");
  $("#work-title").textContent = p.title || "Untitled policy";
  const summary = $("#work-summary");
  summary.replaceChildren(
    el("strong", { text: `${plural(p.clauses.length, "clause")} → ${plural(p.controls.length, "control")}` }),
    ` · ${n("requirement")} requirement clauses (${dup} duplicate) · ${context} context · ${n("not-a-control")} not controls`,
  );
  const counts = { draft: 0, reviewed: 0, accepted: 0 };
  for (const c of p.controls) counts[c.status] = (counts[c.status] || 0) + 1;
  const total = p.controls.length || 1;
  const bar = $("#work-progress");
  const a = el("span", { class: "p-accepted" });
  const r = el("span", { class: "p-reviewed" });
  a.style.width = pct(counts.accepted / total);
  r.style.width = pct(counts.reviewed / total);
  bar.replaceChildren(a, r);
  bar.setAttribute("aria-label", `${counts.accepted} accepted, ${counts.reviewed} reviewed, ${counts.draft} draft`);
  bar.title = bar.getAttribute("aria-label");
}

function scorePill(id) {
  const s = scoreOf(id);
  if (s === null) return el("span", { class: "score", text: "–" });
  return el("span", { class: `score ${s >= READY ? "score--high" : "score--low"}`, text: pct(s), title: "Check score" });
}

function controlRow(c) {
  const box = el("input", { type: "checkbox", "aria-label": `Select ${c.id}` });
  box.checked = state.checked.has(c.id);
  box.addEventListener("change", () => {
    if (box.checked) state.checked.add(c.id); else state.checked.delete(c.id);
    renderBulk();
  });
  const open = el("button", { type: "button", class: "ctl__open" },
    el("span", { class: "ctl__id", text: c.id }), el("span", { class: "ctl__text", text: c.text || "(empty)" }));
  open.addEventListener("click", () => select({ control: c.id }));
  const row = el("div", { class: "ctl", id: `ctl-${c.id}`, "aria-current": String(state.selected?.control === c.id) },
    box, open, scorePill(c.id), el("span", { class: `state state--${c.status}`, text: STATUS_LABELS[c.status] }));
  return row;
}

function clauseCard(clause, controls) {
  const other = clause.type !== "requirement" || clause.duplicate_of;
  const label = clause.duplicate_of ? `Duplicate of ${clause.duplicate_of}` : TYPE_LABELS[clause.type];
  const type = el("select", { class: "clause__type", "aria-label": `Type of clause ${clause.id}` },
    Object.entries(TYPE_LABELS).map(([k, v]) => el("option", { value: k, text: v })));
  type.value = clause.type;
  type.addEventListener("change", () => changeType(clause, type.value, type));
  const open = el("button", { type: "button", class: "clause__select" }, el("span", { class: "clause__text", text: clause.text }));
  open.addEventListener("click", () => select({ clause: clause.id }));
  return el("div", { class: `clause${other ? " is-other" : ""}`, id: `clause-${clause.id}`,
    "aria-current": String(state.selected?.clause === clause.id) },
  el("div", { class: "clause__head" }, el("span", { class: "clause__id", text: clause.id }), type,
    other ? el("span", { class: "clause__reason", text: clause.duplicate_of ? label : clause.reason }) : null),
  open,
  controls.map(controlRow));
}

function renderList() {
  const list = $("#list");
  const visible = new Set(visibleControls().map((c) => c.id));
  const nodes = [];
  let section = null;
  for (const clause of state.project.clauses) {
    const other = clause.type !== "requirement" || clause.duplicate_of;
    const controls = controlsOf(clause.id).filter((c) => visible.has(c.id));
    const show = state.filter === "all" || (state.filter === "other" ? other : controls.length > 0);
    if (!show) continue;
    const heading = clause.section && clause.heading ? `${clause.section}. ${clause.heading}`
      : clause.heading || (clause.section ? `Section ${clause.section}` : "");
    if (heading && heading !== section) {
      nodes.push(el("p", { class: "section-head", text: heading }));
      section = heading;
    }
    nodes.push(clauseCard(clause, controls));
  }
  if (!nodes.length) nodes.push(el("p", { class: "placeholder", text: "Nothing matches this filter." }));
  list.replaceChildren(...nodes);
}

function renderBulk() {
  const n = state.checked.size;
  $("#selected-count").textContent = `${n} selected`;
  for (const b of $$("[data-bulk]")) b.disabled = n === 0;
  $("#select-none").disabled = n === 0;
}

// ---------------------------------------------------------------- the editor

function select(target) {
  state.selected = target;
  render();
  const id = target.control ? `ctl-${target.control}` : `clause-${target.clause}`;
  const row = document.getElementById(id);
  if (row) row.scrollIntoView({ block: "nearest" });
  if (window.matchMedia("(max-width: 980px)").matches) $("#editor").scrollIntoView({ block: "start", behavior: "smooth" });
}

function renderEditor() {
  const box = $("#editor");
  const sel = state.selected;
  if (sel?.control && controlById(sel.control)) return renderControlEditor(box, controlById(sel.control));
  if (sel?.clause && clauseById(sel.clause)) return renderClauseEditor(box, clauseById(sel.clause));
  box.replaceChildren(el("p", { class: "placeholder" }, "Select a control to review it. Keyboard: ",
    el("kbd", { text: "j" }), "/", el("kbd", { text: "k" }), " next and previous, ", el("kbd", { text: "r" }), " reviewed, ",
    el("kbd", { text: "a" }), " accepted."));
}

function legacyBox(clause) {
  return el("div", { class: "legacy" }, el("span", { class: "legacy__label", text: `Legacy clause ${clause.id}` }), clause.text);
}

function partsList(parts) {
  const rows = [["action", "Action"], ["scope", "Scope"], ["limit", "Limit"], ["purpose", "Purpose"]];
  const items = rows.map(([k, label]) => el("li", { class: `p-${k}${parts && parts[k] ? "" : " is-missing"}` },
    el("b", { text: label }), el("span", { text: parts && parts[k] ? parts[k] : "missing" })));
  if (parts && parts.tools) items.push(el("li", { class: "p-tools is-warning" }, el("b", { text: "Tool named" }), el("span", { text: parts.tools })));
  return el("ul", { class: "parts", "aria-label": "Parts of the statement" }, items);
}

function scoreLine(assessment) {
  const fill = el("span", { class: "bar__fill" });
  fill.style.width = pct(assessment.confidence);
  const p = assessment.practices;
  return el("div", { class: "scoreline" },
    el("span", { class: "scoreline__pct", text: pct(assessment.confidence) }),
    el("span", { class: "bar", role: "img", "aria-label": `${pct(assessment.confidence)} score` }, fill),
    el("span", { class: "scoreline__meta", text: `${p.adopted} of ${p.total} practices adopted` }));
}

function improvementsList(items) {
  if (!items.length) return el("p", { class: "none", text: "No areas for improvement found." });
  return el("ul", { class: "improvements" }, items.map((i) => el("li", { text: i })));
}

function renderControlEditor(box, c) {
  const clause = clauseById(c.clause) || { id: c.clause, text: "" };
  const visible = visibleControls();
  const index = visible.findIndex((x) => x.id === c.id);
  const prev = el("button", { type: "button", class: "btn btn--small", text: "← Previous" });
  const next = el("button", { type: "button", class: "btn btn--small", text: "Next →" });
  prev.disabled = index <= 0;
  next.disabled = index < 0 || index >= visible.length - 1;
  prev.addEventListener("click", () => step(-1));
  next.addEventListener("click", () => step(1));

  const statement = el("textarea", { class: "statement", rows: "4", "aria-label": "Control statement" });
  statement.value = c.text;
  const result = el("div", { class: "result" });
  const guidance = el("textarea", { rows: "2", placeholder: "Tools or how-to examples, e.g. AWS Backup" });
  guidance.value = c.guidance || "";
  const risk = el("textarea", { rows: "2", placeholder: "What could happen without this control" });
  risk.value = c.risk || "";
  const who = el("input", { placeholder: "e.g. The IT Department", autocomplete: "off" });
  who.value = c.who || "";

  const check = debounce(async () => {
    try {
      const data = await call({ action: "check", text: c.text || " ", risk: c.risk || "" });
      state.scores[c.id] = { confidence: data.assessment.confidence, improvements: data.assessment.improvements };
      showResult(result, data);
      const pill = $(`#ctl-${CSS.escape(c.id)} .score`);
      if (pill) pill.replaceWith(scorePill(c.id));
      saveSoon();
    } catch (err) { showError(err.message); }
  }, 350);

  statement.addEventListener("input", () => {
    c.text = statement.value.trim();
    if (c.origin === "rules" || c.origin === "catalog") c.origin = "person";
    const row = $(`#ctl-${CSS.escape(c.id)} .ctl__text`);
    if (row) row.textContent = c.text || "(empty)";
    if (c.text) check();
    saveSoon();
  });
  guidance.addEventListener("input", () => { c.guidance = guidance.value.trim(); saveSoon(); });
  risk.addEventListener("input", () => { c.risk = risk.value.trim(); check(); saveSoon(); });
  who.addEventListener("input", () => { c.who = who.value.trim(); saveSoon(); });

  const statuses = el("div", { class: "statuses", role: "group", "aria-label": "Status" },
    Object.entries(STATUS_LABELS).map(([k, label]) => {
      const b = el("button", { type: "button", class: "btn btn--small", "aria-pressed": String(c.status === k), text: label });
      b.addEventListener("click", () => setStatus([c.id], k));
      return b;
    }));

  const add = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Add a control from this clause" });
  add.addEventListener("click", () => addControl(clause));
  const remove = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Delete this control" });
  remove.addEventListener("click", () => deleteControl(c));

  put(box,
    el("div", { class: "editor__nav" },
      el("p", { class: "editor__where" }, "Control ", el("strong", { text: c.id }), ` · ${c.origin === "rules" ? "drafted by rules" : c.origin === "catalog" ? "from the catalog" : "edited"}`),
      el("div", { class: "actions" }, prev, next)),
    clause.text ? legacyBox(clause) : null,
    el("label", { class: "field" }, el("span", { text: "Control statement" }), statement),
    result,
    c.notes && c.notes.length ? el("div", {}, el("h3", { text: "Drafting notes" }), el("ul", { class: "notes" }, c.notes.map((n) => el("li", { text: n })))) : null,
    el("label", { class: "field" }, el("span", {}, "Risk it treats ", el("em", { text: "gives the control its purpose" })), risk),
    el("div", { class: "grid2" },
      el("label", { class: "field" }, el("span", {}, "Guidance ", el("em", { text: "tools, how-to" })), guidance),
      el("label", { class: "field" }, el("span", {}, "Who ", el("em", { text: "for the implementation" })), who)),
    el("h3", { text: "Status" }), statuses,
    el("div", { class: "editor__foot" }, add, remove),
  );
  result.replaceChildren(el("p", { class: "placeholder", text: "Checking…" }));
  call({ action: "check", text: c.text || " ", risk: c.risk || "" }).then((data) => showResult(result, data)).catch((err) => {
    result.replaceChildren(el("p", { class: "placeholder", text: c.text ? err.message : "Write the control statement to check it." }));
  });
}

function showResult(box, data) {
  box.replaceChildren(scoreLine(data.assessment), partsList(data.parts), improvementsList(data.assessment.improvements));
}

function renderClauseEditor(box, clause) {
  const controls = controlsOf(clause.id);
  const type = el("select", { "aria-label": "Clause type" }, Object.entries(TYPE_LABELS).map(([k, v]) => el("option", { value: k, text: v })));
  type.value = clause.type;
  type.addEventListener("change", () => changeType(clause, type.value, type));
  const draftBtn = el("button", { type: "button", class: "btn btn--small", text: controls.length ? "Draft again from this clause" : "Draft controls from this clause" });
  draftBtn.addEventListener("click", () => redraftClause(clause, draftBtn));
  put(box,
    el("p", { class: "editor__where" }, "Clause ", el("strong", { text: clause.id }), clause.heading ? ` · ${clause.heading}` : ""),
    legacyBox(clause),
    el("label", { class: "field" }, el("span", { text: "Type" }), type),
    el("p", { class: "hint", text: clause.duplicate_of ? `Repeats ${clause.duplicate_of}, so no control was drafted from it.` : `Sorted as ${TYPE_LABELS[clause.type].toLowerCase()}: ${clause.reason}.` }),
    clause.type === "requirement" ? el("div", { class: "actions" }, draftBtn) : null,
    controls.length ? el("div", {}, el("h3", { text: `Controls from this clause (${controls.length})` }), controls.map(controlRow)) : null,
  );
}

// ---------------------------------------------------------------- changes

function step(delta) {
  const visible = visibleControls();
  if (!visible.length) return;
  const index = visible.findIndex((c) => c.id === state.selected?.control);
  const next = visible[Math.min(visible.length - 1, Math.max(0, index + delta))];
  if (next) select({ control: next.id });
}

function setStatus(ids, status) {
  for (const id of ids) {
    const c = controlById(id);
    if (c) c.status = status;
  }
  saveLocal();
  render();
}

async function redraftClause(clause, button) {
  const existing = controlsOf(clause.id);
  if (existing.some((c) => c.origin !== "rules") && !confirm(`Replace the ${plural(existing.length, "control")} from clause ${clause.id}, including your edits?`)) return;
  await busy(button, "Drafting…", async () => {
    const data = await call({ action: "redraft", clause_id: clause.id, text: clause.text });
    const at = state.project.controls.findIndex((c) => c.clause === clause.id);
    state.project.controls = state.project.controls.filter((c) => c.clause !== clause.id);
    const insertAt = at >= 0 ? at : insertionPoint(clause);
    state.project.controls.splice(insertAt, 0, ...data.controls);
    Object.assign(state.scores, data.scores);
    state.selected = data.controls[0] ? { control: data.controls[0].id } : { clause: clause.id };
    saveLocal();
    render();
  });
}

function insertionPoint(clause) {
  // after the controls of the clauses before this one
  const order = state.project.clauses.map((c) => c.id);
  const before = new Set(order.slice(0, order.indexOf(clause.id)));
  let at = 0;
  state.project.controls.forEach((c, i) => { if (before.has(c.clause)) at = i + 1; });
  return at;
}

async function changeType(clause, type, select) {
  const controls = controlsOf(clause.id);
  if (type !== "requirement" && controls.length) {
    if (!confirm(`Clause ${clause.id} has ${plural(controls.length, "control")}. Remove them?`)) {
      select.value = clause.type;
      return;
    }
    state.project.controls = state.project.controls.filter((c) => c.clause !== clause.id);
  }
  clause.type = type;
  clause.duplicate_of = null;
  clause.reason = "set by hand";
  saveLocal();
  if (type === "requirement" && !controls.length) return redraftClause(clause, null);
  state.selected = { clause: clause.id };
  render();
}

function addControl(clause) {
  const used = new Set(state.project.controls.map((c) => c.id));
  let n = controlsOf(clause.id).length + 1;
  let id = `${clause.id.replace(/[^A-Za-z0-9.]+/g, "")}-${n}`;
  while (used.has(id)) id = `${clause.id.replace(/[^A-Za-z0-9.]+/g, "")}-${++n}`;
  const control = { id, clause: clause.id, text: "", guidance: "", risk: "", who: "", notes: [], status: "draft", origin: "person" };
  const last = state.project.controls.map((c) => c.clause).lastIndexOf(clause.id);
  state.project.controls.splice(last >= 0 ? last + 1 : insertionPoint(clause), 0, control);
  state.selected = { control: id };
  saveLocal();
  render();
  const box = $("#editor textarea.statement");
  if (box) box.focus();
}

function deleteControl(c) {
  if (!confirm(`Delete control ${c.id}?`)) return;
  const visible = visibleControls();
  const index = visible.findIndex((x) => x.id === c.id);
  state.project.controls = state.project.controls.filter((x) => x.id !== c.id);
  delete state.scores[c.id];
  state.checked.delete(c.id);
  const next = visible[index + 1] || visible[index - 1];
  state.selected = next && next.id !== c.id ? { control: next.id } : { clause: c.clause };
  saveLocal();
  render();
}

// ---------------------------------------------------------------- export

function download(name, mime, data) {
  const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function exportAs(format, button) {
  $("#export-menu").hidden = true;
  $("#export-more").setAttribute("aria-expanded", "false");
  await busy(button, "Preparing…", async () => {
    const out = await call({ action: "export", format, project: state.project });
    if (out.content_base64) {
      const bytes = Uint8Array.from(atob(out.content_base64), (ch) => ch.charCodeAt(0));
      download(out.name, out.mime, new Blob([bytes], { type: out.mime }));
    } else {
      download(out.name, out.mime, out.content);
    }
  });
}

// ---------------------------------------------------------------- guide

function renderGuide() {
  const g = state.guide;
  if (!g) return;
  $("#guide-summary").textContent = g.guide.summary;
  $("#adopted-at").textContent = pct(g.adopted);
  $("#partly-at").textContent = pct(g.partly);
  $("#guide-list").replaceChildren(...Object.values(g.guide.practices).map((p) =>
    el("article", { class: "guide" },
      el("h3", { text: p.title }),
      el("p", { class: "guide__why", text: p.why }),
      el("p", { class: "guide__how" }, el("strong", { text: "How: " }), p.how),
      el("div", { class: "guide__examples" },
        el("figure", { class: "example example--weak" }, el("figcaption", { text: "Weak" }), el("blockquote", { text: p.weak })),
        el("figure", { class: "example example--strong" }, el("figcaption", { text: "Strong" }), el("blockquote", { text: p.strong }))))));
}

// ---------------------------------------------------------------- wiring

function init() {
  if (BROWSER) for (const n of $$("[data-browser-only]")) n.hidden = false;

  for (const b of $$("[data-view]")) b.addEventListener("click", () => showView(b.dataset.view));

  $("#paste-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const text = form.elements.namedItem("text").value;
    if (!text.trim()) return showError("Paste the policy clauses first.");
    busy($("#paste-submit"), "Codifying…", async () => openProject(await call({
      action: "open", name: "pasted text", text, title: form.elements.namedItem("title").value.trim(),
    })));
  });

  const drop = $("#drop");
  const input = $("#file");
  input.addEventListener("change", () => { if (input.files[0]) openFile(input.files[0]); input.value = ""; });
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("is-over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("is-over");
    if (e.dataTransfer.files[0]) openFile(e.dataTransfer.files[0]);
  });

  $("#demo").addEventListener("click", (e) => busy(e.currentTarget, "Opening…", async () => {
    const text = await (await fetch("acme-policy.md")).text();
    openProject(await call({ action: "open", name: "acme-information-security-policy-2016.md", content: text }));
  }));

  $("#resume-open").addEventListener("click", () => {
    const saved = loadLocal();
    if (saved) openProject(saved);
  });
  $("#resume-discard").addEventListener("click", () => {
    if (confirm("Discard the work saved in this browser? Save an OSCAL catalog first if you want to keep it.")) {
      clearLocal();
      renderResume();
    }
  });

  $("#close-project").addEventListener("click", () => {
    saveLocal();
    state.project = null;
    state.selected = null;
    showView("work");
  });

  for (const b of $$("[data-filter]")) {
    b.addEventListener("click", () => {
      state.filter = b.dataset.filter;
      for (const x of $$("[data-filter]")) x.setAttribute("aria-pressed", String(x === b));
      render();
    });
  }
  $("#select-ready").addEventListener("click", () => {
    // ready: a draft at 80% or more with no drafting notes left to decide
    for (const c of state.project.controls) {
      if (c.status === "draft" && (scoreOf(c.id) ?? 0) >= READY && !(c.notes || []).length) state.checked.add(c.id);
    }
    renderList();
    renderBulk();
  });
  $("#select-none").addEventListener("click", () => { state.checked.clear(); renderList(); renderBulk(); });
  for (const b of $$("[data-bulk]")) {
    b.addEventListener("click", () => {
      setStatus([...state.checked], b.dataset.bulk);
      state.checked.clear();
      renderBulk();
    });
  }

  const more = $("#export-more");
  more.addEventListener("click", () => {
    const menu = $("#export-menu");
    menu.hidden = !menu.hidden;
    more.setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".menu")) { $("#export-menu").hidden = true; more.setAttribute("aria-expanded", "false"); }
  });
  for (const b of $$("[data-export]")) b.addEventListener("click", () => exportAs(b.dataset.export, b));

  document.addEventListener("keydown", (e) => {
    if (!state.project || $("#work").hidden || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    const c = state.selected?.control && controlById(state.selected.control);
    if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); step(1); }
    else if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); step(-1); }
    else if (e.key === "r" && c) setStatus([c.id], "reviewed");
    else if (e.key === "a" && c) setStatus([c.id], "accepted");
  });

  backend.config().then((c) => { state.config = c; $("#version").textContent = `Version ${c.version}.`; }).catch(() => {});
  backend.guide().then((g) => { state.guide = g; renderGuide(); }).catch(() => {});
  showView("work");
  if (BROWSER) startPython().catch(() => {});  // warm up while the person reads the page
}

init();
