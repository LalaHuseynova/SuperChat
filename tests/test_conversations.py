from superchat.store import initial_state
from superchat import nlu
import pytest


def say(engine, text, state=None, used=None):
    return engine.respond(text, state or initial_state(), used or {})


def ids(reply, section=0):
    return [c["id"] for c in reply["sections"][section]["cards"]]


def test_brief_domain_switch_and_return(engine):
    r, s, _ = say(engine, "Find me a flight from Baku to Istanbul on Friday.")
    assert ids(r) == ["F013", "F002", "F001"]
    r, s, _ = say(engine, "What is playing tonight?", s)
    assert ids(r) == ["S001", "S003", "S002"]
    r, s, _ = say(engine, "Do you have wireless headphones under 100 AZN?", s)
    assert ids(r) == ["P001"]
    r, s, _ = say(engine, "Back to flights", s)
    assert ids(r) == ["F013", "F002", "F001"]
    r, s, _ = say(engine, "The cheaper one, is it direct?", s)
    assert ids(r) == ["F013"]
    assert (
        next(
            f["value"]
            for f in r["sections"][0]["cards"][0]["fields"]
            if f["label"] == "stops"
        )
        == 1
    )
    assert "max_stops" not in s["domains"]["flights"]["filters"]


def test_return_to_cinema_after_laptops(engine):
    r, s, _ = say(engine, "What is playing tonight?")
    r, s, _ = say(engine, "Show me laptops.", s)
    assert ids(r) == ["P003", "P004"]
    r, s, _ = say(engine, "Okay, and the sci-fi one, any seats on Saturday?", s)
    assert ids(r) == ["S011", "S012"]
    assert all(c["available"] > 0 for c in r["sections"][0]["cards"])
    r, s, _ = say(engine, "Back to laptops", s)
    assert ids(r) == ["P003", "P004"]


def test_ordinal_and_comparison(engine):
    r, s, _ = say(engine, "Show me laptops.")
    r, s, _ = say(engine, "The second one, is it in stock?", s)
    assert ids(r) == ["P004"] and r["sections"][0]["cards"][0]["available"] == 12
    r, s, _ = say(engine, "Compare the first and second", s)
    assert ids(r) == ["P003", "P004"]
    assert r["sections"][0]["comparison"]


def test_mixed_clauses_and_ambiguous_followup(engine):
    r, s, _ = say(
        engine, "I need a flight to Istanbul on 6 November and a backpack for the trip."
    )
    assert r["route"]["category"] == "mixed"
    assert ids(r) == ["F013", "F002", "F001"] and ids(r, 1) == ["P010"]
    r, s, events = say(engine, "book it", s)
    assert r["route"]["category"] == "ambiguous" and not events


@pytest.mark.parametrize(
    "text,kind",
    [
        ("Show me something good.", "ambiguous"),
        ("What is the weather in Ganja?", "out_of_scope"),
        ("Book two seats.", "ambiguous"),
    ],
)
def test_brief_clarifications(engine, text, kind):
    r, s, actions = say(engine, text)
    assert r["route"]["category"] == kind and not actions


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Cümə günü Bakıdan İstanbula uçuş tap.", ["F013", "F002", "F001"]),
        ("Найди рейс из Баку в Стамбул в пятницу.", ["F013", "F002", "F001"]),
        ("100 manatdan ucuz simsiz qulaqlıq var?", ["P001"]),
        ("Есть беспроводные наушники до 100 AZN?", ["P001"]),
        ("Bu axşam kinoda nə göstərilir?", ["S001", "S003", "S002"]),
        ("Что сегодня вечером идёт в кино?", ["S001", "S003", "S002"]),
    ],
)
def test_multilingual_search(engine, text, expected):
    r, s, _ = say(engine, text)
    assert ids(r) == expected
    assert r["language"] in ["az", "ru"]


def test_language_switch(engine):
    r, s, _ = say(engine, "Show me laptops")
    r, s, _ = say(engine, "İkinci, stokda var?", s)
    assert r["language"] == "az" and ids(r) == ["P004"]
    r, s, _ = say(engine, "Добавь второй в корзину", s)
    assert r["language"] == "ru" and s["cart"] == {"P004": 1}


def test_filters_and_empty_results(engine):
    r, s, _ = say(
        engine, "Find a direct flight to Istanbul on Friday after 10:00 under 280 AZN"
    )
    assert ids(r) == ["F002"]
    r, s, _ = say(engine, "Flights from Baku to London on Friday")
    assert ids(r) == []
    r, s, _ = say(engine, "Show me headphones under 20 AZN")
    assert ids(r) == []
    r, s, _ = say(engine, "Showtimes for Titanic")
    assert ids(r) == []
    r, s, _ = say(engine, "Black Sonivo products under 80 AZN")
    assert ids(r) == ["P008"]
    r, s, _ = say(engine, "English sci-fi films rated above 8 on Saturday")
    assert set(ids(r)) == {"S011", "S012"}


def test_cart_stock_and_total(engine):
    r, s, a = say(engine, "Add two headphones to cart")
    assert s["cart"] == {"P001": 2} and engine.cart_total(s) == 179.8
    r, s, a = say(engine, "Add P002 to cart", s)
    assert s["cart"] == {"P001": 2} and not a
    r, s, a = say(engine, "Remove P001 from cart", s)
    assert s["cart"] == {"P001": 1}
    r, s, a = say(engine, "Clear cart", s)
    assert not s["cart"]


def test_reservation_and_sold_out(engine):
    r, s, a = say(engine, "Reserve two seats for S001")
    assert s["reservations"][0]["total"] == 24 and len(a) == 1
    r, s, a = say(engine, "Reserve S003", s)
    assert len(s["reservations"]) == 1 and not a
    r, s, a = say(engine, "Reserve 100 seats for F002", s)
    assert len(s["reservations"]) == 1 and not a


def test_pending_reservation_preserves_quantity(engine):
    r, s, _ = say(engine, "Flights to Istanbul on Friday")
    r, s, a = say(engine, "Book two seats", s)
    assert not a and s["pending"]["quantity"] == 2
    r, s, a = say(engine, "F002", s)
    assert s["reservations"][0]["quantity"] == 2 and not s["pending"]


def test_unknown_ids_and_negation(engine):
    r, s, a = say(engine, "Reserve F999")
    assert not a and not s["reservations"]
    r, s, a = say(engine, "Do not reserve F001")
    assert not a and not s["reservations"]
    r, s, a = say(engine, "Do not add P001 to cart")
    assert not a and not s["cart"]


def test_shared_explicit_preference(engine):
    r, s, _ = say(engine, "I prefer direct flights to Istanbul on Friday")
    assert s["preferences"]["flights"]["max_stops"] == 0
    r, s, _ = say(engine, "Show laptops", s)
    r, s, _ = say(engine, "Flights to Dubai", s)
    assert all(c["fields"][3]["value"] == 0 for c in r["sections"][0]["cards"])


@pytest.mark.parametrize(
    "text,expected",
    [
        ("tonight", "2026-11-02"),
        ("tomorrow", "2026-11-03"),
        ("Friday", "2026-11-06"),
        ("Saturday", "2026-11-07"),
        ("cümə axşamı", "2026-11-05"),
        ("в субботу", "2026-11-07"),
        ("6 November", "2026-11-06"),
        ("2026-02-31", "invalid"),
    ],
)
def test_dates(text, expected):
    assert nlu.parse_date(text) == expected


def test_pending_action_cannot_leak_across_topic_switch(engine):
    r, s, _ = say(engine, "Flights to Istanbul on Friday")
    r, s, _ = say(engine, "Book two seats", s)
    assert s["pending"]
    r, s, _ = say(engine, "Show laptops", s)
    assert s["pending"] is None
    r, s, actions = say(engine, "F001", s)
    assert not actions and not s["reservations"]


def test_airline_sort_and_time_not_price(engine):
    r, s, _ = say(engine, "Flights to Istanbul on Friday sort by airline")
    assert ids(r) == ["F013", "F002", "F001"]
    r, s, _ = say(engine, "Рейсы в Стамбул 6 ноября до 12:00")
    assert ids(r) == ["F013", "F001"]
    assert "max_price" not in s["domains"]["flights"]["filters"]
    r, s, _ = say(engine, "Films rated above 7 on Saturday")
    assert "S013" in ids(r)


def test_how_to_questions_do_not_mutate(engine):
    r, s, a = say(engine, "How can I book F001?")
    assert not a and not s["reservations"]
    r, s, a = say(engine, "How do I add P001 to cart?")
    assert not a and not s["cart"]
