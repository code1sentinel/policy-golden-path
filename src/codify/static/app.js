"use strict";

// Codify web app. All user and file content is rendered with textContent, never innerHTML.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const TYPE_LABELS = {
  "requirement": "Requirement", "scope": "Scope", "definition": "Definition", "role": "Role",
  "exception": "Exception", "not-a-control": "Not a control",
};
const STATUS_LABELS = { draft: "Draft", reviewed: "Reviewed", accepted: "Accepted" };
const ORIGIN_LABELS = {
  rules: "Drafted by Codify's rules (not AI)",
  ai: "Drafted by AI — check before you accept",
  catalog: "Opened from a saved catalog",
  person: "Edited by you",
};
const GLOSSARY = {
  OSCAL: "A standard format from NIST for writing security controls so other GRC tools can read them.",
  Clause: "A paragraph from the policy you pasted.",
  Draft: "Codify's first-pass control statement. Edit it before you accept.",
  Review: "Check the draft against the original clause and the score.",
  Accept: "Keep this statement in this project's catalog and on this device.",
  Catalog: "This project's control statements — the set you export as OSCAL.",
  Library: "Reusable accepted statements saved on this device, across projects.",
};
const PART_HELP = {
  action: "Start with the verb (Review, Restrict, Encrypt).",
  scope: "Say what this applies to (which systems, people, or data).",
  limit: "Add a time limit to make this testable (for example, every [90] days).",
  purpose: "Say why this control exists — the risk it treats.",
};
const SCORE_HELP = "How complete this statement is: testable, scoped, action-first, and has a purpose. 80% or more is usually ready to accept.";
const RISK_STATUS_LABELS = { identified: "Identified", treating: "Treating", accepted: "Accepted", closed: "Closed" };
const RISK_FIELDS = ["id", "title", "description", "asset", "likelihood", "impact", "threat", "vulnerability", "owner", "status"];
const READY = 0.8;  // drafts at or above this score can be selected for review in bulk
const SAVE_KEY = "codify:project";
const LIBRARY_KEY = "codify:statements";
const SPLASH_KEY = "codify:splash-seen";

const state = {
  project: null,       // {uuid, title, source, clauses: [...], controls: [...], risks: [...]}
  scores: {},          // control id -> {confidence, improvements}
  selected: null,      // {control: id} or {clause: id}
  filter: "all",
  checked: new Set(),  // control ids ticked for a bulk action
  guide: null,
  config: null,
  editorTab: "statement", // statement | oscal
  view: "workspace",
  dismissed: {},       // control id -> dismissed review suggestion texts
  lastCheck: {},       // control id -> {assessment, parts}
  selectedRisk: null,  // risk id
  riskPane: "register", // library | register
  riskQuery: "",
  selectedLibrary: null, // library entry id
  libraryPickId: null,
  recommendRiskId: null,
  dismissedTemplates: {},  // risk id -> template ids
  importPreview: null,
  resultStep: false,   // short "here's what we drafted" before the 3-pane workspace
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

function term(word, meaning) {
  return el("abbr", { class: "term", title: meaning || GLOSSARY[word] || word, text: word });
}

function showNotice(message) {
  const box = $("#notice");
  box.textContent = message || "";
  box.hidden = !message;
  box.classList.toggle("toast", Boolean(message));
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

function loadLibrary() {
  try {
    const data = JSON.parse(localStorage.getItem(LIBRARY_KEY) || "null");
    if (Array.isArray(data)) return data;
    return data && Array.isArray(data.entries) ? data.entries : [];
  } catch { return []; }
}

function saveLibrary(entries) {
  try {
    localStorage.setItem(LIBRARY_KEY, JSON.stringify({ entries, saved: new Date().toISOString() }));
  } catch { /* storage full or unavailable: the catalog remains the project save */ }
}

function librarySourceLabel(entry) {
  if ((entry["source-type"] || entry.source_type) === "risk" || entry["risk-id"] || entry.risk_id) {
    return entry["risk-id"] || entry.risk_id || "Risk";
  }
  return "Clause";
}

function formatWhen(iso) {
  if (!iso) return "—";
  const when = new Date(iso);
  return isNaN(when) ? iso : when.toLocaleDateString();
}

async function rememberStatement(control, { used = false } = {}) {
  const text = (control.text || "").trim();
  if (!text) return;
  const data = await call({
    action: "library_upsert",
    library: loadLibrary(),
    statement: text,
    parts: (state.lastCheck[control.id] && state.lastCheck[control.id].parts) || control.parts || null,
    source_type: control.source_type || (control.risk_id ? "risk" : "clause"),
    risk_id: control.risk_id || "",
    used,
  });
  saveLibrary(data.library);
  return data.entry;
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
  const shortName = (PROVIDERS[ai.provider].label.split(" (")[0] || ai.provider);
  b.textContent = ready ? `AI: On · ${shortName}` : ai.on ? "AI: Needs a key" : "AI: Off";
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

function navFor(view) {
  if (view === "work" || view === "result") return "clauses";
  if (view === "workspace") return "workspace";
  return view;
}

function showView(view) {
  if (view === "workspace" && state.project) view = "work";
  if (view === "work" && !state.project) view = "workspace";
  if (view === "work" && state.resultStep) view = "result";
  if (view !== "result") state.resultStep = false;
  state.view = view;
  const nav = navFor(view);
  for (const b of $$("[data-nav]")) {
    if (b.dataset.nav === "export") continue;
    b.setAttribute("aria-pressed", String(b.dataset.nav === nav));
  }
  $("#guide").hidden = view !== "guide";
  $("#start").hidden = view !== "workspace";
  applySplash();
  if ($("#result")) $("#result").hidden = view !== "result";
  $("#work").hidden = view !== "work";
  $("#catalog").hidden = view !== "catalog";
  $("#risks").hidden = view !== "risks";
  $("#library").hidden = view !== "library";
  const exportTop = $("#export-open-top");
  const closeBtn = $("#close-project");
  if (exportTop) exportTop.hidden = !state.project;
  if (closeBtn) closeBtn.hidden = !state.project;
  if (view !== "risks") closeRecommendDialog();
  if (view === "workspace" && !state.project) renderResume();
  if (view === "result" && state.project) renderResult();
  if (view === "work" && state.project) render();
  if (view === "catalog") renderCatalog();
  if (view === "risks") renderRisks();
  if (view === "library") renderLibrary();
  renderCrumb();
}

function renderCrumb() {
  const crumb = $("#crumb");
  if (!crumb) return;
  const item = (text, last = false) => el("span", { class: last ? "crumb__item" : "crumb__item", text });
  const sep = () => el("span", { class: "crumb__sep", "aria-hidden": "true", text: "/" });
  const parts = ["Workspace"];
  if (state.view === "result" && state.project) {
    parts.push("Here's what we drafted");
  } else if (state.view === "work" && state.project) {
    parts.push(state.project.title || "Clauses");
    if (state.selected?.control) parts.push("Control");
    else if (state.selected?.clause) parts.push("Clause");
  } else if (state.view === "catalog") parts.push("Catalog");
  else if (state.view === "risks") {
    parts.push("Risks");
    const risk = state.selectedRisk && riskById(state.selectedRisk);
    if (risk) parts.push(risk.title);
  }
  else if (state.view === "library") parts.push("Library");
  else if (state.view === "guide") parts.push("Guide");
  const nodes = [];
  parts.forEach((p, i) => {
    if (i) nodes.push(sep());
    nodes.push(item(p, i === parts.length - 1));
  });
  crumb.replaceChildren(...nodes);
}

function renderResume() {
  const saved = loadLocal();
  $("#resume").hidden = !saved;
  if (!saved) return;
  $("#resume-title").textContent = saved.project.title || "Untitled policy";
  const when = new Date(saved.saved);
  $("#resume-when").textContent = isNaN(when) ? "" : `(saved ${when.toLocaleString()})`;
}

function splashSeen() {
  try { return Boolean(localStorage.getItem(SPLASH_KEY)); } catch { return false; }
}

function shouldShowSplash() {
  return !splashSeen() && !loadLocal();
}

function applySplash() {
  const splash = $("#splash");
  if (!splash) return;
  const open = !state.project && state.view === "workspace" && shouldShowSplash();
  splash.hidden = !open;
  if (open) {
    document.documentElement.setAttribute("data-splash", "open");
    $("#start").hidden = true;
  } else {
    document.documentElement.removeAttribute("data-splash");
  }
}

function dismissSplash() {
  try { localStorage.setItem(SPLASH_KEY, "1"); } catch { /* ignore */ }
  document.documentElement.removeAttribute("data-splash");
  const splash = $("#splash");
  if (splash) splash.hidden = true;
  if (!state.project) showView("workspace");
  $("#paste-form textarea")?.focus();
}

// ---------------------------------------------------------------- opening a project

function openProject(data, { resultStep = false } = {}) {
  showNotice("");
  state.project = data.project;
  state.scores = data.scores || {};
  state.checked.clear();
  state.filter = "all";
  const first = state.project.controls.find((c) => c.status === "draft") || state.project.controls[0];
  state.selected = first ? { control: first.id } : null;
  state.editorTab = "statement";
  state.resultStep = Boolean(resultStep && (state.project.controls || []).length);
  for (const b of $$("[data-filter]")) b.setAttribute("aria-pressed", String(b.dataset.filter === "all"));
  saveLocal();
  showView(state.resultStep ? "result" : "work");
  if (!state.resultStep) render();
  renderCatalog();
  renderRisks();
  if (!state.resultStep && state.selected) {
    const id = state.selected.control ? `ctl-${state.selected.control}` : `clause-${state.selected.clause}`;
    document.getElementById(id)?.scrollIntoView({ block: "nearest" });
  }
}

function clauseCounts(project) {
  const clauses = project.clauses || [];
  const controls = project.controls || [];
  const reqs = clauses.filter((c) => c.type === "requirement" && !c.duplicate_of);
  const split = reqs.filter((c) => controls.filter((x) => x.clause === c.id).length > 1).length;
  return {
    clauses: clauses.length,
    requirements: reqs.length,
    other: clauses.length - reqs.length,
    controls: controls.length,
    split,
  };
}

function renderResult() {
  const p = state.project;
  if (!p) return;
  const n = clauseCounts(p);
  const lede = $("#result-lede");
  const list = $("#result-drafts");
  if (lede) {
    const bits = [`${plural(n.controls, "control draft")} from ${plural(n.requirements, "requirement")}.`];
    if (n.other) {
      bits.push(`${plural(n.other, "other clause")} ${n.other === 1 ? "was" : "were"} not converted (definitions, scope, roles, or duplicates).`);
    }
    if (n.split) bits.push(`${plural(n.split, "requirement")} split into more than one control.`);
    lede.textContent = bits.join(" ");
  }
  if (list) {
    const drafts = (p.controls || []).slice(0, 3);
    put(list, ...drafts.map((c, i) => el("li", {},
      el("strong", { text: `Draft ${i + 1}` }),
      c.text || "(empty)")));
  }
}

function continueFromResult() {
  state.resultStep = false;
  showView("work");
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
const riskById = (id) => (state.project.risks || []).find((r) => r.id === id);
const controlsOfRisk = (riskId) => state.project.controls.filter((c) => c.risk_id === riskId);
const scoreOf = (id) => (state.scores[id] ? state.scores[id].confidence : null);

function ensureProject() {
  if (!state.project) {
    const uuid = (crypto.randomUUID && crypto.randomUUID()) || `00000000-0000-4000-8000-${String(Date.now()).slice(-12)}`;
    state.project = { uuid, title: "", source: "", version: "", clauses: [], controls: [], risks: [] };
    state.scores = {};
  }
  if (!Array.isArray(state.project.risks)) state.project.risks = [];
}

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
  renderCrumb();
  if (state.view === "catalog") renderCatalog();
  if (state.view === "risks") renderRisks();
  if (state.view === "library") renderLibrary();
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
  const counts = clauseCounts(p);
  put(summary,
    el("strong", { text: `${plural(counts.controls, "control draft")} from ${plural(counts.requirements, "requirement")}` }),
    counts.other ? el("span", { class: "work__summary-detail", text: `. ${plural(counts.other, "other clause")} ${counts.other === 1 ? "was" : "were"} not converted (definitions, scope, roles, or duplicates).` }) : el("span", { text: "." }),
    counts.split ? el("span", { class: "work__summary-detail", text: ` ${plural(counts.split, "requirement")} split into more than one control.` }) : null,
    (p.risks || []).length ? el("span", { text: ` · ${plural(p.risks.length, "risk")}` }) : null,
  );
  summary.title = `${counts.requirements} requirements drafted into ${counts.controls} controls · ${dup} duplicate · ${context} context · ${n("not-a-control")} not controls`;
  const statusCounts = { draft: 0, reviewed: 0, accepted: 0 };
  for (const c of p.controls) statusCounts[c.status] = (statusCounts[c.status] || 0) + 1;
  const total = p.controls.length || 1;
  const bar = $("#work-progress");
  const a = el("span", { class: "p-accepted" });
  const r = el("span", { class: "p-reviewed" });
  a.style.width = pct(statusCounts.accepted / total);
  r.style.width = pct(statusCounts.reviewed / total);
  bar.replaceChildren(a, r);
  bar.setAttribute("aria-label", `${statusCounts.accepted} accepted, ${statusCounts.reviewed} reviewed, ${statusCounts.draft} draft`);
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
  const head = other
    ? el("div", { class: "clause__head" },
      el("span", { class: "clause__type", text: label }),
      !clause.duplicate_of ? el("span", { class: "clause__reason", text: clause.reason }) : null)
    : null;
  return el("div", { class: `clause${other ? " is-other" : ""}`, id: `clause-${clause.id}`,
    "aria-current": String(!!current) },
  head,
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

function emptyState(line, actionLabel, onAction, extraClass, extraActions) {
  const children = [
    el("div", { class: "empty__icon", "aria-hidden": "true" }, emptyGlyph()),
    el("p", { class: "empty__line", text: line }),
  ];
  const actions = [];
  if (actionLabel && onAction) {
    const action = el("button", { type: "button", class: extraActions && extraActions.length ? "btn btn--primary" : "btn", text: actionLabel });
    action.addEventListener("click", onAction);
    actions.push(action);
  }
  for (const extra of extraActions || []) {
    const b = el("button", { type: "button", class: extra.primary ? "btn btn--primary" : "btn", text: extra.label });
    b.addEventListener("click", extra.onClick);
    actions.push(b);
  }
  if (actions.length) children.push(el("div", { class: "empty__actions" }, actions));
  return el("div", { class: extraClass ? `empty ${extraClass}` : "empty" }, ...children);
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
  if (state.filter !== "other") {
    const byRisk = {};
    for (const c of state.project.controls) {
      if (!(c.source_type === "risk" || c.risk_id) || !matches(c)) continue;
      (byRisk[c.risk_id || "risk"] ||= []).push(c);
    }
    for (const [rid, controls] of Object.entries(byRisk)) {
      const risk = riskById(rid);
      nodes.push(el("p", { class: "section-head", text: risk ? `Risk · ${risk.title}` : "From risks" }));
      for (const c of controls) nodes.push(controlRow(c));
    }
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
  const same = state.selected && target
    && state.selected.control === target.control && state.selected.clause === target.clause;
  if (!same) state.editorTab = "statement";
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
  if (sel?.clause && clauseById(sel.clause)) {
    renderProps(null);
    return renderClauseEditor(box, clauseById(sel.clause));
  }
  box.replaceChildren(emptyState("Select a clause to draft its control.", "Open first draft", openFirstDraft));
  renderProps(null);
}

function legacyBox(clause) {
  return el("div", { class: "legacy" }, el("span", { class: "legacy__label", text: "Legacy clause" }), clause.text);
}

function partMissing(key) {
  return el("span", { class: "part-help", text: PART_HELP[key] || "Add this part." });
}

function partsList(parts) {
  const rows = [["action", "Action"], ["scope", "Scope"], ["limit", "Limit"], ["purpose", "Purpose"]];
  const items = rows.map(([k, label]) => el("li", { class: `p-${k}${parts && parts[k] ? "" : " is-missing"}` },
    el("b", { text: label }),
    parts && parts[k] ? el("span", { text: parts[k] }) : partMissing(k)));
  if (parts && parts.tools) items.push(el("li", { class: "p-tools is-warning" }, el("b", { text: "Tool named" }), el("span", { text: parts.tools })));
  return el("ul", { class: "parts", "aria-label": "Parts of the statement" }, items);
}

function partsSubitems(parts) {
  const rows = [["action", "Action"], ["scope", "Scope"], ["limit", "Limit"], ["purpose", "Purpose"]];
  const found = rows.filter(([k]) => parts && parts[k]).length;
  const items = rows.map(([k, label]) => el("li", { class: parts && parts[k] ? "" : "is-missing" },
    el("span", { class: "dot", "aria-hidden": "true" }),
    el("span", {}, el("b", { text: label }), " ", parts && parts[k] ? parts[k] : partMissing(k))));
  if (parts && parts.tools) {
    items.push(el("li", { class: "is-warning" },
      el("span", { class: "dot", "aria-hidden": "true" }),
      el("span", {}, el("b", { text: "Tool named" }), " ", parts.tools)));
  }
  return el("div", {},
    el("p", { class: "subitems__head", text: `Parts ${found} of ${rows.length}` }),
    el("p", { class: "score-help", text: "A testable control usually has these parts assessors look for: an action, what it applies to, a time limit, and why." }),
    el("ul", { class: "subitems", "aria-label": "Parts of the statement" }, items));
}

function scoreLine(assessment) {
  const fill = el("span", { class: "bar__fill" });
  fill.style.width = pct(assessment.confidence);
  return el("div", { class: "scoreline" },
    el("span", { class: "scoreline__pct", text: pct(assessment.confidence) }),
    el("span", { class: "bar", role: "img", "aria-label": `${pct(assessment.confidence)} score` }, fill),
    el("p", { class: "score-help", text: SCORE_HELP }));
}

function improvementsList(items) {
  if (!items.length) return null;
  return el("ul", { class: "improvements" }, items.map((i) => el("li", { text: i })));
}

function editorTabs() {
  const make = (id, label) => {
    const b = el("button", {
      type: "button", class: "editor-tab", role: "tab",
      "aria-selected": String(state.editorTab === id), text: label,
    });
    b.addEventListener("click", () => {
      state.editorTab = id;
      renderEditor();
    });
    return b;
  };
  const oscal = make("oscal", "");
  oscal.replaceChildren(term("OSCAL"), " JSON");
  return el("div", { class: "editor-tabs", role: "tablist", "aria-label": "Control view" },
    make("statement", "Statement"), oscal);
}

function numberedJson(text) {
  return text.split("\n").map((line, i) => el("div", { class: "oscal-line" },
    el("span", { class: "oscal-ln", text: String(i + 1) }),
    el("span", { class: "oscal-code", text: line || " " })));
}

async function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch { /* fall through to execCommand */ }
  }
  const ta = el("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.append(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  ta.remove();
  return ok;
}

function oscalPanel(c) {
  const pre = el("pre", { class: "oscal-pre", id: "oscal-json", tabindex: "0", "aria-label": "OSCAL JSON for this control" });
  const status = el("span", { class: "oscal-copy-status", "aria-live": "polite", id: "oscal-copy-status" });
  const copy = el("button", { type: "button", class: "btn btn--small", id: "oscal-copy", text: "Copy" });
  copy.addEventListener("click", async () => {
    const raw = pre.dataset.raw || "";
    status.textContent = (await copyText(raw)) ? "Copied" : "Copy failed";
  });
  pre.textContent = "Loading…";
  call({ action: "control_oscal", project: state.project, control_id: c.id }).then((data) => {
    const raw = JSON.stringify(data.control, null, 2);
    pre.dataset.raw = raw;
    pre.replaceChildren(...numberedJson(raw));
  }).catch((err) => { pre.textContent = err.message; });
  return el("div", { class: "oscal-view", role: "tabpanel", "aria-label": "OSCAL JSON" },
    el("div", { class: "oscal-view__bar" },
      el("span", { class: "oscal-view__label", text: "This control" }),
      copy, status),
    pre);
}

function renderControlEditor(box, c) {
  const isRisk = c.source_type === "risk" || !!c.risk_id;
  const clause = clauseById(c.clause) || { id: c.clause, text: "" };
  const risk = isRisk ? riskById(c.risk_id) : null;
  const visible = visibleControls();
  const index = visible.findIndex((x) => x.id === c.id);
  const tabs = editorTabs();
  const where = el("div", { class: "editor__nav" },
    el("p", { class: "editor__where" }, "Control", ` · ${ORIGIN_LABELS[c.origin] || "Edited by you"}`),
    tabs);
  if (state.editorTab === "oscal") {
    put(box, where, oscalPanel(c));
    renderProps(c, state.lastCheck[c.id]);
    return;
  }

  const statement = el("textarea", { class: "statement", rows: "5", "aria-label": "Control statement" });
  statement.value = c.text;
  const result = el("div", { class: "result" });
  const guidance = el("textarea", { rows: "2", placeholder: "Tools or how-to examples, e.g. AWS Backup" });
  guidance.value = c.guidance || "";
  const riskBox = el("textarea", { rows: "2", placeholder: "What could happen without this control" });
  riskBox.value = c.risk || "";
  const who = el("input", { placeholder: "e.g. The IT Department", autocomplete: "off" });
  who.value = c.who || "";

  const check = debounce(async () => {
    try {
      const data = await call({ action: "check", text: c.text || " ", risk: c.risk || "" });
      state.scores[c.id] = { confidence: data.assessment.confidence, improvements: data.assessment.improvements };
      state.lastCheck[c.id] = data;
      showResult(result, data);
      sub.replaceChildren(partsSubitems(data.parts));
      renderProps(c, data);
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
  riskBox.addEventListener("input", () => { c.risk = riskBox.value.trim(); check(); saveSoon(); });
  who.addEventListener("input", () => { c.who = who.value.trim(); saveSoon(); });

  const reviewed = el("button", {
    type: "button", class: "btn", "aria-pressed": String(c.status === "reviewed"),
    text: "Mark reviewed",
    title: "You have read this draft. It is not accepted yet — use Accept when the wording is good enough to keep.",
  });
  reviewed.addEventListener("click", () => setStatus([c.id], "reviewed"));
  const accept = el("button", {
    type: "button", class: "btn btn--primary", "aria-pressed": String(c.status === "accepted"),
    text: "Accept",
    title: "Keep this statement in this project's catalog and on this device.",
  });
  accept.addEventListener("click", () => setStatus([c.id], "accepted"));
  const next = el("button", { type: "button", class: "btn", text: "Next control", title: "Open the next control without accepting this one." });
  next.disabled = index < 0 || index >= visible.length - 1;
  next.addEventListener("click", () => step(1));
  let aiBtn = null;
  if (aiReady() && (clause.text || risk)) {
    aiBtn = el("button", { type: "button", class: "btn", text: "Draft with AI" });
    aiBtn.addEventListener("click", () => (risk ? aiRedraftRisk(risk, aiBtn) : aiRedraft(clause, aiBtn)));
  }

  const fromLib = el("button", { type: "button", class: "btn", id: "library-from", text: "From library" });
  fromLib.addEventListener("click", openLibraryPick);
  const add = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Add a control from this clause" });
  add.addEventListener("click", () => addControl(clause));
  const redraft = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Draft again from this clause" });
  redraft.addEventListener("click", () => redraftClause(clause, redraft));
  const remove = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Delete this control" });
  remove.addEventListener("click", () => deleteControl(c));
  const openClause = el("button", { type: "button", class: "btn btn--small btn--quiet", text: isRisk ? "Open risk" : "Open clause" });
  openClause.addEventListener("click", () => {
    if (isRisk && c.risk_id) {
      state.selectedRisk = c.risk_id;
      showView("risks");
    } else {
      select({ clause: clause.id });
    }
  });

  const extras = el("details", { class: "fold fold--block" },
    el("summary", { text: "Guidance, risk, who" }),
    el("div", { class: "fold__body" },
      el("div", { class: "grid2" },
        el("label", { class: "field" }, el("span", {}, "Guidance ", el("em", { text: "tools, how-to" })), guidance),
        el("label", { class: "field" }, el("span", {}, "Who ", el("em", { text: "who implements it" })), who)),
      el("label", { class: "field" }, el("span", { text: "Risk it treats" }), riskBox),
      c.notes && c.notes.length ? el("ul", { class: "notes" }, c.notes.map((n) => el("li", { text: n }))) : null));

  const sub = el("div", { class: "editor__parts" });
  put(box,
    where,
    isRisk && risk ? el("div", { class: "legacy" }, el("span", { class: "legacy__label", text: "Risk" }),
      `${risk.id} · ${risk.title}`) : (clause.text ? legacyBox(clause) : null),
    el("label", { class: "field field--hero" }, statement),
    paramNote(c.text),
    el("div", { class: "editor__primary", role: "group", "aria-label": "Review" }, reviewed, accept, next, fromLib, aiBtn),
    result,
    sub,
    extras,
    el("div", { class: "editor__foot" }, openClause, isRisk ? null : redraft, isRisk ? null : add, remove),
  );
  result.replaceChildren(el("p", { class: "placeholder", text: "Checking…" }));
  call({ action: "check", text: c.text || " ", risk: c.risk || "" }).then((data) => {
    state.lastCheck[c.id] = data;
    showResult(result, data);
    sub.replaceChildren(partsSubitems(data.parts));
    renderProps(c, data);
  }).catch((err) => {
    result.replaceChildren(el("p", { class: "placeholder", text: c.text ? err.message : "Write the control statement to check it." }));
    renderProps(c);
  });
}

function paramNote(text) {
  if (!/\[[^\]]{1,40}\]/.test(text || "")) return null;
  return el("p", { class: "hint param-note" },
    "Bracketed values like [N] or [90] are blanks to fill. Replace [N] with a real number your organisation will test against.");
}

function showResult(box, data) {
  box.replaceChildren(...[scoreLine(data.assessment), partsList(data.parts), improvementsList(data.assessment.improvements)].filter(Boolean));
}

function renderProps(control, data) {
  const box = $("#props");
  if (!box) return;
  if (!control) {
    box.replaceChildren(el("p", { class: "placeholder", text: "Select a control to see its properties." }));
    return;
  }
  const clause = clauseById(control.clause);
  const score = scoreOf(control.id);
  const propsCard = el("div", { class: "props-card" },
    el("h3", { class: "props-card__title", text: "Properties" }),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Status" }),
      el("span", { class: `state state--${control.status}`, text: STATUS_LABELS[control.status] })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Control ID" }),
      el("span", { class: "prop-row__value", text: control.id })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Source" }),
      el("span", { class: "prop-row__value", text: controlSourceLabel(control) })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "How it was written" }),
      el("span", { class: "prop-row__value", text: ORIGIN_LABELS[control.origin] || control.origin })),
    el("p", { class: "prop-help", text: control.origin === "rules"
      ? "A starting point from Codify's rules. Edit freely — it is not finished until you Accept."
      : "Edit the statement, then Accept when it is clear and testable." }),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Score" }),
      el("span", { class: "prop-row__value", text: score === null ? "–" : pct(score) })),
    el("p", { class: "prop-help", text: SCORE_HELP }),
  );
  const suggestions = [];
  const draft = el("div", { class: "suggestion" },
    el("p", { class: "suggestion__text", text: control.status === "accepted"
      ? "This control is accepted. It is in this project's catalog."
      : "When the statement is clear and testable, press Accept under the editor. That keeps it in this project's catalog." }),
    control.status === "accepted" ? null : el("p", { class: "hint", text: "Mark reviewed if you have read it but it still needs work." }),
  );
  suggestions.push(draft);

  const hidden = new Set(state.dismissed[control.id] || []);
  const improvements = (data && data.assessment && data.assessment.improvements) || (state.scores[control.id] && state.scores[control.id].improvements) || [];
  for (const tip of improvements) {
    if (hidden.has(tip)) continue;
    const row = el("div", { class: "suggestion" },
      el("p", { class: "suggestion__text", text: tip }),
      el("div", { class: "suggestion__actions" },
        el("button", { type: "button", class: "btn btn--small", text: "Dismiss" })));
    $("button", row).addEventListener("click", () => {
      state.dismissed[control.id] = [...(state.dismissed[control.id] || []), tip];
      renderProps(control, data);
    });
    suggestions.push(row);
  }

  const libraryCard = el("div", { class: "props-card", id: "library-picks" },
    el("h3", { class: "props-card__title", text: "From library" }),
    el("p", { class: "placeholder", text: "Loading…" }));
  const saved = loadLibrary();
  if (!saved.length) {
    libraryCard.replaceChildren(
      el("h3", { class: "props-card__title", text: "From library" }),
      el("p", { class: "placeholder", text: "No saved statements yet." }),
    );
  } else {
    const browse = el("button", { type: "button", class: "btn btn--small", text: "Browse library" });
    browse.addEventListener("click", openLibraryPick);
    libraryCard.replaceChildren(
      el("h3", { class: "props-card__title", text: "From library" }),
      ...libraryPickRows(saved.slice(0, 5), { add: true }),
      el("div", { class: "actions" }, browse),
    );
  }

  let aiCard = null;
  if (control.origin === "ai") {
    const tryAgain = el("button", { type: "button", class: "btn btn--small", text: "Try again" });
    const useThis = el("button", { type: "button", class: "btn btn--small btn--primary", text: "Use this" });
    const risk = riskById(control.risk_id);
    tryAgain.addEventListener("click", () => {
      if (risk) aiRedraftRisk(risk, tryAgain);
      else if (clause) aiRedraft(clause, tryAgain);
    });
    useThis.addEventListener("click", () => setStatus([control.id], "reviewed"));
    aiCard = el("div", { class: "props-card" },
      el("h3", { class: "props-card__title", text: "AI assist" }),
      el("p", { class: "suggestion__text", text: "This draft came from the model you chose. Check it against the source before you accept it." }),
      el("div", { class: "suggestion__actions" }, tryAgain, useThis),
      el("p", { class: "disclaimer", text: "Optional AI may produce inaccurate wording. The rule draft needs no AI." }));
  }

  box.replaceChildren(...[propsCard,
    el("div", { class: "props-card" },
      el("h3", { class: "props-card__title", text: "Review suggestions" }),
      suggestions.length ? suggestions : el("p", { class: "placeholder", text: "No suggestions." })),
    libraryCard,
    aiCard].filter(Boolean));
}

function controlSourceLabel(control) {
  if (control.source_type === "risk" || control.risk_id) return control.risk_id || "Risk";
  return control.clause ? "Clause" : "—";
}

function renderCatalog() {
  const box = $("#catalog-body");
  if (!box) return;
  if (!state.project) {
    box.replaceChildren(emptyState("No policy loaded.", "Paste a clause", () => showView("workspace"), "empty--list"));
    return;
  }
  const rows = state.project.controls;
  if (!rows.length) {
    box.replaceChildren(emptyState("No controls yet.", "Open first draft", () => { showView("work"); openFirstDraft(); }, "empty--list"));
    return;
  }
  const body = rows.map((c) => {
    const open = el("button", { type: "button", text: c.text || "(empty)" });
    open.addEventListener("click", () => { showView("work"); select({ control: c.id }); });
    return el("tr", {},
      el("td", { text: c.id }),
      el("td", {}, open),
      el("td", {}, el("span", { class: "pill", text: controlSourceLabel(c) })),
      el("td", {}, el("span", { class: `state state--${c.status}`, text: STATUS_LABELS[c.status] })));
  });
  box.replaceChildren(el("div", { class: "catalog-body" },
    el("table", { class: "data-table" },
      el("thead", {}, el("tr", {},
        el("th", { text: "ID" }), el("th", { text: "Control" }),
        el("th", { text: "Source" }), el("th", { text: "Status" }))),
      el("tbody", {}, body))));
}

function statementLead(text) {
  const raw = (text || "").trim();
  if (!raw) return "(empty)";
  const match = raw.match(/^[^.]*\.(?:\s|$)/);
  return match ? match[0].trim() : raw;
}

function renderLibraryDetail(entry) {
  if (!entry) {
    return el("aside", { class: "library-detail", id: "library-detail", "aria-label": "Statement details" },
      el("p", { class: "placeholder", text: "Select a statement to see its details." }));
  }
  const use = el("button", { type: "button", class: "btn btn--primary library-use", text: "Use" });
  const add = el("button", { type: "button", class: "btn library-add", text: "Add" });
  const removeBtn = el("button", { type: "button", class: "btn btn--quiet library-remove", text: "Remove" });
  use.addEventListener("click", () => useLibraryEntry(entry, "use"));
  add.addEventListener("click", () => useLibraryEntry(entry, "add"));
  removeBtn.addEventListener("click", () => removeLibraryEntry(entry));
  const source = librarySourceLabel(entry);
  const domain = (entry["source-type"] || entry.source_type) === "risk" ? "Risk" : "Control statement";
  return el("aside", { class: "library-detail", id: "library-detail", "aria-label": "Statement details" },
    el("h3", { class: "library-detail__title", text: statementLead(entry.statement) }),
    el("p", { class: "library-detail__statement", text: entry.statement }),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "ID" }),
      el("span", { class: "prop-row__value", text: entry.id })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Source" }),
      el("span", { class: "prop-row__value" }, el("span", { class: "pill", text: source }))),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Domain" }),
      el("span", { class: "prop-row__value", text: domain })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Framework" }),
      el("span", { class: "prop-row__value", text: "OSCAL 1.1.2" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Related" }),
      el("span", { class: "prop-row__value", text: entry["risk-id"] || entry.risk_id || "Clause" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Accepted" }),
      el("span", { class: "prop-row__value", text: formatWhen(entry["accepted-at"]) })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Last used" }),
      el("span", { class: "prop-row__value", text: formatWhen(entry["last-used-at"]) })),
    el("div", { class: "library-detail__actions actions" }, use, add, removeBtn));
}

function renderLibrary() {
  const box = $("#library-body");
  if (!box) return;
  const query = ($("#library-search") && $("#library-search").value) || state.libraryQuery || "";
  state.libraryQuery = query;
  const entries = loadLibrary();
  const filtered = query
    ? entries.filter((e) => {
      const hay = `${e.statement} ${e["source-type"] || ""} ${e["risk-id"] || ""} ${e.id}`.toLowerCase();
      return hay.includes(query.trim().toLowerCase());
    })
    : entries;
  const search = el("input", {
    id: "library-search", type: "search", placeholder: "Search statements",
    "aria-label": "Search the statement library", autocomplete: "off",
  });
  search.value = query;
  search.addEventListener("input", () => {
    state.libraryQuery = search.value;
    renderLibrary();
    const again = $("#library-search");
    if (again) { again.focus(); again.setSelectionRange(search.value.length, search.value.length); }
  });
  const exportJson = el("button", { type: "button", class: "btn", id: "library-export-json", text: "Export JSON" });
  const exportCsv = el("button", { type: "button", class: "btn", id: "library-export-csv", text: "Export CSV" });
  exportJson.addEventListener("click", () => exportAs("library-json", exportJson));
  exportCsv.addEventListener("click", () => exportAs("library-csv", exportCsv));
  const head = el("div", { class: "library-toolbar" },
    el("div", { class: "view-head" },
      el("h2", { id: "library-title", class: "section-title section-title--first", text: "Statement library" }),
      el("p", { class: "view-head__lede", text: "Reusable accepted statements saved on this device, across projects. The catalog is this project's export — the library is the reuse drawer." })),
    el("div", { class: "library-toolbar__tools" }, search,
      el("div", { class: "actions" }, exportJson, exportCsv)));
  if (!filtered.length) {
    const empty = entries.length
      ? emptyState("No statements match that search.", "Clear search", () => { state.libraryQuery = ""; renderLibrary(); }, "empty--list")
      : emptyState("No statements saved yet.", "Open clauses", () => showView(state.project ? "work" : "workspace"), "empty--list");
    box.replaceChildren(head, empty);
    return;
  }
  const ids = new Set(filtered.map((e) => e.id));
  if (!state.selectedLibrary || !ids.has(state.selectedLibrary)) state.selectedLibrary = filtered[0].id;
  const selected = filtered.find((e) => e.id === state.selectedLibrary) || filtered[0];
  const list = el("div", { class: "library-list", "aria-label": "Saved statements" },
    el("p", { class: "library-count", text: `Statement library (${filtered.length})` }),
    filtered.map((entry) => {
      const use = el("button", { type: "button", class: "btn btn--small btn--primary library-use", text: "Use" });
      const removeBtn = el("button", { type: "button", class: "btn btn--small library-remove", text: "Remove" });
      use.addEventListener("click", (e) => { e.stopPropagation(); useLibraryEntry(entry, "use"); });
      removeBtn.addEventListener("click", (e) => { e.stopPropagation(); removeLibraryEntry(entry); });
      const row = el("article", {
        class: "library-row", "data-library-id": entry.id,
        "aria-current": String(entry.id === state.selectedLibrary),
      },
        el("p", { class: "library-statement", text: entry.statement }),
        el("div", { class: "library-row__meta" },
          el("span", { class: "pill", text: librarySourceLabel(entry) }),
          el("span", { class: "muted", text: formatWhen(entry["accepted-at"]) })),
        el("div", { class: "library-row__actions" }, use, removeBtn));
      row.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        state.selectedLibrary = entry.id;
        renderLibrary();
      });
      return row;
    }));
  box.replaceChildren(head, el("div", { class: "library-layout" }, list, renderLibraryDetail(selected)));
}

async function removeLibraryEntry(entry) {
  if (!confirm("Remove this statement from the library? The catalog is unchanged.")) return;
  try {
    const data = await call({ action: "library_remove", library: loadLibrary(), id: entry.id });
    saveLibrary(data.library);
    renderLibrary();
    if (state.view === "work" && state.selected?.control) {
      renderProps(controlById(state.selected.control), state.lastCheck[state.selected.control]);
    }
  } catch (err) { showError(err.message); }
}

function addControlFromLibrary(entry, { clauseId = "", riskId = "" } = {}) {
  ensureProject();
  const used = new Set(state.project.controls.map((c) => c.id));
  const base = riskId ? `${riskId}-L` : `${(clauseId || "L").replace(/[^A-Za-z0-9.]+/g, "")}-L`;
  let n = 1;
  let id = `${base}${n}`;
  while (used.has(id)) id = `${base}${++n}`;
  const control = {
    id, clause: clauseId, text: entry.statement, guidance: "", risk: "", who: "", notes: [],
    status: "draft", origin: "person",
    source_type: riskId ? "risk" : "clause",
    risk_id: riskId || "",
  };
  state.project.controls.push(control);
  state.selected = { control: id };
  saveLocal();
  showView("work");
  render();
  const box = $("#editor textarea.statement");
  if (box) box.focus();
  return control;
}

async function useLibraryEntry(entry, mode = "use") {
  try {
    await rememberStatement({ text: entry.statement, id: entry.id, source_type: entry["source-type"],
      risk_id: entry["risk-id"], parts: entry.parts }, { used: true });
  } catch (err) { showError(err.message); return; }
  const dialog = $("#library-pick");
  if (dialog && dialog.open) dialog.close();
  const current = state.selected?.control && controlById(state.selected.control);
  if (mode === "add" || !current) {
    if (!state.project && !state.selectedRisk) {
      return showError("Load a policy before using a library statement.");
    }
    const clauseId = current?.clause || state.selected?.clause || "";
    const riskId = current?.risk_id || state.selectedRisk || "";
    addControlFromLibrary(entry, { clauseId, riskId });
    return;
  }
  current.text = entry.statement;
  if (current.origin !== "person") current.origin = "person";
  saveLocal();
  showView("work");
  render();
  const box = $("#editor textarea.statement");
  if (box) box.focus();
}

function libraryPickRows(entries, { add = true } = {}) {
  if (!entries.length) return [el("p", { class: "placeholder", text: "No matching statements in the library." })];
  return entries.map((entry) => {
    const use = el("button", { type: "button", class: "btn btn--small btn--primary library-use", text: "Use" });
    const addBtn = add ? el("button", { type: "button", class: "btn btn--small", text: "Add" }) : null;
    use.addEventListener("click", () => useLibraryEntry(entry, "use"));
    if (addBtn) addBtn.addEventListener("click", () => useLibraryEntry(entry, "add"));
    const row = el("div", {
      class: "template-row library-pick", "data-library-id": entry.id,
      "aria-current": String(state.libraryPickId === entry.id),
    },
      el("p", { class: "library-statement", text: entry.statement }),
      el("p", { class: "muted", text: `${librarySourceLabel(entry)} · accepted ${formatWhen(entry["accepted-at"])}` }),
      el("div", { class: "suggestion__actions" }, use, addBtn));
    row.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      state.libraryPickId = entry.id;
      const list = $("#library-pick-list");
      if (list && $("#library-pick")?.open) renderLibraryPicks(list, $("#library-pick-search")?.value || "");
    });
    return row;
  });
}

function renderLibraryPickDetail(hits) {
  const box = $("#library-pick-detail");
  if (!box) return;
  const entry = hits.find((e) => e.id === state.libraryPickId) || hits[0];
  if (!entry) {
    box.replaceChildren(el("p", { class: "placeholder", text: "Select a statement." }));
    return;
  }
  state.libraryPickId = entry.id;
  const use = el("button", { type: "button", class: "btn btn--primary library-use", text: "Use" });
  const add = el("button", { type: "button", class: "btn", text: "Add" });
  use.addEventListener("click", () => useLibraryEntry(entry, "use"));
  add.addEventListener("click", () => useLibraryEntry(entry, "add"));
  box.replaceChildren(
    el("h3", { class: "library-detail__title", text: statementLead(entry.statement) }),
    el("p", { class: "library-detail__statement", text: entry.statement }),
    el("p", { class: "muted", text: `${librarySourceLabel(entry)} · OSCAL 1.1.2` }),
    el("div", { class: "actions" }, use, add),
  );
}

function renderLibraryPicks(container, query = "") {
  const entries = loadLibrary();
  const needle = (query || "").trim().toLowerCase();
  const hits = (needle
    ? entries.filter((e) => `${e.statement} ${e["risk-id"] || ""}`.toLowerCase().includes(needle))
    : entries).slice(0, 8);
  put(container, ...libraryPickRows(hits));
  renderLibraryPickDetail(hits);
}

function openLibraryPick() {
  const dialog = $("#library-pick");
  const list = $("#library-pick-list");
  const search = $("#library-pick-search");
  if (!dialog || !list) return;
  if (search) search.value = "";
  renderLibraryPicks(list, "");
  if (dialog.showModal) dialog.showModal();
}

function nextRiskId() {
  const used = new Set((state.project?.risks || []).map((r) => r.id));
  let n = 1;
  while (used.has(`R-${String(n).padStart(3, "0")}`)) n += 1;
  return `R-${String(n).padStart(3, "0")}`;
}

function uniqueControlId(base) {
  const used = new Set(state.project.controls.map((c) => c.id));
  if (!used.has(base)) return base;
  let n = 1;
  while (used.has(`${base}-${n}`)) n += 1;
  return `${base}-${n}`;
}

function scoreBadge(n) {
  const cls = n >= 15 ? "is-high" : n >= 8 ? "is-med" : "";
  return el("span", { class: `score-badge ${cls}`.trim(), text: String(n) });
}

function renderHeatmap(risks) {
  const counts = {};
  for (const r of risks) counts[`${r.likelihood},${r.impact}`] = (counts[`${r.likelihood},${r.impact}`] || 0) + 1;
  const cells = [];
  for (let impact = 5; impact >= 1; impact--) {
    cells.push(el("span", { class: "heat-label", text: String(impact) }));
    for (let likelihood = 1; likelihood <= 5; likelihood++) {
      const n = counts[`${likelihood},${impact}`] || 0;
      cells.push(el("div", { class: n ? "heat-cell is-hit" : "heat-cell", title: `Likelihood ${likelihood}, impact ${impact}`, text: n ? String(n) : "" }));
    }
  }
  cells.push(el("span", { class: "heat-label", text: "" }));
  for (let likelihood = 1; likelihood <= 5; likelihood++) cells.push(el("span", { class: "heat-label", text: String(likelihood) }));
  return el("div", { class: "heatmap-wrap" },
    el("h3", { text: "Inherent risk" }),
    el("div", { class: "heatmap", "aria-label": "Likelihood by impact" }, cells));
}

function openRiskForm(risk) {
  ensureProject();
  $("#risk-dialog-title").textContent = risk ? "Edit risk" : "Add a risk";
  $("#risk-editing").value = risk ? risk.id : "";
  $("#risk-title").value = risk ? risk.title : "";
  $("#risk-description").value = risk ? risk.description : "";
  $("#risk-asset").value = risk ? risk.asset : "";
  $("#risk-owner").value = risk ? risk.owner : "";
  $("#risk-threat").value = risk ? risk.threat : "";
  $("#risk-vulnerability").value = risk ? risk.vulnerability : "";
  $("#risk-likelihood").value = risk ? risk.likelihood : 3;
  $("#risk-impact").value = risk ? risk.impact : 3;
  $("#risk-status").value = risk ? risk.status : "identified";
  $("#risk-form-error").hidden = true;
  $("#risk-dialog").showModal();
}

function saveRiskFromForm() {
  const title = $("#risk-title").value.trim();
  if (!title) throw new Error("Enter a scenario title.");
  const likelihood = Number($("#risk-likelihood").value);
  const impact = Number($("#risk-impact").value);
  if (!(likelihood >= 1 && likelihood <= 5) || !(impact >= 1 && impact <= 5)) {
    throw new Error("Likelihood and impact must be numbers from 1 to 5.");
  }
  ensureProject();
  const editing = $("#risk-editing").value;
  const risk = {
    id: editing || nextRiskId(),
    title,
    description: $("#risk-description").value.trim(),
    asset: $("#risk-asset").value.trim(),
    likelihood, impact, score: likelihood * impact,
    threat: $("#risk-threat").value.trim(),
    vulnerability: $("#risk-vulnerability").value.trim(),
    owner: $("#risk-owner").value.trim(),
    status: $("#risk-status").value || "identified",
  };
  const at = state.project.risks.findIndex((r) => r.id === risk.id);
  if (at >= 0) state.project.risks[at] = risk;
  else state.project.risks.push(risk);
  state.selectedRisk = risk.id;
  saveLocal();
  showView("risks");
  renderRisks();
}

function openRiskImport() {
  $("#risk-file").click();
}

async function previewRiskFile(file) {
  const payload = await readFile(file);
  const parsed = await call({ action: "import_risks", ...payload });
  state.importPreview = parsed;
  $("#risk-import-summary").textContent =
    `${parsed.risks.length} ${parsed.risks.length === 1 ? "risk" : "risks"} recognised`
    + (parsed.errors?.length ? ` · ${parsed.errors.length} row${parsed.errors.length === 1 ? "" : "s"} skipped` : "")
    + ". Nothing left this device.";
  const fields = ["", ...RISK_FIELDS];
  const rows = (parsed.columns || []).map((col, i) => {
    const match = (parsed.recognised || []).find((r) => r.column === col || r.index === i);
    const select = el("select", { "data-col": String(i), "aria-label": `Map ${col}` },
      fields.map((f) => el("option", { value: f, text: f || "(ignore)" })));
    if (match) select.value = match.field;
    const tick = el("span", { class: match ? "mapping-tick" : "muted", text: match ? "Recognised" : "Map this column" });
    return el("div", { class: "mapping-row" }, el("strong", { text: col }), tick, select);
  });
  $("#risk-mapping").replaceChildren(...(rows.length ? rows : [el("p", { class: "placeholder", text: "No columns found." })]));
  const err = $("#risk-import-errors");
  if (parsed.errors?.length) {
    err.hidden = false;
    err.textContent = parsed.errors.map((e) => `Row ${e.row}: ${e.error}`).join(" · ");
  } else {
    err.hidden = true;
    err.textContent = "";
  }
  $("#risk-import-dialog").showModal();
}

function mappingFromDialog() {
  const mapping = {};
  for (const sel of $$("#risk-mapping select")) {
    if (sel.value) mapping[sel.dataset.col] = sel.value;
  }
  return mapping;
}

async function applyRiskImport() {
  const preview = state.importPreview;
  if (!preview) throw new Error("Choose a CSV or JSON file first.");
  const file = $("#risk-file");
  let parsed = preview;
  const mapping = mappingFromDialog();
  if (preview.columns?.length && file.files[0]) {
    const payload = await readFile(file.files[0]);
    parsed = await call({ action: "import_risks", ...payload, mapping });
  }
  ensureProject();
  const byId = Object.fromEntries(state.project.risks.map((r, i) => [r.id, i]));
  for (const r of parsed.risks) {
    if (r.id in byId) state.project.risks[byId[r.id]] = r;
    else {
      byId[r.id] = state.project.risks.length;
      state.project.risks.push(r);
    }
  }
  state.importPreview = null;
  if (parsed.risks[0]) state.selectedRisk = parsed.risks[0].id;
  saveLocal();
  showView("risks");
  renderRisks();
}

function appendRiskControls(data) {
  const incoming = (data.controls || []).map((c) => ({ ...c, id: uniqueControlId(c.id) }));
  state.project.controls.push(...incoming);
  Object.assign(state.scores, data.scores || {});
  if (incoming[0]) state.selected = { control: incoming[0].id };
  saveLocal();
  closeRecommendDialog();
  showView("work");
  render();
}

async function addRiskTemplate(risk, templateId, status, button) {
  await busy(button, "Adding…", async () => {
    const data = await call({ action: "draft_risk_controls", risk, template_ids: [templateId] });
    if (status && data.controls[0]) data.controls[0].status = status;
    appendRiskControls(data);
    if (status === "accepted" && data.controls[0]) {
      try { await rememberStatement(data.controls[0]); } catch (err) { showError(err.message); }
      if (state.view === "work" && state.selected?.control) {
        renderProps(controlById(state.selected.control), state.lastCheck[state.selected.control]);
      }
    }
  });
}

function dismissTemplate(riskId, templateId) {
  state.dismissedTemplates[riskId] = [...(state.dismissedTemplates[riskId] || []), templateId];
  const risk = riskById(riskId);
  if (state.view === "risks") renderRisks();
  if ($("#recommend-dialog")?.open && risk) fillRecommendList($("#recommend-list"), risk, { heading: false });
}

async function aiDraftRisk(risk) {
  const prompt = await call({ action: "ai_prompt", risk });
  const reply = await PROVIDERS[ai.provider].send(ai.key, ai.model, prompt);
  return call({ action: "ai_reply", risk_id: risk.id, source_type: "risk", reply, model: ai.model });
}

async function aiRedraftRisk(risk, button) {
  if (!aiReady()) return openAiDialog();
  const existing = controlsOfRisk(risk.id);
  if (existing.some((c) => c.status !== "draft" || (c.origin !== "rules" && c.origin !== "ai"))
      && !confirm(`Replace the ${plural(existing.length, "control")} from this risk, including your edits, with AI drafts?`)) return;
  await busy(button, "Drafting with AI…", async () => {
    const data = await aiDraftRisk(risk);
    for (const c of controlsOfRisk(risk.id)) { delete state.scores[c.id]; state.checked.delete(c.id); }
    state.project.controls = state.project.controls.filter((c) => c.risk_id !== risk.id);
    state.project.controls.push(...data.controls);
    Object.assign(state.scores, data.scores);
    state.selected = data.controls[0] ? { control: data.controls[0].id } : null;
    saveLocal();
    showView("work");
    render();
  });
}

function riskCategory(risk) {
  return ((risk.asset || risk.threat || "Uncategorised").trim()) || "Uncategorised";
}

function riskHasControls(risk) {
  return controlsOfRisk(risk.id).length > 0;
}

function closeRecommendDialog() {
  const dialog = $("#recommend-dialog");
  if (dialog && dialog.open) dialog.close();
  state.recommendRiskId = null;
}

function fillRecommendList(container, risk, { heading = true } = {}) {
  if (!container || !risk) return;
  container.replaceChildren(el("p", { class: "placeholder", text: "Loading templates…" }));
  call({ action: "suggest_risk_controls", risk }).then((data) => {
    const hidden = new Set(state.dismissedTemplates[risk.id] || []);
    const visible = data.suggestions.filter((s) => !hidden.has(s.id));
    const rows = visible.map((s) => {
      const add = el("button", { type: "button", class: "btn btn--small", text: "Add", "data-template": s.id });
      const accept = el("button", { type: "button", class: "btn btn--small btn--primary", text: "Accept" });
      const dismiss = el("button", { type: "button", class: "btn btn--small", text: "Dismiss" });
      add.addEventListener("click", () => addRiskTemplate(risk, s.id, "draft", add));
      accept.addEventListener("click", () => addRiskTemplate(risk, s.id, "accepted", accept));
      dismiss.addEventListener("click", () => dismissTemplate(risk.id, s.id));
      return el("div", { class: "template-row", "data-template": s.id },
        el("p", {}, el("strong", { text: s.label }), " — ", s.statement),
        el("div", { class: "suggestion__actions" }, add, accept, dismiss));
    });
    const aiBtn = aiReady() ? el("button", { type: "button", class: "btn btn--small", text: "Draft with AI" }) : null;
    if (aiBtn) aiBtn.addEventListener("click", () => aiRedraftRisk(risk, aiBtn));
    const lib = loadLibrary().slice(0, 4);
    const title = $("#recommend-title");
    if (title && container.id === "recommend-list") {
      title.textContent = `Add ${visible.length} recommended control${visible.length === 1 ? "" : "s"}?`;
    }
    put(container,
      heading ? el("h3", { class: "props-card__title", text: "Recommended controls" }) : null,
      rows.length ? rows : el("p", { class: "placeholder", text: "No matching templates. Add a control from the editor." }),
      lib.length ? el("h3", { class: "props-card__title", text: "From library" }) : null,
      lib.length ? libraryPickRows(lib, { add: true }) : null,
      aiBtn,
      el("p", { class: "disclaimer", text: "Templates are deterministic. Optional AI may produce inaccurate wording." }),
    );
  }).catch((err) => { container.replaceChildren(el("p", { class: "placeholder", text: err.message })); });
}

function openRecommendDialog(risk) {
  const dialog = $("#recommend-dialog");
  if (!dialog || !risk) return;
  state.recommendRiskId = risk.id;
  state.selectedRisk = risk.id;
  const scenario = $("#recommend-scenario");
  if (scenario) scenario.textContent = risk.description || risk.title;
  fillRecommendList($("#recommend-list"), risk, { heading: false });
  if (dialog.showModal && !dialog.open) dialog.showModal();
}

async function addAllRecommended(button) {
  const risk = riskById(state.recommendRiskId || state.selectedRisk);
  if (!risk) return;
  await busy(button, "Adding…", async () => {
    const data = await call({ action: "suggest_risk_controls", risk });
    const hidden = new Set(state.dismissedTemplates[risk.id] || []);
    const ids = data.suggestions.filter((s) => !hidden.has(s.id)).map((s) => s.id);
    if (!ids.length) return;
    const drafted = await call({ action: "draft_risk_controls", risk, template_ids: ids });
    appendRiskControls(drafted);
    showNotice("Successfully added recommended controls");
  });
}

function removeRisk(risk) {
  if (!state.project) return;
  if (!confirm("Remove this risk from the register? Catalog controls stay.")) return;
  state.project.risks = state.project.risks.filter((r) => r.id !== risk.id);
  if (state.selectedRisk === risk.id) state.selectedRisk = null;
  saveLocal();
  renderRisks();
}

function renderRiskSubnav() {
  return el("nav", { class: "subnav", id: "risks-subnav", "aria-label": "Risk views" },
    [["library", "Library"], ["register", "Register"]].map(([id, label]) => {
      const b = el("button", {
        type: "button", class: "subnav__btn", "data-risk-pane": id,
        "aria-pressed": String(state.riskPane === id), text: label,
      });
      b.addEventListener("click", () => { state.riskPane = id; renderRisks(); });
      return b;
    }));
}

function riskSearchInput() {
  const search = el("input", {
    id: "risk-search", type: "search", placeholder: "Search",
    "aria-label": "Search risks", autocomplete: "off",
  });
  search.value = state.riskQuery || "";
  search.addEventListener("input", () => {
    state.riskQuery = search.value;
    renderRisks();
    const again = $("#risk-search");
    if (again) { again.focus(); again.setSelectionRange(search.value.length, search.value.length); }
  });
  return search;
}

function filteredRisks(risks) {
  const query = (state.riskQuery || "").trim().toLowerCase();
  if (!query) return risks;
  return risks.filter((r) => `${r.title} ${r.asset || ""} ${r.threat || ""} ${r.id} ${r.owner || ""}`.toLowerCase().includes(query));
}

function renderRiskLibrary(risks) {
  const rows = filteredRisks(risks).map((r) => {
    const added = riskHasControls(r);
    const add = el("button", {
      type: "button", class: "btn btn--small btn--primary risk-add-controls",
      text: added ? "Add more" : "Add",
    });
    add.addEventListener("click", (e) => { e.stopPropagation(); openRecommendDialog(r); });
    const remove = el("button", { type: "button", class: "btn btn--small risk-remove", text: "Remove" });
    remove.addEventListener("click", (e) => { e.stopPropagation(); removeRisk(r); });
    const open = el("button", { type: "button", class: "risk-scenario", text: r.title });
    open.addEventListener("click", () => { state.selectedRisk = r.id; state.riskPane = "register"; renderRisks(); });
    return el("tr", { class: "risk-library-row", "data-risk-id": r.id, "aria-current": String(state.selectedRisk === r.id) },
      el("td", {}, open, r.description ? el("p", { class: "muted risk-library-desc", text: r.description }) : null),
      el("td", {}, el("span", { class: "pill", text: riskCategory(r) })),
      el("td", { class: "risk-library-actions" },
        added ? el("span", { class: "ready-chip is-ready", text: "Added" }) : null,
        add, remove));
  });
  return el("div", { class: "catalog-body" },
    el("table", { class: "data-table risk-library-table" },
      el("thead", {}, el("tr", {},
        el("th", { text: "Scenario" }), el("th", { text: "Category" }), el("th", { text: "Add recommended" }))),
      el("tbody", {}, rows.length ? rows : el("tr", {},
        el("td", { colspan: "3" }, el("p", { class: "placeholder", text: "No scenarios match that search." }))))));
}

function renderRiskDrawer(risk) {
  const linked = controlsOfRisk(risk.id);
  const open = (c) => { showView("work"); select({ control: c.id }); };
  const suggestionsBox = el("div", { id: "risk-templates", class: "recommend-panel props-card" },
    el("h3", { class: "props-card__title", text: "Recommended controls" }),
    el("p", { class: "placeholder", text: "Loading templates…" }));
  fillRecommendList(suggestionsBox, risk);
  const edit = el("button", { type: "button", class: "btn btn--small", text: "Edit" });
  edit.addEventListener("click", () => openRiskForm(risk));
  const openModal = el("button", { type: "button", class: "btn btn--small btn--primary", text: "Add recommended controls" });
  openModal.addEventListener("click", () => openRecommendDialog(risk));
  return el("aside", { class: "risk-drawer", id: "risk-drawer", "aria-label": "Risk details" },
    el("h3", { class: "section-title", text: risk.title }),
    el("p", { class: "muted", text: `${risk.id} · score ${risk.score} · ${RISK_STATUS_LABELS[risk.status] || risk.status}` }),
    risk.description ? el("p", { text: risk.description }) : null,
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Category" }),
      el("span", { class: "prop-row__value" }, el("span", { class: "pill", text: riskCategory(risk) }))),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Asset" }), el("span", { class: "prop-row__value", text: risk.asset || "—" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Owner" }), el("span", { class: "prop-row__value", text: risk.owner || "—" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Threat" }), el("span", { class: "prop-row__value", text: risk.threat || "—" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Vulnerability" }), el("span", { class: "prop-row__value", text: risk.vulnerability || "—" })),
    el("p", { class: "subitems__head", text: `Linked controls (${linked.length})` }),
    linked.length ? linked.map((c) => {
      const b = el("button", { type: "button", class: "linked-ctl", text: c.text || "(empty)" });
      b.addEventListener("click", () => open(c));
      return b;
    }) : el("p", { class: "placeholder", text: "None yet. Add a template below." }),
    suggestionsBox,
    el("div", { class: "actions" }, edit, openModal),
  );
}

function renderRisks() {
  const box = $("#risks-body");
  if (!box) return;
  const risks = state.project?.risks || [];
  const add = () => openRiskForm(null);
  const library = state.riskPane === "library";
  const title = library ? "Risk library" : "Risk register";
  const lede = library
    ? "Select the risks that apply, then add recommended control statements. Nothing is uploaded."
    : "Review each identified risk, then draft and accept control statements.";
  if (!risks.length) {
    box.replaceChildren(
      renderRiskSubnav(),
      el("div", { class: "view-head" },
        el("h2", { id: "risks-title", class: "section-title section-title--first", text: title }),
        el("p", { class: "view-head__lede", text: "Identify risks on this device and draft control statements from them." })),
      emptyState("No risks yet.", "Create", add, "empty--list",
        [{ label: "Import", onClick: openRiskImport }]),
    );
    const createBtn = box.querySelector(".empty__actions .btn--primary");
    if (createBtn) createBtn.id = "risk-add";
    const importBtn = box.querySelector(".empty__actions .btn:not(.btn--primary)");
    if (importBtn) importBtn.id = "risk-import";
    return;
  }
  const addBtn = el("button", { type: "button", class: "btn btn--primary", id: "risk-add", text: "Add scenario" });
  const importBtn = el("button", { type: "button", class: "btn", id: "risk-import", text: "Import" });
  addBtn.addEventListener("click", add);
  importBtn.addEventListener("click", openRiskImport);
  const shown = filteredRisks(risks);
  const body = shown.map((r) => {
    const open = el("button", { type: "button", text: r.title });
    open.addEventListener("click", () => { state.selectedRisk = r.id; renderRisks(); });
    return el("tr", { "aria-current": String(state.selectedRisk === r.id) },
      el("td", { text: r.id }),
      el("td", {}, open),
      el("td", {}, el("span", { class: "pill", text: riskCategory(r) })),
      el("td", { text: r.owner || "—" }),
      el("td", {}, scoreBadge(r.score)),
      el("td", {}, el("span", { class: `state ${r.status === "accepted" ? "state--accepted" : "state--draft"}`, text: RISK_STATUS_LABELS[r.status] || r.status })));
  });
  const table = el("table", { class: "data-table risk-table" },
    el("thead", {}, el("tr", {},
      el("th", { text: "ID" }), el("th", { text: "Scenario" }), el("th", { text: "Category" }),
      el("th", { text: "Owner" }), el("th", { text: "Inherent" }), el("th", { text: "Status" }))),
    el("tbody", {}, body.length ? body : el("tr", {},
      el("td", { colspan: "6" }, el("p", { class: "placeholder", text: "No risks match that search." })))));
  const selected = riskById(state.selectedRisk) || shown[0] || risks[0];
  if (selected && !state.selectedRisk) state.selectedRisk = selected.id;
  const main = el("div", { class: "risks-main" },
    el("div", { class: "grc-card" }, renderHeatmap(risks)),
    table);
  box.replaceChildren(
    renderRiskSubnav(),
    el("div", { class: "risks-toolbar" },
      el("div", { class: "view-head" },
        el("h2", { id: "risks-title", class: "section-title section-title--first", text: title }),
        el("p", { class: "view-head__lede", text: lede })),
      el("div", { class: "actions" }, riskSearchInput(), importBtn, addBtn)),
    library
      ? renderRiskLibrary(risks)
      : el("div", { class: "risks-layout" }, main, selected ? renderRiskDrawer(selected) : null),
  );
  renderCrumb();
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

async function setStatus(ids, status) {
  for (const id of ids) {
    const c = controlById(id);
    if (c) c.status = status;
  }
  saveLocal();
  render();
  if (status === "accepted") {
    for (const id of ids) {
      const c = controlById(id);
      if (c && (c.text || "").trim()) {
        try { await rememberStatement(c); } catch (err) { showError(err.message); }
      }
    }
    if (state.view === "library") renderLibrary();
    else if (state.view === "work" && state.selected?.control) {
      renderProps(controlById(state.selected.control), state.lastCheck[state.selected.control]);
    }
  }
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
  const control = { id, clause: clause.id, text: "", guidance: "", risk: "", who: "", notes: [], status: "draft", origin: "person", source_type: "clause", risk_id: "" };
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
  await busy(button, "Preparing…", async () => {
    let out;
    if (format === "library-json" || format === "library-csv") {
      out = await call({
        action: "library_export",
        library: loadLibrary(),
        format: format === "library-json" ? "json" : "csv",
      });
    } else {
      if (!state.project) throw new Error("Load a policy before exporting.");
      out = await call({ action: "export", format, project: state.project });
    }
    if (out.content_base64) {
      const bytes = Uint8Array.from(atob(out.content_base64), (ch) => ch.charCodeAt(0));
      download(out.name, out.mime, new Blob([bytes], { type: out.mime }));
    } else {
      download(out.name, out.mime, out.content);
    }
  });
  const dialog = $("#export-dialog");
  if (dialog && dialog.open) dialog.close();
}

function openExportDialog() {
  if (!state.project) return showError("Load a policy before exporting.");
  const dialog = $("#export-dialog");
  if (dialog && dialog.showModal) dialog.showModal();
}

// ---------------------------------------------------------------- guide

function renderGuide() {
  const g = state.guide;
  if (!g) return;
  $("#guide-summary").textContent = g.guide.summary;
  $("#guide-list").replaceChildren(...Object.values(g.guide.practices).map((p) =>
    el("article", { class: "guide" },
      el("h3", { text: p.title }),
      el("p", { class: "guide__why", text: p.why }),
      el("p", { class: "guide__how", text: p.how }),
      el("div", { class: "guide__examples" },
        el("figure", { class: "example example--weak" }, el("figcaption", { text: "Weak" }), el("blockquote", { text: p.weak })),
        el("figure", { class: "example example--strong" }, el("figcaption", { text: "Strong" }), el("blockquote", { text: p.strong }))))));
}

// ---------------------------------------------------------------- wiring

function init() {
  if (BROWSER) for (const n of $$("[data-browser-only]")) n.hidden = false;

  for (const b of $$("[data-nav]")) {
    b.addEventListener("click", () => {
      if (b.dataset.nav === "export") return openExportDialog();
      showView(b.dataset.view || b.dataset.nav);
    });
  }

  $("#splash-continue")?.addEventListener("click", dismissSplash);
  $("#result-continue")?.addEventListener("click", continueFromResult);

  $("#paste-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const text = form.elements.namedItem("text").value;
    if (!text.trim()) return showError("Paste the policy clauses first.");
    busy($("#paste-submit"), "Codifying…", async () => openProject(await call({
      action: "open", name: "pasted text", text,
    }), { resultStep: true }));
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
    openProject(await call({ action: "open", name: "acme-information-security-policy-2016.md", content: text }), { resultStep: true });
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
    state.resultStep = false;
    showView("workspace");
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

  const openExport = () => openExportDialog();
  $("#export-open-top")?.addEventListener("click", openExport);
  for (const b of $$("[data-export]")) b.addEventListener("click", () => exportAs(b.dataset.export, b));

  $("#risk-form")?.addEventListener("submit", (e) => {
    const action = e.submitter ? e.submitter.value : "cancel";
    if (action !== "save") return;
    e.preventDefault();
    try {
      saveRiskFromForm();
      $("#risk-dialog").close();
    } catch (err) {
      const box = $("#risk-form-error");
      box.textContent = err.message;
      box.hidden = false;
    }
  });
  $("#risk-import-form")?.addEventListener("submit", (e) => {
    if ((e.submitter ? e.submitter.value : "") !== "import") return;
    e.preventDefault();
    busy($("#risk-import-apply"), "Importing…", async () => {
      await applyRiskImport();
      $("#risk-import-dialog").close();
    });
  });
  $("#risk-file")?.addEventListener("change", () => {
    const file = $("#risk-file").files[0];
    if (!file) return;
    busy(null, "", async () => previewRiskFile(file));
  });
  $("#library-pick-search")?.addEventListener("input", () => {
    const list = $("#library-pick-list");
    if (list) renderLibraryPicks(list, $("#library-pick-search").value);
  });
  $("#recommend-add")?.addEventListener("click", (e) => addAllRecommended(e.currentTarget));
  $("#recommend-dialog")?.addEventListener("close", () => { state.recommendRiskId = null; });

  $("#sidebar-toggle")?.addEventListener("click", () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    $("#sidebar-toggle").setAttribute("aria-expanded", String(!collapsed));
    $("#sidebar-toggle").setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && state.project) {
      const c = state.selected?.control && controlById(state.selected.control);
      if (c) {
        e.preventDefault();
        setStatus([c.id], "accepted");
      }
      return;
    }
    if (e.key === "Escape" && $("#export-dialog")?.open) {
      $("#export-dialog").close();
      e.preventDefault();
      return;
    }
    if (e.key === "Escape" && $("#library-pick")?.open) {
      $("#library-pick").close();
      e.preventDefault();
      return;
    }
    if (e.key === "Escape" && $("#recommend-dialog")?.open) {
      closeRecommendDialog();
      e.preventDefault();
      return;
    }
    if (!state.project || $("#work").hidden || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest("dialog, input, textarea, select, [contenteditable]")) return;
    const c = state.selected?.control && controlById(state.selected.control);
    if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); step(1); }
    else if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); step(-1); }
    else if (e.key === "Escape" && state.selected) { e.preventDefault(); state.selected = null; render(); }
    else if (e.key === "r" && c) setStatus([c.id], "reviewed");
    else if (e.key === "a" && c) setStatus([c.id], "accepted");
  });

  backend.config().then((c) => { state.config = c; }).catch(() => {});
  backend.guide().then((g) => { state.guide = g; renderGuide(); }).catch(() => {});
  showView("workspace");
  if (BROWSER) startPython().catch(() => {});  // warm up while the person reads the page
}

init();
