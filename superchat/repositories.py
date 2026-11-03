"""Read-only source adapters. Replace these Protocol implementations for Phase 2."""

import json
import unicodedata
from pathlib import Path
from typing import Protocol


def normalize(value):
    value = str(value).lower().replace("ı", "i").replace("ə", "e")
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


class FlightRepository(Protocol):
    def search(self, filters: dict) -> list[dict]: ...
    def get(self, item_id: str) -> dict | None: ...


class ProductRepository(Protocol):
    def search(self, filters: dict) -> list[dict]: ...
    def get(self, item_id: str) -> dict | None: ...


class ShowtimeRepository(Protocol):
    def search(self, filters: dict) -> list[dict]: ...
    def get(self, item_id: str) -> dict | None: ...


class JsonRepository:
    filename = ""
    mode = "mock"

    def __init__(self, directory):
        self.directory = Path(directory)

    def all(self):
        # Re-read authoritative data for every turn, never trust logged prices/stock.
        return json.loads((self.directory / self.filename).read_text())

    def get(self, item_id):
        return next((item for item in self.all() if item["id"].lower() == item_id.lower()), None)

    def price_match(self, item, f):
        if item.get("price_azn") is None:
            return "min_price" not in f and "max_price" not in f
        return (
            f.get("min_price", 0)
            <= item["price_azn"]
            <= f.get("max_price", float("inf"))
        )


class JsonFlightRepository(JsonRepository):
    filename = "flights.json"

    def search(self, f):
        rows = self.all()
        for field in ["origin", "destination"]:
            if f.get(field):
                rows = [
                    r
                    for r in rows
                    if normalize(f[field])
                    in [normalize(r[field]["city"]), normalize(r[field]["code"])]
                ]
        if f.get("date"):
            rows = [r for r in rows if r["departure_local"][:10] == f["date"]]
        if f.get("airline"):
            rows = [
                r for r in rows if normalize(f["airline"]) in normalize(r["airline"])
            ]
        if "max_stops" in f:
            rows = [r for r in rows if r["stops"] is not None and r["stops"] <= f["max_stops"]]
        if f.get("cabin"):
            rows = [r for r in rows if r["cabin"] == f["cabin"]]
        for field, op in [
            ("after", lambda a, b: a >= b),
            ("before", lambda a, b: a <= b),
        ]:
            if f.get(field):
                rows = [r for r in rows if op(r["departure_local"][11:16], f[field])]
        rows = [r for r in rows if self.price_match(r, f)]
        key = {
            "price": "price_azn",
            "departure": "departure_local",
            "stops": "stops",
            "duration": "duration_min",
            "airline": "airline",
        }.get(f.get("sort"), "price_azn")
        return sort_known(rows, key, f.get("descending", False))


def sort_known(rows, key, descending=False):
    return sorted([r for r in rows if r.get(key) is not None], key=lambda r: r[key], reverse=descending) + [r for r in rows if r.get(key) is None]


def product_matches(row, query, real=False):
    from .nlu import PRODUCTS, has
    name = normalize(" ".join(v for v in row["name"].values() if v))
    if real and query not in PRODUCTS:
        import re
        t = normalize(query)
        for canonical, variants in sorted(PRODUCTS.items(), key=lambda v: -len(v[0])):
            for variant in [canonical] + variants:
                pattern = r'(?<!\w)' + re.escape(normalize(variant)) + r'\w*'
                if re.search(pattern, t):
                    if not product_matches(row, canonical, real=True):
                        return False
                    t = re.sub(pattern, ' ', t)
        # Names/model IDs, not long marketing descriptions, establish an exact requested product.
        haystack = name + ' ' + normalize(row.get('model') or '') + ' ' + normalize(row.get('brand') or '')
        return all(bool(re.search(r'(?<!\w)' + re.escape(token) + r'(?!\w)', haystack))
                   if any(c.isdigit() for c in token) else token in haystack
                   for token in re.findall(r'[\w-]+', t))
    if real and query in PRODUCTS:
        categories = {"laptop": "computers", "smartphone": "phones", "smartwatch": "wearables",
                      "running shoes": "sport", "backpack": "accessories", "coffee machine": "home", "board game": "gifts"}
        if query in categories:
            return row["category"] == categories[query]
        if query in ['pen', 'pencil']:
            # Recognize product requests beyond the sampled categories, but only
            # match a real source name; never substitute a sampled product type.
            return has(name, PRODUCTS[query])
        return row["category"] == "audio" and has(name, PRODUCTS[query] + (["buds"] if query == "earbuds" else []))
    haystack = name + ("" if query in PRODUCTS else " " + normalize(row.get("description") or ""))
    return all(t in haystack for t in normalize(query).split())


def color_key(value):
    from .nlu import has
    aliases = {"black": ["black", "qara", "черн"], "white": ["white", "ag", "бел"],
               "blue": ["blue", "mavi", "син"], "grey": ["grey", "gray", "boz", "сер"],
               "silver": ["silver", "gumus", "серебр"], "red": ["red", "qirmizi", "красн"]}
    return next((k for k, words in aliases.items() if has(normalize(value), words)), normalize(value))


def language_key(value):
    from .nlu import has
    aliases = {"English": ["english", "ingilis", "английск"], "Russian": ["russian", "rus", "русск"],
               "Azerbaijani": ["azerbaijani", "azerbaycan", "азербайджан"]}
    return next((k for k, words in aliases.items() if has(normalize(value), words)), value)


class JsonProductRepository(JsonRepository):
    filename = "products.json"

    def search(self, f):
        rows = self.all()
        for field in ["category", "brand", "color"]:
            if f.get(field):
                key = color_key if field == "color" else normalize
                rows = [r for r in rows if r.get(field) is not None and key(f[field]) == key(r[field])]
        if f.get("query"):
            rows = [r for r in rows if product_matches(r, f["query"], self.mode != "mock")]
        if f.get("in_stock"):
            rows = [r for r in rows if r.get("in_stock") is True or (r.get("stock") is not None and r["stock"] > 0)]
        rows = [r for r in rows if self.price_match(r, f)]
        if f.get("sort") == "rating":
            return sort_known(rows, "rating", True)
        if f.get("sort") == "price":
            return sort_known(rows, "price_azn", f.get("descending", False))
        return rows


class JsonShowtimeRepository(JsonRepository):
    filename = "showtimes.json"

    def movies(self):
        return json.loads((self.directory / "movies.json").read_text())

    def cinemas(self):
        return json.loads((self.directory / "cinemas.json").read_text())

    def all(self):
        movies = {m["id"]: m for m in self.movies()}
        cinemas = {c["id"]: c for c in self.cinemas()}
        return [
            {**s, "movie": movies[s["movie_id"]], "cinema": cinemas[s["cinema_id"]]}
            for s in super().all()
        ]

    def search(self, f):
        rows = self.all()
        for field in ["date", "movie_id", "cinema_id"]:
            if f.get(field):
                rows = [r for r in rows if r[field] == f[field]]
        if f.get("query"):
            rows = [
                r
                for r in rows
                if normalize(f["query"]) in normalize(r["movie"]["title"])
            ]
        if f.get("genre"):
            from .nlu import GENRES, has
            terms = GENRES.get(f["genre"], [f["genre"]])
            rows = [r for r in rows if any(has(normalize(g), terms) for g in r["movie"]["genre"])]
        if f.get("language"):
            rows = [r for r in rows if f["language"] in [language_key(v) for v in r.get("languages", [r["movie"]["language"]])]]
        if f.get("min_rating"):
            rows = [r for r in rows if r["movie"]["rating"] is not None and r["movie"]["rating"] >= f["min_rating"]]
        if f.get("after"):
            rows = [r for r in rows if r["time"] >= f["after"]]
        if f.get("before"):
            rows = [r for r in rows if r["time"] <= f["before"]]
        rows = [r for r in rows if self.price_match(r, f)]
        if f.get("sort") == "rating":
            return sorted([r for r in rows if r["movie"]["rating"] is not None], key=lambda r: r["movie"]["rating"], reverse=True) + [r for r in rows if r["movie"]["rating"] is None]
        if f.get("sort") == "price":
            return sort_known(rows, "price_azn")
        return sorted(rows, key=lambda r: (r["date"], r["time"]))
