"""Manzuri WSGI entry point — for hosts that only run WSGI apps
(e.g. PythonAnywhere free tier, no card needed).

PythonAnywhere setup: upload this repo to /home/<user>/manzuri,
then in the Web tab create a Python 3 app whose WSGI file is this
file (or imports `application` from it). The SQLite store and the
uploads live under the repo's data/ directory, which PythonAnywhere
can write to. No env vars, no dependencies beyond the stdlib.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core import dispatch  # noqa: E402


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    if environ.get("QUERY_STRING"):
        path += "?" + environ["QUERY_STRING"]
    headers = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            headers[key[5:].lower().replace("_", "-")] = value
    if "CONTENT_TYPE" in environ:
        headers["content-type"] = environ["CONTENT_TYPE"]
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length) if length else b""

    status, ctype, out, extra = dispatch(method, path, headers, body)
    response_headers = [("Content-Type", ctype),
                        ("Content-Length", str(len(out)))]
    response_headers += list(extra.items())
    start_response(f"{status} {_reason(status)}", response_headers)
    return [out]


def _reason(status):
    return {200: "OK", 201: "Created", 400: "Bad Request",
            404: "Not Found", 405: "Method Not Allowed",
            500: "Internal Server Error"}.get(status, "OK")
