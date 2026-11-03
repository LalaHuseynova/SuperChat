"""SQLite catalogue with atomic source publication and consistent turn snapshots."""
import copy
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from .snapshots import TABLES, SnapshotDataset, SnapshotError


def stamp():
    return datetime.now(timezone.utc).isoformat()


def validate_tables(tables):
    validated = {}
    for name, rows in tables.items():
        model = TABLES[name][2]
        validated[name] = [model.model_validate(row).model_dump(mode="json") for row in rows]
        if len({r['id'] for r in validated[name]}) != len(rows):
            raise SnapshotError("Duplicate catalogue IDs")
    if 'showtimes' in validated:
        movies = {r['id'] for r in validated['movies']}
        cinemas = {r['id'] for r in validated['cinemas']}
        for row in validated['showtimes']:
            row['time'] = row['time'][:5]
            if row['movie_id'] not in movies or row['cinema_id'] not in cinemas:
                raise SnapshotError("Unresolved cinema relationship")
    return validated


class CatalogueDatabase:
    def __init__(self, path, root):
        self.path, self.root = Path(path), Path(root).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._view = ContextVar('catalogue_view', default=None)
        self._cache = None
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS refresh_runs (
                    id INTEGER PRIMARY KEY, source TEXT, started_at TEXT, finished_at TEXT,
                    status TEXT, detail TEXT);
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY, expires REAL NOT NULL, payload TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def seed(self):
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM metadata WHERE key='version'").fetchone()
        if not exists:
            source = SnapshotDataset(self.root)
            self.publish(source.tables, source.descriptor['manifests'])

    def publish(self, tables, manifests):
        """Replace complete source bundles in one transaction. Never patch partial runs."""
        for source in manifests:
            expected = {n for n, (s, _, _) in TABLES.items() if s == source}
            if not expected.issubset(tables):
                raise SnapshotError('Incomplete source publication')
        tables = validate_tables(tables)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for name, rows in tables.items():
                db.execute('DELETE FROM records WHERE kind=?', (name,))
                db.executemany('INSERT INTO records VALUES (?,?,?)',
                               [(name, r['id'], json.dumps(r, ensure_ascii=False)) for r in rows])
            for source, manifest in manifests.items():
                db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',
                           ('source:' + source, json.dumps(manifest, ensure_ascii=False)))
            content = db.execute('SELECT kind,id,payload FROM records ORDER BY kind,id').fetchall()
            version = hashlib.sha256(json.dumps(content).encode()).hexdigest()[:16]
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('version', version))
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('published_at', stamp()))
        return version

    def current(self):
        pinned = self._view.get()
        if pinned is not None:
            return pinned
        with self.lock, self.connect() as db:
            db.execute('BEGIN')
            meta = dict(db.execute('SELECT key,value FROM metadata'))
            if self._cache is None or self._cache['version'] != meta.get('version'):
                tables = {name: [] for name in TABLES}
                for kind, payload in db.execute('SELECT kind,payload FROM records ORDER BY rowid'):
                    tables[kind].append(json.loads(payload))
                manifests = {k[7:]: json.loads(v) for k, v in meta.items() if k.startswith('source:')}
                self._cache = {'version': meta.get('version'), 'tables': tables,
                               'manifests': manifests, 'published_at': meta.get('published_at')}
            return self._cache

    @contextmanager
    def read(self):
        token = self._view.set(self.current())
        try:
            yield self
        finally:
            self._view.reset(token)

    @property
    def tables(self):
        return self.current()['tables']

    @property
    def version(self):
        return self.current()['version']

    @property
    def descriptor(self):
        return {'tables': {n: {'file': f'sqlite:{n}'} for n in TABLES},
                'manifests': self.current()['manifests']}

    def records(self, name):
        return copy.deepcopy(self.tables[name])

    def begin_refresh(self, source):
        with self.connect() as db:
            return db.execute('INSERT INTO refresh_runs(source,started_at,status) VALUES (?,?,?)',
                              (source, stamp(), 'running')).lastrowid

    def end_refresh(self, run_id, status, detail):
        with self.connect() as db:
            db.execute('UPDATE refresh_runs SET finished_at=?,status=?,detail=? WHERE id=?',
                       (stamp(), status, detail, run_id))

    def status(self):
        view = self.current()
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            runs = [dict(r) for r in db.execute('SELECT * FROM refresh_runs ORDER BY id DESC LIMIT 6')]
        return {'version': view['version'], 'published_at': view['published_at'],
                'counts': {k: len(v) for k, v in view['tables'].items()},
                'sources': {k: {'fetched_at': v.get('fetched_at'), 'coverage': v.get('coverage')}
                            for k, v in view['manifests'].items()}, 'refreshes': runs}
