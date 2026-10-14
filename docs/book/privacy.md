# Privacy and security

Codify's default promise: **the policy never leaves your device.**

{% hint style="info" %}
This book does not add scripts, widgets, or analytics to the app. The app itself makes no third-party requests unless you turn AI drafting on.
{% endhint %}

## What stays on the device

| Surface | What happens |
| --- | --- |
| Online site | Python runs in the browser (Pyodide), served from the site. No upload. |
| `codify-web` | Binds to `127.0.0.1`, no login, refuses cross-origin POSTs, writes nothing to disk. |
| Command line | Reads a local file, writes a local file or stdout. No network. |

The site and the local app use the system font stack. They do not load fonts, scripts, or analytics from other hosts.

Work in the browser is stored only in this browser:

- `codify:project` — the open project (clauses, controls, identified risks)
- `codify:statements` — the statement library
- `codify:splash-seen` — whether you dismissed the welcome
- `codify:theme` — Light / Dark / System

Clearing site data removes them. Closing the tab forgets an API key unless you chose to remember it.

## Optional AI

See [Optional AI assist](ai-assist.md). Summary:

- Off unless you turn it on and confirm
- One clause per request, plus its heading and the rule drafts
- Key stays in the browser — never written to the project, library, or exports
- Ollama is localhost only (`http://localhost:11434`)

Do not send classified or sensitive text to a cloud provider.

## What the page is allowed to talk to

Content-Security-Policy `connect-src` may include only `'self'`, the three opt-in cloud AI origins (Anthropic, OpenAI, Gemini), and `http://localhost:11434` / `http://127.0.0.1:11434`.

No new outbound origin is added without an architecture decision and a privacy check on the pull request.

## What we do not do

- Host policy text or API keys on a Codify server
- Authenticate users or expose `codify-web` on a public interface
- Call AI from the command line or from rule drafts
