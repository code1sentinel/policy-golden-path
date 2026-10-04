"use strict";

// Codify web app. All user and file content is rendered with textContent, never innerHTML.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const TYPE_LABELS = {
  "requirement": "Requirement", "scope": "Scope", "definition": "Definition", "role": "Role",
  "exception": "Exception", "not-a-control": "Not a control",
};
const STATUS_LABELS = { draft: "Draft", reviewed: "Reviewed", accepted: "Accepted" };
const ORIGIN_LABELS = { rules: "drafted by rules", ai: "drafted by AI", catalog: "from the catalog", person: "edited" };
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

function showNotice(message) {
  const box = $("#notice");
  box.textContent = message || "";
  box.hidden = !message;
}

function friendlyNetworkMessage(message) {
  const text = (message || "").trim();
  if (!text || /^failed to fetch$/i.test(text) || /networkerror when attempting to fetch/i.test(text) || /^load failed$/i.test(text)) {
    return "Could not reach the service. Check the connection and try again.";
  }
  return text;
}

function showError(message) {
  const box = $("#error");
  const text = message ? friendlyNetworkMessage(message) : "";
  box.textContent = text;
  box.hidden = !text;
  if (text) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
  showNotice("");
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

// ---------------------------------------------------------------- AI drafting, with the person's own key
//
// Off unless turned on. The prompt comes from Codify's Python (ai_prompt), goes from this browser straight to
// the provider, and the reply goes back through Python (ai_reply), which builds the drafts and scores them.
// One clause per request. The key is kept in sessionStorage, or localStorage if the person asks; never in
// the project, the autosave or an export.

const AI_SETTINGS = "codify:ai";
const AI_KEY = "codify:ai-key";

async function providerFetch(url, options, name) {
  try {
    return await fetch(url, options);
  } catch {
    throw new Error(`Could not reach ${name}. Check the connection and try again.`);
  }
}

async function providerJson(res, name) {
  let data = null;
  try { data = await res.json(); } catch { /* fall through */ }
  if (!res.ok) {
    const detail = data && data.error && (data.error.message || data.error);
    if (res.status === 401 || res.status === 403) throw new Error(`${name} did not accept the API key${detail ? `: ${detail}` : "."}`);
    throw new Error(`${name} returned an error (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  if (!data) throw new Error(`${name} sent a reply Codify could not read.`);
  return data;
}

const PROVIDERS = {
  anthropic: {
    label: "Anthropic (Claude)",
    models: ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-4-5"],
    async send(key, model, p) {
      const headers = {
        "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      };
      const body = { model, max_tokens: 16000, system: p.system, messages: [{ role: "user", content: p.user }],
        output_config: { format: { type: "json_schema", schema: p.schema } } };
      if (/^claude-(opus-5|sonnet-5-5|fable)/.test(model)) {
        // if a safety classifier declines, the API retries on a fallback model in the same call
        headers["anthropic-beta"] = "server-side-fallback-2026-07-01";
        body.fallbacks = "default";
      }
      const res = await providerFetch("https://api.anthropic.com/v1/messages", { method: "POST", headers, body: JSON.stringify(body) }, "Anthropic");
      const data = await providerJson(res, "Anthropic");
      if (data.stop_reason === "refusal") throw new Error("Claude declined to draft this clause.");
      if (data.stop_reason === "max_tokens") throw new Error("Claude's reply was cut off; try again.");
      return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
    },
  },
  openai: {
    label: "OpenAI",
    models: ["gpt-5-mini", "gpt-5"],
    async send(key, model, p) {
      const res = await providerFetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
        body: JSON.stringify({ model, messages: [{ role: "system", content: p.system }, { role: "user", content: p.user }],
          response_format: { type: "json_schema", json_schema: { name: "controls", strict: true, schema: p.schema } } }),
      }, "OpenAI");
      const data = await providerJson(res, "OpenAI");
      const message = data.choices && data.choices[0] && data.choices[0].message;
      if (message && message.refusal) throw new Error(`OpenAI declined to draft this clause: ${message.refusal}`);
      return (message && message.content) || "";
    },
  },
  gemini: {
    label: "Google (Gemini)",
    models: ["gemini-2.5-flash", "gemini-2.5-pro"],
    async send(key, model, p) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
      const res = await providerFetch(url, {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({ systemInstruction: { parts: [{ text: p.system }] },
          contents: [{ role: "user", parts: [{ text: p.user }] }],
          generationConfig: { responseMimeType: "application/json" } }),
      }, "Gemini");
      const data = await providerJson(res, "Gemini");
      const parts = (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) || [];
      if (!parts.length) throw new Error("Gemini returned no draft for this clause.");
      return parts.map((x) => x.text || "").join("");
    },
  },
  ollama: {
    label: "Ollama (local)",
    models: ["llama3.2", "mistral", "qwen2.5"],
    requiresKey: false,
    async send(key, model, p) {
      let res;
      try {
        res = await fetch("http://localhost:11434/v1/chat/completions", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            model,
            messages: [{ role: "system", content: p.system }, { role: "user", content: p.user }],
            response_format: { type: "json_object" },
          }),
        });
      } catch {
        if (location.protocol === "https:") {
          throw new Error("Ollama is local (http://localhost:11434). Browsers block that from this HTTPS page. Run codify-web --open on this machine to draft with Ollama.");
        }
        throw new Error("Could not reach Ollama at http://localhost:11434. Is it running?");
      }
      const data = await providerJson(res, "Ollama");
      const message = data.choices && data.choices[0] && data.choices[0].message;
      const text = (message && message.content) || "";
      if (!text) throw new Error("Ollama returned no draft for this clause.");
      return text;
    },
  },
};

const ai = { on: false, provider: "anthropic", model: PROVIDERS.anthropic.models[0], key: "", remember: false, stop: false };

function loadAi() {
  try {
    const saved = JSON.parse(localStorage.getItem(AI_SETTINGS) || "null");
    if (saved && PROVIDERS[saved.provider]) Object.assign(ai, { on: !!saved.on, provider: saved.provider, model: String(saved.model || ""), remember: !!saved.remember });
  } catch { /* defaults */ }
  try { ai.key = (ai.remember ? localStorage : sessionStorage).getItem(AI_KEY) || ""; } catch { ai.key = ""; }
  if (!ai.model) ai.model = PROVIDERS[ai.provider].models[0];
}

function saveAi() {
  try {
    localStorage.setItem(AI_SETTINGS, JSON.stringify({ on: ai.on, provider: ai.provider, model: ai.model, remember: ai.remember }));
    localStorage.removeItem(AI_KEY);
    sessionStorage.removeItem(AI_KEY);
    if (ai.key) (ai.remember ? localStorage : sessionStorage).setItem(AI_KEY, ai.key);
  } catch { /* storage unavailable: the settings last for this page only */ }
}

function providerNeedsKey(name = ai.provider) {
  const p = PROVIDERS[name];
  return !p || p.requiresKey !== false;
}

const aiReady = () => ai.on && (!providerNeedsKey() || !!ai.key);
const aiName = () => `${PROVIDERS[ai.provider].label}, ${ai.model}`;

function renderAiButton() {
  const b = $("#ai-open");
  const ready = aiReady();
  b.textContent = ready ? "AI drafting: on" : ai.on ? "AI drafting: needs a key" : "AI drafting: off";
  b.setAttribute("aria-pressed", String(ready));
  b.classList.toggle("is-on", ready);
  b.classList.toggle("is-needs", ai.on && !ready);
  $("#ai-bulk").hidden = !ready;
}

function updateAiDialogStatus() {
  const chip = $("#ai-ready-chip");
  if (!chip) return;
  const name = $("#ai-provider")?.value || ai.provider;
  const local = !providerNeedsKey(name);
  const key = ($("#ai-key")?.value || "").trim() || (name === ai.provider ? ai.key : "");
  chip.classList.remove("is-ready", "is-needs", "is-off");
  if (local) {
    chip.textContent = "Ready · no key";
    chip.classList.add("is-ready");
  } else if (key) {
    chip.textContent = "Ready";
    chip.classList.add("is-ready");
  } else {
    chip.textContent = "Needs a key";
    chip.classList.add("is-needs");
  }
}

function syncAiProviderForm(provider) {
  const local = !providerNeedsKey(provider);
  $("#ai-key-field").hidden = local;
  $("#ai-remember-row").hidden = local;
  $("#ai-key").disabled = local;
  $("#ai-key").placeholder = local ? "" : (ai.key && provider === ai.provider ? "" : "Paste your API key");
  $("#ai-model-hint").textContent = local ? "any model you have pulled" : "any model your account has";
  const note = $("#ai-local-note");
  note.hidden = !local;
  if (local) {
    note.textContent = location.protocol === "https:"
      ? "Ollama runs on this machine at http://localhost:11434. Browsers block that from this HTTPS page, so run codify-web --open on this machine to draft with Ollama."
      : "Talks to Ollama on this machine at http://localhost:11434. No API key. The clause is sent only to that local model.";
  }
  updateAiDialogStatus();
}

function fillModels(provider) {
  $("#ai-models").replaceChildren(...PROVIDERS[provider].models.map((m) => el("option", { value: m })));
  syncAiProviderForm(provider);
}

function openAiDialog() {
  $("#ai-provider").replaceChildren(...Object.entries(PROVIDERS).map(([k, v]) => el("option", { value: k, text: v.label })));
  $("#ai-provider").value = ai.provider;
  fillModels(ai.provider);
  $("#ai-model").value = ai.model;
  $("#ai-key").value = providerNeedsKey(ai.provider) ? ai.key : "";
  $("#ai-remember").checked = ai.remember;
  $("#ai-ack").checked = false;
  $("#ai-off").hidden = !ai.on && !ai.key;
  $("#ai-off").textContent = ai.key ? "Turn off and forget the key" : "Turn off";
  $("#ai-form-error").hidden = true;
  updateAiDialogStatus();
  $("#ai-dialog").showModal();
}

function aiFormSubmit(e) {
  const action = e.submitter ? e.submitter.value : "cancel";
  const fail = (message) => {
    e.preventDefault();
    const box = $("#ai-form-error");
    box.textContent = friendlyNetworkMessage(message);
    box.hidden = false;
  };
  if (action === "off") {
    Object.assign(ai, { on: false, key: "", remember: false });
  } else if (action === "on") {
    const model = $("#ai-model").value.trim();
    const name = $("#ai-provider").value;
    const key = $("#ai-key").value.trim();
    const needsKey = providerNeedsKey(name);
    if (!$("#ai-ack").checked) return fail("Tick the box to confirm you have read what is sent.");
    if (!model) return fail("Enter a model.");
    if (needsKey && !key) return fail("Enter your API key.");
    Object.assign(ai, { on: true, provider: name, model, key: needsKey ? key : "", remember: needsKey && $("#ai-remember").checked });
  } else {
    return;
  }
  saveAi();
  renderAiButton();
  if (state.project) render();
}

async function aiDraftClause(clause) {
  const prompt = await call({ action: "ai_prompt", clause_id: clause.id, text: clause.text, heading: clause.heading || "" });
  const reply = await PROVIDERS[ai.provider].send(ai.key, ai.model, prompt);
  return call({ action: "ai_reply", clause_id: clause.id, reply, model: ai.model });
}

function needsConfirm(clause) {
  // the person has worked on this clause's controls: edited, reviewed or accepted them
  return controlsOf(clause.id).some((c) => c.status !== "draft" || (c.origin !== "rules" && c.origin !== "ai"));
}

async function aiRedraft(clause, button) {
  if (!aiReady()) return openAiDialog();
  const existing = controlsOf(clause.id);
  if (needsConfirm(clause) && !confirm(`Replace the ${plural(existing.length, "control")} from this clause, including your edits, with AI drafts?`)) return;
  await busy(button, "Drafting with AI…", async () => replaceControls(clause, await aiDraftClause(clause)));
}

async function aiBulk() {
  if (!aiReady()) return openAiDialog();
  const ids = new Set([...state.checked].map((id) => controlById(id)?.clause).filter(Boolean));
  const clauses = state.project.clauses.filter((c) => ids.has(c.id));
  const todo = clauses.filter((c) => !needsConfirm(c));
  const skipped = clauses.length - todo.length;
  if (!todo.length) return showError("The selected controls have all been edited, reviewed or accepted, so AI drafting leaves them alone. Use \"Draft with AI\" on a clause to replace its controls.");
  const note = skipped ? `\n\n${plural(skipped, "clause")} with edited, reviewed or accepted controls will be left alone.` : "";
  if (!confirm(`Send ${plural(todo.length, "clause")} to ${aiName()}, one request per clause?\n\nEach request holds one clause's text, section heading and rule drafts. Their controls are replaced with AI drafts.${note}`)) return;
  ai.stop = false;
  showError("");
  const bar = $("#ai-progress");
  bar.hidden = false;
  let done = 0;
  try {
    for (const clause of todo) {
      if (ai.stop) break;
      $("#ai-progress-text").textContent = `Drafting with AI: clause ${done + 1} of ${todo.length}…`;
      replaceControls(clause, await aiDraftClause(clause), false);
      done += 1;
    }
  } catch (err) {
    showError(`Stopped after ${plural(done, "clause")}: ${err.message}`);
  } finally {
    bar.hidden = true;
    state.checked.clear();
    saveLocal();
    render();
  }
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
  showNotice("");
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
  if (state.selected) {
    const id = state.selected.control ? `ctl-${state.selected.control}` : `clause-${state.selected.clause}`;
    document.getElementById(id)?.scrollIntoView({ block: "nearest" });
  }
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
  renderMoreLabel();
}

function renderMoreLabel() {
  const summary = $("#work-more summary");
  if (!summary) return;
  const names = { all: "More", draft: "Drafts", reviewed: "Reviewed", accepted: "Accepted",
    low: "Below 80%", other: "Not converted" };
  summary.textContent = names[state.filter] || "More";
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
  );
  summary.title = `${n("requirement")} requirement clauses (${dup} duplicate) · ${context} context · ${n("not-a-control")} not controls`;
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

function controlRow(c, inEditor = false) {
  const box = el("input", { type: "checkbox", "aria-label": "Select this control" });
  box.checked = state.checked.has(c.id);
  const open = el("button", { type: "button", class: "ctl__open" },
    el("span", { class: "ctl__text", text: c.text || "(empty)" }));
  open.addEventListener("click", () => select({ control: c.id }));
  const row = el("div", {
    class: `ctl${state.checked.has(c.id) ? " is-checked" : ""}`,
    id: inEditor ? null : `ctl-${c.id}`,
    "aria-current": String(state.selected?.control === c.id),
  }, box, open, scorePill(c.id), el("span", { class: `state state--${c.status}`, text: STATUS_LABELS[c.status] }));
  box.addEventListener("change", () => {
    if (box.checked) state.checked.add(c.id); else state.checked.delete(c.id);
    row.classList.toggle("is-checked", box.checked);
    renderBulk();
  });
  return row;
}

function clauseCard(clause, controls) {
  const other = clause.type !== "requirement" || clause.duplicate_of;
  const label = clause.duplicate_of ? "Duplicate" : TYPE_LABELS[clause.type];
  const open = el("button", { type: "button", class: "clause__select" }, el("span", { class: "clause__text", text: clause.text }));
  open.addEventListener("click", () => {
    const first = controlsOf(clause.id)[0];
    select(first ? { control: first.id } : { clause: clause.id });
  });
  const current = state.selected?.clause === clause.id ||
    (state.selected?.control && controlById(state.selected.control)?.clause === clause.id);
  return el("div", { class: `clause${other ? " is-other" : ""}`, id: `clause-${clause.id}`,
    "aria-current": String(!!current) },
  el("div", { class: "clause__head" },
    el("span", { class: "clause__type", text: label }),
    other && !clause.duplicate_of ? el("span", { class: "clause__reason", text: clause.reason }) : null),
  open,
  controls.map((c) => controlRow(c)));
}

function emptyGlyph() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "empty__glyph");
  svg.setAttribute("fill", "none");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", "M8 3.5h6.2L19 8.3V20.5H8zM14.2 3.5v4.8H19M9.5 13h5M9.5 16.5h3.5");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.5");
  path.setAttribute("stroke-linejoin", "round");
  path.setAttribute("stroke-linecap", "round");
  svg.append(path);
  return svg;
}

function emptyState(line, actionLabel, onAction, extraClass) {
  const action = el("button", { type: "button", class: "btn", text: actionLabel });
  action.addEventListener("click", onAction);
  return el("div", { class: extraClass ? `empty ${extraClass}` : "empty" },
    el("div", { class: "empty__icon", "aria-hidden": "true" }, emptyGlyph()),
    el("p", { class: "empty__line", text: line }),
    action);
}

function showAllFilters() {
  state.filter = "all";
  for (const b of $$("[data-filter]")) b.setAttribute("aria-pressed", String(b.dataset.filter === "all"));
  render();
}

function openFirstDraft() {
  const first = state.project?.controls.find((c) => c.status === "draft") || state.project?.controls[0];
  if (first) select({ control: first.id });
}

function renderList() {
  const list = $("#list");
  const visible = new Set(visibleControls().map((c) => c.id));
  const nodes = [];
  let section = null;
  for (const clause of state.project.clauses) {
    const other = clause.type !== "requirement" || clause.duplicate_of;
    const controls = controlsOf(clause.id).filter((c) => visible.has(c.id));
    const show = state.filter === "other" ? other : !other && (state.filter === "all" || controls.length > 0);
    if (!show) continue;
    const heading = clause.heading || "";
    if (heading && heading !== section) {
      nodes.push(el("p", { class: "section-head", text: heading }));
      section = heading;
    }
    nodes.push(clauseCard(clause, controls));
  }
  if (!nodes.length) {
    nodes.push(emptyState("Nothing matches this filter.", "Show all", showAllFilters, "empty--list"));
  }
  list.replaceChildren(...nodes);
}

function renderBulk() {
  const n = state.checked.size;
  const bar = $("#selection-bar");
  $("#selected-count").textContent = `${n} selected`;
  if (bar) bar.hidden = n === 0;
  $("#work")?.classList.toggle("has-selection", n > 0);
  for (const b of $$("[data-bulk]")) b.disabled = n === 0;
  $("#select-none").disabled = n === 0;
  $("#ai-bulk").disabled = n === 0;
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
  box.replaceChildren(emptyState("Select a clause to draft its control.", "Open first draft", openFirstDraft));
}

function legacyBox(clause) {
  return el("div", { class: "legacy" }, el("span", { class: "legacy__label", text: "Legacy clause" }), clause.text);
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
  if (!items.length) return null;
  return el("ul", { class: "improvements" }, items.map((i) => el("li", { text: i })));
}

function renderControlEditor(box, c) {
  const clause = clauseById(c.clause) || { id: c.clause, text: "" };
  const visible = visibleControls();
  const index = visible.findIndex((x) => x.id === c.id);

  const statement = el("textarea", { class: "statement", rows: "5", "aria-label": "Control statement" });
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
    if (c.origin !== "person") c.origin = "person";  // the drafting notes still say how it began
    const row = $(`#ctl-${CSS.escape(c.id)} .ctl__text`);
    if (row) row.textContent = c.text || "(empty)";
    if (c.text) check();
    saveSoon();
  });
  guidance.addEventListener("input", () => { c.guidance = guidance.value.trim(); saveSoon(); });
  risk.addEventListener("input", () => { c.risk = risk.value.trim(); check(); saveSoon(); });
  who.addEventListener("input", () => { c.who = who.value.trim(); saveSoon(); });

  const reviewed = el("button", { type: "button", class: "btn", "aria-pressed": String(c.status === "reviewed"), text: "Reviewed" });
  reviewed.addEventListener("click", () => setStatus([c.id], "reviewed"));
  const accept = el("button", { type: "button", class: "btn btn--primary", "aria-pressed": String(c.status === "accepted"), text: "Accept" });
  accept.addEventListener("click", () => setStatus([c.id], "accepted"));
  const next = el("button", { type: "button", class: "btn", text: "Next" });
  next.disabled = index < 0 || index >= visible.length - 1;
  next.addEventListener("click", () => step(1));
  let aiBtn = null;
  if (aiReady() && clause.text) {
    aiBtn = el("button", { type: "button", class: "btn", text: "Draft with AI" });
    aiBtn.addEventListener("click", () => aiRedraft(clause, aiBtn));
  }

  const add = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Add a control from this clause" });
  add.addEventListener("click", () => addControl(clause));
  const redraft = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Draft again from this clause" });
  redraft.addEventListener("click", () => redraftClause(clause, redraft));
  const remove = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Delete this control" });
  remove.addEventListener("click", () => deleteControl(c));
  const openClause = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Open clause" });
  openClause.addEventListener("click", () => select({ clause: clause.id }));

  const extras = el("details", { class: "fold fold--block" },
    el("summary", { text: "Guidance, who, notes" }),
    el("div", { class: "fold__body" },
      el("div", { class: "grid2" },
        el("label", { class: "field" }, el("span", {}, "Guidance ", el("em", { text: "tools, how-to" })), guidance),
        el("label", { class: "field" }, el("span", {}, "Who ", el("em", { text: "who implements it" })), who)),
      c.notes && c.notes.length ? el("ul", { class: "notes" }, c.notes.map((n) => el("li", { text: n }))) : null));

  put(box,
    el("div", { class: "editor__nav" },
      el("p", { class: "editor__where" }, "Control", ` · ${ORIGIN_LABELS[c.origin] || "edited"}`)),
    clause.text ? legacyBox(clause) : null,
    el("label", { class: "field" }, el("span", { text: "Control statement" }), statement),
    el("div", { class: "editor__primary", role: "group", "aria-label": "Review" }, reviewed, accept, next, aiBtn),
    result,
    el("label", { class: "field" }, el("span", {}, "Risk it treats ", el("em", { text: "gives the control its purpose" })), risk),
    extras,
    el("div", { class: "editor__foot" }, openClause, redraft, add, remove),
  );
  result.replaceChildren(el("p", { class: "placeholder", text: "Checking…" }));
  call({ action: "check", text: c.text || " ", risk: c.risk || "" }).then((data) => showResult(result, data)).catch((err) => {
    result.replaceChildren(el("p", { class: "placeholder", text: c.text ? err.message : "Write the control statement to check it." }));
  });
}

function showResult(box, data) {
  box.replaceChildren(...[scoreLine(data.assessment), partsList(data.parts), improvementsList(data.assessment.improvements)].filter(Boolean));
}

function renderClauseEditor(box, clause) {
  const controls = controlsOf(clause.id);
  const type = el("select", { "aria-label": "Clause type" }, Object.entries(TYPE_LABELS).map(([k, v]) => el("option", { value: k, text: v })));
  type.value = clause.type;
  type.addEventListener("change", () => changeType(clause, type.value, type));
  const draftBtn = el("button", { type: "button", class: "btn btn--small", text: controls.length ? "Draft again from this clause" : "Draft controls from this clause" });
  draftBtn.addEventListener("click", () => redraftClause(clause, draftBtn));
  const aiBtn = el("button", { type: "button", class: "btn btn--small", text: "Draft with AI" });
  aiBtn.addEventListener("click", () => aiRedraft(clause, aiBtn));
  put(box,
    el("p", { class: "editor__where" }, "Clause", clause.heading ? ` · ${clause.heading}` : ""),
    legacyBox(clause),
    el("label", { class: "field" }, el("span", { text: "Type" }), type),
    el("p", { class: "hint", text: clause.duplicate_of ? "Repeats another clause, so no control was drafted from it." : `Sorted as ${TYPE_LABELS[clause.type].toLowerCase()}: ${clause.reason}.` }),
    clause.type === "requirement" ? el("div", { class: "actions" }, draftBtn, aiReady() ? aiBtn : null) : null,
    controls.length ? el("div", {}, el("h3", { text: `Controls from this clause (${controls.length})` }), controls.map((c) => controlRow(c, true))) : null,
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
  if (existing.some((c) => c.origin !== "rules") && !confirm(`Replace the ${plural(existing.length, "control")} from this clause, including your edits?`)) return;
  await busy(button, "Drafting…", async () => replaceControls(clause, await call({ action: "redraft", clause_id: clause.id, text: clause.text })));
}

function replaceControls(clause, data, show = true) {
  // put new drafts where the clause's controls were
  const at = state.project.controls.findIndex((c) => c.clause === clause.id);
  for (const c of controlsOf(clause.id)) { delete state.scores[c.id]; state.checked.delete(c.id); }
  state.project.controls = state.project.controls.filter((c) => c.clause !== clause.id);
  state.project.controls.splice(at >= 0 ? at : insertionPoint(clause), 0, ...data.controls);
  Object.assign(state.scores, data.scores);
  if (!show) return;
  state.selected = data.controls[0] ? { control: data.controls[0].id } : { clause: clause.id };
  saveLocal();
  render();
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
    if (!confirm(`This clause has ${plural(controls.length, "control")}. Remove them?`)) {
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
  if (!confirm("Delete this control?")) return;
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
      action: "open", name: "pasted text", text,
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
    showNotice("");
    state.project = null;
    state.selected = null;
    showView("work");
  });

  for (const b of $$("[data-filter]")) {
    b.addEventListener("click", () => {
      state.filter = b.dataset.filter;
      for (const x of $$("[data-filter]")) x.setAttribute("aria-pressed", String(x === b));
      const more = $("#work-more");
      if (more) more.open = false;
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
  $("#select-shown").addEventListener("click", () => {
    for (const c of visibleControls()) state.checked.add(c.id);
    renderList();
    renderBulk();
  });

  loadAi();
  renderAiButton();
  $("#ai-open").addEventListener("click", openAiDialog);
  $("#ai-provider").addEventListener("change", () => {
    const p = $("#ai-provider").value;
    fillModels(p);
    $("#ai-model").value = p === ai.provider ? ai.model : PROVIDERS[p].models[0];
    $("#ai-key").value = p === ai.provider && providerNeedsKey(p) ? ai.key : "";  // a key belongs to one provider
  });
  $("#ai-form").addEventListener("submit", aiFormSubmit);
  $("#ai-form").addEventListener("input", () => {
    $("#ai-form-error").hidden = true;
    updateAiDialogStatus();
  });
  $("#ai-bulk").addEventListener("click", aiBulk);
  $("#ai-stop").addEventListener("click", () => {
    ai.stop = true;
    $("#ai-progress-text").textContent = "Stopping after this clause…";
  });
  for (const b of $$("[data-bulk]")) {
    b.addEventListener("click", () => {
      const ids = [...state.checked];
      state.checked.clear();
      setStatus(ids, b.dataset.bulk);
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
    if (e.target.closest("dialog, input, textarea, select, [contenteditable]")) return;
    const c = state.selected?.control && controlById(state.selected.control);
    if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); step(1); }
    else if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); step(-1); }
    else if (e.key === "Escape" && state.selected) { e.preventDefault(); state.selected = null; render(); }
    else if (e.key === "r" && c) setStatus([c.id], "reviewed");
    else if (e.key === "a" && c) setStatus([c.id], "accepted");
  });

  backend.config().then((c) => { state.config = c; $("#version").textContent = `Version ${c.version}.`; }).catch(() => {});
  backend.guide().then((g) => { state.guide = g; renderGuide(); }).catch(() => {});
  showView("work");
  if (BROWSER) startPython().catch(() => {});  // warm up while the person reads the page
}

init();
