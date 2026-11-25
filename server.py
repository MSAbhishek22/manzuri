#!/usr/bin/env python3
"""Manzuri server — stdlib http.server, thin wrapper over core.dispatch.

Run: python3 server.py [port]   (default 8797)
"""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import core  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, ctype, body, extra):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        headers = {k.lower(): v for k, v in self.headers.items()}
        status, ctype, out, extra = core.dispatch(method, self.path, headers, body)
        self._send(status, ctype, out, extra)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    import os
    # Hosts (Render etc.) inject PORT; a CLI arg still wins locally.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8797"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
