"""Scheduled, bounded public-page collection. Failed runs never replace the database."""
import fcntl
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx
from .config import ROOT
from .database import validate_tables
from .snapshots import TABLES, inside

log = logging.getLogger(__name__)
SOURCES = {
    'birmarket': ('https://birmarket.az', 'birmarket_scraper.py'),
    'cinema': ('https://cinemastercard.az', 'cinema_scraper.py'),
}


def check_access(source):
    base = SOURCES[source][0]
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        response = client.get(base + '/robots.txt')
    if response.status_code == 404:
        return
    response.raise_for_status()
    rules = RobotFileParser()
    rules.parse(response.text.splitlines())
    paths = ['/az/films/', '/az/cinema/about-cinemaplus/'] if source == 'cinema' else ['/product/', '/categories/']
    if any(not rules.can_fetch('SuperChat', base + p) for p in paths):
        raise RuntimeError('Public collection disallowed by robots.txt')


def collection_limits(per_category=None, pages=None):
    per_category = int(per_category if per_category is not None else os.getenv('BIRMARKET_PER_CATEGORY', '100'))
    pages = int(pages if pages is not None else os.getenv('BIRMARKET_PAGES', '10'))
    if not 0 <= per_category <= 1000 or not 1 <= pages <= 100:
        raise ValueError('Birmarket limits: per-category 0..1000 and pages 1..100')
    return per_category, pages


def refresh_source(database, source, *, runner=subprocess.run, access_check=check_access,
                   per_category=None, pages=None, categories_file=None, browser=False, expand=False):
    """Keep archived inputs intact; promote only a complete, validated scrape."""
    if source not in SOURCES:
        raise ValueError('Unknown collection source')
    if source == 'birmarket':
        per_category, pages = collection_limits(per_category, pages)
        categories_file = categories_file or os.getenv('BIRMARKET_CATEGORIES_FILE')
        if categories_file:
            categories_file = Path(categories_file).expanduser().resolve()
            if not categories_file.is_file():
                raise ValueError('Birmarket categories file does not exist')
    lock_path = database.path.with_suffix('.refresh.lock')
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        run_id = database.begin_refresh(source)
        staging = database.root / '.staging' / uuid.uuid4().hex
        staging.mkdir(parents=True)
        try:
            if not (browser and source == 'birmarket'):
                access_check(source)
            args = [sys.executable, str(ROOT / 'preparation_dataset' / SOURCES[source][1]),
                    '--output', str(staging), '--delay', '2']
            if source == 'birmarket':
                args += ['--download-images', '--max-images', '1', '--per-category', str(per_category), '--pages', str(pages)]
                if categories_file:
                    args += ['--categories-file', str(categories_file)]
                if browser:
                    # The same robots check runs through Chrome in BrowserClient.
                    args += ['--browser']
                if expand:
                    existing = staging / 'existing-products.json'
                    existing.write_text(json.dumps(database.records('products'), ensure_ascii=False))
                    args += ['--existing-products', str(existing)]
            # No AI/provider credentials are passed into the scraper subprocess.
            env = {k: v for k, v in os.environ.items()
                   if not any(s in k.upper() for s in ('TOKEN', 'SECRET', 'API_KEY', 'PASSWORD'))}
            result = runner(args, cwd=ROOT / 'preparation_dataset', env=env,
                            capture_output=True, text=True, timeout=7200 if source == 'birmarket' else 3600)
            if result.returncode:
                # Keep failed public-page inputs for diagnosis, outside the live catalogue.
                # Scraper subprocesses receive no provider credentials.
                (staging / 'scraper.stdout.log').write_text(getattr(result, 'stdout', '') or '')
                (staging / 'scraper.stderr.log').write_text(getattr(result, 'stderr', '') or '')
                raise RuntimeError('Scraper failed or returned incomplete data')
            manifest = json.loads((staging / source / 'manifest.json').read_text())
            if manifest.get('coverage') == 'partial' or manifest.get('stopped_by_site'):
                raise RuntimeError('Incomplete collection; previous database retained')
            # Missing images alone do not invalidate grounded product facts.
            if any(e.get('stage') != 'image' for e in manifest.get('errors', [])):
                raise RuntimeError('Collection contains page errors')
            tables = {name: json.loads((staging / source / filename).read_text())
                      for name, (s, filename, _) in TABLES.items() if s == source}
            if not tables.get('products', tables.get('movies')):
                raise RuntimeError('No records collected')
            tables = validate_tables(tables)
            run = inside(staging, manifest['run_directory'])
            destination = inside(database.root, manifest['run_directory'])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(run), destination)
            database.publish(tables, {source: manifest})
            database.end_refresh(run_id, 'success', 'Validated source published')
            log.info('catalogue_refresh source=%s status=success', source)
            return True
        except Exception as exc:
            if any(staging.iterdir()):
                failed = database.root / '.failed' / staging.name
                failed.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staging), failed)
            # Log safe categories only: no raw request URLs, headers or user input.
            detail = f'HTTP {exc.response.status_code}' if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
            database.end_refresh(run_id, 'failed', detail + ': previous data retained')
            log.warning('catalogue_refresh source=%s status=failed error=%s', source, type(exc).__name__)
            return False
        finally:
            shutil.rmtree(staging, ignore_errors=True)


class RefreshWorker:
    def __init__(self, database, hours=24):
        self.database = database
        self.hours = max(6, hours)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='catalogue-refresh')

    def run(self):
        while not self.stop.is_set():
            for source in SOURCES:
                if self.stop.is_set():
                    return
                manifest = self.database.descriptor['manifests'].get(source, {})
                fetched = manifest.get('fetched_at')
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(fetched)).total_seconds() if fetched else float('inf')
                # Also back off after failure, including across process restarts.
                attempts = [r for r in self.database.status()['refreshes'] if r['source'] == source]
                if attempts:
                    last_age = (datetime.now(timezone.utc) - datetime.fromisoformat(attempts[0]['started_at'])).total_seconds()
                    age = min(age, last_age)
                if age >= self.hours * 3600:
                    refresh_source(self.database, source)
            self.stop.wait(60)
