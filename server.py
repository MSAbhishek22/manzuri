#!/usr/bin/env python3
"""Manzuri server — stdlib http.server + the SQLite store.

Routes:
  /                     agency console (static)
  /c/<token>            client approval page (the link IS the login)
  /api/clients          GET list · POST {name} create
  /api/clients/<id>/posts   GET posts · POST (multipart) add post
  /api/posts/<id>/edit      POST (multipart) edit -> voids approval
  /api/clients/<id>/export  GET approved-only checklist (.txt)
  /api/link/<token>         GET client view (name + posts)
  /api/link/<token>/decide POST {post_id, action, note_kind, note_text}
  /uploads/<name>       uploaded creatives

Run: python3 server.py [port]   (default 8797)
"""
import json
import mimetypes
import re
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from store import Store  # noqa: E402

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
UPLOADS = ROOT / "data" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
store = Store(ROOT / "data" / "manzuri.db")
MAX_UPLOAD = 3 * 1024 * 1024


def parse_multipart(body: bytes, content_type: str) -> tuple[dict, dict]:
    boundary = content_type.split("boundary=")[-1].strip().encode()
    fields, files = {}, {}
    for chunk in body.split(b"--" + boundary):
        if b"Content-Disposition" not in chunk:
            continue
        head, _, data = chunk.partition(b"\r\n\r\n")
        data = data.rstrip(b"\r\n-")
        name_m = re.search(rb'name="([^"]+)"', head)
        if not name_m:
            continue
        name = name_m.group(1).decode()
        file_m = re.search(rb'filename="([^"]*)"', head)
        if file_m and file_m.group(1):
            files[name] = (file_m.group(1).decode(), data)
        else:
            fields[name] = data.decode(errors="replace")
    return fields, files


def save_upload(filename: str, data: bytes) -> str | None:
    if not data or len(data) > MAX_UPLOAD:
        return None
    ext = Path(filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return None
    name = secrets.token_hex(10) + ext
    (UPLOADS / name).write_bytes(data)
    return name


class Handler(BaseHTTPRequestHandler):
    # ----- helpers -----
    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path):
        if not path.is_file():
            return self._json(404, {"error": "Not found."})
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _form(self):
        return parse_multipart(self._body(), self.headers.get("Content-Type", ""))

    # ----- routes -----
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._file(STATIC / "index.html")
        if path.startswith("/c/"):
            return self._file(STATIC / "client.html")
        if path.startswith("/static/"):
            return self._file(ROOT / path.lstrip("/"))
        if path.startswith("/uploads/"):
            return self._file(UPLOADS / Path(path).name)
        if path == "/api/clients":
            return self._json(200, store.list_clients())
        m = re.fullmatch(r"/api/clients/(\d+)/posts", path)
        if m:
            return self._json(200, store.posts_for_client(int(m.group(1))))
        m = re.fullmatch(r"/api/clients/(\d+)/export", path)
        if m:
            client_id = int(m.group(1))
            posts = store.export_checklist(client_id)
            lines = ["Manzuri — approved posts, ready to schedule", ""]
            for p in posts:
                lines.append(f"[ ] {p['day_label']} — v{p['version']} — {p['caption'][:80]}")
            if not posts:
                lines.append("(nothing approved yet)")
            body = ("\n".join(lines) + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="approved-checklist.txt"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        m = re.fullmatch(r"/api/link/([\w\-]+)", path)
        if m:
            client = store.client_by_token(m.group(1))
            if not client:
                return self._json(404, {"error": "This link is not valid. Ask your agency to send it again."})
            posts = store.posts_for_client(client["id"])
            return self._json(200, {"client": client["name"], "posts": posts})
        return self._json(404, {"error": "Not found."})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/clients":
                data = json.loads(self._body() or b"{}")
                name = (data.get("name") or "").strip()
                if not name:
                    return self._json(400, {"error": "Give the client a name."})
                return self._json(201, store.create_client(name))
            m = re.fullmatch(r"/api/clients/(\d+)/posts", path)
            if m:
                fields, files = self._form()
                image_name = None
                if "image" in files:
                    image_name = save_upload(*files["image"])
                    if image_name is None:
                        return self._json(400, {"error": "Image must be png/jpg/webp/gif, under 3 MB."})
                post = store.add_post(int(m.group(1)), fields.get("day_label", "").strip() or "Someday",
                                      fields.get("caption", ""), image_name)
                return self._json(201, post)
            m = re.fullmatch(r"/api/posts/(\d+)/edit", path)
            if m:
                fields, files = self._form()
                image_name = None
                if "image" in files:
                    image_name = save_upload(*files["image"])
                    if image_name is None:
                        return self._json(400, {"error": "Image must be png/jpg/webp/gif, under 3 MB."})
                result = store.edit_post(int(m.group(1)),
                                         caption=fields.get("caption"),
                                         image_name=image_name)
                return self._json(200, result)
            m = re.fullmatch(r"/api/link/([\w\-]+)/decide", path)
            if m:
                client = store.client_by_token(m.group(1))
                if not client:
                    return self._json(404, {"error": "This link is not valid."})
                data = json.loads(self._body() or b"{}")
                post = store.get_post(int(data.get("post_id", 0)))
                if not post or post["client_id"] != client["id"]:
                    return self._json(404, {"error": "That post is not on this page."})
                updated = store.decide(post["id"], data.get("action"),
                                       data.get("note_kind"), data.get("note_text"))
                return self._json(200, updated)
            return self._json(404, {"error": "Not found."})
        except (ValueError, KeyError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception as exc:  # keep the console honest, not crashy
            return self._json(500, {"error": f"Something broke ({type(exc).__name__})."})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    import os
    # Hosts (Render etc.) inject PORT; a CLI arg still wins locally.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8797"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
