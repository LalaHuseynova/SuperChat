"""Validated source records shared by snapshot and future API adapters.

Unknown values remain None. These models do not confer booking capabilities.
"""
from datetime import date, datetime, time
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def public_url(value):
    if not value:
        return None
    parts = urlsplit(str(value))
    return str(value) if parts.scheme in ("https", "http") and parts.hostname and not parts.username and not parts.password else None


class Record(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    fetched_at: datetime

    @field_validator("fetched_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Collection timestamp must include timezone")
        return value


class Product(Record):
    name: dict[str, str | None]
    descriptions: dict[str, str | None] = Field(default_factory=dict)
    description: str | None = None
    category: str
    brand: str | None = None
    color: str | None = None
    price_azn: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    url: str

    @model_validator(mode="after")
    def valid_name(self):
        if not any(self.name.values()) or not public_url(self.url):
            raise ValueError("Product needs a source name and URL")
        return self


class Location(BaseModel):
    model_config = ConfigDict(extra="allow")
    city: str | None
    code: str


class Flight(Record):
    origin: Location
    destination: Location
    departure_local: datetime
    arrival_local: datetime | None = None
    airline: str | None = None
    flight_number: str | None = None
    duration_min: int | None = Field(default=None, gt=0)
    stops: int | None = Field(default=None, ge=0)
    baggage_kg: int | None = Field(default=None, ge=0)
    seats_available: int | None = Field(default=None, ge=0)
    price_azn: float | None = Field(default=None, ge=0)
    cabin: str | None = None
    via: str | list | None = None
    trip_type: Literal["one_way", "round_trip"]
    price_scope: Literal["entire_one_way_itinerary", "entire_round_trip"]
    return_date: date | None = None

    @model_validator(mode="after")
    def itinerary(self):
        expected = "entire_round_trip" if self.trip_type == "round_trip" else "entire_one_way_itinerary"
        if self.price_scope != expected or (self.trip_type == "round_trip" and not self.return_date):
            raise ValueError("Fare type and price scope disagree")
        return self


class Movie(Record):
    title: str = Field(min_length=1)
    genre: list[str]
    language: str | None = None
    duration_min: int | None = Field(default=None, gt=0)
    rating: float | None = Field(default=None, ge=0, le=10)
    age_rating: str | None = None
    synopsis: str | None = None


class Cinema(Record):
    name: str = Field(min_length=1)
    address: str | None = None
    district: str | None = None


class Showtime(Record):
    movie_id: str
    cinema_id: str
    date: date
    time: time
    start_local: datetime
    hall: str | None = None
    price_azn: float | None = Field(default=None, ge=0)
    seats_available: int | None = Field(default=None, ge=0)
    seats_total: int | None = Field(default=None, ge=0)
    languages: list[str] = Field(default_factory=list)
    price_conflict: bool = False
    price_observations: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self):
        if self.start_local.tzinfo is None or self.start_local.date() != self.date or self.start_local.time() != self.time:
            raise ValueError("Showtime date/time mismatch")
        prices = {p["price_azn"] for p in self.price_observations}
        if prices and (self.price_azn not in prices or self.price_conflict != (len(prices) > 1)):
            raise ValueError("Unsupported or conflicting price metadata")
        return self
