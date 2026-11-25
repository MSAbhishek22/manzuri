"""Manzuri core — pure request dispatch shared by the local stdlib
server (server.py) and the WSGI adapter (wsgi.py, for hosts like
PythonAnywhere that only run WSGI apps).

dispatch(method, path, headers, body) -> (status, content_type,
body_bytes, extra_headers). No sockets, no globals besides the Store.
"""
import json
import mimetypes
import re
import secrets
from pathlib import Path

from store import Store

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


def _json(status, payload):
    return status, "application/json", json.dumps(payload).encode(), {}


def _file(path: Path):
    if not path.is_file():
        return _json(404, {"error": "Not found."})
    body = path.read_bytes()
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return 200, ctype, body, {}


def dispatch(method: str, path: str, headers: dict, body: bytes):
    """Route one request. headers keys are lower-cased. Returns
    (status, content_type, body_bytes, extra_headers)."""
    path = path.split("?")[0]
    ctype = headers.get("content-type", "")
    try:
        if method == "GET":
            if path == "/":
                return _file(STATIC / "index.html")
            if path.startswith("/c/"):
                return _file(STATIC / "client.html")
            if path.startswith("/static/"):
                return _file(ROOT / path.lstrip("/"))
            if path.startswith("/uploads/"):
                return _file(UPLOADS / Path(path).name)
            if path == "/api/clients":
                return _json(200, store.list_clients())
            m = re.fullmatch(r"/api/clients/(\d+)/posts", path)
            if m:
                return _json(200, store.posts_for_client(int(m.group(1))))
            m = re.fullmatch(r"/api/clients/(\d+)/export", path)
            if m:
                posts = store.export_checklist(int(m.group(1)))
                lines = ["Manzuri — approved posts, ready to schedule", ""]
                for p in posts:
                    lines.append(f"[ ] {p['day_label']} — v{p['version']} — {p['caption'][:80]}")
                if not posts:
                    lines.append("(nothing approved yet)")
                body = ("\n".join(lines) + "\n").encode()
                return 200, "text/plain; charset=utf-8", body, {
                    "Content-Disposition": 'attachment; filename="approved-checklist.txt"'}
            m = re.fullmatch(r"/api/link/([\w\-]+)", path)
            if m:
                client = store.client_by_token(m.group(1))
                if not client:
                    return _json(404, {"error": "This link is not valid. Ask your agency to send it again."})
                return _json(200, {"client": client["name"],
                                   "posts": store.posts_for_client(client["id"])})
            return _json(404, {"error": "Not found."})

        if method == "POST":
            if path == "/api/clients":
                data = json.loads(body or b"{}")
                name = (data.get("name") or "").strip()
                if not name:
                    return _json(400, {"error": "Give the client a name."})
                return _json(201, store.create_client(name))
            m = re.fullmatch(r"/api/clients/(\d+)/posts", path)
            if m:
                fields, files = parse_multipart(body, ctype)
                image_name = None
                if "image" in files:
                    image_name = save_upload(*files["image"])
                    if image_name is None:
                        return _json(400, {"error": "Image must be png/jpg/webp/gif, under 3 MB."})
                post = store.add_post(int(m.group(1)), fields.get("day_label", "").strip() or "Someday",
                                      fields.get("caption", ""), image_name)
                return _json(201, post)
            m = re.fullmatch(r"/api/posts/(\d+)/edit", path)
            if m:
                fields, files = parse_multipart(body, ctype)
                image_name = None
                if "image" in files:
                    image_name = save_upload(*files["image"])
                    if image_name is None:
                        return _json(400, {"error": "Image must be png/jpg/webp/gif, under 3 MB."})
                result = store.edit_post(int(m.group(1)),
                                         caption=fields.get("caption"),
                                         image_name=image_name)
                return _json(200, result)
            m = re.fullmatch(r"/api/link/([\w\-]+)/decide", path)
            if m:
                client = store.client_by_token(m.group(1))
                if not client:
                    return _json(404, {"error": "This link is not valid."})
                data = json.loads(body or b"{}")
                post = store.get_post(int(data.get("post_id", 0)))
                if not post or post["client_id"] != client["id"]:
                    return _json(404, {"error": "That post is not on this page."})
                updated = store.decide(post["id"], data.get("action"),
                                       data.get("note_kind"), data.get("note_text"))
                return _json(200, updated)
            return _json(404, {"error": "Not found."})

        return _json(405, {"error": "Method not allowed."})
    except (ValueError, KeyError) as exc:
        return _json(400, {"error": str(exc)})
    except Exception as exc:  # keep the app honest, not crashy
        return _json(500, {"error": f"Something broke ({type(exc).__name__})."})
