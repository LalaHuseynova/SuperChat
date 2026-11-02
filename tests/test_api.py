import copy
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from superchat.app import create_app
from superchat.config import DATA_DIR
from superchat.store import SessionStore


def create(client, **kwargs):
    r = client.post("/api/sessions", json=kwargs)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def send(client, sid, text, rid=None):
    r = client.post(
        f"/api/sessions/{sid}/messages",
        json={"text": text, "request_id": rid or str(uuid.uuid4())},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_restart_replays_memory_and_transcript(client, offline):
    sid = create(client)
    send(client, sid, "Show me laptops")
    directory = client.app.state.store.directory
    resumed = TestClient(create_app(directory, DATA_DIR, offline))
    result = send(resumed, sid, "The second one, is it in stock?")
    assert result["reply"]["sections"][0]["cards"][0]["id"] == "P004"
    assert len(result["session"]["messages"]) == 4
    records = [
        json.loads(line)
        for line in (directory / f"{sid}.jsonl").read_text().splitlines()
    ]
    assert len(records) == 3 and records[-1]["trace"]["route"]["domains"] == [
        "shopping"
    ]


def test_isolation_and_explicit_continuation(client):
    sid = create(client)
    send(client, sid, "Show me headphones under 100 AZN")
    send(client, sid, "Add P001 to cart")
    fresh = create(client)
    assert (
        send(client, fresh, "the second one")["reply"]["route"]["category"]
        == "ambiguous"
    )
    fork = create(client, source_id=sid)
    data = client.get(f"/api/sessions/{fork}").json()
    assert data["state"]["domains"]["shopping"]["filters"]["max_price"] == 100
    assert not data["state"]["cart"] and not data["messages"]
    assert data["source"]["id"] == sid


def test_duplicate_requests_do_not_double_book(client):
    sid = create(client)
    rid = str(uuid.uuid4())
    one = send(client, sid, "Reserve two seats for F002", rid)
    two = send(client, sid, "Reserve two seats for F002", rid)
    assert two["replayed"] and two["reply"] == one["reply"]
    assert len(two["session"]["state"]["reservations"]) == 1
    assert (
        client.post(
            f"/api/sessions/{sid}/messages",
            json={"text": "Reserve F001", "request_id": rid},
        ).status_code
        == 409
    )


def test_concurrent_sessions_cannot_oversell(client):
    a = create(client)
    b = create(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda sid: send(client, sid, "Reserve two seats for F002"), [a, b]
            )
        )
    reservations = [
        r for result in results for r in result["session"]["state"]["reservations"]
    ]
    assert sum(r["quantity"] for r in reservations) == 2
    assert client.app.state.store.inventory()["F002"] == 2


def test_changed_data_revalidated(client, tmp_path, offline):
    import shutil

    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data)
    app = create_app(tmp_path / "logs2", data, offline)
    c = TestClient(app)
    sid = create(c)
    send(c, sid, "Show me headphones")
    products = json.loads((data / "products.json").read_text())
    products[0]["stock"] = 0
    (data / "products.json").write_text(json.dumps(products))
    result = send(c, sid, "Add the first one to cart")
    assert not result["session"]["state"]["cart"]
    assert result["reply"]["sections"][0]["cards"][0]["available"] == 0


def test_source_failure_rolls_back_mixed_turn(client, tmp_path, offline):
    import shutil

    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data)
    c = TestClient(create_app(tmp_path / "logs3", data, offline))
    sid = create(c)
    (data / "products.json").write_text("broken")
    result = send(c, sid, "Reserve F001 and add P001 to cart")
    assert result["reply"]["route"]["category"] == "error"
    assert not result["session"]["state"]["reservations"]
    assert not result["session"]["state"]["cart"]


def test_malformed_log_fails_closed(client):
    sid = create(client)
    with client.app.state.store.path(sid).open("a") as f:
        f.write("{broken")
    r = client.get(f"/api/sessions/{sid}")
    assert r.status_code == 503 and "traceback" not in r.text.lower()


def test_export_and_validation(client):
    sid = create(client)
    send(client, sid, "Hello")
    export = client.get(f"/api/sessions/{sid}/export")
    assert (
        export.status_code == 200
        and "application/x-ndjson" in export.headers["content-type"]
    )
    assert "trace" in export.text
    assert client.get("/api/sessions/not-a-uuid").status_code == 400
    assert (
        client.post(f"/api/sessions/{sid}/messages", json={"text": "   "}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/sessions", json={}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_images_only_search_and_ask_when_uncertain(client, monkeypatch):
    sid = create(client)
    monkeypatch.setattr(
        client.app.state.vision,
        "classify",
        lambda data: {
            "label": "headphones",
            "confidence": 0.94,
            "engine": "test",
            "accepted": True,
        },
    )
    rid = str(uuid.uuid4())
    r = client.post(
        f"/api/sessions/{sid}/images",
        files={"file": ("test.png", b"image", "image/png")},
        data={"request_id": rid},
    )
    assert r.status_code == 200
    value = r.json()
    assert value["reply"]["sections"][0]["cards"][0]["id"] == "P001"
    assert (
        not value["session"]["state"]["cart"]
        and not value["session"]["state"]["reservations"]
    )
    assert "94%" in value["reply"]["text"]
    monkeypatch.setattr(
        client.app.state.vision,
        "classify",
        lambda data: {
            "label": "other",
            "confidence": 0.2,
            "engine": "test",
            "accepted": False,
        },
    )
    r = client.post(
        f"/api/sessions/{sid}/images",
        files={"file": ("test.png", b"image", "image/png")},
        data={"request_id": str(uuid.uuid4())},
    )
    assert not r.json()["reply"]["sections"] and "?" in r.json()["reply"]["text"]


def test_bad_image_rejected(client):
    sid = create(client)
    r = client.post(
        f"/api/sessions/{sid}/images",
        files={"file": ("bad.png", b"not an image", "image/png")},
        data={"request_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400
