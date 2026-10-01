"""codify-web: Codify as a local web app.

Runs on the standard library only. It binds to 127.0.0.1 by default and has
no authentication, so only expose it on a network you trust.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlsplit

from . import __version__, api
from .api import BadRequest

MAX_BODY = 30 * 1024 * 1024  # bytes per request
STATIC = {"index.html": "text/html", "app.css": "text/css", "app.js": "text/javascript",
          "acme-policy.md": "text/markdown", "acme-policy.docx":
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
# AI drafting (off unless the person turns it on) calls these providers from the page with the person's own key.
AI_ORIGINS = "https://api.anthropic.com https://api.openai.com https://generativelanguage.googleapis.com"
CSP = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' " + AI_ORIGINS + "; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Handler(BaseHTTPRequestHandler):
    server_version = f"codify/{__version__}"

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
            body = resources.files("codify").joinpath("static", name).read_bytes()
            return self._send(HTTPStatus.OK, body, f"{STATIC[name]}; charset=utf-8")
        if path == "/api/config":
            return self._json(HTTPStatus.OK, api.config())
        if path == "/api/guide":
            return self._json(HTTPStatus.OK, api.guide())
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api":
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        try:
            self._check_origin()
            body = self._read_json()
            result = api.call(body)
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


def make_server(host: str = "127.0.0.1", port: int = 8765, verbose: bool = False):
    server = ThreadingHTTPServer((host, port), Handler)
    server.verbose = verbose
    return server


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="codify-web", description="Codify web app.")
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
    print(f"Codify on {url}  (Ctrl+C to stop)")
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
