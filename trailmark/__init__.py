"""Trailmark: a small, local learning library."""

import json
import ipaddress
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import click
from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

FIELDS = {"title", "url", "kind", "status", "tags", "notes", "favorite"}
STATUSES = ("queued", "learning", "completed")
KINDS = ("article", "video", "course", "tool", "book")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(g.app_database, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def serialize(row):
    result = dict(row)
    result["tags"] = json.loads(result["tags"])
    result["favorite"] = bool(result["favorite"])
    return result


def validate(data):
    """Validate an entire record before any writes (including bulk imports)."""
    if not isinstance(data, dict):
        raise ValueError("Each resource must be a JSON object.")
    unknown = data.keys() - FIELDS
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}.")
    result = {}
    for field, limit, default in (("title", 160, ""), ("url", 2048, ""), ("notes", 10000, "")):
        value = data.get(field, default)
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(f"{field} must be text with at most {limit} characters.")
        result[field] = value.strip()
    if not result["title"]:
        raise ValueError("Give your resource a title.")
    try:
        parsed = urlsplit(result["url"])
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(char.isspace() or ord(char) < 32 for char in result["url"])
                or "\\" in result["url"]):
            raise ValueError()
        _ = parsed.port  # Invalid ports raise ValueError.
        host = parsed.hostname
        try:
            ipaddress.ip_address(host)
        except ValueError:
            ascii_host = host.encode("idna").decode("ascii").rstrip(".")
            # Browsers interpret numeric final labels as IPv4 addresses. Reject
            # invalid numeric hosts instead of storing links the UI cannot parse.
            if ascii_host.split(".")[-1].isdigit() or len(ascii_host) > 253 or any(
                not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in ascii_host.split(".")
            ):
                raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError("Use a valid http:// or https:// URL without credentials.") from None
    result["url"] = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, parsed.fragment))
    for field, choices, default in (("kind", KINDS, "article"), ("status", STATUSES, "queued")):
        value = data.get(field, default)
        if value not in choices:
            raise ValueError(f"{field} must be one of: {', '.join(choices)}.")
        result[field] = value
    favorite = data.get("favorite", False)
    if not isinstance(favorite, bool):
        raise ValueError("favorite must be true or false.")
    result["favorite"] = favorite
    tags = data.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 12:
        raise ValueError("Use a list of at most 12 tags.")
    if any(not isinstance(tag, str) or not tag.strip() or len(tag) > 30 for tag in tags):
        raise ValueError("Each tag must contain 1–30 characters.")
    result["tags"] = sorted(set(tag.strip().lower() for tag in tags))
    return result


def insert(db, data):
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """INSERT INTO resources (title,url,kind,status,tags,notes,favorite,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (data["title"], data["url"], data["kind"], data["status"], json.dumps(data["tags"]),
         data["notes"], int(data["favorite"]), now, now),
    )
    return cursor.lastrowid


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get("TRAILMARK_DATABASE", str(Path(app.instance_path) / "trailmark.sqlite3")),
        MAX_CONTENT_LENGTH=1024 * 1024,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL CHECK(kind IN ('article','video','course','tool','book')),
            status TEXT NOT NULL CHECK(status IN ('queued','learning','completed')),
            tags TEXT NOT NULL DEFAULT '[]', notes TEXT NOT NULL DEFAULT '',
            favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")

    @app.before_request
    def prepare_request():
        g.app_database = app.config["DATABASE"]
        if request.method in ("POST", "PATCH", "DELETE"):
            # Custom headers cannot be sent by cross-origin forms. No CORS is enabled.
            if request.headers.get("X-Trailmark-Request") != "1":
                return jsonify(error="Missing X-Trailmark-Request header."), 403
            origin = request.headers.get("Origin")
            if origin and origin != request.host_url.rstrip("/"):
                return jsonify(error="Cross-origin writes are not allowed."), 403

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(_error):
        return jsonify(error="That URL is already in your library."), 409

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify(status="ok", version="0.1.0")

    @app.get("/api/resources")
    def resources():
        return jsonify(resources=[serialize(row) for row in get_db().execute(
            "SELECT * FROM resources ORDER BY created_at DESC, id DESC"
        )])

    @app.post("/api/resources")
    def create():
        data = validate(request.get_json())
        db = get_db()
        with db:
            resource_id = insert(db, data)
        return jsonify(serialize(db.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone())), 201

    @app.patch("/api/resources/<int:resource_id>")
    def update(resource_id):
        db = get_db()
        existing = db.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
        if existing is None:
            return jsonify(error="Resource not found."), 404
        patch = request.get_json()
        if not isinstance(patch, dict):
            raise ValueError("Send a JSON object.")
        current = serialize(existing)
        data = validate({**{key: current[key] for key in FIELDS}, **patch})
        with db:
            db.execute("""UPDATE resources SET title=?,url=?,kind=?,status=?,tags=?,notes=?,favorite=?,updated_at=?
                          WHERE id=?""", (data["title"], data["url"], data["kind"], data["status"],
                          json.dumps(data["tags"]), data["notes"], int(data["favorite"]),
                          datetime.now(timezone.utc).isoformat(), resource_id))
        return jsonify(serialize(db.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()))

    @app.delete("/api/resources/<int:resource_id>")
    def delete(resource_id):
        db = get_db()
        with db:
            deleted = db.execute("DELETE FROM resources WHERE id=?", (resource_id,)).rowcount
        if not deleted:
            return jsonify(error="Resource not found."), 404
        return "", 204

    @app.get("/api/export")
    def export():
        response = jsonify(schema_version=1, resources=[serialize(row) for row in get_db().execute("SELECT * FROM resources ORDER BY id")])
        response.headers["Content-Disposition"] = 'attachment; filename="trailmark-backup.json"'
        return response

    @app.post("/api/import")
    def import_resources():
        payload = request.get_json()
        if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
            raise ValueError("Import a Trailmark backup with schema_version 1.")
        rows = payload.get("resources")
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError("A backup must contain a resources list with at most 1,000 entries.")
        validated = []
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                raise ValueError(f"Resource {index} must be an object. Nothing was imported.")
            try:
                validated.append(validate({k: v for k, v in row.items() if k not in {"id", "created_at", "updated_at"}}))
            except ValueError as error:
                raise ValueError(f"Resource {index}: {error} Nothing was imported.") from None
        db = get_db()
        added = 0
        with db:
            for data in validated:
                if db.execute("SELECT 1 FROM resources WHERE url=?", (data["url"],)).fetchone():
                    continue
                insert(db, data)
                added += 1
        return jsonify(imported=added, skipped=len(validated) - added)

    @app.cli.command("seed")
    def seed():
        """Add sample learning resources without replacing existing entries."""
        from .sample_data import SAMPLES
        g.app_database = app.config["DATABASE"]
        db = get_db()
        added = 0
        with db:
            for sample in SAMPLES:
                data = validate(sample)
                if not db.execute("SELECT 1 FROM resources WHERE url=?", (data["url"],)).fetchone():
                    insert(db, data)
                    added += 1
        click.echo(f"Added {added} sample resources.")

    return app
