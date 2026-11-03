import uuid

import pytest

from superchat.i18n import tr


@pytest.mark.parametrize("language", ["en", "az", "ru"])
def test_selected_reply_language_wins_over_input_and_saved_session(client, language):
    sid = client.post("/api/sessions", json={"language": "az"}).json()["id"]
    # Both a recognizably Azerbaijani message and an unrecognized English fragment
    # must honor the selector instead of detecting/inheriting Azerbaijani.
    for text in ["Salam", "something"]:
        response = client.post(
            f"/api/sessions/{sid}/messages",
            json={"text": text, "language": language},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["reply"]["language"] == language
        assert result["reply"]["text"] == tr(
            "welcome" if text == "Salam" else "clarify", language
        )
    reloaded = client.get(f"/api/sessions/{sid}").json()
    assert reloaded["state"]["language"] == language
    assert reloaded["messages"][-1]["language"] == language


def test_model_language_cannot_override_selection(client, monkeypatch):
    provider = client.app.state.ai
    provider.key = "test-placeholder"
    monkeypatch.setattr(provider, "completion", lambda *args: {
        "category": "shopping", "language": "az",
        "intents": [{"domain": "shopping", "action": "search",
                     "filters": {"query": "laptop"}}],
    })
    sid = client.post("/api/sessions", json={"language": "az"}).json()["id"]
    result = client.post(
        f"/api/sessions/{sid}/messages",
        json={"text": "Noutbukları göstər", "language": "en"},
    ).json()
    assert result["reply"]["language"] == "en"
    section = result["reply"]["sections"][0]
    assert section["text"] == tr("found", "en", count=len(section["cards"]))
    assert section["cards"][0]["title"] == 'Laptop 15" Pro'


@pytest.mark.parametrize("accepted", [True, False])
def test_images_use_current_selection(client, monkeypatch, accepted):
    sid = client.post("/api/sessions", json={"language": "az"}).json()["id"]
    monkeypatch.setattr(client.app.state.vision, "classify", lambda data: {
        "label": "headphones", "confidence": 0.94,
        "engine": "test", "accepted": accepted,
    })
    response = client.post(
        f"/api/sessions/{sid}/images",
        files={"file": ("test.png", b"image", "image/png")},
        data={"request_id": str(uuid.uuid4()), "language": "en"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["reply"]["language"] == "en"
    assert result["session"]["state"]["language"] == "en"
    assert result["reply"]["text"] == (
        tr("vision_ready", "en", label="headphones", score=94)
        if accepted else tr("vision_unsure", "en")
    )


def test_continuation_uses_selected_language(client):
    original = client.post("/api/sessions", json={"language": "az"}).json()
    continued = client.post(
        "/api/sessions", json={"source_id": original["id"], "language": "en"}
    ).json()
    assert continued["state"]["language"] == "en"
    assert client.get(f"/api/sessions/{original['id']}").json()["state"]["language"] == "az"


def test_error_reply_uses_selected_language(client, monkeypatch):
    sid = client.post("/api/sessions", json={"language": "az"}).json()["id"]

    def fail(*args, **kwargs):
        raise OSError("Catalogue unavailable")

    monkeypatch.setattr(client.app.state.engine, "respond", fail)
    result = client.post(
        f"/api/sessions/{sid}/messages", json={"text": "laptops", "language": "en"}
    ).json()
    assert result["reply"]["language"] == "en"
    assert result["reply"]["text"] == tr("error", "en")


def test_unsupported_language_rejected(client):
    sid = client.post("/api/sessions", json={}).json()["id"]
    assert client.post(
        f"/api/sessions/{sid}/messages", json={"text": "Hello", "language": "xx"}
    ).status_code == 422
    assert client.post(
        f"/api/sessions/{sid}/images",
        files={"file": ("test.png", b"image", "image/png")},
        data={"request_id": str(uuid.uuid4()), "language": "xx"},
    ).status_code == 422
