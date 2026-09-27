"""policygp-web: PolicyGP as a local web app for guides, single and batch health checks.

Runs on the standard library only. It binds to 127.0.0.1 by default and has
no authentication, so only expose it on a network you trust.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import importlib.util
import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlsplit

from . import __version__, report
from .catalog import Catalog
from .guides import ADOPTED, GUIDES, PARTLY, STATUS_LABELS
from .models import KIND_LABELS, RECOMMENDATION, RISK_STATEMENT, Statement
from .policy import parse_policies
from .service import assess_all, parse_document, prepare
from .tabular import template, template_xlsx

MAX_BODY = 20 * 1024 * 1024  # bytes per request
MAX_CLAUDE_ITEMS = 200  # items per request with the Claude engine, to bound cost
STATIC = {"index.html": "text/html", "app.css": "text/css", "app.js": "text/javascript"}
CSP = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class BadRequest(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


def claude_available() -> bool:
    return importlib.util.find_spec("anthropic") is not None


def _text(value, name: str, limit: int = 20000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BadRequest(f"'{name}' must be text")
    if len(value) > limit:
        raise BadRequest(f"'{name}' is longer than {limit} characters")
    return value.strip()


def single_statement(item: dict) -> Statement:
    if not isinstance(item, dict):
        raise BadRequest("'item' must be an object")
    kind = item.get("kind") or "implementation"
    if kind not in KIND_LABELS:
        raise BadRequest(f"unknown kind {kind!r}")
    t = {k: _text(item.get(k), k) for k in ("control_id", "statement_id", "component", "title", "text",
                                            "requirement", "policy_intent", "risk_statement", "owner",
                                            "deadline", "likelihood", "impact", "risk")}
    if not t["text"]:
        raise BadRequest("enter the text to assess")
    ratings = {k: t[k] for k in ("likelihood", "impact", "risk") if t[k]}
    return Statement(
        control_id=t["control_id"], text=t["text"], source="single", uuid=None,
        statement_id=t["statement_id"] or None, component=t["component"] or None,
        requirement=t["requirement"] or None, policy_intent=t["policy_intent"] or None,
        policy_ids=["entered"] if t["policy_intent"] else [], kind=kind,
        title=t["title"] or (None if kind == "implementation" else KIND_LABELS[kind]),
        risk_statement=(t["risk_statement"] or None) if kind == RECOMMENDATION else None,
        ratings=ratings if kind in (RISK_STATEMENT, RECOMMENDATION) else {},
        owner=(t["owner"] or None) if kind == RECOMMENDATION else None,
        deadline=(t["deadline"] or None) if kind == RECOMMENDATION else None,
    )


def _upload(value, name: str) -> tuple[str, str | bytes] | None:
    """(file name, content): text as sent, or bytes for a base64-encoded binary file such as .xlsx."""
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        raise BadRequest(f"'{name}' must be an object with 'name' and 'content'")
    filename = str(value.get("name") or name)
    if isinstance(value.get("content_base64"), str):
        try:
            return filename, base64.b64decode(value["content_base64"], validate=True)
        except (binascii.Error, ValueError):
            raise BadRequest(f"{filename}: content_base64 is not valid base64") from None
    if not isinstance(value.get("content"), str):
        raise BadRequest(f"'{name}' must be an object with 'name' and 'content'")
    return filename, value["content"]


def batch_statements(body: dict) -> tuple[list[Statement], list[dict], list[str]]:
    docs = body.get("documents")
    if not isinstance(docs, list) or not docs:
        raise BadRequest("add at least one file to assess")
    catalog = policies = None
    cat = _upload(body.get("catalog"), "catalog")
    if cat:
        try:
            catalog = Catalog(json.loads(cat[1]))
        except (ValueError, KeyError, TypeError) as exc:
            raise BadRequest(f"catalog {cat[0]}: {exc}") from None
    pol = _upload(body.get("policy"), "policy")
    if pol:
        try:
            policies = parse_policies(json.loads(pol[1]))
        except (ValueError, KeyError, TypeError) as exc:
            raise BadRequest(f"policy file {pol[0]}: {exc}") from None

    items: list[Statement] = []
    names: list[str] = []
    files: list[dict] = []
    for i, doc in enumerate(docs):
        upload = _upload(doc, f"documents[{i}]")
        name, content = upload if upload else (f"file {i + 1}", "")
        try:
            found = parse_document(name, content)
        except (ValueError, KeyError, TypeError) as exc:
            files.append({"name": name, "count": 0, "error": str(exc)})
            continue
        if not found:
            files.append({"name": name, "count": 0, "error": "nothing to assess in this file"})
            continue
        files.append({"name": name, "count": len(found), "error": None})
        items += found
        names += [name] * len(found)
    prepare(items, catalog, policies)
    return items, files, names


class Handler(BaseHTTPRequestHandler):
    server_version = f"policygp/{__version__}"
    assessor = None  # injected in tests

    def log_message(self, fmt, *args):  # quieter than the default
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _send(self, status: HTTPStatus, body: bytes, content_type: str, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, data: dict):
        self._send(status, json.dumps(data).encode(), "application/json")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            path = "/index.html"
        name = path.lstrip("/")
        if name in STATIC:
            body = resources.files("policygp").joinpath("static", name).read_bytes()
            return self._send(HTTPStatus.OK, body, f"{STATIC[name]}; charset=utf-8")
        if path == "/api/config":
            from .llm import DEFAULT_MODEL

            return self._json(HTTPStatus.OK, {
                "version": __version__,
                "engines": ["heuristic"] + (["claude"] if claude_available() else []),
                "claude_model": DEFAULT_MODEL,
                "kinds": KIND_LABELS,
                "max_claude_items": MAX_CLAUDE_ITEMS,
            })
        if path == "/api/guides":
            return self._json(HTTPStatus.OK, {
                "guides": GUIDES, "statuses": STATUS_LABELS, "adopted": ADOPTED, "partly": PARTLY,
            })
        if path == "/api/template.xlsx":
            return self._send(HTTPStatus.OK, template_xlsx(),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              {"Content-Disposition": 'attachment; filename="policygp-template.xlsx"'})
        if path == "/api/template.csv":
            return self._send(HTTPStatus.OK, template().encode(), "text/csv; charset=utf-8",
                              {"Content-Disposition": 'attachment; filename="policygp-template.csv"'})
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/assess":
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        try:
            self._check_origin()
            body = self._read_json()
            result = self._assess(body)
        except BadRequest as exc:
            return self._json(exc.status, {"error": str(exc)})
        self._json(HTTPStatus.OK, result)

    def _check_origin(self):
        # Browsers send Origin on cross-site POSTs; refuse them so other sites cannot drive this server.
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            raise BadRequest("cross-origin requests are not allowed", HTTPStatus.FORBIDDEN)
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            raise BadRequest("send JSON", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise BadRequest("bad Content-Length") from None
        if length > MAX_BODY:
            raise BadRequest(f"request is larger than {MAX_BODY // (1024 * 1024)} MB",
                             HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise BadRequest("request body is not valid JSON") from None
        if not isinstance(body, dict):
            raise BadRequest("request body must be a JSON object")
        return body

    def _assess(self, body: dict) -> dict:
        engine = body.get("engine") or "heuristic"
        if engine not in ("heuristic", "claude"):
            raise BadRequest(f"unknown engine {engine!r}")
        if engine == "claude" and self.assessor is None and not claude_available():
            raise BadRequest("the Claude engine needs the anthropic package: pip install 'policygp[claude]'")

        mode = body.get("mode")
        if mode == "single":
            items, files, names = [single_statement(body.get("item"))], [], ["Single input"]
        elif mode == "batch":
            items, files, names = batch_statements(body)
        else:
            raise BadRequest("'mode' must be 'single' or 'batch'")

        if engine == "claude" and len(items) > MAX_CLAUDE_ITEMS:
            raise BadRequest(f"{len(items)} items is more than the {MAX_CLAUDE_ITEMS} allowed per Claude run; "
                             "split the batch or use the heuristic engine")
        try:
            assessments = assess_all(items, engine, effort=body.get("effort") or "medium",
                                     assessor=self.assessor)
        except Exception as exc:  # engine failures (auth, network) go back to the page, not a stack trace
            if engine != "claude":
                raise
            raise BadRequest(f"Claude engine failed: {exc.__class__.__name__}: {exc}", HTTPStatus.BAD_GATEWAY)

        rows = []
        for name, a in zip(names, assessments):
            d = a.to_dict()
            d["file"] = name
            rows.append(d)
        return {
            "summary": report.summary(assessments),
            "files": files,
            "assessments": rows,
            "markdown": report.to_markdown(assessments),
        }


def make_server(host: str = "127.0.0.1", port: int = 8765, assessor=None, verbose: bool = False):
    handler = type("BoundHandler", (Handler,), {"assessor": assessor})
    server = ThreadingHTTPServer((host, port), handler)
    server.verbose = verbose
    return server


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="policygp-web", description="PolicyGP web app.")
    p.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="port (default: 8765)")
    p.add_argument("--open", action="store_true", help="open the page in a browser")
    p.add_argument("--verbose", action="store_true", help="log each request")
    args = p.parse_args(argv)
    server = make_server(args.host, args.port, verbose=args.verbose)
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '::1') else args.host}:{server.server_port}/"
    if args.host not in ("127.0.0.1", "::1", "localhost"):
        print("warning: the app has no authentication; anyone who can reach this address can use it",
              file=sys.stderr)
    print(f"PolicyGP on {url}  (Ctrl+C to stop)")
    if args.open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
