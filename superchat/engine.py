import copy
import uuid
from . import nlu
from .i18n import tr, PRODUCT_DESCRIPTIONS
from .repositories import (
    JsonFlightRepository,
    JsonProductRepository,
    JsonShowtimeRepository,
)
from .store import now


class Engine:
    def __init__(self, data_dir, repositories=None):
        self.repos = repositories or {
            "flights": JsonFlightRepository(data_dir),
            "shopping": JsonProductRepository(data_dir),
            "cinema": JsonShowtimeRepository(data_dir),
        }

    def card(self, domain, r, used, lang):
        fields = []

        def f(label, value):
            fields.append({"label": label, "value": value})

        if domain == "flights":
            title = f"{r['origin']['city']} → {r['destination']['city']}"
            subtitle = f"{r['airline']} · {r['flight_number']}"
            for label, key in [
                ("departure", "departure_local"),
                ("arrival", "arrival_local"),
                ("duration", "duration_min"),
                ("stops", "stops"),
                ("baggage", "baggage_kg"),
                ("cabin", "cabin"),
            ]:
                f(label, r[key])
            if r["via"]:
                f("via", r["via"])
            available = max(0, r["seats_available"] - used.get(r["id"], 0))
            source = "flights.json"
        elif domain == "shopping":
            title = r["name"][lang]
            subtitle = r["brand"]
            desc = (
                r["description"]
                if lang == "en"
                else PRODUCT_DESCRIPTIONS[r["id"]][0 if lang == "az" else 1]
            )
            for label, value in [
                ("description", desc),
                ("color", r["color"]),
                ("rating", r["rating"]),
                ("category", r["category"]),
            ]:
                f(label, value)
            available = r["stock"]
            source = "products.json"
        else:
            title = r["movie"]["title"]
            subtitle = f"{r['cinema']['name']} · {r['hall']}"
            for label, value in [
                ("date", r["date"]),
                ("time", r["time"]),
                ("duration", r["movie"]["duration_min"]),
                ("language", r["movie"]["language"]),
                ("rating", r["movie"]["rating"]),
                ("age", r["movie"]["age_rating"]),
                ("genre", ", ".join(r["movie"]["genre"])),
                ("address", r["cinema"]["address"]),
            ]:
                f(label, value)
            available = max(0, r["seats_available"] - used.get(r["id"], 0))
            source = "showtimes.json + movies.json + cinemas.json"
        return {
            "kind": domain,
            "id": r["id"],
            "title": title,
            "subtitle": subtitle,
            "price": r["price_azn"],
            "available": available,
            "fields": fields,
            "source": source,
        }

    def cart_total(self, state):
        total = 0
        for pid, qty in state["cart"].items():
            product = self.repos["shopping"].get(pid)
            if product:
                total += product["price_azn"] * qty
        return round(total, 2)

    def respond(self, text, old_state, used, plan=None):
        state = copy.deepcopy(old_state)
        lang = nlu.language(text, state["language"])
        state["language"] = lang
        route = nlu.route(text, state)
        if plan:
            route = {
                "category": plan.category,
                "domains": [i.domain for i in plan.intents],
                "engine": "openrouter",
                "reason": "validated structured plan",
            }
            lang = plan.language
            state["language"] = lang
        sections = []
        actions = []
        if not route["domains"]:
            key = {
                "greeting": "welcome",
                "out_of_scope": "out",
                "ambiguous": "mixed_clarify"
                if len(state["active_domains"]) > 1
                else "clarify",
            }.get(route["category"], "clarify")
            return (
                {
                    "text": tr(key, lang),
                    "sections": [],
                    "route": route,
                    "language": lang,
                },
                state,
                actions,
            )
        pending = state.get("pending")
        if pending and pending["domain"] not in route["domains"]:
            state["pending"] = None
        chunks = nlu.clauses(text, route["domains"])
        for domain in route["domains"]:
            intent = (
                next((i for i in plan.intents if i.domain == domain), None)
                if plan
                else None
            )
            section, events = self.handle(domain, chunks[domain], state, used, intent)
            sections.append(section)
            actions.extend(events)
        state["active_domains"] = route["domains"]
        return (
            {"text": "", "sections": sections, "route": route, "language": lang},
            state,
            actions,
        )

    def handle(self, domain, text, state, used, intent=None):
        lang = state["language"]
        repo = self.repos[domain]
        ds = state["domains"][domain]
        t = nlu.normalize(text)
        act = nlu.action(text, domain)
        filters = nlu.parse_filters(text, domain)
        qty = nlu.quantity(text)
        ids = nlu.selected_ids(text, domain, ds["results"], repo)
        if intent:
            act = intent.action
            filters = intent.filters.model_dump(exclude_none=True)
            qty = intent.quantity
            # Model-chosen IDs must have appeared in the request or recent results.
            ids = [i for i in intent.ids if i in ds["results"] or i.lower() in t]
        if ids and act == "details":
            filters = {}
        # Complete a prior action only when the user supplies a concrete selection.
        pending = state.get("pending")
        if (
            pending
            and pending["domain"] == domain
            and ids
            and act in ["search", "details"]
        ):
            act = pending["action"]
            qty = pending["quantity"]
        section = {
            "domain": domain,
            "text": "",
            "cards": [],
            "filters": {},
            "action": act,
        }
        events = []

        def say(key, **kwargs):
            section["text"] = tr(key, lang, **kwargs)

        def cards(rows):
            section["cards"] = [self.card(domain, r, used, lang) for r in rows]

        if filters.get("date") == "invalid":
            say("bad_date")
            return section, events
        if qty < 1 or qty > 100:
            say("bad_quantity")
            return section, events
        if act in ["cart", "clear_cart"]:
            if act == "clear_cart":
                state["cart"] = {}
                events.append({"type": "cart_cleared"})
            rows = [repo.get(i) for i in state["cart"]]
            cards([r for r in rows if r])
            for c in section["cards"]:
                c["quantity"] = state["cart"][c["id"]]
            say(
                "cart" if state["cart"] else "empty_cart",
                total=f"{self.cart_total(state):.2f}",
            )
            return section, events
        if act == "reservations":
            reservations = [r for r in state["reservations"] if r["domain"] == domain]
            section["reservations"] = reservations
            say("reservations", count=len(reservations))
            return section, events
        # A new explicitly named entity starts a new search; returning preserves filters.
        entity_keys = {
            "flights": ["origin", "destination"],
            "shopping": ["query", "category", "brand"],
            "cinema": ["movie_id", "query", "genre"],
        }[domain]
        returning = nlu.has(
            t, ["back to", "return", "qayit", "geri", "вернем", "вернём", "снова"]
        )
        new_entity = any(
            k in filters and filters[k] != ds["filters"].get(k) for k in entity_keys
        )
        if new_entity and not returning:
            ds["filters"] = {}
            ds["selected"] = None
            state["pending"] = None
        if nlu.has(
            t,
            [
                "show all",
                "any date",
                "all dates",
                "butun",
                "hamisi",
                "все даты",
                "все варианты",
            ],
        ):
            ds["filters"] = {}
        if nlu.has(t, ["prefer", "preference", "ustunluk", "tercih", "предпочита"]):
            state["preferences"].setdefault(domain, {}).update(
                {
                    k: v
                    for k, v in filters.items()
                    if k
                    in ["max_stops", "airline", "cabin", "color", "brand", "language"]
                }
            )
        if filters:
            ds["filters"].update(filters)
        for key, value in state["preferences"].get(domain, {}).items():
            ds["filters"].setdefault(key, value)
        if filters:
            if act == "search":
                ds["selected"] = None
        if domain == "flights" and "origin" not in ds["filters"]:
            ds["filters"]["origin"] = "Baku"
        section["filters"] = ds["filters"].copy()
        # Queries for entity details still re-read source data.
        if ids:
            rows = [repo.get(i) for i in ids]
            if any(r is None for r in rows):
                say("unknown_id")
                return section, events
        elif act in ["reserve", "add", "remove", "details"]:
            selected = ds["selected"]
            if selected and not filters:
                ids = [selected]
            elif act == "details" and ds["results"] and not filters:
                ids = ds["results"][:]
            elif len(ds["results"]) == 1 and not filters:
                ids = ds["results"][:]
            if not ids:
                rows = repo.search(ds["filters"])
                # Adding a named product or reserving a unique search is explicit enough.
                if len(rows) == 1:
                    ids = [rows[0]["id"]]
            rows = [repo.get(i) for i in ids]
        elif act == "compare":
            ids = ds["results"][:]
            rows = [repo.get(i) for i in ids]
        else:
            rows = repo.search(ds["filters"])
        rows = [r for r in rows if r]
        if act in ["reserve", "add", "remove"]:
            if len(rows) != 1:
                state["pending"] = {"domain": domain, "action": act, "quantity": qty}
                say("choose_reserve" if act == "reserve" else "choose", quantity=qty)
                cards(repo.search(ds["filters"]))
                ds["results"] = [c["id"] for c in section["cards"]]
                return section, events
            r = rows[0]
            item_id = r["id"]
            available = self.card(domain, r, used, lang)["available"]
            if act == "remove":
                if item_id not in state["cart"]:
                    say("not_in_cart")
                    return section, events
                remaining = state["cart"][item_id] - qty
                if remaining > 0:
                    state["cart"][item_id] = remaining
                else:
                    state["cart"].pop(item_id)
                say("removed", total=f"{self.cart_total(state):.2f}")
                events.append(
                    {"type": "cart_removed", "item_id": item_id, "quantity": qty}
                )
            elif act == "add":
                current = state["cart"].get(item_id, 0)
                if current + qty > available:
                    say("unavailable", available=max(0, available - current))
                    cards(rows)
                    return section, events
                state["cart"][item_id] = current + qty
                say("added", quantity=qty, total=f"{self.cart_total(state):.2f}")
                events.append(
                    {"type": "cart_added", "item_id": item_id, "quantity": qty}
                )
            else:
                if qty > available:
                    say("unavailable", available=available)
                    cards(rows)
                    return section, events
                reservation = {
                    "code": "SC-" + uuid.uuid4().hex[:8].upper(),
                    "domain": domain,
                    "item_id": item_id,
                    "quantity": qty,
                    "unit_price": r["price_azn"],
                    "total": round(qty * r["price_azn"], 2),
                    "created_at": now(),
                }
                state["reservations"].append(reservation)
                used[item_id] = used.get(item_id, 0) + qty
                say(
                    "reserved",
                    code=reservation["code"],
                    quantity=qty,
                    total=f"{reservation['total']:.2f}",
                )
                section["reservations"] = [reservation]
                events.append({"type": "reservation_created", **reservation})
            state["pending"] = None
            ds["selected"] = item_id
            cards(rows)
            return section, events
        if act == "compare":
            if len(rows) < 2:
                say("compare_need")
            else:
                say("compare")
                cards(rows)
                section["comparison"] = True
        elif rows:
            cards(rows)
            say("details" if act == "details" or ids else "found", count=len(rows))
            if act != "details" and not ids:
                ds["results"] = [r["id"] for r in rows]
            if not ds["results"]:
                ds["results"] = [r["id"] for r in rows]
            if len(rows) == 1:
                ds["selected"] = rows[0]["id"]
        else:
            say("no_match")
            ds["results"] = []
            ds["selected"] = None
        return section, events
