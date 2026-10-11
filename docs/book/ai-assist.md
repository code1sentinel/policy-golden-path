# Optional AI assist

AI drafting is **off** unless you turn it on. Codify still drafts with rules. The command line never uses AI.

The **AI** chip at the top of the page opens the settings. Leave it off unless you need a second opinion on wording.

{% hint style="warning" %}
Do not send classified or sensitive text. If in doubt, leave AI off: the rule drafts need no model.
{% endhint %}

## Keys stay in the browser

Your API key stays in this browser: for the tab only, unless you choose **Remember the key on this device**.

The key is **never** written to:

- the project
- the autosave
- the catalog
- the statement library
- any export

**Turn off and forget the key** removes it.

## What is sent

One clause per request: its text, its section heading, and Codify's rule drafts for it. Nothing else from the policy.

The request goes straight from your browser to the provider you choose, under your account and that provider's terms. There is no Codify server in between.

Turning AI on asks you to confirm this. Drafting several clauses at once asks once more, naming the provider and how many clauses will be sent.

## Providers

| Provider | Notes |
| --- | --- |
| Anthropic (Claude), OpenAI, or Google Gemini | Bring your own API key. Use any model your account has. |
| Ollama | A model on this machine at `http://localhost:11434`. No API key. The clause never leaves this device. |

Ollama works with `codify-web`. Browsers block `http://localhost` from the HTTPS online site, so Ollama is for the local app.

Codify will not point Ollama at a remote host.

## What comes back

The model fills in the parts of each statement (action, scope, limit, purpose) plus guidance and the risk. Codify joins the parts, scores the statement like any other draft, and marks it **drafted by AI** (`origin: ai` in the catalog).

AI drafts stay drafts. They are left out of **Select ready drafts**, so a person reviews each one.

## Where to run it

- **Draft with AI** on a clause replaces that clause's controls.
- With controls selected, the bulk action redrafts their clauses one by one. You can stop it. Clauses whose controls you have edited, reviewed, or accepted are left alone in bulk.
