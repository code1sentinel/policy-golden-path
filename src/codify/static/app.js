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
  Risks: "Identified risks you already have. Control statements exist to address them. Not a register.",
  "Identified risks": "Risks you already identified. Control statements exist to address them. Not a register.",
};
const PART_HELP = {
  action: "Start with the verb (Review, Restrict, Encrypt).",
  scope: "Say what this applies to (which systems, people, or data).",
  limit: "Add a time limit to make this testable (for example, every [90] days).",
  purpose: "Say why this control exists — the risk it treats.",
};
const SCORE_HELP = "How complete this statement is: testable, scoped, action-first, and has a purpose. 80% or more is usually ready to accept.";
const READY = 0.8;  // drafts at or above this score can be selected for review in bulk
const SAVE_KEY = "codify:project";
const LIBRARY_KEY = "codify:statements";
const GUIDE_KEY = "codify:step-guides";
const LEGACY_RISKS_KEY = "codify:risks";  // leftover store from older builds; never rewrite statements
const ENACT_APP = "https://code1sentinel.github.io/enact/";
const ENACT_DOC = "https://github.com/code1sentinel/policy-golden-path/blob/main/docs/book/enact.md";

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
  selectedLibrary: null, // library entry id
  libraryPickId: null,
  resultStep: false,   // short "here's what we drafted" before the 3-pane workspace
  selectedRisk: null,  // identified-risk id
  suggestRiskId: null,
  suggestPicked: new Set(),
  suggestAi: [],
  flowStep: null,      // risks | controls | clause | link | review | enact
  startPath: null,     // "clause" when the paste form is showing
  guideDismissed: {},
  identifyFocus: null, // selector to focus after the identify list re-renders
  selectedStatementKey: null, // risk:<id> or clause:<id> on the statements page
  statementFocus: null,
  statementLibraryTarget: null,
};

const STEP_LABELS = {
  risks: "Identify risks",
  controls: "Control statements",
  clause: "Paste a clause",
  link: "Link to risks",
  review: "Review",
  enact: "Send to Enact",
};

const STEP_GUIDES = {
  risks: {
    title: "Identify risks",
    what: "Enter each risk you already identified: a short statement, and an optional note.",
    why: "Control statements exist to treat a risk. Start there so coverage is visible.",
    example: "Screens left unlocked at unattended desks.",
    mistakes: "Do not score likelihood or impact. Do not assign owners. This is not a register.",
  },
  controls: {
    title: "Develop control statements",
    what: "For each risk, write one or more statements that treat it. Suggest matching wording from the library on this device.",
    why: "A risk with no control is uncovered. Every risk needs at least one non-empty statement.",
    example: "Require users to lock screens when they leave their desk.",
    mistakes: "Empty wording does not count. Do not skip a risk. Product names belong in guidance.",
  },
  clause: {
    title: "Paste a clause",
    what: "Paste a policy clause. Codify drafts control statements from requirements.",
    why: "Use this when you have policy wording and still need those drafts to treat identified risks.",
    example: "Access to systems shall be granted on a need-to-know basis.",
    mistakes: "A clause is context. You still link every draft to a risk on the next step.",
  },
  link: {
    title: "Link to risks",
    what: "Link every control to an identified risk. Add a risk here if you do not have one yet.",
    why: "Unlinked controls have no purpose in the catalog trace.",
    example: "Lock-screens draft → R-001 Screens left unlocked.",
    mistakes: "Leaving a control unlinked, or a risk with no control, blocks review.",
  },
  review: {
    title: "Review",
    what: "Check coverage, edit statements, and accept the wording you will keep.",
    why: "Accept is what puts a statement in the catalog you send to Enact.",
    example: "Every risk shows at least one accepted control. Unlinked rows are flagged.",
    mistakes: "Export is blocked until every risk has an accepted control statement.",
  },
  enact: {
    title: "Send to Enact",
    what: "Download the OSCAL catalog on this device, then open it in Enact. This turns control statements into testable Rego policy.",
    why: "Codify writes the catalog. Enact runs the checks as Rego. They share a file, not a server.",
    example: "Save catalog.json, open Enact, load that file.",
    mistakes: "Codify does not upload the catalog. If download is blocked, accept coverage first.",
  },
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

function dropLegacyRiskStore() {
  try { localStorage.removeItem(LEGACY_RISKS_KEY); } catch { /* ignore */ }
}

const REGISTER_FIELDS = ["likelihood", "impact", "score", "owner", "asset", "threat", "vulnerability"];
const REGISTER_STATUSES = ["identified", "treating", "accepted", "closed"];
const MATCH_STOP = new Set([
  "a", "an", "and", "are", "as", "at", "be", "by", "due", "for", "from", "in", "into",
  "is", "it", "of", "on", "or", "that", "the", "this", "to", "when", "with", "without",
]);

function isRegisterRisk(raw) {
  if (!raw || typeof raw !== "object") return true;
  if (REGISTER_FIELDS.some((key) => key in raw)) return true;
  if (REGISTER_STATUSES.includes(raw.status)) return true;
  return !String(raw.statement || "").trim();
}

function nextRiskId(risks) {
  let n = 0;
  for (const risk of risks) {
    const match = /^R-(\d{3,})$/.exec(risk.id || "");
    if (match) n = Math.max(n, parseInt(match[1], 10));
  }
  return `R-${String(n + 1).padStart(3, "0")}`;
}

function cleanRisks(value) {
  if (!Array.isArray(value)) return [];
  const out = [];
  const seen = new Set();
  for (const raw of value) {
    if (isRegisterRisk(raw)) continue;
    const statement = String(raw.statement || "").trim().replace(/\s+/g, " ");
    const note = String(raw.note || "").trim().replace(/\s+/g, " ");
    let id = String(raw.id || "").trim();
    if (!id || seen.has(id) || !/^R-\d{3,}$/.test(id)) id = nextRiskId(out);
    seen.add(id);
    out.push({ id, statement, note });
  }
  return out;
}

function dropLegacyRegister(project) {
  dropLegacyRiskStore();
  if (!project || typeof project !== "object") return project;
  if (project.authoring_path !== "risks") delete project.authoring_path;
  project.risks = cleanRisks(project.risks);
  const known = new Set(project.risks.map((r) => r.id));
  if (Array.isArray(project.controls)) {
    for (const control of project.controls) {
      if (!control || typeof control !== "object") continue;
      control.risk_ids = Array.isArray(control.risk_ids)
        ? control.risk_ids.filter((id) => known.has(id)) : [];
      delete control.risk_id;
      control.source_type = "clause";
    }
  }
  return project;
}

function matchTokens(text) {
  return new Set((String(text || "").toLowerCase().match(/[a-z0-9]{4,}/g) || []).filter((w) => !MATCH_STOP.has(w)));
}

function matchLibrary(entries, statement) {
  const needle = matchTokens(statement);
  if (!needle.size) return [];
  const ranked = [];
  for (const entry of entries) {
    const purpose = entry.parts && typeof entry.parts === "object" ? (entry.parts.purpose || "") : "";
    const overlap = [...needle].filter((w) => matchTokens(`${entry.statement || ""} ${purpose}`).has(w));
    if (overlap.length) ranked.push({ n: overlap.length, entry });
  }
  ranked.sort((a, b) => b.n - a.n || String(a.entry.id).localeCompare(String(b.entry.id)));
  return ranked.map((row) => row.entry);
}

function coverageFlags(project) {
  const linked = new Set();
  const unlinked = [];
  for (const control of project.controls || []) {
    const ids = control.risk_ids || [];
    if (!ids.length) unlinked.push(control.id);
    for (const id of ids) linked.add(id);
  }
  const uncovered = (project.risks || []).filter((r) => !linked.has(r.id)).map((r) => r.id);
  return { uncovered, unlinked };
}

function purposeFromRisks(project, ids) {
  const byId = Object.fromEntries((project.risks || []).map((r) => [r.id, r.statement]));
  return ids.map((id) => byId[id]).filter(Boolean).join(" ");
}

function riskById(id) {
  return (state.project && state.project.risks || []).find((r) => r.id === id) || null;
}

function controlsForRisk(id) {
  return (state.project.controls || []).filter((c) => (c.risk_ids || []).includes(id));
}

function authoringPath(project) {
  return project && project.authoring_path === "risks" ? "risks" : "clauses";
}

function flowSteps(project) {
  return authoringPath(project) === "risks"
    ? ["risks", "controls", "review", "enact"]
    : ["clause", "controls", "link", "review", "enact"];
}

function nonemptyControls(project) {
  return (project.controls || []).filter((c) => String(c.text || "").trim());
}

function identifiedRisks(project) {
  return (project.risks || []).filter((r) => String(r.statement || "").trim());
}

function linkedControlsFor(project, riskId) {
  return nonemptyControls(project).filter((c) => (c.risk_ids || []).includes(riskId));
}

function uncoveredRiskIds(project) {
  return identifiedRisks(project).filter((r) => !linkedControlsFor(project, r.id).length).map((r) => r.id);
}

function unlinkedControlIds(project) {
  return nonemptyControls(project).filter((c) => !(c.risk_ids || []).length).map((c) => c.id);
}

function unacceptedRiskIds(project) {
  return identifiedRisks(project)
    .filter((r) => !linkedControlsFor(project, r.id).some((c) => c.status === "accepted"))
    .map((r) => r.id);
}

function stepComplete(project, step) {
  if (!project) return false;
  if (step === "risks") return identifiedRisks(project).length > 0;
  if (step === "controls") {
    if (authoringPath(project) === "clauses") {
      const items = statementItemsFor(project);
      return items.length > 0 && items.every((item) => item.covered);
    }
    return identifiedRisks(project).length > 0 && uncoveredRiskIds(project).length === 0;
  }
  if (step === "clause") return nonemptyControls(project).length > 0 || (project.clauses || []).length > 0;
  if (step === "link") {
    return identifiedRisks(project).length > 0 && uncoveredRiskIds(project).length === 0 && unlinkedControlIds(project).length === 0;
  }
  if (step === "review" || step === "enact") return canExport(project)[0];
  return false;
}

function canAdvance(project, step) {
  if (step === "risks") {
    return identifiedRisks(project).length
      ? [true, ""]
      : [false, "Add at least one identified risk to continue."];
  }
  if (step === "controls") {
    if (authoringPath(project) === "clauses") {
      const items = statementItemsFor(project);
      if (!items.length || items.some((item) => !item.covered)) {
        return [false, "Every clause needs at least one control statement."];
      }
      return [true, ""];
    }
    if (!identifiedRisks(project).length || uncoveredRiskIds(project).length) {
      return [false, "Every risk needs at least one control statement."];
    }
    return [true, ""];
  }
  if (step === "clause") {
    if (nonemptyControls(project).length || (project.clauses || []).length) return [true, ""];
    return [false, "Paste a policy clause to draft control statements."];
  }
  if (step === "link") {
    if (!identifiedRisks(project).length) {
      return [false, "Add at least one identified risk and link each control to it."];
    }
    if (unlinkedControlIds(project).length) {
      return [false, "Link every control statement to an identified risk."];
    }
    if (uncoveredRiskIds(project).length) {
      return [false, "Every risk needs at least one control statement."];
    }
    return [true, ""];
  }
  if (step === "review") return canExport(project);
  return [true, ""];
}

function canExport(project) {
  if (!project || !identifiedRisks(project).length) {
    return [false, "Add at least one identified risk before exporting."];
  }
  if (unlinkedControlIds(project).length) {
    return [false, "Link every control statement to an identified risk before exporting."];
  }
  if (unacceptedRiskIds(project).length) {
    return [false, "Every risk needs an accepted control statement before you can send this to Enact."];
  }
  return [true, ""];
}

function firstIncompleteStep(project) {
  for (const step of flowSteps(project)) {
    if (!stepComplete(project, step)) return step;
  }
  return "enact";
}

function saveLocal() {
  if (!state.project) return;
  try {
    dropLegacyRegister(state.project);
    localStorage.setItem(SAVE_KEY, JSON.stringify({
      project: state.project, scores: state.scores, saved: new Date().toISOString(), flowStep: state.flowStep,
    }));
  } catch { /* storage full or unavailable: the OSCAL file is the real save */ }
}
const saveSoon = debounce(saveLocal, 600);

function loadLocal() {
  try {
    const data = JSON.parse(localStorage.getItem(SAVE_KEY) || "null");
    if (!(data && data.project && Array.isArray(data.project.controls))) return null;
    data.project = dropLegacyRegister(data.project);
    if (data.project.authoring_path !== "risks") delete data.project.authoring_path;
    return data;
  } catch { return null; }
}

function clearLocal() {
  try { localStorage.removeItem(SAVE_KEY); } catch { /* ignore */ }
  dropLegacyRiskStore();
}

function loadGuideDismissed() {
  try { return JSON.parse(localStorage.getItem(GUIDE_KEY) || "{}") || {}; } catch { return {}; }
}

function saveGuideDismissed() {
  try { localStorage.setItem(GUIDE_KEY, JSON.stringify(state.guideDismissed || {})); } catch { /* ignore */ }
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
    source_type: "clause",
    risk_id: (control.risk_ids && control.risk_ids[0]) || "",
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
  if (view === "work" || view === "result" || view === "flow") return "clauses";
  if (view === "workspace") return "workspace";
  return view;
}

function showView(view) {
  if (view === "work" && !state.project) view = "workspace";
  if (view === "flow" && !state.project) view = "workspace";
  if (view === "work" && state.resultStep) view = "result";
  if (view === "flow" && state.flowStep === "review") view = "work";
  if (view !== "result") state.resultStep = false;
  state.view = view;
  const nav = navFor(view);
  for (const b of $$("[data-nav]")) {
    if (b.dataset.nav === "export") continue;
    b.setAttribute("aria-pressed", String(b.dataset.nav === nav));
  }
  $("#guide").hidden = view !== "guide";
  $("#start").hidden = view !== "workspace";
  document.body.dataset.chrome = view === "workspace" ? "landing" : "app";
  if ($("#result")) $("#result").hidden = view !== "result";
  const authoring = Boolean(state.project) && (view === "flow" || view === "work");
  if ($("#flow")) $("#flow").hidden = !authoring;
  if ($("#flow-step")) $("#flow-step").hidden = view !== "flow";
  $("#work").hidden = view !== "work";
  $("#catalog").hidden = view !== "catalog";
  $("#library").hidden = view !== "library";
  if ($("#risks")) $("#risks").hidden = view !== "risks";
  const exportTop = $("#export-open-top");
  const closeBtn = $("#close-project");
  if (exportTop) exportTop.hidden = !state.project;
  if (closeBtn) closeBtn.hidden = !state.project;
  if (view === "workspace") {
    state.startPath = null;
    renderResume();
    renderStartChoice();
  }
  if (view === "result" && state.project) renderResult();
  if (authoring) renderFlowChrome();
  if (view === "flow" && state.project) renderFlowStep();
  if (view === "work" && state.project) render();
  if (view === "catalog") renderCatalog();
  if (view === "library") renderLibrary();
  if (view === "risks") renderRisks();
  renderCrumb();
}

function confirmReplace() {
  if (!state.project) return true;
  return confirm("Replace the open policy? Export the catalog first if you want to keep this version.");
}

function renderCrumb() {
  const crumb = $("#crumb");
  if (!crumb) return;
  const item = (text, last = false) => el("span", { class: last ? "crumb__item" : "crumb__item", text });
  const sep = () => el("span", { class: "crumb__sep", "aria-hidden": "true", text: "/" });
  const parts = ["Workspace"];
  if (state.view === "result" && state.project) {
    parts.push("Here's what we drafted");
  } else if ((state.view === "work" || state.view === "flow") && state.project) {
    parts.push(state.project.title || "Project");
    if (state.flowStep && STEP_LABELS[state.flowStep]) parts.push(STEP_LABELS[state.flowStep]);
  } else if (state.view === "catalog") parts.push("Catalog");
  else if (state.view === "library") parts.push("Library");
  else if (state.view === "risks") parts.push("Identified risks");
  else if (state.view === "guide") parts.push("Guide");
  const nodes = [];
  parts.forEach((p, i) => {
    if (i) nodes.push(sep());
    nodes.push(item(p, i === parts.length - 1));
  });
  crumb.replaceChildren(...nodes);
}

function renderResume() {
  const box = $("#resume");
  if (!box) return;
  const saved = loadLocal();
  const current = state.project;
  const show = Boolean(current || saved);
  box.hidden = !show;
  if (!show) return;
  const title = (current && current.title)
    || (saved && saved.project && saved.project.title)
    || "Untitled policy";
  $("#resume-title").textContent = title;
  if (current) {
    $("#resume-when").textContent = "";
  } else if (saved) {
    const when = new Date(saved.saved);
    $("#resume-when").textContent = isNaN(when) ? "" : `(saved ${when.toLocaleString()})`;
  }
}

// ---------------------------------------------------------------- opening a project

function openProject(data, { resultStep = false, path = null, flowStep = null } = {}) {
  showNotice("");
  state.project = dropLegacyRegister(data.project);
  if (path === "risks") state.project.authoring_path = "risks";
  else if (path === "clauses") delete state.project.authoring_path;
  else if (state.project.authoring_path !== "risks") delete state.project.authoring_path;
  state.scores = data.scores || {};
  state.checked.clear();
  state.filter = "all";
  const first = (state.project.controls || []).find((c) => c.status === "draft") || (state.project.controls || [])[0];
  state.selected = first ? { control: first.id } : null;
  state.editorTab = "statement";
  state.resultStep = Boolean(resultStep && (state.project.controls || []).length);
  const savedStep = flowStep || data.flowStep;
  const allowed = new Set(flowSteps(state.project));
  state.flowStep = allowed.has(savedStep) ? savedStep : (state.resultStep ? "clause" : firstIncompleteStep(state.project));
  for (const b of $$("[data-filter]")) b.setAttribute("aria-pressed", String(b.dataset.filter === "all"));
  saveLocal();
  if (state.resultStep) showView("result");
  else openFlow();
  renderCatalog();
  if (state.view === "work" && state.selected) {
    const id = state.selected.control ? `ctl-${state.selected.control}` : `clause-${state.selected.clause}`;
    document.getElementById(id)?.scrollIntoView({ block: "nearest" });
  }
}

function openFlow() {
  if (!state.project) return showView("workspace");
  if (!state.flowStep) state.flowStep = firstIncompleteStep(state.project);
  if (state.flowStep === "review" && !state.selected && (state.project.controls || [])[0]) {
    state.selected = { control: state.project.controls[0].id };
  }
  showView(state.flowStep === "review" ? "work" : "flow");
}

function renderStartChoice() {
  const landing = $("#landing");
  const drop = $("#drop");
  if (!drop) return;
  const clause = state.startPath === "clause";
  if (landing) landing.hidden = clause;
  drop.hidden = !clause;
}

function setFlowError(message) {
  const box = $("#flow-error");
  if (!box) return;
  box.textContent = message || "";
  box.hidden = !message;
}

function renderFlowChrome() {
  const identify = Boolean(state.project) && state.view === "flow" && state.flowStep === "risks";
  const statements = Boolean(state.project) && state.view === "flow" && state.flowStep === "controls";
  $("#flow")?.classList.toggle("flow-view--identify", identify);
  $("#flow")?.classList.toggle("flow-view--statements", statements);
  const head = $(".flow-view__head");
  const nav = $("#flow-nav");
  const guide = $("#step-guide");
  const reopen = $("#step-guide-open");
  if (identify || statements) {
    if (head) head.hidden = true;
    if (nav) nav.hidden = true;
    if (guide) {
      guide.hidden = true;
      guide.replaceChildren();
    }
    if (reopen) reopen.hidden = true;
    setFlowError("");
    return;
  }
  if (head) head.hidden = false;
  renderStepper();
  renderStepGuide();
  renderFlowNav();
}

function renderStepper() {
  const list = $("#stepper");
  if (!list || !state.project) return;
  const steps = flowSteps(state.project);
  const current = state.flowStep || firstIncompleteStep(state.project);
  const nodes = steps.map((step, i) => {
    const done = stepComplete(state.project, step);
    const isCurrent = step === current;
    const prevDone = steps.slice(0, i).every((s) => stepComplete(state.project, s));
    const enabled = isCurrent || done || prevDone;
    const btn = el("button", {
      type: "button",
      class: `stepper__step${isCurrent ? " is-current" : ""}${done && !isCurrent ? " is-done" : ""}`,
      "data-step": step,
      "aria-current": isCurrent ? "step" : null,
      disabled: enabled ? null : true,
    },
      el("span", { class: "stepper__n", text: done && !isCurrent ? "✓" : String(i + 1) }),
      el("span", { class: "stepper__label" },
        step === "clause" ? term("Clause", GLOSSARY.Clause) : STEP_LABELS[step]));
    btn.addEventListener("click", () => goToStep(step));
    return el("li", {}, btn);
  });
  list.replaceChildren(...nodes);
}

function renderStepGuide() {
  const panel = $("#step-guide");
  const reopen = $("#step-guide-open");
  if (!panel) return;
  const step = state.flowStep || "risks";
  const guide = STEP_GUIDES[step];
  const dismissed = Boolean(state.guideDismissed[step]);
  panel.hidden = !guide || dismissed;
  if (reopen) reopen.hidden = !guide || !dismissed;
  if (!guide || dismissed) {
    panel.replaceChildren();
    return;
  }
  const hide = el("button", { type: "button", class: "btn btn--quiet btn--small step-guide__dismiss", text: "Hide guide" });
  hide.addEventListener("click", () => {
    state.guideDismissed[step] = true;
    saveGuideDismissed();
    renderStepGuide();
  });
  panel.replaceChildren(
    el("h3", { text: guide.title }),
    el("h4", { text: "What" }), el("p", { text: guide.what }),
    el("h4", { text: "Why" }), el("p", { text: guide.why }),
    el("h4", { text: "A good example" }), el("p", { text: guide.example }),
    el("h4", { text: "Common mistakes" }), el("p", { text: guide.mistakes }),
    hide,
  );
}

function renderFlowNav() {
  const back = $("#flow-back");
  const next = $("#flow-next");
  const nav = $("#flow-nav");
  if (!nav || !state.project) return;
  const steps = flowSteps(state.project);
  const i = steps.indexOf(state.flowStep);
  const last = i === steps.length - 1;
  nav.hidden = state.view === "result";
  if (back) back.disabled = i <= 0;
  if (next) {
    next.textContent = state.flowStep === "review" ? "Send to Enact"
      : state.flowStep === "enact" ? "Download catalog"
      : "Next";
    next.hidden = false;
    next.disabled = last && state.flowStep !== "enact" ? true : false;
  }
}

function goToStep(step) {
  if (!state.project) return;
  const steps = flowSteps(state.project);
  if (!steps.includes(step)) return;
  state.flowStep = step;
  setFlowError("");
  if (step === "review" && !state.selected && (state.project.controls || [])[0]) {
    state.selected = { control: state.project.controls[0].id };
  }
  saveLocal();
  showView(step === "review" ? "work" : "flow");
}

function flowNext() {
  if (!state.project) return;
  if (state.flowStep === "enact") {
    openExportDialog();
    return;
  }
  const [ok, message] = canAdvance(state.project, state.flowStep);
  if (!ok) {
    setFlowError(message);
    return;
  }
  setFlowError("");
  const steps = flowSteps(state.project);
  const i = steps.indexOf(state.flowStep);
  if (i < 0 || i >= steps.length - 1) return;
  goToStep(steps[i + 1]);
}

function flowBack() {
  if (!state.project) return;
  const steps = flowSteps(state.project);
  const i = steps.indexOf(state.flowStep);
  if (i <= 0) return;
  goToStep(steps[i - 1]);
}

function startRiskPath() {
  if (!confirmReplace()) return;
  const uuid = (crypto.randomUUID && crypto.randomUUID()) || `00000000-0000-4000-8000-${String(Date.now()).slice(-12)}`;
  state.project = {
    uuid, title: "Untitled policy", source: "", version: "", clauses: [], controls: [],
    risks: [], authoring_path: "risks",
  };
  state.scores = {};
  state.selected = null;
  state.flowStep = "risks";
  state.startPath = null;
  state.identifyFocus = null;
  saveLocal();
  showView("flow");
}

function showClausePath() {
  state.startPath = "clause";
  renderStartChoice();
  $("#paste-form textarea")?.focus();
}

function hideClausePath() {
  state.startPath = null;
  renderStartChoice();
  $("#start-from-risks")?.focus();
}

function renderFlowStep() {
  const box = $("#flow-step");
  if (!box || !state.project) return;
  box.hidden = false;
  const step = state.flowStep;
  if (step === "risks") return renderIdentifyStep(box);
  if (step === "controls") return renderDevelopStep(box);
  if (step === "link") return renderLinkStep(box);
  if (step === "enact") return renderEnactStep(box);
  box.replaceChildren();
}

function renderIdentifyStep(box) {
  ensureRisks();
  const risks = identifiedRisks(state.project);
  const back = el("button", {
    type: "button", class: "btn btn--quiet identify-back", id: "identify-back",
    text: "Back to the landing",
  });
  back.addEventListener("click", () => {
    saveLocal();
    showView("workspace");
    $("#start-from-risks")?.focus();
  });
  const steps = el("ol", {
    class: "identify-steps", id: "identify-steps",
    "aria-label": "Identify risks, then control statements, then policy as code (Rego)",
  },
    el("li", { "aria-current": "step" },
      el("span", { class: "identify-steps__n", text: "1" }),
      el("span", { class: "identify-steps__label", text: "Identify risks" })),
    el("li", {},
      el("span", { class: "identify-steps__n", text: "2" }),
      el("span", { class: "identify-steps__label", text: "Control statements" })),
    el("li", {},
      el("span", { class: "identify-steps__n", text: "3" }),
      el("span", { class: "identify-steps__label", text: "Policy as code (Rego)" })),
  );
  const tip = el("details", { class: "identify-tip", id: "identify-tip" },
    el("summary", { text: "How to write a good risk statement" }),
    el("p", { text: "Name what could go wrong and why. For example: “Unauthorised access to customer data due to shared admin accounts”." }));
  const addInput = el("input", {
    type: "text", id: "flow-risk-statement", maxlength: "500", autocomplete: "off",
    placeholder: "Add a risk", "aria-label": "Add a risk",
  });
  const addRisk = () => {
    if (!String(addInput.value || "").trim()) return;
    addIdentifiedRisk(addInput.value, "");
    state.identifyFocus = "#flow-risk-statement";
    renderFlowStep();
    renderFlowChrome();
  };
  addInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addRisk(); }
    if (e.key === "Escape") { e.preventDefault(); addInput.value = ""; }
  });
  const list = el("ul", { class: "identify-list", id: "identify-list" },
    ...risks.map(identifyRiskRow),
    el("li", { class: "identify-add" },
      el("span", { class: "identify-add__mark", "aria-hidden": "true", text: "+" }),
      addInput));
  const cont = el("button", {
    type: "button", class: "btn btn--primary", id: "identify-continue",
    text: "Continue to control statements",
    disabled: risks.length ? null : true,
    title: risks.length ? null : "Add a risk first.",
  });
  cont.addEventListener("click", () => {
    const [ok] = canAdvance(state.project, "risks");
    if (!ok) return;
    goToStep("controls");
  });
  const empty = risks.length ? null : el("p", {
    class: "identify-empty", id: "identify-empty", role: "status",
    text: "Nothing here yet. Add the first risk below — a short sentence of what could go wrong.",
  });
  const live = el("p", {
    class: "visually-hidden", "aria-live": "polite",
    text: risks.length ? plural(risks.length, "identified risk") : "No identified risks yet",
  });
  box.replaceChildren(
    el("div", { class: "identify-page", id: "identify-page" },
      back, steps,
      el("h2", { class: "identify-title", id: "identify-title", text: "What risks have you identified?" }),
      el("p", {
        class: "identify-lede", id: "identify-lede",
        text: "Write each one as a short sentence of what could go wrong. You can add a note if you need to remember where it came from.",
      }),
      tip, live, empty, list,
      el("div", { class: "identify-actions" }, cont)));
  const focusSel = state.identifyFocus || null;
  state.identifyFocus = null;
  if (focusSel) queueMicrotask(() => $(focusSel)?.focus());
}

function identifyRiskRow(risk) {
  const statement = el("input", {
    type: "text", class: "identify-row__statement", maxlength: "500", autocomplete: "off",
    "aria-label": "Risk statement",
  });
  statement.value = risk.statement;
  const note = el("input", {
    type: "text", class: "identify-row__note", maxlength: "500", autocomplete: "off",
    placeholder: "Add a note (optional)", "aria-label": "Optional note",
  });
  note.value = risk.note || "";
  const remove = el("button", {
    type: "button", class: "btn btn--quiet btn--small identify-row__remove",
    text: "Remove", "aria-label": `Remove risk: ${risk.statement}`,
  });
  statement.addEventListener("focus", () => { statement.dataset.saved = statement.value; });
  statement.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); statement.blur(); }
    if (e.key === "Escape") {
      e.preventDefault();
      statement.value = statement.dataset.saved || (riskById(risk.id) || risk).statement;
      statement.blur();
    }
  });
  statement.addEventListener("blur", () => {
    const current = riskById(risk.id) || risk;
    if (!String(statement.value || "").trim()) {
      statement.value = current.statement;
      return;
    }
    updateIdentifiedRisk(risk.id, { statement: statement.value });
    const saved = riskById(risk.id) || current;
    statement.value = saved.statement;
    remove.setAttribute("aria-label", `Remove risk: ${saved.statement}`);
  });
  note.addEventListener("focus", () => { note.dataset.saved = note.value; });
  note.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); note.blur(); }
    if (e.key === "Escape") {
      e.preventDefault();
      note.value = note.dataset.saved || "";
      note.blur();
    }
  });
  note.addEventListener("blur", () => {
    updateIdentifiedRisk(risk.id, { note: note.value });
    const saved = riskById(risk.id);
    note.value = (saved && saved.note) || "";
  });
  remove.addEventListener("click", () => {
    const list = identifiedRisks(state.project);
    const i = list.findIndex((item) => item.id === risk.id);
    const next = list[i + 1] || list[i - 1];
    removeIdentifiedRisk(risk.id);
    state.identifyFocus = next
      ? `#identify-list [data-risk-id="${next.id}"] .identify-row__statement`
      : "#flow-risk-statement";
    renderFlowStep();
    renderFlowChrome();
  });
  return el("li", { class: "identify-row", "data-risk-id": risk.id },
    el("span", { class: "identify-row__mark", "aria-hidden": "true" }),
    el("div", { class: "identify-row__fields" }, statement, note),
    remove);
}

function statementItemsFor(project) {
  if (authoringPath(project) === "clauses") {
    const clauses = (project.clauses || []).filter((c) => !c.duplicate_of);
    const reqs = clauses.filter((c) => c.type === "requirement");
    const list = reqs.length ? reqs : clauses;
    return list.map((clause) => {
      const controls = (project.controls || []).filter((c) => c.clause === clause.id);
      return {
        key: `clause:${clause.id}`,
        kind: "clause",
        id: clause.id,
        text: clause.text,
        covered: controls.some((c) => String(c.text || "").trim()),
        controls,
        clause,
      };
    });
  }
  return identifiedRisks(project).map((risk) => {
    const controls = linkedControlsFor(project, risk.id);
    return {
      key: `risk:${risk.id}`,
      kind: "risk",
      id: risk.id,
      text: risk.statement,
      covered: controls.length > 0,
      controls,
      risk,
    };
  });
}

function statementCoverageLabel(items) {
  const n = items.filter((item) => item.covered).length;
  const noun = items[0] && items[0].kind === "clause" ? "clause" : "risk";
  return `${n} of ${plural(items.length, noun)} covered`;
}

function currentStatementItem() {
  const items = statementItemsFor(state.project);
  return items.find((item) => item.key === state.selectedStatementKey) || items[0] || null;
}

function refreshStatementsChrome() {
  const items = statementItemsFor(state.project);
  const progress = $("#statements-progress");
  if (progress) progress.textContent = items.length ? statementCoverageLabel(items) : "";
  const cont = $("#statements-continue");
  if (cont) cont.disabled = !items.length || items.some((item) => !item.covered) ? true : null;
  for (const btn of $$("#statements-list [data-statement-item]")) {
    const item = items.find((row) => row.key === btn.getAttribute("data-statement-item"));
    if (!item) continue;
    btn.setAttribute("data-covered", item.covered ? "true" : "false");
    const dot = btn.querySelector(".statements-dot");
    if (dot) {
      dot.classList.toggle("is-covered", item.covered);
      dot.setAttribute("aria-label", item.covered ? "Covered" : "Not covered");
    }
  }
}

function persistStatement(item, area) {
  const id = area.getAttribute("data-control-id");
  const text = area.value;
  if (id) {
    const control = controlById(id);
    if (!control) return;
    control.text = text;
    saveLocal();
    return;
  }
  if (!String(text || "").trim()) return;
  const control = item.kind === "risk"
    ? addControlForRisk(item.risk, text, "")
    : addControlForClause(item.clause, text);
  if (control) area.setAttribute("data-control-id", control.id);
}

function removeStatementControl(control) {
  state.project.controls = state.project.controls.filter((x) => x.id !== control.id);
  delete state.scores[control.id];
  state.checked.delete(control.id);
  saveLocal();
}

function addControlForClause(clause, text) {
  const statement = String(text || "").trim();
  if (!statement) return null;
  const used = new Set(state.project.controls.map((c) => c.id));
  let n = controlsOf(clause.id).length + 1;
  let id = `${String(clause.id).replace(/[^A-Za-z0-9.]+/g, "")}-${n}`;
  while (used.has(id)) id = `${String(clause.id).replace(/[^A-Za-z0-9.]+/g, "")}-${++n}`;
  const control = {
    id, clause: clause.id, text: statement, guidance: "", risk: "", who: "", notes: [],
    status: "draft", origin: "person", source_type: "clause", risk_ids: [],
  };
  const last = state.project.controls.map((c) => c.clause).lastIndexOf(clause.id);
  state.project.controls.splice(last >= 0 ? last + 1 : insertionPoint(clause), 0, control);
  saveLocal();
  return control;
}

function moveStatementItem(delta) {
  const items = statementItemsFor(state.project);
  if (!items.length) return;
  const current = currentStatementItem();
  const index = Math.max(0, items.findIndex((item) => item.key === (current && current.key)));
  const next = items[Math.min(items.length - 1, Math.max(0, index + delta))];
  if (!next || next.key === (current && current.key)) return;
  state.selectedStatementKey = next.key;
  renderFlowStep();
  renderFlowChrome();
  $("#statements-list")?.focus();
}

function insertStatementFromLibrary(item) {
  if (item.kind === "risk") {
    openRiskSuggestDialog(item.risk);
    return;
  }
  state.statementLibraryTarget = item;
  openLibraryPick();
}

function continueFromStatements() {
  const [ok] = canAdvance(state.project, "controls");
  if (!ok) return;
  const steps = flowSteps(state.project);
  const i = steps.indexOf("controls");
  goToStep(steps[i + 1] || "review");
}

function backFromStatements() {
  if (authoringPath(state.project) === "risks") {
    goToStep("risks");
    return;
  }
  state.resultStep = true;
  showView("result");
}

function statementBlock(item, control) {
  const area = el("textarea", {
    rows: "4",
    class: "statements-area",
    placeholder: "Write the control statement.",
    "aria-label": control ? "Control statement" : "New control statement",
    "data-control-for": item.kind === "risk" ? item.id : null,
    "data-control-id": control ? control.id : null,
  });
  if (control) area.value = control.text || "";
  area.addEventListener("input", () => {
    persistStatement(item, area);
    refreshStatementsChrome();
  });
  const remove = el("button", {
    type: "button", class: "btn btn--quiet btn--small statements-remove",
    text: "Remove",
    "aria-label": "Remove statement",
  });
  remove.hidden = !control;
  remove.addEventListener("click", () => {
    const id = area.getAttribute("data-control-id");
    const existing = id && controlById(id);
    if (existing) removeStatementControl(existing);
    const wrap = $("#statements-blocks");
    const block = remove.closest(".statements-block");
    if (block) block.remove();
    if (wrap && !wrap.querySelector("textarea")) wrap.append(statementBlock(item, null));
    refreshStatementsChrome();
  });
  area.addEventListener("input", () => {
    if (area.getAttribute("data-control-id")) remove.hidden = false;
  });
  return el("div", { class: "statements-block" }, area, remove);
}

function statementEditor(item) {
  const blocks = (item.controls || []).length
    ? item.controls.map((control) => statementBlock(item, control))
    : [statementBlock(item, null)];
  const add = el("button", {
    type: "button", class: "btn btn--quiet", id: "statements-add",
    text: "Add another statement",
  });
  add.addEventListener("click", () => {
    const wrap = $("#statements-blocks");
    if (!wrap) return;
    wrap.append(statementBlock(item, null));
    wrap.querySelector(".statements-block:last-child textarea")?.focus();
  });
  const insert = el("button", {
    type: "button", class: "btn btn--quiet", id: "statements-library",
    text: "Insert from library",
  });
  insert.addEventListener("click", () => insertStatementFromLibrary(item));
  return el("section", {
    class: "statements-editor", id: "statements-editor",
    "aria-label": "Control statement editor",
  },
    el("p", { class: "statements-source", id: "statements-source", text: item.text }),
    el("div", { class: "statements-blocks", id: "statements-blocks" }, blocks),
    el("div", { class: "statements-editor__actions" }, add, insert));
}

function renderDevelopStep(box) {
  const clausePath = authoringPath(state.project) === "clauses";
  if (!clausePath) ensureRisks();
  const items = statementItemsFor(state.project);
  if (!items.length) {
    box.replaceChildren(el("p", { class: "field-error", text: clausePath
      ? "Paste a policy clause first."
      : "Add identified risks first." }));
    return;
  }
  if (!items.some((item) => item.key === state.selectedStatementKey)) {
    state.selectedStatementKey = items[0].key;
  }
  const selected = currentStatementItem();
  const firstLabel = clausePath ? "Policy clause" : "Identify risks";
  const back = el("button", {
    type: "button", class: "btn btn--quiet identify-back", id: "statements-back",
    text: "Back",
  });
  back.addEventListener("click", backFromStatements);
  const steps = el("ol", {
    class: "identify-steps", id: "statements-steps",
    "aria-label": `${firstLabel}, then control statements, then policy as code (Rego)`,
  },
    el("li", {},
      el("span", { class: "identify-steps__n", text: "1" }),
      el("span", { class: "identify-steps__label", text: firstLabel })),
    el("li", { "aria-current": "step" },
      el("span", { class: "identify-steps__n", text: "2" }),
      el("span", { class: "identify-steps__label", text: "Control statements" })),
    el("li", {},
      el("span", { class: "identify-steps__n", text: "3" }),
      el("span", { class: "identify-steps__label", text: "Policy as code (Rego)" })),
  );
  const tip = el("details", { class: "identify-tip", id: "statements-tip" },
    el("summary", { text: "What makes a good control statement" }),
    el("p", { text: "Say who does what, how often, and the evidence produced. For example: “Customer data at rest is encrypted with AES-256 using managed keys; encryption is verified monthly by automated scan.”" }));
  const list = el("div", {
    class: "statements-list", id: "statements-list", role: "listbox",
    tabindex: "0",
    "aria-label": clausePath ? "Clauses" : "Identified risks",
  }, items.map((item) => {
    const selectedItem = item.key === state.selectedStatementKey;
    const btn = el("button", {
      type: "button",
      class: `statements-item${selectedItem ? " is-selected" : ""}`,
      role: "option",
      "data-statement-item": item.key,
      "data-covered": item.covered ? "true" : "false",
      "aria-selected": selectedItem ? "true" : "false",
    },
      el("span", {
        class: `statements-dot${item.covered ? " is-covered" : ""}`,
        "aria-label": item.covered ? "Covered" : "Not covered",
      }),
      el("span", { class: "statements-item__text", text: item.text }));
    btn.addEventListener("click", () => {
      if (state.selectedStatementKey === item.key) return;
      state.selectedStatementKey = item.key;
      renderFlowStep();
      renderFlowChrome();
    });
    return btn;
  }));
  list.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); moveStatementItem(1); }
    else if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); moveStatementItem(-1); }
  });
  const covered = items.filter((item) => item.covered).length;
  const cont = el("button", {
    type: "button", class: "btn btn--primary", id: "statements-continue",
    text: "Continue to policy as code",
    disabled: covered === items.length ? null : true,
  });
  cont.addEventListener("click", continueFromStatements);
  const title = clausePath
    ? "Write a control statement for each clause"
    : "Write a control statement for each risk";
  const lede = clausePath
    ? "Say who does what, how often, and what evidence is produced — one clear statement for each clause."
    : "Say who does what, how often, and what evidence is produced — one clear statement for each risk.";
  box.replaceChildren(
    el("div", { class: "statements-page", id: "statements-page" },
      back, steps,
      el("h2", { class: "statements-title", id: "statements-title", text: title }),
      el("p", { class: "statements-lede", id: "statements-lede", text: lede }),
      tip,
      el("div", { class: "statements-layout" }, list, statementEditor(selected)),
      el("div", { class: "statements-footer" },
        el("p", { class: "statements-progress", id: "statements-progress", "aria-live": "polite",
          text: statementCoverageLabel(items) }),
        cont)));
  const focusSel = state.statementFocus || null;
  state.statementFocus = null;
  if (focusSel) queueMicrotask(() => $(focusSel)?.focus());
}

function renderLinkStep(box) {
  ensureRisks();
  const controls = nonemptyControls(state.project);
  const legacy = authoringPath(state.project) === "clauses" && !identifiedRisks(state.project).length;
  const prompt = legacy
    ? el("p", { class: "legacy-prompt", id: "legacy-risk-prompt",
        text: "This project started from clauses. Add identified risks and link each control before review." })
    : null;
  const statement = el("input", {
    type: "text", id: "link-risk-statement", maxlength: "500", autocomplete: "off",
    placeholder: "Short risk statement",
  });
  const addRisk = el("button", { type: "button", class: "btn", id: "link-risk-add", text: "Add risk" });
  addRisk.addEventListener("click", () => {
    if (!String(statement.value || "").trim()) {
      setFlowError("A risk statement is required.");
      return;
    }
    setFlowError("");
    addIdentifiedRisk(statement.value, "");
    statement.value = "";
    renderFlowStep();
    renderFlowChrome();
  });
  const risks = state.project.risks || [];
  const firstId = risks[0] && risks[0].id;
  const linkAll = el("button", { type: "button", class: "btn", id: "link-remaining", text: "Link remaining to first risk" });
  linkAll.hidden = !firstId || !unlinkedControlIds(state.project).length;
  linkAll.addEventListener("click", () => {
    if (!firstId) return;
    for (const control of state.project.controls) {
      if (String(control.text || "").trim() && !(control.risk_ids || []).length) {
        applyRiskLink(control, firstId);
      }
    }
    saveLocal();
    renderFlowStep();
    renderFlowChrome();
  });
  const rows = controls.map((control) => {
    const unlinked = !(control.risk_ids || []).length;
    const select = el("select", { "aria-label": `Risk for ${control.id}` });
    select.append(el("option", { value: "", text: risks.length ? "Link a risk" : "Add a risk first" }));
    for (const risk of risks) {
      select.append(el("option", {
        value: risk.id, text: `${risk.id} — ${risk.statement}`,
        selected: (control.risk_ids || []).includes(risk.id) ? true : null,
      }));
    }
    select.addEventListener("change", () => {
      if (!select.value) return;
      control.risk_ids = [select.value];
      control.risk = purposeFromRisks(state.project, control.risk_ids);
      saveLocal();
      renderFlowStep();
      renderFlowChrome();
    });
    return el("div", { class: "link-row" },
      el("div", {},
        el("p", { text: control.text }),
        unlinked ? el("p", { class: "field-error", text: "This control is not linked to a risk." }) : null),
      select);
  });
  box.replaceChildren(
    el("h3", { class: "section-title", text: "Link to risks" }),
    prompt,
    el("p", { class: "start__lede", text: "Every control must treat an identified risk. Add a risk if you need one." }),
    el("div", { class: "risks-form card" },
      el("label", { class: "field" }, el("span", { text: "Identified risk" }), statement),
      el("div", { class: "actions" }, addRisk, linkAll)),
    rows.length ? el("div", {}, rows) : el("p", { class: "muted", text: "No control drafts yet." }),
  );
}

function renderEnactStep(box) {
  const [ok, message] = canExport(state.project);
  const download = el("button", { type: "button", class: "btn btn--primary btn--lg", id: "enact-download", text: "Download OSCAL catalog" });
  download.disabled = !ok;
  download.addEventListener("click", () => openExportDialog());
  box.replaceChildren(
    el("div", { class: "card enact-panel", id: "enact-step" },
      el("h3", { class: "section-title", text: "Send to Enact" }),
      el("p", { text: "Send to Enact turns control statements into testable Rego policy. Codify writes the catalog. Enact runs the checks. They share a file, not a server. Download only — nothing is uploaded." }),
      el("ol", { class: "enact-handoff__steps" },
        el("li", { text: "Download the OSCAL catalog on this device." }),
        el("li", {}, "Open ", el("a", { href: ENACT_APP, target: "_blank", rel: "noopener noreferrer", text: "Enact" }), " (Pages app)."),
        el("li", {}, "Load that JSON as the catalog. See ",
          el("a", { href: ENACT_DOC, target: "_blank", rel: "noopener noreferrer", text: "Using Codify with Enact" }), ".")),
      ok ? null : el("p", { class: "field-error", id: "enact-gate", text: message }),
      el("div", { class: "actions" }, download,
        el("button", { type: "button", class: "btn", id: "enact-other", text: "Other formats" }))),
  );
  $("#enact-other")?.addEventListener("click", () => openExportDialog());
}

function addControlForRisk(risk, text, clauseText) {
  const statement = String(text || "").trim();
  if (!statement) return;
  const control = {
    id: nextSuggestedControlId(risk.id),
    clause: "",
    text: statement,
    guidance: "",
    risk: risk.statement,
    who: "",
    notes: [],
    status: "draft",
    origin: "person",
    source_type: "clause",
    risk_ids: [risk.id],
  };
  const attached = String(clauseText || "").trim();
  if (attached) {
    const used = new Set((state.project.clauses || []).map((c) => c.id));
    let n = 1;
    let cid = `c${n}`;
    while (used.has(cid)) cid = `c${++n}`;
    state.project.clauses.push({
      id: cid, text: attached, section: "", heading: "", type: "requirement",
      reason: "attached as optional context", duplicate_of: null,
    });
    control.clause = cid;
  }
  state.project.controls.push(control);
  saveLocal();
  call({ action: "score", project: state.project }).then((data) => {
    state.scores = data.scores || {};
  }).catch(() => {});
  return control;
}

function clauseCounts(project) {
  const clauses = project.clauses || [];
  const controls = project.controls || [];
  const reqs = clauses.filter((c) => c.type === "requirement" && !c.duplicate_of);
  const split = reqs.filter((c) => controls.filter((x) => x.clause === c.id).length > 1).length;
  const n = (t) => clauses.filter((c) => c.type === t).length;
  return {
    clauses: clauses.length,
    requirements: reqs.length,
    other: clauses.length - reqs.length,
    controls: controls.length,
    split,
    duplicates: clauses.filter((c) => c.duplicate_of).length,
    context: n("scope") + n("definition") + n("role") + n("exception"),
    notControls: n("not-a-control"),
  };
}

function countsBreakdown(n) {
  return `${n.requirements} requirements drafted into ${n.controls} controls · ${n.duplicates} duplicate · ${n.context} context · ${n.notControls} not controls`;
}

function renderResult() {
  const p = state.project;
  if (!p) return;
  const n = clauseCounts(p);
  const lede = $("#result-lede");
  const list = $("#result-drafts");
  if (lede) {
    const bits = [`${plural(n.controls, "control draft")} from ${plural(n.requirements, "requirement")}.`];
    bits.push(countsBreakdown(n) + ".");
    if (n.split) bits.push(`${plural(n.split, "requirement")} split into more than one control.`);
    lede.textContent = bits.join(" ");
  }
  if (list) {
    const all = p.controls || [];
    const drafts = all.slice(0, 3);
    const extra = all.length - drafts.length;
    const items = drafts.map((c, i) => el("li", {},
      el("strong", { text: `Draft ${i + 1}` }),
      c.text || "(empty)"));
    if (extra > 0) items.push(el("li", { class: "result-step__more", text: `and ${extra} more` }));
    put(list, ...items);
  }
}

function continueFromResult() {
  state.resultStep = false;
  state.flowStep = "controls";
  showView("flow");
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

function ensureProject() {
  if (!state.project) {
    const uuid = (crypto.randomUUID && crypto.randomUUID()) || `00000000-0000-4000-8000-${String(Date.now()).slice(-12)}`;
    state.project = { uuid, title: "", source: "", version: "", clauses: [], controls: [], risks: [] };
    state.scores = {};
  }
  state.project = dropLegacyRegister(state.project);
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
  if (state.view === "library") renderLibrary();
  if (state.view === "risks") renderRisks();
  if (state.project && (state.view === "work" || state.view === "flow")) renderFlowChrome();
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
  const title = $("#work-title");
  if (title && document.activeElement !== title) title.value = p.title || "";
  const summary = $("#work-summary");
  const counts = clauseCounts(p);
  put(summary,
    el("strong", { text: `${plural(counts.controls, "control draft")} from ${plural(counts.requirements, "requirement")}` }),
    counts.other ? el("span", { class: "work__summary-detail", text: `. ${plural(counts.other, "other clause")} ${counts.other === 1 ? "was" : "were"} not converted (definitions, scope, roles, or duplicates).` }) : el("span", { text: "." }),
    counts.split ? el("span", { class: "work__summary-detail", text: ` ${plural(counts.split, "requirement")} split into more than one control.` }) : null,
  );
  const countsBox = $("#work-counts");
  if (countsBox) {
    countsBox.replaceChildren(el("p", { id: "work-counts-detail", text: countsBreakdown(counts) }));
  }
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
  const selected = state.selected?.control && controlById(state.selected.control);
  const stage = !selected ? (state.selected?.clause ? "clause" : "draft")
    : selected.status === "accepted" ? "accept" : "review";
  for (const li of $$(".flow [data-stage]")) {
    li.classList.toggle("is-current", li.dataset.stage === stage);
  }
  const uncovered = uncoveredRiskIds(p);
  const unlinked = unlinkedControlIds(p);
  if (countsBox && (uncovered.length || unlinked.length || identifiedRisks(p).length)) {
    countsBox.append(
      el("p", { id: "review-coverage" },
        uncovered.length
          ? el("span", { class: "coverage-flag", text: `${plural(uncovered.length, "risk")} with no control` })
          : el("span", { class: "muted", text: identifiedRisks(p).length ? "Every identified risk has a linked control." : "Add identified risks to cover." }),
        " · ",
        unlinked.length
          ? el("span", { class: "coverage-flag", text: `${plural(unlinked.length, "control")} not linked to a risk` })
          : el("span", { class: "muted", text: "Every control is linked to a risk." })),
    );
  }
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
    const known = new Set(state.project.clauses.map((c) => c.id));
    const orphans = state.project.controls.filter((c) => (!c.clause || !known.has(c.clause)) && matches(c));
    if (orphans.length) {
      nodes.push(el("p", { class: "section-head", text: "Controls" }));
      for (const c of orphans) nodes.push(controlRow(c));
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

function partsSubitems(parts, { accepted = false } = {}) {
  const rows = [["action", "Action"], ["scope", "Scope"], ["limit", "Limit"], ["purpose", "Purpose"]];
  const found = rows.filter(([k]) => parts && parts[k]).length;
  const items = rows.map(([k, label]) => {
    const missing = !(parts && parts[k]);
    const hint = missing
      ? el("span", { class: "part-help", text: accepted ? `Optional: ${PART_HELP[k]}` : (PART_HELP[k] || "Add this part.") })
      : parts[k];
    return el("li", { class: missing ? (accepted ? "is-optional" : "is-missing") : "" },
      el("span", { class: "dot", "aria-hidden": "true" }),
      el("span", {}, el("b", { text: label }), " ", hint));
  });
  if (parts && parts.tools) {
    items.push(el("li", { class: "is-warning" },
      el("span", { class: "dot", "aria-hidden": "true" }),
      el("span", {}, el("b", { text: "Tool named" }), " ", parts.tools)));
  }
  return el("div", {},
    el("p", { class: "subitems__head", text: `Parts ${found} of ${rows.length}` }),
    el("p", { class: "score-help", text: accepted
      ? "Accepted. Remaining gaps below are optional improvements."
      : "A testable control usually has these parts assessors look for: an action, what it applies to, a time limit, and why." }),
    el("ul", { class: "subitems", "aria-label": "Parts of the statement" }, items));
}

function scoreLine(assessment, { accepted = false } = {}) {
  const fill = el("span", { class: "bar__fill" });
  fill.style.width = pct(assessment.confidence);
  return el("div", { class: "scoreline" },
    el("span", { class: "scoreline__pct", text: pct(assessment.confidence) }),
    el("span", { class: "bar", role: "img", "aria-label": `${pct(assessment.confidence)} score` }, fill),
    el("p", { class: "score-help", text: accepted
      ? `Accepted at ${pct(assessment.confidence)}. Remaining gaps are optional improvements.`
      : SCORE_HELP }));
}

function isPartTip(tip, parts) {
  const t = (tip || "").toLowerCase();
  if (!(parts && parts.purpose) && /purpose|why this control/.test(t)) return true;
  if (!(parts && parts.limit) && /time limit|how often|\[n\]|parameter/.test(t)) return true;
  if (!(parts && parts.scope) && /scope|applies to/.test(t)) return true;
  if (!(parts && parts.action) && /start with the verb|action-first/.test(t)) return true;
  return false;
}

function isUnfilledParam(inner) {
  return !/\d/.test(inner || "");
}

function paramPrompts(text, onFill) {
  const matches = [...(text || "").matchAll(/\[([^\]]{1,40})\]/g)];
  const seen = new Set();
  const unfilled = [];
  for (const m of matches) {
    if (seen.has(m[0]) || !isUnfilledParam(m[1])) continue;
    seen.add(m[0]);
    unfilled.push({ token: m[0], inner: m[1] });
  }
  if (!unfilled.length) return null;
  return el("div", { class: "param-prompts" }, unfilled.map((item) => {
    const input = el("input", {
      type: "text", inputmode: "numeric", "aria-label": `Value for ${item.token}`,
      autocomplete: "off",
    });
    const set = el("button", { type: "button", class: "btn btn--small btn--primary", text: "Set" });
    const apply = () => {
      const value = input.value.trim();
      if (!value) return;
      const replacement = `[${value.replace(/^\[|\]$/g, "")}]`;
      onFill(item.token, replacement);
    };
    set.addEventListener("click", apply);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); apply(); } });
    return el("div", { class: "param-prompt" },
      el("div", { class: "param-prompt__row" },
        el("strong", { text: "Set this value" }),
        el("mark", { class: "param-token", text: item.token }),
        input, set),
      el("p", { class: "param-prompt__hint",
        text: "Unfilled blanks look like [N]. Type the number your organisation will test against — for example 90." }));
  }));
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
    el("p", { class: "oscal-view__help", text: GLOSSARY.OSCAL }),
    el("div", { class: "oscal-view__bar" },
      el("span", { class: "oscal-view__label", text: "This control" }),
      copy, status),
    pre);
}

function renderControlEditor(box, c) {
  const clause = clauseById(c.clause) || { id: c.clause, text: "" };
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
  riskBox.value = purposeFromRisks(state.project, c.risk_ids || []) || c.risk || "";
  const who = el("input", { placeholder: "e.g. The IT Department", autocomplete: "off" });
  who.value = c.who || "";

  const check = debounce(async () => {
    try {
      const data = await call({ action: "check", text: c.text || " ", risk: c.risk || "" });
      state.scores[c.id] = { confidence: data.assessment.confidence, improvements: data.assessment.improvements };
      state.lastCheck[c.id] = data;
      showResult(result, data, c);
      sub.replaceChildren(partsSubitems(data.parts, { accepted: c.status === "accepted" }));
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

  const accepted = c.status === "accepted";
  const reviewed = accepted ? null : el("button", {
    type: "button", class: "btn", "aria-pressed": String(c.status === "reviewed"),
    text: "Mark reviewed",
    title: "You have read this draft. It is not accepted yet — use Accept when the wording is good enough to keep.",
  });
  if (reviewed) reviewed.addEventListener("click", () => setStatus([c.id], "reviewed"));
  const accept = accepted
    ? el("span", { class: "accepted-flag", id: "accept-control", text: "Accepted ✓" })
    : el("button", {
      type: "button", class: "btn btn--primary", id: "accept-control",
      text: "Accept",
      title: "Keep this statement in this project's catalog and on this device.",
    });
  if (!accepted) accept.addEventListener("click", () => setStatus([c.id], "accepted"));
  const undo = accepted
    ? el("button", {
      type: "button", class: "btn btn--quiet", id: "undo-accept", text: "Undo accept",
      title: "Return this control to draft. It stays in the library until you remove it there.",
    })
    : null;
  if (undo) undo.addEventListener("click", () => setStatus([c.id], "draft"));
  const next = el("button", {
    type: "button", class: accepted ? "btn btn--primary" : "btn", id: "next-control",
    text: "Next control",
    title: accepted ? "Open the next control." : "Open the next control without accepting this one.",
  });
  next.disabled = index < 0 || index >= visible.length - 1;
  next.addEventListener("click", () => step(1));
  let aiBtn = null;
  if (aiReady() && clause.text) {
    aiBtn = el("button", { type: "button", class: "btn", text: "Draft with AI" });
    aiBtn.addEventListener("click", () => aiRedraft(clause, aiBtn));
  }

  const fromLib = el("button", { type: "button", class: "btn", id: "library-from", text: "From library" });
  fromLib.addEventListener("click", openLibraryPick);
  const add = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Add a control from this clause" });
  add.addEventListener("click", () => addControl(clause));
  const redraft = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Draft again from this clause" });
  redraft.addEventListener("click", () => redraftClause(clause, redraft));
  const remove = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Delete this control" });
  remove.addEventListener("click", () => deleteControl(c));
  const openClause = clause.id ? el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Open clause" }) : null;
  if (openClause) openClause.addEventListener("click", () => select({ clause: clause.id }));

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
    clause.text ? legacyBox(clause) : null,
    el("label", { class: "field field--hero" }, statement),
    paramPrompts(c.text, (token, replacement) => {
      c.text = (c.text || "").split(token).join(replacement);
      if (c.origin !== "person") c.origin = "person";
      saveSoon();
      renderEditor();
    }),
    el("div", { class: "editor__primary", role: "group", "aria-label": "Review" }, reviewed, accept, undo, next, fromLib, aiBtn),
    result,
    sub,
    extras,
    mappedRisksField(c),
    el("div", { class: "editor__foot" }, openClause, clause.id ? redraft : null, clause.id ? add : null, remove),
  );
  result.replaceChildren(el("p", { class: "placeholder", text: "Checking…" }));
  call({ action: "check", text: c.text || " ", risk: c.risk || "" }).then((data) => {
    state.lastCheck[c.id] = data;
    showResult(result, data, c);
    sub.replaceChildren(partsSubitems(data.parts, { accepted: c.status === "accepted" }));
    renderProps(c, data);
  }).catch((err) => {
    result.replaceChildren(el("p", { class: "placeholder", text: c.text ? err.message : "Write the control statement to check it." }));
    renderProps(c);
  });
}

function showResult(box, data, control) {
  const accepted = control && control.status === "accepted";
  box.replaceChildren(...[scoreLine(data.assessment, { accepted })].filter(Boolean));
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
    mappedRisksProp(control),
    el("p", { class: "prop-help", text: control.status === "accepted"
      ? `Accepted at ${score === null ? "–" : pct(score)}. Remaining gaps are optional improvements.`
      : SCORE_HELP }),
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
  const parts = data && data.parts;
  const improvements = ((data && data.assessment && data.assessment.improvements) || (state.scores[control.id] && state.scores[control.id].improvements) || [])
    .filter((tip) => !isPartTip(tip, parts));
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
    tryAgain.addEventListener("click", () => {
      if (clause) aiRedraft(clause, tryAgain);
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
      el("h3", { class: "props-card__title", text: control.status === "accepted" ? "Optional improvements" : "Review suggestions" }),
      suggestions.length ? suggestions : el("p", { class: "placeholder", text: "No suggestions." })),
    libraryCard,
    aiCard].filter(Boolean));
}

function controlSourceLabel(control) {
  return control.clause ? "Clause" : "—";
}

function mappedRisksField(control) {
  const ids = control.risk_ids || [];
  const flags = coverageFlags(state.project);
  const unlinked = flags.unlinked.includes(control.id);
  const rows = ids.map((id) => {
    const risk = riskById(id);
    const unlink = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Unlink" });
    unlink.addEventListener("click", () => unlinkRisk(control, id));
    return el("div", { class: "mapped-risk" },
      el("div", { class: "mapped-risk__meta" },
        el("span", { class: "pill", text: id }),
        unlinked ? null : el("span", { class: "mapped-risk__statement", text: (risk && risk.statement) || id })),
      unlink);
  });
  const available = (state.project.risks || []).filter((r) => !ids.includes(r.id));
  const select = el("select", { "aria-label": "Link an identified risk" },
    el("option", { value: "", text: available.length ? "Link an identified risk" : "No other identified risks" }),
    available.map((r) => el("option", { value: r.id, text: `${r.id} — ${r.statement}` })));
  select.disabled = !available.length;
  select.addEventListener("change", () => {
    if (select.value) linkRisk(control, select.value);
  });
  const openRisks = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Identified risks" });
  openRisks.addEventListener("click", () => showView("risks"));
  return el("div", { class: "mapped-risks" },
    el("span", { class: "field-label", text: "Mapped risks" }),
    unlinked ? el("p", { class: "coverage-flag", text: "Not linked to an identified risk." }) : null,
    rows.length ? rows : el("p", { class: "hint", text: "Link the identified risk this statement treats." }),
    el("div", { class: "mapped-risks__add" }, select, openRisks));
}

function applyRiskLink(control, riskId) {
  const ids = [...(control.risk_ids || [])];
  if (!ids.includes(riskId)) ids.push(riskId);
  control.risk_ids = ids;
  const linked = purposeFromRisks(state.project, ids);
  if (linked) control.risk = linked;
}

function linkRisk(control, riskId) {
  applyRiskLink(control, riskId);
  saveLocal();
  if (state.view === "work") render();
  else if (state.view === "risks") renderRisks();
  else if (state.view === "flow") { renderFlowStep(); renderFlowChrome(); }
  else render();
}

function unlinkRisk(control, riskId) {
  control.risk_ids = (control.risk_ids || []).filter((id) => id !== riskId);
  const linked = purposeFromRisks(state.project, control.risk_ids);
  control.risk = linked;
  saveLocal();
  if (state.view === "work") render();
  else if (state.view === "risks") renderRisks();
  else render();
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
  const flags = coverageFlags(state.project);
  const body = rows.map((c) => {
    const open = el("button", { type: "button", text: c.text || "(empty)" });
    open.addEventListener("click", () => { showView("work"); select({ control: c.id }); });
    const linked = (c.risk_ids || []).join(", ") || "—";
    return el("tr", {},
      el("td", { text: c.id }),
      el("td", {}, open),
      el("td", {}, el("span", { class: "pill", text: controlSourceLabel(c) })),
      el("td", {}, flags.unlinked.includes(c.id)
        ? el("span", { class: "coverage-flag", text: "Unlinked" })
        : el("span", { class: "pill", text: linked })),
      el("td", {}, el("span", { class: `state state--${c.status}`, text: STATUS_LABELS[c.status] })));
  });
  box.replaceChildren(el("div", { class: "catalog-body" },
    el("table", { class: "data-table" },
      el("thead", {}, el("tr", {},
        el("th", { text: "ID" }), el("th", { text: "Control" }),
        el("th", { text: "Source" }), el("th", { text: "Risks" }), el("th", { text: "Status" }))),
      el("tbody", {}, body))));
}

function mappedRisksProp(control) {
  const ids = control.risk_ids || [];
  const unlinked = coverageFlags(state.project).unlinked.includes(control.id);
  if (!ids.length && !(state.project.risks || []).length) {
    return el("p", { class: "prop-help", text: "Add identified risks if you want this statement to treat one." });
  }
  return el("div", { class: "mapped-risks mapped-risks--props" },
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Mapped risks" }),
      el("span", { class: "prop-row__value", text: ids.length ? ids.join(", ") : "None" })),
    unlinked ? el("p", { class: "coverage-flag", text: "Not linked to an identified risk." }) : null,
    ids.map((id) => {
      const risk = riskById(id);
      return el("p", { class: "mapped-risk__statement", text: risk ? risk.statement : id });
    }));
}

function ensureRisks() {
  if (!state.project.risks) state.project.risks = [];
  state.project.risks = cleanRisks(state.project.risks);
}

function addIdentifiedRisk(statement, note) {
  ensureRisks();
  const text = String(statement || "").trim().replace(/\s+/g, " ");
  if (!text) return;
  const risk = { id: nextRiskId(state.project.risks), statement: text, note: String(note || "").trim() };
  state.project.risks.push(risk);
  state.selectedRisk = risk.id;
  saveLocal();
  renderRisks();
}

function updateIdentifiedRisk(id, fields) {
  const risk = riskById(id);
  if (!risk) return;
  if ("statement" in fields) risk.statement = String(fields.statement || "").trim().replace(/\s+/g, " ");
  if ("note" in fields) risk.note = String(fields.note || "").trim();
  if (!risk.statement) return;
  for (const control of controlsForRisk(id)) {
    const linked = purposeFromRisks(state.project, control.risk_ids || []);
    if (linked) control.risk = linked;
  }
  saveLocal();
}

function removeIdentifiedRisk(id) {
  ensureRisks();
  state.project.risks = state.project.risks.filter((r) => r.id !== id);
  for (const control of state.project.controls) {
    if (!(control.risk_ids || []).includes(id)) continue;
    control.risk_ids = control.risk_ids.filter((x) => x !== id);
    control.risk = purposeFromRisks(state.project, control.risk_ids);
  }
  if (state.selectedRisk === id) state.selectedRisk = (state.project.risks[0] && state.project.risks[0].id) || null;
  saveLocal();
  renderRisks();
}

function renderRisks() {
  const box = $("#risks-body");
  if (!box) return;
  if (!state.project) {
    box.replaceChildren(emptyState("Load a policy first.", "Paste a clause", () => showView("workspace"), "empty--list"));
    return;
  }
  ensureRisks();
  const flags = coverageFlags(state.project);
  const statement = el("input", {
    type: "text", id: "risk-statement", maxlength: "500", autocomplete: "off",
    placeholder: "Short risk statement, e.g. Screens left unlocked.",
  });
  const note = el("input", {
    type: "text", id: "risk-note", maxlength: "500", autocomplete: "off",
    placeholder: "Optional note",
  });
  const add = el("button", { type: "button", class: "btn btn--primary", id: "risk-add", text: "Add risk" });
  const submit = () => addIdentifiedRisk(statement.value, note.value);
  add.addEventListener("click", submit);
  statement.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } });
  const form = el("div", { class: "risks-form card" },
    el("p", { class: "risks-form__label", text: "Add an identified risk" }),
    el("label", { class: "field" }, el("span", { text: "Statement" }), statement),
    el("label", { class: "field" }, el("span", {}, "Note ", el("em", { text: "optional" })), note),
    el("div", { class: "actions" }, add));

  const risks = state.project.risks || [];
  const uncoveredN = flags.uncovered.length;
  const unlinkedN = flags.unlinked.length;
  const summary = el("p", { class: "risks-coverage", id: "risks-coverage" },
    el("span", {
      class: uncoveredN ? "coverage-flag" : "muted",
      text: !risks.length
        ? "Add identified risks to track coverage."
        : uncoveredN ? `${plural(uncoveredN, "risk")} with no control` : "Every identified risk has a linked control.",
    }),
    " · ",
    el("span", {
      class: unlinkedN ? "coverage-flag" : "muted",
      text: unlinkedN ? `${plural(unlinkedN, "control")} not linked to a risk` : "Every control is linked to a risk.",
    }));
  const related = renderRelatedTable(flags);
  if (!risks.length) {
    box.replaceChildren(
      form,
      summary,
      emptyState("No identified risks yet. Add the risks you already identified.", null, null, "empty--list"),
      related,
    );
    return;
  }
  if (!state.selectedRisk || !riskById(state.selectedRisk)) state.selectedRisk = risks[0].id;
  const list = el("div", { class: "risk-list" }, risks.map((risk) => {
      const uncovered = flags.uncovered.includes(risk.id);
      const open = el("button", { type: "button", class: "risk-row__open" },
        el("span", { class: "pill", text: risk.id }),
        el("span", { class: "risk-row__statement", text: risk.statement }));
      open.addEventListener("click", () => { state.selectedRisk = risk.id; renderRisks(); });
      const suggest = el("button", { type: "button", class: "btn btn--small", "data-suggest": risk.id, text: "Suggest statements" });
      suggest.addEventListener("click", () => openRiskSuggestDialog(risk));
      const remove = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Remove" });
      remove.addEventListener("click", () => {
        if (confirm("Remove this identified risk? Linked controls stay; the link is dropped.")) removeIdentifiedRisk(risk.id);
      });
      return el("div", {
        class: "risk-row",
        "aria-current": state.selectedRisk === risk.id ? "true" : null,
        "data-risk-id": risk.id,
      },
        open,
        uncovered ? el("span", { class: "coverage-flag", text: "No control" }) : el("span", { class: "pill", text: plural(controlsForRisk(risk.id).length, "control") }),
        el("div", { class: "risk-row__actions" }, suggest, remove));
    }));

  const selected = riskById(state.selectedRisk);
  const detail = selected ? renderRiskDetail(selected, flags) : el("p", { class: "placeholder", text: "Add a risk to see matching statements." });

  box.replaceChildren(
    form,
    summary,
    el("div", { class: "risks-layout" }, list, detail),
    related,
  );
}

function renderRiskDetail(risk, flags) {
  const statement = el("textarea", { rows: "3", id: "risk-edit-statement", "aria-label": "Risk statement" });
  statement.value = risk.statement;
  const note = el("textarea", { rows: "2", id: "risk-edit-note", "aria-label": "Optional note" });
  note.value = risk.note || "";
  statement.addEventListener("input", () => updateIdentifiedRisk(risk.id, { statement: statement.value }));
  note.addEventListener("input", () => updateIdentifiedRisk(risk.id, { note: note.value }));
  const mapped = controlsForRisk(risk.id);
  const mappedRows = mapped.length
    ? mapped.map((c) => {
      const open = el("button", { type: "button", text: c.text || "(empty)" });
      open.addEventListener("click", () => { showView("work"); select({ control: c.id }); });
      return el("div", { class: "mapped-risk" },
        el("span", { class: "pill", text: c.id }),
        open);
    })
    : [el("p", { class: "coverage-flag", text: "No control treats this risk yet." })];
  const suggest = el("button", { type: "button", class: "btn btn--primary", text: "Suggest statements" });
  suggest.addEventListener("click", () => openRiskSuggestDialog(risk));
  return el("aside", { class: "risk-detail", id: "risk-detail", "aria-label": "Risk details" },
    el("h3", { class: "risk-detail__title", text: risk.id }),
    flags.uncovered.includes(risk.id) ? el("p", { class: "coverage-flag", text: "No control linked." }) : null,
    el("label", { class: "field" }, el("span", { text: "Statement" }), statement),
    el("label", { class: "field" }, el("span", {}, "Note ", el("em", { text: "optional" })), note),
    el("h3", { class: "props-card__title", text: "Mapped controls" }),
    ...mappedRows,
    el("div", { class: "actions" }, suggest));
}

function renderRelatedTable(flags) {
  const rows = [];
  for (const risk of state.project.risks || []) {
    const linked = controlsForRisk(risk.id);
    if (!linked.length) {
      rows.push(el("tr", { class: "is-uncovered" },
        el("td", { text: risk.id }),
        el("td", { text: risk.statement }),
        el("td", {}, el("span", { class: "coverage-flag", text: "No control" })),
        el("td", { text: "—" })));
      continue;
    }
    for (const control of linked) {
      const open = el("button", { type: "button", text: control.text || "(empty)" });
      open.addEventListener("click", () => { showView("work"); select({ control: control.id }); });
      rows.push(el("tr", {},
        el("td", { text: risk.id }),
        el("td", { text: risk.statement }),
        el("td", {}, open),
        el("td", {}, el("span", { class: `state state--${control.status}`, text: STATUS_LABELS[control.status] }))));
    }
  }
  for (const id of flags.unlinked) {
    const control = controlById(id);
    if (!control) continue;
    const open = el("button", { type: "button", text: control.text || "(empty)" });
    open.addEventListener("click", () => { showView("work"); select({ control: control.id }); });
    rows.push(el("tr", { class: "is-unlinked" },
      el("td", {}, el("span", { class: "coverage-flag", text: "—" })),
      el("td", {}, el("span", { class: "coverage-flag", text: "Unlinked control" })),
      el("td", {}, open),
      el("td", {}, el("span", { class: `state state--${control.status}`, text: STATUS_LABELS[control.status] }))));
  }
  if (!rows.length) {
    return el("p", { class: "placeholder", text: "Related controls will appear here once you add a risk or a control." });
  }
  return el("div", { class: "related-table" },
    el("h3", { class: "section-title", text: "Related controls" }),
    el("table", { class: "data-table", id: "risks-related" },
      el("thead", {}, el("tr", {},
        el("th", { text: "Risk" }), el("th", { text: "Scenario" }),
        el("th", { text: "Control" }), el("th", { text: "Status" }))),
      el("tbody", {}, rows)));
}

function openRiskSuggestDialog(risk) {
  state.suggestRiskId = risk.id;
  state.suggestPicked = new Set();
  state.suggestAi = [];
  const hits = matchLibrary(loadLibrary(), risk.statement);
  for (const entry of hits) state.suggestPicked.add(entry.id);
  renderRiskSuggest();
  const dialog = $("#risk-suggest-dialog");
  if (dialog && dialog.showModal) dialog.showModal();
}

function renderRiskSuggest() {
  const risk = riskById(state.suggestRiskId);
  const title = $("#risk-suggest-title");
  const scenario = $("#risk-suggest-scenario");
  const body = $("#risk-suggest-body");
  if (!risk || !body) return;
  const libraryHits = matchLibrary(loadLibrary(), risk.statement);
  const n = libraryHits.length + state.suggestAi.length;
  if (title) title.textContent = n ? `Add ${n} recommended statement${n === 1 ? "" : "s"}?` : "Recommended statements";
  if (scenario) scenario.textContent = risk.statement;
  const rows = [];
  if (!libraryHits.length && !state.suggestAi.length) {
    rows.push(el("p", { class: "placeholder", text: "No matching statements in the library yet. Accept a control, or use AI drafting if it is on." }));
  }
  for (const entry of libraryHits) {
    const add = el("button", { type: "button", class: "btn btn--small", text: "Add" });
    add.addEventListener("click", () => {
      addSuggestedStatement(risk, { statement: entry.statement, origin: "person", libraryId: entry.id });
      if (state.view === "flow") { renderFlowStep(); renderFlowChrome(); }
    });
    rows.push(el("div", { class: "risk-suggest__row template-row" },
      el("p", { text: entry.statement }),
      add));
  }
  for (const draft of state.suggestAi) {
    const add = el("button", { type: "button", class: "btn btn--small", text: "Add" });
    add.addEventListener("click", () => {
      addSuggestedStatement(risk, { statement: draft.text, origin: "ai", libraryId: null, draft });
      if (state.view === "flow") { renderFlowStep(); renderFlowChrome(); }
    });
    rows.push(el("div", { class: "risk-suggest__row template-row" },
      el("p", { text: draft.text }),
      el("span", { class: "pill", text: "AI" }),
      add));
  }
  let aiBtn = null;
  if (aiReady()) {
    aiBtn = el("button", { type: "button", class: "btn", id: "risk-suggest-ai", text: "Also draft with AI" });
    aiBtn.addEventListener("click", () => aiSuggestForRisk(risk, aiBtn));
  }
  body.replaceChildren(...[...rows, aiBtn].filter(Boolean));
  const addAll = $("#risk-suggest-add");
  if (addAll) {
    addAll.disabled = n === 0;
    addAll.onclick = () => {
      for (const entry of libraryHits) addSuggestedStatement(risk, { statement: entry.statement, origin: "person", libraryId: entry.id });
      for (const draft of state.suggestAi) addSuggestedStatement(risk, { statement: draft.text, origin: "ai", libraryId: null, draft });
      const dialog = $("#risk-suggest-dialog");
      if (dialog && dialog.open) dialog.close();
      renderRisks();
      if (state.view === "flow") { renderFlowStep(); renderFlowChrome(); }
    };
  }
}

async function aiSuggestForRisk(risk, button) {
  await busy(button, "Drafting…", async () => {
    const data = await aiDraftClause({ id: risk.id, text: risk.statement, heading: "Identified risk" });
    state.suggestAi = data.controls || [];
    renderRiskSuggest();
  });
}

function nextSuggestedControlId(base) {
  const used = new Set(state.project.controls.map((c) => c.id));
  const stem = String(base || "r").replace(/[^A-Za-z0-9.]+/g, "") || "r";
  let n = 1;
  let id = `${stem}-${n}`;
  while (used.has(id)) id = `${stem}-${++n}`;
  return id;
}

function addSuggestedStatement(risk, item) {
  const text = String(item.statement || "").trim();
  if (!text) return;
  const existing = state.project.controls.find((c) => (c.text || "").trim().toLowerCase() === text.toLowerCase());
  if (existing) {
    linkRisk(existing, risk.id);
    if (item.libraryId) {
      rememberStatement({ text, id: existing.id, risk_ids: existing.risk_ids, parts: null }, { used: true }).catch((err) => showError(err.message));
    }
    return;
  }
  const control = {
    id: nextSuggestedControlId(risk.id),
    clause: "",
    text,
    guidance: (item.draft && item.draft.guidance) || "",
    risk: risk.statement,
    who: "",
    notes: (item.draft && item.draft.notes) || [],
    status: "draft",
    origin: item.origin || "person",
    source_type: "clause",
    risk_ids: [risk.id],
  };
  state.project.controls.push(control);
  saveLocal();
  if (item.libraryId) {
    rememberStatement(control, { used: true }).catch((err) => showError(err.message));
  }
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
  const lead = statementLead(entry.statement);
  const full = (entry.statement || "").trim();
  const heading = lead && lead !== full
    ? el("h3", { class: "library-detail__title", text: lead })
    : null;
  return el("aside", { class: "library-detail", id: "library-detail", "aria-label": "Statement details" },
    heading,
    el("p", { class: "library-detail__statement", text: full || "(empty)" }),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "ID" }),
      el("span", { class: "prop-row__value", text: entry.id })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Source" }),
      el("span", { class: "prop-row__value" }, el("span", { class: "pill", text: source }))),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Domain" }),
      el("span", { class: "prop-row__value", text: "Control statement" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Framework" }),
      el("span", { class: "prop-row__value", text: "OSCAL 1.1.2" })),
    el("div", { class: "prop-row" }, el("span", { class: "prop-row__label", text: "Related" }),
      el("span", { class: "prop-row__value", text: "Clause" })),
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
  if (filtered.length === 1) {
    box.replaceChildren(head, el("div", { class: "library-layout library-layout--single" }, renderLibraryDetail(selected)));
    return;
  }
  const list = el("div", { class: "library-list", "aria-label": "Saved statements" },
    el("p", { class: "library-count", text: `Statement library (${filtered.length})` }),
    filtered.map((entry) => {
      const row = el("article", {
        class: "library-row", "data-library-id": entry.id,
        "aria-current": String(entry.id === state.selectedLibrary),
      },
        el("p", { class: "library-statement", text: statementLead(entry.statement) }),
        el("div", { class: "library-row__meta" },
          el("span", { class: "pill", text: librarySourceLabel(entry) }),
          el("span", { class: "muted", text: formatWhen(entry["accepted-at"]) })));
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

function addControlFromLibrary(entry, { clauseId = "" } = {}) {
  ensureProject();
  const used = new Set(state.project.controls.map((c) => c.id));
  const base = `${(clauseId || "L").replace(/[^A-Za-z0-9.]+/g, "")}-L`;
  let n = 1;
  let id = `${base}${n}`;
  while (used.has(id)) id = `${base}${++n}`;
  const control = {
    id, clause: clauseId, text: entry.statement, guidance: "", risk: "", who: "", notes: [],
    status: "draft", origin: "person",
    source_type: "clause",
    risk_ids: [],
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
    await rememberStatement({ text: entry.statement, id: entry.id, source_type: "clause",
      risk_ids: [], parts: entry.parts }, { used: true });
  } catch (err) { showError(err.message); return; }
  const dialog = $("#library-pick");
  if (dialog && dialog.open) dialog.close();
  if (state.view === "flow" && state.flowStep === "controls" && state.statementLibraryTarget) {
    const item = state.statementLibraryTarget;
    state.statementLibraryTarget = null;
    if (item.kind === "risk") {
      addSuggestedStatement(item.risk, { statement: entry.statement, origin: "person", libraryId: entry.id });
    } else {
      addControlForClause(item.clause, entry.statement);
    }
    renderFlowStep();
    renderFlowChrome();
    return;
  }
  const current = state.selected?.control && controlById(state.selected.control);
  if (mode === "add" || !current) {
    if (!state.project) {
      return showError("Load a policy before using a library statement.");
    }
    const clauseId = current?.clause || state.selected?.clause || "";
    addControlFromLibrary(entry, { clauseId });
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

function inheritRiskLinks(outgoing, incoming) {
  const inherited = [];
  for (const control of outgoing) {
    for (const id of control.risk_ids || []) {
      if (id && !inherited.includes(id)) inherited.push(id);
    }
  }
  if (!inherited.length) return;
  for (const control of incoming) {
    if ((control.risk_ids || []).length) continue;
    control.risk_ids = [...inherited];
    if (!control.risk) control.risk = purposeFromRisks(state.project, control.risk_ids);
  }
}

function replaceControls(clause, data, show = true) {
  // put new drafts where the clause's controls were; keep identified-risk links
  const outgoing = controlsOf(clause.id);
  inheritRiskLinks(outgoing, data.controls || []);
  const at = state.project.controls.findIndex((c) => c.clause === clause.id);
  for (const c of outgoing) { delete state.scores[c.id]; state.checked.delete(c.id); }
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
  const control = { id, clause: clause.id, text: "", guidance: "", risk: "", who: "", notes: [], status: "draft", origin: "person", source_type: "clause", risk_ids: [] };
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
      const [ok, message] = canExport(state.project);
      if (!ok) throw new Error(message);
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
  const [ok, message] = canExport(state.project);
  const gate = $("#export-gate");
  if (gate) {
    gate.hidden = ok;
    gate.textContent = ok ? "" : message;
  }
  for (const b of $$("#export-dialog [data-export]")) {
    if (String(b.dataset.export || "").startsWith("library")) continue;
    b.disabled = !ok;
  }
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
  dropLegacyRiskStore();
  if (BROWSER) for (const n of $$("[data-browser-only]")) n.hidden = false;

  for (const b of $$("[data-nav]")) {
    b.addEventListener("click", () => {
      if (b.dataset.nav === "export") return openExportDialog();
      showView(b.dataset.view || b.dataset.nav);
    });
  }

  $("#result-continue")?.addEventListener("click", continueFromResult);
  for (const b of $$("[data-start-risks]")) b.addEventListener("click", startRiskPath);
  $("#start-from-clause")?.addEventListener("click", showClausePath);
  $("#start-clause-back")?.addEventListener("click", hideClausePath);
  $("#flow-next")?.addEventListener("click", flowNext);
  $("#flow-back")?.addEventListener("click", flowBack);
  $("#step-guide-open")?.addEventListener("click", () => {
    if (!state.flowStep) return;
    delete state.guideDismissed[state.flowStep];
    saveGuideDismissed();
    renderStepGuide();
  });

  $("#paste-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const text = form.elements.namedItem("text").value;
    if (!text.trim()) return showError("Paste the policy clauses first.");
    if (!confirmReplace()) return;
    busy($("#paste-submit"), "Codifying…", async () => openProject(await call({
      action: "open", name: "pasted text", text,
    }), { resultStep: true, path: "clauses" }));
  });

  const drop = $("#drop");
  const bindFile = (input) => {
    if (!input) return;
    input.addEventListener("change", () => {
      if (!input.files[0]) return;
      if (!confirmReplace()) { input.value = ""; return; }
      openFile(input.files[0]);
      input.value = "";
    });
  };
  bindFile($("#file"));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("is-over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("is-over");
    if (e.dataTransfer.files[0] && confirmReplace()) openFile(e.dataTransfer.files[0]);
  });

  $("#demo").addEventListener("click", (e) => {
    if (!confirmReplace()) return;
    busy(e.currentTarget, "Opening…", async () => {
      const text = await (await fetch("acme-policy.md")).text();
      openProject(await call({ action: "open", name: "acme-information-security-policy-2016.md", content: text }), { resultStep: true, path: "clauses" });
    });
  });

  $("#resume-open").addEventListener("click", () => {
    if (state.project) {
      openFlow();
      return;
    }
    const saved = loadLocal();
    if (saved) openProject(saved);
  });
  $("#resume-discard")?.addEventListener("click", () => {
    if (confirm("Discard the work saved in this browser? Save an OSCAL catalog first if you want to keep it.")) {
      clearLocal();
      state.project = null;
      state.selected = null;
      state.flowStep = null;
      state.startPath = null;
      renderResume();
    }
  });

  const closeProject = () => {
    saveLocal();
    showNotice("");
    state.project = null;
    state.selected = null;
    state.resultStep = false;
    state.flowStep = null;
    state.startPath = null;
    showView("workspace");
  };
  $("#close-project").addEventListener("click", closeProject);
  $("#work-title")?.addEventListener("input", () => {
    if (!state.project) return;
    state.project.title = $("#work-title").value;
    saveSoon();
    renderCrumb();
    const resumeTitle = $("#resume-title");
    if (resumeTitle) resumeTitle.textContent = state.project.title || "Untitled policy";
  });
  $("#work-title")?.addEventListener("blur", () => {
    if (!state.project) return;
    if (!state.project.title.trim()) {
      state.project.title = "Untitled policy";
      $("#work-title").value = state.project.title;
      saveSoon();
      renderCrumb();
    }
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

  state.guideDismissed = loadGuideDismissed();
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

  $("#library-pick-search")?.addEventListener("input", () => {
    const list = $("#library-pick-list");
    if (list) renderLibraryPicks(list, $("#library-pick-search").value);
  });

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
    if (state.project && state.view === "flow" && state.flowStep === "controls"
        && !e.metaKey && !e.ctrlKey && !e.altKey
        && !e.target.closest("dialog, input, textarea, select, [contenteditable]")) {
      if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); moveStatementItem(1); return; }
      if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); moveStatementItem(-1); return; }
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
