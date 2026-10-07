"""Browser tests: the web app driven in Chromium with Playwright.

By default the page is served by codify-web. With CODIFY_SITE set to a site built by
scripts/build_site.py, the same tests run against the browser-only build that GitHub
Pages serves, with Codify's Python running in Pyodide.

Left out when Playwright is not installed (pip install -e ".[e2e]"; python -m
playwright install chromium). AI providers are never called: their APIs are answered by a fake.
"""

import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright import sync_api

from codify.webapp import make_server

PROVIDER_HOSTS = ("https://api.anthropic.com/**", "https://api.openai.com/**",
                  "https://generativelanguage.googleapis.com/**",
                  "http://localhost:11434/**", "http://127.0.0.1:11434/**")


class _Static(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript",
                      ".wasm": "application/wasm", ".json": "application/json"}

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def base_url():
    site = os.environ.get("CODIFY_SITE")
    if site:
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Static, directory=site))
    else:
        server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


class FakeProvider:
    """Answers AI provider requests with drafts, and records what was sent."""

    def __init__(self):
        self.requests = []
        self.status = 200
        self.controls = [{"action": "Review", "scope": "the clause duties", "limit": "at least every [N] days",
                          "purpose": "to detect gaps early", "guidance": "", "risk": "", "notes": []}]

    def handle(self, route):
        req = route.request
        self.requests.append({"url": req.url, "headers": req.headers, "body": json.loads(req.post_data or "{}")})
        cors = {"access-control-allow-origin": "*"}
        if self.status != 200:
            return route.fulfill(status=self.status, headers=cors, content_type="application/json",
                                 body=json.dumps({"error": {"message": "invalid x-api-key"}}))
        text = json.dumps({"controls": self.controls})
        url = req.url
        if "localhost:11434" in url or "127.0.0.1:11434" in url or "api.openai.com" in url:
            body = {"choices": [{"message": {"content": text}}]}
        elif "generativelanguage" in url:
            body = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        else:
            body = {"type": "message", "stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}
        return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(body))


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def page(browser, base_url, provider):
    context = browser.new_context(viewport={"width": 1360, "height": 900}, accept_downloads=True)
    # Shared fixtures land on the paste start. First-visit splash has its own tests.
    context.add_init_script("localStorage.setItem('codify:splash-seen', '1');")
    context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
    context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
    for host in PROVIDER_HOSTS:
        context.route(host, provider.handle)
    pg = context.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base_url)
    yield pg
    context.close()
    assert errors == [], errors


@pytest.fixture
def demo(page):
    """The Acme demo policy, open in the workspace."""
    page.click("#demo")
    page.wait_for_selector("#work:not([hidden]) .ctl", timeout=120_000)  # Pyodide's first load can be slow
    return page
