"""Append-only JSONL transactions are the source of truth, including reservations.

An OS file lock serializes read/validate/append across processes. Each completed
turn is one fsynced event; replay restores both the transcript and domain state.
No generated summary is ever used as authoritative memory.
"""

import copy
import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def initial_state(language="en"):
    return {
        "language": language,
        "active_domains": [],
        "preferences": {},
        "domains": {
            k: {"filters": {}, "results": [], "selected": None}
            for k in ["flights", "shopping", "cinema"]
        },
        "cart": {},
        "reservations": [],
        "pending": None,
    }


class LogCorruptionError(Exception):
    pass


class SessionStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def transaction(self):
        with (self.directory / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def path(self, session_id):
        # Canonical UUIDs only: a user cannot turn an ID into a filesystem path.
        if str(uuid.UUID(session_id)) != session_id:
            raise ValueError("Invalid session ID")
        return self.directory / f"{session_id}.jsonl"

    def append(self, session_id, event):
        path = self.path(session_id)
        payload = (
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode()
        with path.open("ab") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(path, 0o600)

    def events(self, session_id):
        path = self.path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        events = []
        for line in path.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                # Fail closed; silently skipping a damaged reservation can oversell.
                raise LogCorruptionError(
                    "A session log needs repair; no changes were saved."
                ) from exc
        if not events or events[0].get("type") != "created":
            raise LogCorruptionError("Invalid session log")
        return events

    def create(self, language="en", source_id=None):
        session_id = str(uuid.uuid4())
        state = initial_state(language)
        source = None
        if source_id:
            old = self.load(source_id)
            state = copy.deepcopy(old["state"])
            # Preferences and search context are inherited explicitly, not actions.
            state["cart"], state["reservations"], state["pending"] = {}, [], None
            source = {"id": source_id, "title": old["title"]}
        self.append(
            session_id,
            {
                "type": "created",
                "at": now(),
                "id": session_id,
                "title": "New conversation",
                "state": state,
                "source": source,
            },
        )
        return self.load(session_id)

    def load(self, session_id):
        events = self.events(session_id)
        first = events[0]
        state, title, messages = first["state"], first["title"], []
        for event in events[1:]:
            if event["type"] == "turn":
                state = event["state"]
                messages.extend(event["messages"])
                if title == "New conversation":
                    title = event["messages"][0]["text"][:65]
        return {
            "id": session_id,
            "title": title,
            "created_at": first["at"],
            "updated_at": events[-1]["at"],
            "messages": messages,
            "state": state,
            "source": first.get("source"),
        }

    def list(self):
        items = []
        for path in self.directory.glob("*.jsonl"):
            session = self.load(path.stem)
            items.append(
                {
                    k: session[k]
                    for k in ["id", "title", "created_at", "updated_at", "source"]
                }
            )
        return sorted(items, key=lambda s: s["updated_at"], reverse=True)

    def inventory(self):
        used = {}
        for path in self.directory.glob("*.jsonl"):
            session = self.load(path.stem)
            for r in session["state"]["reservations"]:
                used[r["item_id"]] = used.get(r["item_id"], 0) + r["quantity"]
        return used

    def commit(self, session_id, request_id, messages, state, trace):
        self.append(
            session_id,
            {
                "type": "turn",
                "at": now(),
                "request_id": request_id,
                "messages": messages,
                "state": state,
                "trace": trace,
            },
        )

    def previous_request(self, session_id, request_id):
        for event in self.events(session_id):
            if event.get("request_id") == request_id:
                return event
        return None
