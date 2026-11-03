"""Read-only, validated snapshots. No supplier orders or reservations."""
import copy
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .catalogue import Product, Flight, Movie, Cinema, Showtime
from .repositories import JsonFlightRepository, JsonProductRepository, JsonShowtimeRepository, normalize, product_matches

TABLES = {
    "products": ("birmarket", "products.json", Product),
    "flights": ("aviasales", "flights.json", Flight),
    "round_trips": ("aviasales", "round_trip_flights.json", Flight),
    "movies": ("cinema", "movies.json", Movie),
    "cinemas": ("cinema", "cinemas.json", Cinema),
    "showtimes": ("cinema", "showtimes.json", Showtime),
}


class SnapshotError(ValueError):
    pass


def inside(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise SnapshotError("Invalid snapshot reference")
    return path


class SnapshotDataset:
    def __init__(self, root, publication=None):
        self.root = Path(root).resolve()
        if publication and Path(publication).exists():
            descriptor = json.loads(Path(publication).read_text())
        else:
            descriptor = {"schema_version": 1, "tables": {}, "manifests": {}}
            for name, (source, filename, _) in TABLES.items():
                if source not in descriptor["manifests"]:
                    descriptor["manifests"][source] = json.loads((self.root / source / "manifest.json").read_text())
                manifest = descriptor["manifests"][source]
                path = inside(self.root, manifest["run_directory"]) / filename
                descriptor["tables"][name] = {
                    "file": str(path.relative_to(self.root)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
        if descriptor.get("schema_version") != 1 or set(descriptor["tables"]) != set(TABLES):
            raise SnapshotError("Unsupported snapshot index")
        self.tables = {}
        for name, (_, _, model) in TABLES.items():
            ref = descriptor["tables"][name]
            raw = inside(self.root, ref["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
                raise SnapshotError("Snapshot content changed; publish a new validated version")
            self.tables[name] = [model.model_validate(r).model_dump(mode="json") for r in json.loads(raw)]
            if name == "showtimes":
                for row in self.tables[name]:
                    row["time"] = row["time"][:5]
            ids = [r["id"] for r in self.tables[name]]
            if len(set(ids)) != len(ids):
                raise SnapshotError("Duplicate catalogue IDs")
        movies = {r["id"] for r in self.tables["movies"]}
        cinemas = {r["id"] for r in self.tables["cinemas"]}
        if any(r["movie_id"] not in movies or r["cinema_id"] not in cinemas for r in self.tables["showtimes"]):
            raise SnapshotError("Unresolved cinema relationship")
        if any(r["trip_type"] != "one_way" for r in self.tables["flights"]) or any(r["trip_type"] != "round_trip" for r in self.tables["round_trips"]):
            raise SnapshotError("One-way and return tables are mixed")
        self.descriptor = descriptor
        self.version = hashlib.sha256(json.dumps(descriptor["tables"], sort_keys=True).encode()).hexdigest()[:16]

    def records(self, name):
        return copy.deepcopy(self.tables[name])

    def publish(self, destination):
        """Switch one descriptor only after every table passed validation."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        payload = {**self.descriptor, "version": self.version, "published_at": datetime.now(timezone.utc).isoformat()}
        try:
            with temporary.open("w") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


def contains(text, word):
    return bool(re.search(r"(?<!\w)" + re.escape(normalize(word)) + r"(?!\w)", normalize(text)))


class SnapshotMixin:
    mode = "snapshot"

    def __init__(self, dataset):
        self.dataset = dataset


class SnapshotFlightRepository(SnapshotMixin, JsonFlightRepository):
    def all(self):
        return self.dataset.records("flights") + self.dataset.records("round_trips")

    def search(self, filters):
        rows = super().search(filters)
        return [r for r in rows if r["trip_type"] == filters.get("trip_type", "one_way")
                and (not filters.get("return_date") or r["return_date"] == filters["return_date"])]


class SnapshotProductRepository(SnapshotMixin, JsonProductRepository):
    def all(self):
        return self.dataset.records("products")

    def hints(self, text):
        from . import nlu
        from .search_text import product_query
        if normalize(text).strip(' .!?') in {
            'show more', 'next page', 'daha cox', 'novbeti sehife',
            'еще результаты', 'следующая страница',
        }:
            # Control phrases must not become product/brand constraints when
            # newly collected catalogue text happens to contain those words.
            return {}
        brands = {p["brand"] for p in self.dataset.tables["products"] if p.get("brand")}
        hits = [b for b in brands if contains(text, b)]
        result = {"brand": max(hits, key=len)} if hits else {}
        # Only explicit searches create new query constraints; follow-ups retain state.
        domain = nlu.route(text, {'active_domains': []})
        if nlu.action(text, 'shopping') == 'search' and ('shopping' in domain['domains'] or hits):
            query = product_query(text, brands)
            if query:
                result['query'] = query
        if result:
            return result
        # Recognize specific catalogue terms such as iPhone/Redmi without a
        # hard-coded brand list. Require an explicit search request.
        match = re.fullmatch(r"(?:show|find|search for|goster|tap|покажи|найди)\s+(?:me\s+)?(.+?)[.!?]?", normalize(text))
        if match and len(match[1]) >= 3 and any(product_matches(p, match[1], real=True) for p in self.dataset.tables["products"]):
            return {"query": match[1]}
        return {}


class SnapshotShowtimeRepository(SnapshotMixin, JsonShowtimeRepository):
    def movies(self):
        return self.dataset.records("movies")

    def cinemas(self):
        return self.dataset.records("cinemas")

    def all(self):
        movies = {m["id"]: m for m in self.movies()}
        cinemas = {c["id"]: c for c in self.cinemas()}
        return [{**r, "movie": movies[r["movie_id"]], "cinema": cinemas[r["cinema_id"]]}
                for r in self.dataset.records("showtimes")]

    def hints(self, text):
        from .nlu import has
        from .search_text import result_request
        _, _, lookup_text = result_request(text, 'cinema')
        result = {}
        aliases = {'Deniz Mall': ['deniz', 'dəniz', 'дениз', 'дениз молл'],
                   'Ganjlik Mall': ['genclik', 'gənclik', 'гянджлик'],
                   '28 Mall': ['28 mol', '28 молл']}
        for table, field, label in [("movies", "movie_id", "title"), ("cinemas", "cinema_id", "name")]:
            hits = [r for r in self.dataset.tables[table]
                    if (len(r[label]) >= 3 or (table == "movies" and has(normalize(text), ["film", "movie", "showtime", "kino", "фильм", "сеанс"]))) and (contains(lookup_text, r[label]) or (table == 'cinemas' and has(normalize(text), aliases.get(r[label], []))))]
            if hits:
                result[field] = max(hits, key=lambda r: len(r[label]))["id"]
        if 'movie_id' not in result:
            from . import nlu
            from .search_text import request_terms
            if 'cinema' in nlu.route(text, {'active_domains': []})['domains'] and nlu.action(text, 'cinema') == 'search':
                names = [r['name'] for r in self.dataset.tables['cinemas']]
                names += [a for values in aliases.values() for a in values] + ['mall', 'молл']
                query = request_terms(text, 'cinema', names)
                if query:
                    result['query'] = query
        return result


def repositories(dataset):
    return {"flights": SnapshotFlightRepository(dataset), "shopping": SnapshotProductRepository(dataset),
            "cinema": SnapshotShowtimeRepository(dataset)}
