# When to Mock

Mock at **system boundaries** only:

- External AI HTTP APIs (Anthropic, OpenAI, Gemini, Ollama)
- Time / randomness
- The real browser download or clipboard, when the test cannot observe them
  through the page

Prefer a real in-process object when you control it (`codify.api.call`,
`new_project`, the local `codify-web` server).

Do not mock:

- `codify.classify`, `codify.draft`, `codify.project`, or other modules
  you own
- Internal collaborators
- Anything you control

E2E already fakes AI providers in `tests/e2e/conftest.py`
(`FakeProvider` + Playwright route). Unit tests must not open a network
connection; they call `api.call` or the library functions directly.

## Designing for mockability

At system boundaries, pass the external dependency in rather than
creating it internally.

```python
# Easy to fake: the page owns the fetch; tests route it
# tests/e2e/conftest.py — FakeProvider.handle(route)

# Hard to fake: a hidden client built from an env key
def draft_with_ai(clause):
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return client.messages.create(...)
```

Prefer one function per external operation over a generic fetcher that
the mock must branch on:

```python
# GOOD: each operation is independently fakeable
class Providers:
    def complete_anthropic(self, payload): ...
    def complete_ollama(self, payload): ...

# BAD: mock must switch on URL / method
def complete(url, payload): ...
```

The SDK approach means each fake returns one specific shape, with no
conditional logic in test setup. Keys stay out of the fake: use
`sk-test` in e2e only, never a real secret.
