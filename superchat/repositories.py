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

    def __init__(self, directory):
        self.directory = Path(directory)

    def all(self):
        # Re-read authoritative data for every turn, never trust logged prices/stock.
        return json.loads((self.directory / self.filename).read_text())

    def get(self, item_id):
        return next((item for item in self.all() if item["id"] == item_id), None)

    def price_match(self, item, f):
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
            rows = [r for r in rows if r["stops"] <= f["max_stops"]]
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
        return sorted(rows, key=lambda r: r[key], reverse=f.get("descending", False))


class JsonProductRepository(JsonRepository):
    filename = "products.json"

    def search(self, f):
        rows = self.all()
        for field in ["category", "brand", "color"]:
            if f.get(field):
                rows = [r for r in rows if normalize(f[field]) == normalize(r[field])]
        if f.get("query"):
            terms = normalize(f["query"]).split()
            canonical = f["query"] in [
                "headphones",
                "earbuds",
                "laptop",
                "smartphone",
                "smartwatch",
                "speaker",
                "running shoes",
                "backpack",
                "coffee machine",
                "board game",
            ]
            rows = [
                r
                for r in rows
                if all(
                    t
                    in normalize(
                        " ".join(r["name"].values())
                        + ("" if canonical else " " + r["description"])
                    )
                    for t in terms
                )
            ]
        if f.get("in_stock"):
            rows = [r for r in rows if r["stock"] > 0]
        rows = [r for r in rows if self.price_match(r, f)]
        if f.get("sort") == "rating":
            return sorted(rows, key=lambda r: r["rating"], reverse=True)
        if f.get("sort") == "price":
            return sorted(
                rows, key=lambda r: r["price_azn"], reverse=f.get("descending", False)
            )
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
            rows = [r for r in rows if f["genre"] in r["movie"]["genre"]]
        if f.get("language"):
            rows = [r for r in rows if r["movie"]["language"] == f["language"]]
        if f.get("min_rating"):
            rows = [r for r in rows if r["movie"]["rating"] >= f["min_rating"]]
        if f.get("after"):
            rows = [r for r in rows if r["time"] >= f["after"]]
        if f.get("before"):
            rows = [r for r in rows if r["time"] <= f["before"]]
        rows = [r for r in rows if self.price_match(r, f)]
        if f.get("sort") == "rating":
            return sorted(rows, key=lambda r: r["movie"]["rating"], reverse=True)
        if f.get("sort") == "price":
            return sorted(rows, key=lambda r: r["price_azn"])
        return sorted(rows, key=lambda r: (r["date"], r["time"]))
