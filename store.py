"""Manzuri data layer — SQLite, stdlib only.

The one rule the product exists for lives here:
    Editing a post VOIDS its approval.
An approval is a decision about a specific version. edit_post bumps
the version, returns the post to 'pending', and writes a 'voided'
row into the decision history — nothing is silently overwritten.
"""
import secrets
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    day_label TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    image_name TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | changes
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id),
    action TEXT NOT NULL,  -- approved | changes | voided
    note_kind TEXT,        -- image | caption | both (for changes)
    note_text TEXT,
    version_seen INTEGER NOT NULL,
    at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _locked(fn):
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)
    return wrapper


class Store:
    def __init__(self, db_path: str | Path):
        # One connection shared by the HTTP server's threads: sqlite
        # connections are thread-bound by default, so allow sharing
        # and serialise every operation through one lock. (Found by
        # the live smoke: single-threaded unit tests passed while the
        # threaded server raised ProgrammingError on request one.)
        self._lock = threading.RLock()  # re-entrant: decide() calls get_post(), both locked
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    # ---------- clients ----------
    @_locked
    def create_client(self, name: str) -> dict:
        token = secrets.token_urlsafe(24)
        cur = self.db.execute("INSERT INTO clients (name, token) VALUES (?, ?)", (name, token))
        self.db.commit()
        return {"id": cur.lastrowid, "name": name, "token": token}

    @_locked
    def list_clients(self) -> list[dict]:
        rows = self.db.execute(
            """SELECT c.id, c.name, c.token,
                      COUNT(p.id) AS posts,
                      SUM(CASE WHEN p.status='approved' THEN 1 ELSE 0 END) AS approved,
                      SUM(CASE WHEN p.status='changes' THEN 1 ELSE 0 END) AS changes,
                      SUM(CASE WHEN p.status='pending' THEN 1 ELSE 0 END) AS pending
               FROM clients c LEFT JOIN posts p ON p.client_id = c.id
               GROUP BY c.id ORDER BY c.id""").fetchall()
        return [dict(r) for r in rows]

    @_locked
    def client_by_token(self, token: str) -> dict | None:
        row = self.db.execute("SELECT * FROM clients WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else None

    # ---------- posts ----------
    @_locked
    def add_post(self, client_id: int, day_label: str, caption: str,
                 image_name: str | None) -> dict:
        cur = self.db.execute(
            "INSERT INTO posts (client_id, day_label, caption, image_name) VALUES (?, ?, ?, ?)",
            (client_id, day_label, caption, image_name))
        self.db.commit()
        return self.get_post(cur.lastrowid)

    @_locked
    def get_post(self, post_id: int) -> dict | None:
        row = self.db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return dict(row) if row else None

    @_locked
    def posts_for_client(self, client_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM posts WHERE client_id = ? ORDER BY day_label, id",
            (client_id,)).fetchall()
        return [dict(r) for r in rows]

    @_locked
    def edit_post(self, post_id: int, caption: str | None = None,
                  image_name: str | None = None) -> dict:
        """Bump the version; a decided post returns to pending and the
        voiding is written into its history. Returns the post plus
        'voided': True/False."""
        post = self.get_post(post_id)
        if post is None:
            raise KeyError(f"no post {post_id}")
        new_caption = post["caption"] if caption is None else caption
        new_image = post["image_name"] if image_name is None else image_name
        if new_caption == post["caption"] and new_image == post["image_name"]:
            return {**post, "voided": False}
        voided = post["status"] != "pending"
        self.db.execute(
            """UPDATE posts SET caption = ?, image_name = ?, version = version + 1,
                      status = 'pending', updated_at = datetime('now') WHERE id = ?""",
            (new_caption, new_image, post_id))
        if voided:
            self.db.execute(
                "INSERT INTO decisions (post_id, action, version_seen) VALUES (?, 'voided', ?)",
                (post_id, post["version"]))
        self.db.commit()
        return {**self.get_post(post_id), "voided": voided}

    # ---------- decisions ----------
    @_locked
    def decide(self, post_id: int, action: str, note_kind: str | None = None,
               note_text: str | None = None) -> dict:
        if action not in ("approved", "changes"):
            raise ValueError("action must be 'approved' or 'changes'")
        if action == "changes" and note_kind not in ("image", "caption", "both"):
            raise ValueError("a change request must say: image, caption, or both")
        post = self.get_post(post_id)
        if post is None:
            raise KeyError(f"no post {post_id}")
        self.db.execute(
            "INSERT INTO decisions (post_id, action, note_kind, note_text, version_seen) "
            "VALUES (?, ?, ?, ?, ?)",
            (post_id, action, note_kind, note_text, post["version"]))
        self.db.execute(
            "UPDATE posts SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (action, post_id))
        self.db.commit()
        return self.get_post(post_id)

    @_locked
    def history(self, post_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM decisions WHERE post_id = ? ORDER BY id", (post_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---------- export ----------
    @_locked
    def export_checklist(self, client_id: int) -> list[dict]:
        """Only posts approved at their CURRENT version — guaranteed
        by the void rule, so this is a plain status read."""
        rows = self.db.execute(
            "SELECT * FROM posts WHERE client_id = ? AND status = 'approved' "
            "ORDER BY day_label, id", (client_id,)).fetchall()
        return [dict(r) for r in rows]
