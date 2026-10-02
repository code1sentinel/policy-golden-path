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
  im8: null,           // the IM8 Reform catalog: {title, version, domains, controls: [brief...]}
  im8Risk: "low",
  im8Show: "all",
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
      const res = await fetch("https://api.anthropic.com/v1/messages", { method: "POST", headers, body: JSON.stringify(body) });
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
      const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
        body: JSON.stringify({ model, messages: [{ role: "system", content: p.system }, { role: "user", content: p.user }],
          response_format: { type: "json_schema", json_schema: { name: "controls", strict: true, schema: p.schema } } }),
      });
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
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({ systemInstruction: { parts: [{ text: p.system }] },
          contents: [{ role: "user", parts: [{ text: p.user }] }],
          generationConfig: { responseMimeType: "application/json" } }),
      });
      const data = await providerJson(res, "Gemini");
      const parts = (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) || [];
      if (!parts.length) throw new Error("Gemini returned no draft for this clause.");
      return parts.map((x) => x.text || "").join("");
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

const aiReady = () => ai.on && !!ai.key;
const aiName = () => `${PROVIDERS[ai.provider].label}, ${ai.model}`;

function renderAiButton() {
  const b = $("#ai-open");
  b.textContent = aiReady() ? "AI drafting: on" : ai.on ? "AI drafting: needs a key" : "AI drafting: off";
  b.setAttribute("aria-pressed", String(aiReady()));
  $("#ai-bulk").hidden = !aiReady();
}

function fillModels(provider) {
  $("#ai-models").replaceChildren(...PROVIDERS[provider].models.map((m) => el("option", { value: m })));
}

function openAiDialog() {
  $("#ai-provider").replaceChildren(...Object.entries(PROVIDERS).map(([k, v]) => el("option", { value: k, text: v.label })));
  $("#ai-provider").value = ai.provider;
  fillModels(ai.provider);
  $("#ai-model").value = ai.model;
  $("#ai-key").value = ai.key;
  $("#ai-key").placeholder = ai.key ? "" : "Paste your API key";
  $("#ai-remember").checked = ai.remember;
  $("#ai-ack").checked = false;
  $("#ai-off").hidden = !ai.on && !ai.key;
  $("#ai-form-error").hidden = true;
  $("#ai-dialog").showModal();
}

function aiFormSubmit(e) {
  const action = e.submitter ? e.submitter.value : "cancel";
  const fail = (message) => {
    e.preventDefault();
    const box = $("#ai-form-error");
    box.textContent = message;
    box.hidden = false;
  };
  if (action === "off") {
    Object.assign(ai, { on: false, key: "", remember: false });
  } else if (action === "on") {
    const model = $("#ai-model").value.trim();
    const key = $("#ai-key").value.trim();
    if (!$("#ai-ack").checked) return fail("Tick the box to confirm you have read what is sent.");
    if (!model) return fail("Enter a model.");
    if (!key) return fail("Enter your API key.");
    Object.assign(ai, { on: true, provider: $("#ai-provider").value, model, key, remember: $("#ai-remember").checked });
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
  // the person has worked on this clause's controls: edited, reviewed, accepted or mapped them
  return controlsOf(clause.id).some((c) => c.status !== "draft" || (c.origin !== "rules" && c.origin !== "ai") ||
    (c.im8 || []).length);
}

async function aiRedraft(clause, button) {
  if (!aiReady()) return openAiDialog();
  const existing = controlsOf(clause.id);
  if (needsConfirm(clause) && !confirm(`Replace the ${plural(existing.length, "control")} from clause ${clause.id}, including your edits, with AI drafts?`)) return;
  await busy(button, "Drafting with AI…", async () => replaceControls(clause, await aiDraftClause(clause)));
}

async function aiBulk() {
  if (!aiReady()) return openAiDialog();
  const ids = new Set([...state.checked].map((id) => controlById(id)?.clause).filter(Boolean));
  const clauses = state.project.clauses.filter((c) => ids.has(c.id));
  const todo = clauses.filter((c) => !needsConfirm(c));
  const skipped = clauses.length - todo.length;
  if (!todo.length) return showError("The selected controls have all been edited, reviewed, accepted or mapped, so AI drafting leaves them alone. Use \"Draft with AI\" on a clause to replace its controls.");
  const note = skipped ? `\n\n${plural(skipped, "clause")} with edited, reviewed, accepted or mapped controls will be left alone.` : "";
  if (!confirm(`Send ${plural(todo.length, "clause")} to ${aiName()}, one request per clause?\n\nEach request holds one clause's text, section heading and rule drafts. Their controls are replaced with AI drafts.${note}`)) return;
  ai.stop = false;
  showError("");
  const bar = $("#ai-progress");
  bar.hidden = false;
  let done = 0;
  try {
    for (const clause of todo) {
      if (ai.stop) break;
      $("#ai-progress-text").textContent = `Drafting with AI: clause ${clause.id} (${done + 1} of ${todo.length})…`;
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

// ---------------------------------------------------------------- IM8 Reform mapping
//
// Suggestions rank IM8 Reform controls by shared wording; a mapping counts once the person adds it.

async function loadIm8() {
  if (!state.im8) state.im8 = await call({ action: "im8" });
  return state.im8;
}

const im8Brief = (id) => (state.im8 ? state.im8.controls.find((x) => x.id === id) : null);

function levelBadges(levels) {
  return el("span", { class: "levels" }, ["low", "medium"].map((risk) =>
    levels && levels[risk] !== undefined
      ? el("span", { class: `level level--${levels[risk]}`, title: `${risk}-risk systems: Level ${levels[risk]}`, text: `${risk === "low" ? "Low" : "Med"} L${levels[risk]}` })
      : null));
}

function setMappings(c, ids) {
  c.im8 = [...new Set(ids)];
  saveLocal();
  render();
}

function im8Panel(c, clause) {
  const mapped = c.im8 || [];
  const box = el("div", { class: "im8" });
  const chips = el("div", { class: "im8__mapped" }, mapped.length ? mapped.map((id) => {
    const b = im8Brief(id);
    const remove = el("button", { type: "button", class: "chip-x", "aria-label": `Remove mapping to ${id}`, text: "×" });
    remove.addEventListener("click", () => setMappings(c, mapped.filter((x) => x !== id)));
    return el("span", { class: "im8-chip", title: b ? b.statement : "" }, el("strong", { text: id }), b ? ` ${b.title}` : "", remove);
  }) : el("span", { class: "muted", text: "Not mapped yet." }));
  const suggestions = el("div", { class: "im8__suggest" }, el("p", { class: "placeholder", text: "Finding IM8 controls…" }));

  const find = el("input", { list: "im8-all", placeholder: "Find an IM8 control: id or title", autocomplete: "off", "aria-label": "Find an IM8 Reform control" });
  const options = el("datalist", { id: "im8-all" });
  const addBtn = el("button", { type: "button", class: "btn btn--small", text: "Map" });
  const addFound = () => {
    const id = find.value.trim().split(/\s/)[0].toLowerCase();
    if (!im8Brief(id)) return showError(`"${find.value}" is not an IM8 Reform control. Pick one from the list.`);
    showError("");
    setMappings(c, [...mapped, id]);
  };
  addBtn.addEventListener("click", addFound);
  find.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addFound(); } });

  box.append(el("h3", {}, "IM8 Reform ", el("em", { text: "what this control maps to" })), chips, suggestions,
    el("div", { class: "im8__find" }, find, addBtn, options));

  loadIm8().then((cat) => {
    options.replaceChildren(...cat.controls.map((x) => el("option", { value: `${x.id} ${x.title}` })));
    // names for the chips, now that the catalog is here
    for (const chip of $$(".im8-chip", chips)) {
      const id = chip.querySelector("strong").textContent;
      const b = im8Brief(id);
      if (b && chip.childNodes.length === 2) chip.insertBefore(document.createTextNode(` ${b.title}`), chip.lastChild);
      if (b) chip.title = b.statement;
    }
    if (!c.text) return suggestions.replaceChildren();
    return call({ action: "im8", text: c.text, context: clause.text || "", exclude: mapped }).then((data) => {
      if (!data.suggestions.length) return suggestions.replaceChildren(el("p", { class: "hint", text: "No close match in IM8 Reform. Find one below if it maps to something." }));
      suggestions.replaceChildren(el("p", { class: "hint", text: "Suggested from shared wording. Map only what really matches." }),
        el("ul", { class: "im8__list" }, data.suggestions.map((x) => {
          const map = el("button", { type: "button", class: "btn btn--small", text: "Map", "aria-label": `Map to ${x.id}` });
          map.addEventListener("click", () => setMappings(c, [...(c.im8 || []), x.id]));
          return el("li", {},
            el("div", { class: "im8__head" }, el("strong", { text: x.id }), ` ${x.title}`, el("span", { class: "muted", text: ` · ${x.domain}` }), levelBadges(x.levels)),
            el("p", { class: "im8__smt", text: x.statement }), map);
        })));
    });
  }).catch((err) => suggestions.replaceChildren(el("p", { class: "placeholder", text: err.message })));
  return box;
}

async function im8Bulk() {
  const targets = [...state.checked].map(controlById).filter((c) => c && c.text && !(c.im8 || []).length);
  if (!targets.length) return showError("The selected controls are all mapped already (or empty). Change a mapping in the editor.");
  if (!confirm(`Map ${plural(targets.length, "control")} to their top IM8 Reform suggestion?\n\nSuggestions come from shared wording, so check each one in the editor or the coverage view. Controls with no close match stay unmapped.`)) return;
  await busy($("#im8-bulk"), "Mapping…", async () => {
    let mappedCount = 0;
    for (const c of targets) {
      const clause = clauseById(c.clause) || { text: "" };
      const data = await call({ action: "im8", text: c.text, context: clause.text });
      if (data.suggestions.length) { c.im8 = [data.suggestions[0].id]; mappedCount += 1; }
    }
    state.checked.clear();
    saveLocal();
    render();
    showNotice(`Mapped ${plural(mappedCount, "control")} to their top IM8 suggestion.` +
      (mappedCount < targets.length ? ` ${plural(targets.length - mappedCount, "control")} had no close match and stay unmapped: filter "Not mapped to IM8" to see them.` : ""));
  });
}

async function renderCoverage() {
  const has = !!state.project;
  $("#im8-empty").hidden = has;
  $("#im8-body").hidden = !has;
  if (!has) return;
  try {
    const cov = await call({ action: "coverage", project: state.project });
    $("#im8-source").textContent = `${cov.title}, version ${cov.version} (GovTech, MIT licence).`;
    const risk = state.im8Risk;
    const levelNames = ["Level 0 must-have", "Level 1 should-have", "Level 2 good-to-have"];
    $("#im8-levels").replaceChildren(
      el("div", { class: "im8-level im8-level--all" }, el("strong", { text: `${cov.covered} of ${cov.total}` }), el("span", { text: "IM8 controls covered" })),
      ...[0, 1, 2].map((n) => {
        const l = cov.levels[`${risk}-${n}`];
        const fill = el("span", { class: "bar__fill" });
        fill.style.width = pct(l.total ? l.covered / l.total : 0);
        return el("div", { class: "im8-level" }, el("strong", { text: `${l.covered} of ${l.total}` }), el("span", { text: levelNames[n] }),
          el("span", { class: "bar", role: "img", "aria-label": `${l.covered} of ${l.total} covered` }, fill));
      }));
    const gapsOnly = state.im8Show === "gaps";
    $("#im8-domains").replaceChildren(...cov.domains.map((d) => {
      const rows = d.controls.filter((r) => !gapsOnly || !r.controls.length);
      if (!rows.length) return null;
      return el("section", { class: "im8-domain card" },
        el("h3", {}, d.title, el("span", { class: "muted", text: ` ${d.covered} of ${d.controls.length} covered` })),
        el("ul", { class: "im8-rows" }, rows.map((r) => {
          const level = r.levels[risk];
          return el("li", { class: r.controls.length ? "is-covered" : "is-gap" },
            el("div", { class: "im8__head" }, el("strong", { text: r.id }), ` ${r.title}`,
              level !== undefined ? el("span", { class: `level level--${level}`, text: `L${level}` }) : el("span", { class: "level level--none", text: `not in ${risk}-risk profiles` })),
            el("p", { class: "im8__smt", text: r.statement }),
            r.controls.length
              ? el("div", { class: "im8-from" }, "Mapped from ", r.controls.map((id) => {
                const b = el("button", { type: "button", class: "linkish", text: id });
                b.addEventListener("click", () => { showView("work"); select({ control: id }); });
                return b;
              }))
              : el("span", { class: "gap", text: "Gap" }));
        })));
    }).filter(Boolean));
  } catch (err) { showError(err.message); }
}

// ---------------------------------------------------------------- views

function showView(view) {
  for (const b of $$("[data-view]")) b.setAttribute("aria-pressed", String(b.dataset.view === view));
  $("#guide").hidden = view !== "guide";
  $("#im8-view").hidden = view !== "im8";
  if (view === "im8") renderCoverage();
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
  if (f === "unmapped") return !(control.im8 || []).length;
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

function controlRow(c, inEditor = false) {
  const box = el("input", { type: "checkbox", "aria-label": `Select ${c.id}` });
  box.checked = state.checked.has(c.id);
  box.addEventListener("change", () => {
    if (box.checked) state.checked.add(c.id); else state.checked.delete(c.id);
    renderBulk();
  });
  const mapped = c.im8 || [];
  const open = el("button", { type: "button", class: "ctl__open" },
    el("span", { class: "ctl__id", text: c.id }), el("span", { class: "ctl__text", text: c.text || "(empty)" }),
    mapped.length ? el("span", { class: "im8-tag", title: "Mapped to IM8 Reform", text: `IM8 ${mapped.join(", ")}` }) : null);
  open.addEventListener("click", () => select({ control: c.id }));
  const row = el("div", { class: "ctl", id: inEditor ? null : `ctl-${c.id}`, "aria-current": String(state.selected?.control === c.id) },
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
  controls.map((c) => controlRow(c)));
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
  $("#ai-bulk").disabled = n === 0;
  $("#im8-bulk").disabled = n === 0;
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
    if (c.origin !== "person") c.origin = "person";  // the drafting notes still say how it began
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
  let aiBtn = null;
  if (aiReady() && clause.text) {
    aiBtn = el("button", { type: "button", class: "btn btn--small btn--quiet", text: "Draft this clause with AI" });
    aiBtn.addEventListener("click", () => aiRedraft(clause, aiBtn));
  }

  put(box,
    el("div", { class: "editor__nav" },
      el("p", { class: "editor__where" }, "Control ", el("strong", { text: c.id }), ` · ${ORIGIN_LABELS[c.origin] || "edited"}`),
      el("div", { class: "actions" }, prev, next)),
    clause.text ? legacyBox(clause) : null,
    el("label", { class: "field" }, el("span", { text: "Control statement" }), statement),
    result,
    c.notes && c.notes.length ? el("div", {}, el("h3", { text: "Drafting notes" }), el("ul", { class: "notes" }, c.notes.map((n) => el("li", { text: n })))) : null,
    el("label", { class: "field" }, el("span", {}, "Risk it treats ", el("em", { text: "gives the control its purpose" })), risk),
    el("div", { class: "grid2" },
      el("label", { class: "field" }, el("span", {}, "Guidance ", el("em", { text: "tools, how-to" })), guidance),
      el("label", { class: "field" }, el("span", {}, "Who ", el("em", { text: "who implements it" })), who)),
    im8Panel(c, clause),
    el("h3", { text: "Status" }), statuses,
    el("div", { class: "editor__foot" }, add, aiBtn, remove),
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
  const aiBtn = el("button", { type: "button", class: "btn btn--small", text: "Draft with AI" });
  aiBtn.addEventListener("click", () => aiRedraft(clause, aiBtn));
  put(box,
    el("p", { class: "editor__where" }, "Clause ", el("strong", { text: clause.id }), clause.heading ? ` · ${clause.heading}` : ""),
    legacyBox(clause),
    el("label", { class: "field" }, el("span", { text: "Type" }), type),
    el("p", { class: "hint", text: clause.duplicate_of ? `Repeats ${clause.duplicate_of}, so no control was drafted from it.` : `Sorted as ${TYPE_LABELS[clause.type].toLowerCase()}: ${clause.reason}.` }),
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
  if (existing.some((c) => c.origin !== "rules") && !confirm(`Replace the ${plural(existing.length, "control")} from clause ${clause.id}, including your edits?`)) return;
  await busy(button, "Drafting…", async () => replaceControls(clause, await call({ action: "redraft", clause_id: clause.id, text: clause.text })));
}

function replaceControls(clause, data, show = true) {
  // put new drafts where the clause's controls were
  const at = state.project.controls.findIndex((c) => c.clause === clause.id);
  keepMappings(controlsOf(clause.id), data.controls);
  for (const c of controlsOf(clause.id)) { delete state.scores[c.id]; state.checked.delete(c.id); }
  state.project.controls = state.project.controls.filter((c) => c.clause !== clause.id);
  state.project.controls.splice(at >= 0 ? at : insertionPoint(clause), 0, ...data.controls);
  Object.assign(state.scores, data.scores);
  if (!show) return;
  state.selected = data.controls[0] ? { control: data.controls[0].id } : { clause: clause.id };
  saveLocal();
  render();
}

function keepMappings(before, after) {
  // IM8 mappings are a person's work: a new draft with the same id keeps them, and the rest go to the first draft
  if (!after.length) return;
  const byId = new Map(after.map((c) => [c.id, c]));
  for (const old of before) {
    if (!(old.im8 || []).length) continue;
    const to = byId.get(old.id) || after[0];
    to.im8 = [...new Set([...(to.im8 || []), ...old.im8])];
  }
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
  const control = { id, clause: clause.id, text: "", guidance: "", risk: "", who: "", notes: [], status: "draft", origin: "person", im8: [] };
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
    showNotice("");
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
    $("#ai-key").value = p === ai.provider ? ai.key : "";  // a key belongs to one provider
  });
  $("#ai-form").addEventListener("submit", aiFormSubmit);
  $("#ai-form").addEventListener("input", () => { $("#ai-form-error").hidden = true; });
  $("#ai-bulk").addEventListener("click", aiBulk);
  $("#im8-bulk").addEventListener("click", im8Bulk);
  $("#im8-risk").addEventListener("change", () => { state.im8Risk = $("#im8-risk").value; renderCoverage(); });
  for (const b of $$("[data-im8-show]")) {
    b.addEventListener("click", () => {
      state.im8Show = b.dataset.im8Show;
      for (const x of $$("[data-im8-show]")) x.setAttribute("aria-pressed", String(x === b));
      renderCoverage();
    });
  }
  $("#ai-stop").addEventListener("click", () => {
    ai.stop = true;
    $("#ai-progress-text").textContent = "Stopping after this clause…";
  });
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
