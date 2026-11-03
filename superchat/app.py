import copy
import json
import logging
import uuid
import os
from contextlib import nullcontext, asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import DATA_DIR, LOG_DIR, DATA_MODE, REAL_DATA_DIR, SNAPSHOT_PUBLICATION, CATALOGUE_DB
from .database import CatalogueDatabase
from .snapshots import SnapshotDataset, repositories as snapshot_repositories
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
    language: Literal["en", "az", "ru"] | None = None


def create_app(log_dir=LOG_DIR, data_dir=DATA_DIR, provider=None, *, data_mode=None, real_data_dir=None, clock=None, database_path=None, refresh=None, flight_repository=None):
    mode = data_mode or DATA_MODE
    if mode not in ("mock", "snapshot", "database"):
        raise ValueError("Choose mock, snapshot or database mode.")
    dataset = SnapshotDataset(real_data_dir or REAL_DATA_DIR, None if real_data_dir else SNAPSHOT_PUBLICATION) if mode == "snapshot" else None
    if mode == 'database':
        dataset = CatalogueDatabase(database_path or CATALOGUE_DB, real_data_dir or REAL_DATA_DIR)
        dataset.seed()
    @asynccontextmanager
    async def lifespan(app):
        worker = None
        if mode == 'database' and (refresh if refresh is not None else os.getenv('SUPERCHAT_AUTO_REFRESH', 'true').lower() == 'true'):
            from .refresh import RefreshWorker
            worker = RefreshWorker(dataset, float(os.getenv('SUPERCHAT_REFRESH_HOURS', '24')))
            worker.thread.start()
        yield
        if worker:
            worker.stop.set()

    app = FastAPI(title="Bir SuperChat", version="2.0.0", lifespan=lifespan)
    def catalogue_read():
        return dataset.read() if mode == 'database' else nullcontext()
    # Existing mock logs stay untouched. Real IDs and mock reservations cannot mix.
    store = SessionStore(Path(log_dir) / "snapshot" if dataset else log_dir)
    repos = snapshot_repositories(dataset) if dataset else None
    if mode == 'database' and flight_repository is None and os.getenv('TRAVELPAYOUTS_API_TOKEN'):
        from .travelpayouts import TravelpayoutsRepository
        flight_repository = TravelpayoutsRepository(dataset, os.environ['TRAVELPAYOUTS_API_TOKEN'])
    if flight_repository and repos:
        repos['flights'] = flight_repository
    engine = Engine(data_dir, repos, clock=clock)
    ai = provider or AIProvider()
    vision = VisualSearch(ai)
    app.state.store = store
    app.state.engine = engine
    app.state.ai = ai
    app.state.vision = vision
    app.state.dataset = dataset
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
            "reference_date": engine.today().isoformat(),
            "timezone": "Asia/Baku",
            "ai_enabled": ai.enabled,
            "ai_model": ai.model if ai.enabled else None,
            "local_vision_installed": bool(importlib.util.find_spec("transformers")),
            "mock_data": mode == "mock",
            "data_mode": mode,
            "snapshot_version": dataset.version if dataset else None,
            "supplier_bookings": False,
            "flight_source": 'aviasales_data_api' if flight_repository else mode,
            "catalogue": dataset.status() if mode == 'database' else None,
        }

    @app.get('/api/catalogue/status')
    def catalogue_status():
        return dataset.status() if mode == 'database' else {'mode': mode}

    @app.get('/api/catalogue/products')
    def products(q: str = '', category: str | None = None, brand: str | None = None,
                 language: Literal['en', 'az', 'ru'] = 'en', page: int = 1, limit: int = 20):
        if page < 1 or not 1 <= limit <= 50 or len(q) > 200:
            raise HTTPException(400, 'Invalid search or pagination')
        with catalogue_read():
            rows = engine.repos['shopping'].search({k: v for k, v in {'query': q, 'category': category, 'brand': brand}.items() if v})
            return {'total': len(rows), 'page': page, 'version': dataset.version if dataset else None,
                    'items': [engine.card('shopping', r, {}, language) for r in rows[(page - 1)*limit:page*limit]]}

    @app.get('/api/catalogue/showtimes')
    def showtimes(date: str | None = None, cinema_id: str | None = None,
                  language: Literal['en', 'az', 'ru'] = 'en', page: int = 1, limit: int = 20):
        if page < 1 or not 1 <= limit <= 50:
            raise HTTPException(400, 'Invalid pagination')
        with catalogue_read():
            rows = engine.repos['cinema'].search({k: v for k, v in {'date': date, 'cinema_id': cinema_id}.items() if v})
            return {'total': len(rows), 'page': page, 'version': dataset.version if dataset else None,
                    'items': [engine.card('cinema', r, {}, language) for r in rows[(page - 1)*limit:page*limit]]}

    @app.get("/api/sessions")
    def list_sessions():
        with store.transaction():
            return store.list()

    @app.get("/api/catalogue/images/{item_id}")
    def catalogue_image(item_id: str):
        from .snapshots import inside
        if dataset is None:
            raise HTTPException(404, "Image not available")
        product = engine.repos["shopping"].get(item_id)
        showtime = None if product else engine.repos["cinema"].get(item_id)
        movie = showtime["movie"] if showtime else next((m for m in dataset.tables["movies"] if m["id"] == item_id), None)
        files = product.get("image_files", []) if product else ([movie.get("poster_file")] if movie else [])
        if not files or not files[0]:
            raise HTTPException(404, "Image not available")
        path = inside(dataset.root, files[0])
        if not path.is_file() or path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp", ".avif"]:
            raise HTTPException(404, "Image not available")
        return FileResponse(path)

    @app.post("/api/sessions")
    def new_session(body: SessionInput):
        with store.transaction():
            return store.create(body.language, body.source_id)

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str):
        with store.transaction():
            return store.load(session_id)

    @app.delete('/api/sessions/{session_id}')
    def delete_session(session_id: str):
        with store.transaction():
            store.delete(session_id)
        return {'deleted': session_id}

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
        with store.transaction(), catalogue_read():
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
            plan, fallback = ai.plan(text, session, language=body.language, reference_date=engine.today())
            try:
                reply, state, actions = engine.respond(
                    text, session["state"], store.inventory(), plan,
                    language=body.language,
                )
            except (OSError, KeyError, ValueError, TypeError):
                # No partial domain changes, including mixed-intent turns, are committed.
                state = copy.deepcopy(session["state"])
                if body.language:
                    state["language"] = body.language
                actions = []
                reply = {
                    "text": tr("error", state["language"]),
                    "sections": [],
                    "language": state["language"],
                    "route": {"category": "error", "domains": [], "engine": "rules"},
                }
            reply.update(id=str(uuid.uuid4()), role="assistant", at=now())
            if fallback:
                reply["notice"] = 'ai_auth_failed' if fallback == 'provider_auth_failed' else 'ai_fallback'
            messages = [
                {"id": str(uuid.uuid4()), "role": "user", "text": text, "at": now()},
                reply,
            ]
            trace = {
                "data_mode": mode,
                "snapshot_version": dataset.version if dataset else None,
                "route": reply["route"],
                "actions": actions,
                "provider_fallback": fallback,
                "source_files": [r["file"] for r in dataset.descriptor["tables"].values()] if dataset else [
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
        session_id: str,
        file: UploadFile = File(...),
        request_id: str = Form(...),
        language: Literal["en", "az", "ru"] | None = Form(None),
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
            with catalogue_read():
                prediction = vision.search(data, engine.repos['shopping'], dataset) if dataset else vision.classify(data)
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
        with store.transaction(), catalogue_read():
            previous = store.previous_request(session_id, request_id)
            if previous:
                return {
                    "session": store.load(session_id),
                    "reply": previous["messages"][-1],
                    "replayed": True,
                }
            session = store.load(session_id)
            state = copy.deepcopy(session["state"])
            lang = language or state["language"]
            state["language"] = lang
            sections = []
            if prediction["accepted"]:
                label = prediction["label"]
                localized = (
                    label
                    if lang == "en"
                    else LABEL_TRANSLATIONS[label][0 if lang == "az" else 1]
                )
                if dataset:
                    # Re-resolve IDs after inference; a concurrent refresh may remove an item.
                    cards = []
                    for match in prediction.get('matches', []):
                        row = engine.repos['shopping'].get(match['id'])
                        if row:
                            card = engine.card('shopping', row, {}, lang)
                            card['similarity'] = match['score']
                            cards.append(card)
                    section = {'domain': 'shopping', 'text': tr('visual_matches' if cards else 'vision_no_match', lang),
                               'cards': cards, 'action': 'search', 'filters': {'query': label}}
                    state['domains']['shopping'].update(filters={'query': label}, results=[c['id'] for c in cards], selected=None, offset=0)
                else:
                    section, events = engine.handle('shopping', 'Show me ' + label, state, store.inventory())
                sections = [section]
                state["active_domains"] = ["shopping"]
                state["pending"] = None
                text = tr(
                    "vision_ready",
                    lang,
                    label=localized,
                    score=round(prediction["confidence"] * 100),
                )
                if dataset and not section['cards']:
                    text = tr('vision_no_match', lang)
                    sections = []
                elif dataset and prediction.get('method') == 'image_similarity':
                    text += ' ' + tr('similarity_note', lang)
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
                {"vision": prediction, "actions": [], "data_mode": mode, "snapshot_version": dataset.version if dataset else None},
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
