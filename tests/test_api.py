import pytest

from trailmark import create_app

HEADERS = {"X-Trailmark-Request": "1"}


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture()
def client(app):
    return app.test_client()


def create(client, **overrides):
    return client.post("/api/resources", json={"title": "Learn Python", "url": "https://example.com/python", **overrides}, headers=HEADERS)


def test_full_lifecycle_and_persistence(client, app):
    response = create(client, tags=["Python", "python", " backend "], notes="Practice daily")
    assert response.status_code == 201
    item = response.json
    assert item["tags"] == ["backend", "python"]
    assert item["status"] == "queued"
    updated = client.patch(f"/api/resources/{item['id']}", json={"status": "completed", "favorite": True}, headers=HEADERS)
    assert updated.status_code == 200
    assert updated.json["notes"] == "Practice daily"
    # A fresh app reading the same disk file must see the saved changes.
    second = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]}).test_client()
    persisted = second.get("/api/resources").json["resources"]
    assert persisted[0]["favorite"] is True
    assert persisted[0]["status"] == "completed"
    assert second.delete(f"/api/resources/{item['id']}", headers=HEADERS).status_code == 204
    assert client.get("/api/resources").json == {"resources": []}


@pytest.mark.parametrize("overrides", [
    {"title": "  "}, {"title": "x" * 161}, {"title": 123},
    {"url": "javascript:alert(1)"}, {"url": "https://user:pass@example.com"},
    {"url": "https://example.com:abc"}, {"url": "https://bad%host.com"},
    {"url": "https://bad host.com"}, {"url": "https://example.com\\evil"},
    {"url": "https://999.999.999.999"}, {"url": "https://example.123"},
    {"status": "future"}, {"kind": []}, {"favorite": "false"},
    {"tags": "python"}, {"tags": [None]}, {"tags": ["a"] * 13},
    {"tags": ["x" * 31]}, {"notes": "x" * 10001}, {"surprise": True},
])
def test_invalid_records_do_not_write(client, overrides):
    response = create(client, **overrides)
    assert response.status_code == 400
    assert "error" in response.json
    assert client.get("/api/resources").json["resources"] == []


def test_duplicate_creation_and_update_rollback(client):
    first = create(client, url="https://EXAMPLE.com").json
    assert create(client, url="https://example.com/").status_code == 409
    second = create(client, url="https://example.com/other").json
    response = client.patch(f"/api/resources/{second['id']}", json={"url": first["url"], "title": "Changed"}, headers=HEADERS)
    assert response.status_code == 409
    items = client.get("/api/resources").json["resources"]
    assert next(item for item in items if item["id"] == second["id"])["title"] == "Learn Python"


def test_backup_roundtrip_and_duplicate_import(client, tmp_path):
    create(client, favorite=True, tags=["python"], notes="<script>literal text</script>", status="learning")
    backup = client.get("/api/export")
    assert "attachment" in backup.headers["Content-Disposition"]
    destination = create_app({"TESTING": True, "DATABASE": str(tmp_path / "restored.sqlite3")}).test_client()
    result = destination.post("/api/import", json=backup.json, headers=HEADERS)
    assert result.json == {"imported": 1, "skipped": 0}
    restored = destination.get("/api/resources").json["resources"][0]
    for key in ("title", "url", "kind", "status", "tags", "notes", "favorite"):
        assert restored[key] == backup.json["resources"][0][key]
    assert destination.post("/api/import", json=backup.json, headers=HEADERS).json == {"imported": 0, "skipped": 1}


def test_import_is_atomic(client):
    payload = {"schema_version": 1, "resources": [
        {"title": "Good", "url": "https://example.com"},
        {"title": "Bad", "url": "file:///etc/passwd"},
    ]}
    response = client.post("/api/import", json=payload, headers=HEADERS)
    assert response.status_code == 400
    assert "Resource 2" in response.json["error"]
    assert client.get("/api/resources").json["resources"] == []


@pytest.mark.parametrize("payload", [[], {}, {"schema_version": True}, {"schema_version": 2},
    {"schema_version": 1, "resources": [None]}, {"schema_version": 1, "resources": [{}] * 1001}])
def test_invalid_backup(client, payload):
    assert client.post("/api/import", json=payload, headers=HEADERS).status_code == 400


def test_duplicate_rows_within_backup_are_skipped(client):
    row = {"title": "Docs", "url": "https://example.com"}
    assert client.post("/api/import", json={"schema_version": 1, "resources": [row, row]}, headers=HEADERS).json == {"imported": 1, "skipped": 1}


def test_request_boundaries(client):
    assert client.post("/api/resources", json={}).status_code == 403
    assert client.post("/api/resources", json={}, headers={**HEADERS, "Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/resources", headers={"Host": "evil.example"}).status_code == 400
    assert client.post("/api/resources", data="{", content_type="application/json", headers=HEADERS).status_code == 400
    assert client.post("/api/resources", data="text", headers=HEADERS).status_code == 415
    assert client.post("/api/import", data="x" * (1024 * 1024 + 1), content_type="application/json", headers=HEADERS).status_code == 413


def test_missing_resource_and_bad_patch(client):
    assert client.patch("/api/resources/999", json={}, headers=HEADERS).status_code == 404
    assert client.delete("/api/resources/999", headers=HEADERS).status_code == 404
    item = create(client).json
    assert client.patch(f"/api/resources/{item['id']}", json=[], headers=HEADERS).status_code == 400


def test_page_assets_health_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Your next rabbit hole" in response.data
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/api/health").json["status"] == "ok"


def test_optional_demo_is_idempotent(app, client):
    assert client.get("/api/resources").json["resources"] == []
    first = app.test_cli_runner().invoke(args=["seed"])
    assert first.exit_code == 0
    assert "Added 6" in first.output
    second = app.test_cli_runner().invoke(args=["seed"])
    assert "Added 0" in second.output
    assert len(client.get("/api/resources").json["resources"]) == 6
