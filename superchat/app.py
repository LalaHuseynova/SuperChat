import copy
import json
import logging
import uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import DATA_DIR, LOG_DIR, REFERENCE_DATE
from .store import SessionStore, LogCorruptionError, now
from .engine import Engine
from .ai import AIProvider
from .vision import VisualSearch, LABEL_TRANSLATIONS
from .i18n import tr


class SessionInput(BaseModel):
    language: Literal["en", "az", "ru"] = "en"
    source_id: str | None = None


class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)


def create_app(log_dir=LOG_DIR, data_dir=DATA_DIR, provider=None):
    app = FastAPI(title="SuperChat", version="1.0.0")
    store = SessionStore(log_dir)
    engine = Engine(data_dir)
    ai = provider or AIProvider()
    vision = VisualSearch(ai)
    app.state.store = store
    app.state.engine = engine
    app.state.ai = ai
    app.state.vision = vision
    static = Path(__file__).parent / "static"

    @app.exception_handler(LogCorruptionError)
    async def corrupt(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "A saved log needs repair. No changes were made. Restore the affected log from backup before continuing."
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "This conversation or data file could not be found."},
        )

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid request. Check the conversation ID and input."},
        )

    @app.middleware("http")
    async def headers(request, call_next):
        # Local app: reject cross-origin writes while allowing same-origin browser traffic.
        origin = request.headers.get("origin")
        if (
            request.method in ["POST", "PUT", "DELETE", "PATCH"]
            and origin
            and origin.rstrip("/") != str(request.base_url).rstrip("/")
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin requests are not allowed."},
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "no-cache"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'"
        )
        return response

    @app.get("/api/config")
    def config():
        import importlib.util

        return {
            "reference_date": REFERENCE_DATE.isoformat(),
            "timezone": "Asia/Baku",
            "ai_enabled": ai.enabled,
            "ai_model": ai.model if ai.enabled else None,
            "local_vision_installed": bool(importlib.util.find_spec("transformers")),
            "mock_data": True,
        }

    @app.get("/api/sessions")
    def list_sessions():
        with store.transaction():
            return store.list()

    @app.post("/api/sessions")
    def new_session(body: SessionInput):
        with store.transaction():
            return store.create(body.language, body.source_id)

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str):
        with store.transaction():
            return store.load(session_id)

    @app.get("/api/sessions/{session_id}/export")
    def export_session(session_id: str):
        with store.transaction():
            store.load(session_id)
            return Response(
                store.path(session_id).read_bytes(),
                media_type="application/x-ndjson",
                headers={
                    "Content-Disposition": f'attachment; filename="superchat-{session_id}.jsonl"'
                },
            )

    @app.post("/api/sessions/{session_id}/messages")
    def message(session_id: str, body: MessageInput):
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "Write a message first.")
        request_id = str(body.request_id)
        with store.transaction():
            previous = store.previous_request(session_id, request_id)
            if previous:
                if previous["messages"][0]["text"] != text:
                    raise HTTPException(
                        409, "This request ID was already used for a different message."
                    )
                return {
                    "session": store.load(session_id),
                    "reply": previous["messages"][-1],
                    "replayed": True,
                }
            session = store.load(session_id)
            plan, fallback = ai.plan(text, session)
            try:
                reply, state, actions = engine.respond(
                    text, session["state"], store.inventory(), plan
                )
            except (OSError, KeyError, ValueError, TypeError):
                # No partial domain changes, including mixed-intent turns, are committed.
                state = session["state"]
                actions = []
                reply = {
                    "text": tr("error", state["language"]),
                    "sections": [],
                    "language": state["language"],
                    "route": {"category": "error", "domains": [], "engine": "rules"},
                }
            reply.update(id=str(uuid.uuid4()), role="assistant", at=now())
            if fallback:
                reply["notice"] = "ai_fallback"
            messages = [
                {"id": str(uuid.uuid4()), "role": "user", "text": text, "at": now()},
                reply,
            ]
            trace = {
                "route": reply["route"],
                "actions": actions,
                "provider_fallback": fallback,
                "source_files": [
                    "flights.json",
                    "products.json",
                    "movies.json",
                    "cinemas.json",
                    "showtimes.json",
                ],
            }
            store.commit(session_id, request_id, messages, state, trace)
            return {
                "session": store.load(session_id),
                "reply": reply,
                "replayed": False,
            }

    @app.post("/api/sessions/{session_id}/images")
    def image_search(
        session_id: str, file: UploadFile = File(...), request_id: str = Form(...)
    ):
        uuid.UUID(request_id)
        with store.transaction():
            previous = store.previous_request(session_id, request_id)
            if previous:
                return {
                    "session": store.load(session_id),
                    "reply": previous["messages"][-1],
                    "replayed": True,
                }
            store.load(session_id)
        data = file.file.read(8 * 1024 * 1024 + 1)
        try:
            prediction = vision.classify(data)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        except Exception:
            prediction = {
                "engine": "unavailable",
                "label": "other",
                "confidence": 0,
                "accepted": False,
            }
        # Inference happens outside the lock; state is reloaded before committing.
        with store.transaction():
            previous = store.previous_request(session_id, request_id)
            if previous:
                return {
                    "session": store.load(session_id),
                    "reply": previous["messages"][-1],
                    "replayed": True,
                }
            session = store.load(session_id)
            state = copy.deepcopy(session["state"])
            lang = state["language"]
            sections = []
            if prediction["accepted"]:
                label = prediction["label"]
                localized = (
                    label
                    if lang == "en"
                    else LABEL_TRANSLATIONS[label][0 if lang == "az" else 1]
                )
                section, events = engine.handle(
                    "shopping", "Show me " + label, state, store.inventory()
                )
                sections = [section]
                state["active_domains"] = ["shopping"]
                state["pending"] = None
                text = tr(
                    "vision_ready",
                    lang,
                    label=localized,
                    score=round(prediction["confidence"] * 100),
                )
            else:
                text = tr(
                    "vision_unavailable"
                    if prediction["engine"] == "unavailable"
                    else "vision_unsure",
                    lang,
                )
            reply = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "at": now(),
                "text": text,
                "sections": sections,
                "language": lang,
                "vision": prediction,
                "route": {
                    "category": "shopping" if prediction["accepted"] else "ambiguous",
                    "domains": ["shopping"],
                    "engine": prediction["engine"],
                },
            }
            user = {
                "id": str(uuid.uuid4()),
                "role": "user",
                "at": now(),
                "text": {
                    "en": "Find products from this photo",
                    "az": "Bu şəkilə uyğun məhsul tap",
                    "ru": "Найди товары по этому фото",
                }[lang],
                "attachment": {"type": "image", "stored": False},
            }
            # Images/EXIF are not retained. Only classification and grounded results are logged.
            store.commit(
                session_id,
                request_id,
                [user, reply],
                state,
                {"vision": prediction, "actions": []},
            )
            return {
                "session": store.load(session_id),
                "reply": reply,
                "replayed": False,
            }

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    app.mount("/static", StaticFiles(directory=static), name="static")
    return app


app = create_app()
