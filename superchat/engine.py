import copy
import uuid
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from . import nlu
from .catalogue import public_url
from .config import REFERENCE_DATE
from .i18n import tr, PRODUCT_DESCRIPTIONS
from .repositories import (
    JsonFlightRepository,
    JsonProductRepository,
    JsonShowtimeRepository,
)
from .store import now


class Engine:
    def __init__(self, data_dir, repositories=None, clock=None):
        self.repos = repositories or {
            "flights": JsonFlightRepository(data_dir),
            "shopping": JsonProductRepository(data_dir),
            "cinema": JsonShowtimeRepository(data_dir),
        }
        self.real = any(getattr(r, "mode", "mock") != "mock" for r in self.repos.values())
        self.clock = clock or (lambda: datetime.now(ZoneInfo("Asia/Baku")))

    def today(self):
        return self.clock().date() if self.real else REFERENCE_DATE

    def route(self, text, state):
        route = nlu.route(text, state)
        if self.real and route["reason"] not in ["unclear keyword fragment", "malformed numeric fragment", "unsupported request"]:
            domains = list(route["domains"]) if route["category"] not in ["follow_up", "ambiguous"] else []
            for domain, repo in self.repos.items():
                if hasattr(repo, "hints") and repo.hints(text) and domain not in domains:
                    domains.append(domain)
            if domains:
                route.update(domains=domains, category="mixed" if len(domains) > 1 else domains[0], reason="catalogue vocabulary")
        return route

    def card(self, domain, r, used, lang):
        fields = []

        def f(label, value):
            fields.append({"label": label, "value": value})

        if domain == "flights":
            title = f"{r['origin']['city']} → {r['destination']['city']}"
            subtitle = " · ".join(v for v in [r['airline'], r['flight_number']] if v)
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
            available = max(0, r["seats_available"] - used.get(r["id"], 0)) if r["seats_available"] is not None and not self.real else None
            source = "flights.json"
        elif domain == "shopping":
            title = r["name"].get(lang) or r["name"].get("az") or r["name"].get("ru") or r["name"].get("en")
            subtitle = r["brand"]
            desc = (
                r["description"]
                if lang == "en"
                else (r.get("descriptions", {}).get(lang) or r.get("description") if self.real else PRODUCT_DESCRIPTIONS[r["id"]][0 if lang == "az" else 1])
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
                ("language", ", ".join(r.get("languages", [])) or r["movie"]["language"]),
                ("rating", r["movie"]["rating"]),
                ("age", r["movie"]["age_rating"]),
                ("genre", ", ".join(r["movie"]["genre"])),
                ("address", r["cinema"]["address"]),
            ]:
                f(label, value)
            available = max(0, r["seats_available"] - used.get(r["id"], 0)) if r["seats_available"] is not None and not self.real else None
            source = "showtimes.json + movies.json + cinemas.json"
        card = {
            "kind": domain,
            "id": r["id"],
            "title": title,
            "subtitle": subtitle,
            "price": r["price_azn"],
            "available": available,
            "fields": fields,
            "source": source,
        }
        if self.real:
            collected = datetime.fromisoformat(r["fetched_at"])
            expired = False
            if domain == "cinema":
                expired = datetime.fromisoformat(r["start_local"]) < self.clock()
            elif domain == "flights":
                start = r.get("departure_utc")
                expired = datetime.fromisoformat(start) < self.clock() if start else r["departure_local"][:10] < self.today().isoformat()
            card.update(
                source=r.get("source") or "cinemastercard.az",
                source_url=public_url(r.get("search_url") or r.get("booking_url") or r.get("url") or r.get("source_url")),
                fetched_at=r["fetched_at"], snapshot=True,
                stale=(self.clock() - collected).total_seconds() > 86400,
                expired=expired, price_conflict=bool(r.get("price_conflict")),
                price_observations=r.get("price_observations", []),
                availability="listed_in_stock" if domain == "shopping" and r.get("in_stock") is True else "out_of_stock" if domain == "shopping" and r.get("in_stock") is False else "unknown",
                action="add_to_list" if domain == "shopping" else "save_plan",
                provider_cached=bool(r.get('provider_cached')),
                price_scope=r.get("price_scope", "item_snapshot"),
                content_language=(lang if r["name"].get(lang) else ("az" if r["name"].get("az") else "ru")) if domain == "shopping" else r["movie"].get("content_language", "az") if domain == "cinema" else None,
            )
            if domain == "flights":
                f("trip_type", r.get("trip_type"))
                if r.get("return_date"):
                    f("return_date", r["return_date"])
                if r.get("nearby_airport_search"):
                    card["nearby_airport_search"] = True
            if (domain == "shopping" and r.get("image_files")) or (domain == "cinema" and r["movie"].get("poster_file")):
                card["image_url"] = "/api/catalogue/images/" + r["id"]
            if hasattr(getattr(self.repos[domain], 'dataset', None), 'path'):
                from .localization import localize_card
                card = localize_card(card, r, domain, lang)
        return card

    def cart_total(self, state):
        total = 0
        for pid, qty in state["cart"].items():
            product = self.repos["shopping"].get(pid)
            if product:
                if product["price_azn"] is None:
                    return None
                total += product["price_azn"] * qty
            else:
                return None
        return round(total, 2)

    def total_text(self, state):
        total = self.cart_total(state)
        return tr("unknown", state["language"]) if total is None else f"{total:.2f}"

    def movie_card(self, movie, lang):
        card = {
            "kind": "cinema", "id": movie["id"], "title": movie["title"],
            "subtitle": tr("movie_without_sessions", lang), "price": None,
            "available": None, "availability": "unknown", "action": "source",
            "snapshot": True, "source": "cinemastercard.az",
            "content_language": movie.get("content_language", "az"),
            "source_url": public_url(movie.get("source_url")), "fetched_at": movie["fetched_at"],
            "stale": (self.clock() - datetime.fromisoformat(movie["fetched_at"])).total_seconds() > 86400,
            "fields": [{"label": key, "value": val} for key, val in [
                ("genre", ", ".join(movie["genre"])), ("duration", movie["duration_min"]),
                ("age", movie["age_rating"]), ("description", movie.get("synopsis")),
            ]],
        }
        if movie.get("poster_file"):
            card["image_url"] = "/api/catalogue/images/" + movie["id"]
        return card

    def respond(self, text, old_state, used, plan=None, *, language=None):
        state = copy.deepcopy(old_state)
        # An explicit selector choice takes priority over input/model detection.
        lang = language or nlu.language(text, state["language"])
        state["language"] = lang
        route = self.route(text, state)
        unclear_fragment = route["reason"] == "unclear keyword fragment"
        malformed_fragment = route['reason'] == 'malformed numeric fragment'
        if plan and not unclear_fragment and not malformed_fragment and route['reason'] != 'unsupported request':
            route = {
                "category": plan.category,
                "domains": [i.domain for i in plan.intents],
                "engine": getattr(plan, '_provider', 'ai'),
                "reason": "validated structured plan",
            }
            lang = language or plan.language
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
            if unclear_fragment:
                key = "unclear_request"
            if malformed_fragment:
                key = 'malformed_request'
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
        from .search_text import result_request
        lang = state["language"]
        repo = self.repos[domain]
        ds = state["domains"][domain]
        t = nlu.normalize(text)
        act = nlu.action(text, domain)
        filters = nlu.parse_filters(text, domain, self.today())
        qty = nlu.quantity(text)
        ids = nlu.selected_ids(text, domain, ds["results"], repo)
        if intent:
            act = intent.action
            filters = intent.filters.model_dump(exclude_none=True)
            qty = intent.quantity
            # Model-chosen IDs must have appeared in the request or recent results.
            ids = [i for i in intent.ids if i in ds["results"] or i.lower() in t]
        if self.real:
            if domain == "cinema" and re.fullmatch(r"M\d{3}", filters.get("movie_id", "")):
                filters["query"] = nlu.MOVIE_TITLES[int(filters.pop("movie_id")[1:]) - 1]
            if domain == "cinema" and re.fullmatch(r"C\d{3}", filters.get("cinema_id", "")):
                # Mock venue IDs cannot select real venues. Resolve the name
                # against the snapshot, or leave an explicit unmatched filter.
                filters["cinema_id"] = "unknown-source-venue"
            if hasattr(repo, "hints"):
                hints = repo.hints(text)
                filters.update(hints)
                if "movie_id" in hints or (hints.get("brand") and nlu.normalize(filters.get("query", "")) == nlu.normalize(hints["brand"])):
                    filters.pop("query", None)
            if domain == "flights":
                if nlu.has(t, ["round trip", "round-trip", "return flight", "gedis donus", "туда и обратно"]):
                    filters["trip_type"] = "round_trip"
                elif nlu.has(t, ["one way", "one-way", "tek istiqamet", "в одну сторону"]):
                    filters["trip_type"] = "one_way"
                    filters.pop("return_date", None)
                    ds["filters"].pop("return_date", None)
                dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", t)
                if filters.get("trip_type") == "round_trip" and len(dates) >= 2:
                    filters["return_date"] = dates[1]
            for prefix, field in [("cm-m-", "movie_id"), ("cm-c-", "cinema_id")]:
                match = re.search(r"\b" + prefix + r"[a-f0-9]{16}\b", t)
                if domain == "cinema" and match:
                    filters[field] = prefix.upper() + match[0][len(prefix):]
        if ids and act == "details":
            filters = {}
        count, distinct_movies, _ = result_request(text, domain)
        if intent and intent.limit and count is None:
            count, distinct_movies = intent.limit, intent.distinct_movies
        next_page = self.real and nlu.has(t, ["show more", "next page", "daha cox", "novbeti sehife", "еще результаты", "следующая страница"])
        if act == 'search' and not next_page:
            ds['page_size'] = count or 20
            ds['distinct_movies'] = distinct_movies
        page_size = ds.get('page_size', 20) if act == 'search' else 20
        if count and act == 'search':
            # A new list request must recover from an old malformed title filter.
            for key in ['query', 'movie_id']:
                if key not in filters:
                    ds['filters'].pop(key, None)
        if self.real and act == "search":
            ds["offset"] = ds.get("offset", 0) + page_size if next_page else 0
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

        if act == 'unsave':
            matches = [r for r in state['reservations'] if r.get('status') == 'saved_local'
                       and r['domain'] == domain and r['item_id'].casefold() in {i.casefold() for i in ids}]
            if len(matches) != 1:
                say('choose_saved_plan')
                return section, events
            state['reservations'].remove(matches[0])
            state['pending'] = None
            say('plan_removed')
            events.append({'type': 'plan_removed', 'domain': domain, 'item_id': matches[0]['item_id']})
            return section, events

        def cards(rows):
            if domain == 'cinema' and ds.get('distinct_movies') and act == 'search' and not ids:
                unique = {}
                for row in rows:
                    unique.setdefault(row['movie_id'], row)
                rows = list(unique.values())
            section["total_matches"] = len(rows)
            offset = ds.get("offset", 0) if self.real and act == "search" and not ids else 0
            if self.real and offset >= len(rows):
                offset = ds["offset"] = max(0, ((len(rows) - 1) // page_size) * page_size)
            section["offset"] = offset
            section["has_more"] = self.real and act == "search" and offset + page_size < len(rows)
            visible = rows[offset:offset + page_size] if self.real and act != "cart" else rows
            section["cards"] = [self.card(domain, r, used, lang) for r in visible]

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
                total=self.total_text(state),
            )
            if self.real and state["cart"]:
                say("snapshot_list", total=self.total_text(state))
            return section, events
        if act == "reservations":
            reservations = [r for r in state["reservations"] if r["domain"] == domain]
            section["reservations"] = reservations
            say("saved_plans" if self.real else "reservations", count=len(reservations))
            return section, events
        # A new explicitly named entity starts a new search; returning preserves filters.
        entity_keys = {
            "flights": ["origin", "destination"],
            "shopping": ["query", "category", "brand"],
            "cinema": ["movie_id", "query", "genre"],
        }[domain]
        new_entity = any(
            k in filters and filters[k] != ds["filters"].get(k) for k in entity_keys
        )
        if new_entity:
            ds["filters"] = {}
            ds["selected"] = None
            state["pending"] = None
            # "Cheapest Samsung phones" starts a new shortlist, rather than
            # selecting the cheapest ID from an unrelated previous domain search.
            if act == 'details' and nlu.has(t, ['cheapest', 'cheaper', 'ucuz', 'дешев']):
                act = section['action'] = 'search'
                ids = []
                filters['sort'] = 'price'
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
        elif act in ["reserve", "save", "add", "remove", "details"]:
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
            try:
                rows = repo.search(ds["filters"])
            except OSError:
                say('provider_unavailable')
                ds['results'], ds['selected'] = [], None
                return section, events
        rows = [r for r in rows if r]
        if self.real and domain == "cinema" and not rows and filters.get("movie_id"):
            movie = next((m for m in repo.movies() if m["id"] == filters["movie_id"]), None)
            if movie:
                say("source_booking" if act == "reserve" else "no_snapshot_match")
                section["cards"] = [self.movie_card(movie, lang)]
                ds["results"], ds["selected"], state["pending"] = [], None, None
                return section, events
        if act in ["reserve", "save", "add", "remove"]:
            if len(rows) != 1:
                state["pending"] = {"domain": domain, "action": act, "quantity": qty}
                say('choose_plan' if act == 'save' or (self.real and act == 'reserve') else "choose_reserve" if act == "reserve" else "choose", quantity=qty)
                cards(repo.search(ds["filters"]))
                ds["results"] = [c["id"] for c in section["cards"]]
                return section, events
            r = rows[0]
            item_id = r["id"]
            available = self.card(domain, r, used, lang)["available"]
            if act == 'save' or (self.real and act == "reserve"):
                card = self.card(domain, r, used, lang)
                saved = {'status': 'saved_local', 'domain': domain, 'item_id': item_id,
                         'quantity': qty, 'unit_price': card['price'],
                         'total': round(qty * card['price'], 2) if card['price'] is not None else None,
                         'title': card['title'], 'subtitle': card['subtitle'],
                         'source_url': card.get('source_url'), 'created_at': now()}
                previous = next((x for x in state['reservations'] if x.get('status') == 'saved_local'
                                 and x['domain'] == domain and x['item_id'] == item_id), None)
                if previous:
                    saved['created_at'] = previous['created_at']
                    previous.update(saved)
                else:
                    state['reservations'].append(saved)
                section['reservations'] = [saved]
                say('plan_saved')
                cards(rows)
                state["pending"] = None
                ds['selected'] = item_id
                events.append({'type': 'plan_saved', **saved})
                return section, events
            if act == "remove":
                if item_id not in state["cart"]:
                    say("not_in_cart")
                    return section, events
                remaining = state["cart"][item_id] - qty
                if remaining > 0:
                    state["cart"][item_id] = remaining
                else:
                    state["cart"].pop(item_id)
                say("removed", total=self.total_text(state))
                events.append(
                    {"type": "cart_removed", "item_id": item_id, "quantity": qty}
                )
            elif act == "add":
                current = state["cart"].get(item_id, 0)
                if self.real and r.get("in_stock") is False:
                    say("unavailable", available=0)
                    cards(rows)
                    return section, events
                if available is not None and current + qty > available:
                    say("unavailable", available=max(0, available - current))
                    cards(rows)
                    return section, events
                state["cart"][item_id] = current + qty
                say("saved_to_list" if self.real else "added", quantity=qty, total=self.total_text(state))
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
            say("details" if act == "details" or ids else "found", count=section['total_matches'])
            if act != "details" and not ids:
                ds["results"] = [c["id"] for c in section["cards"]]
            if not ds["results"]:
                ds["results"] = [c["id"] for c in section["cards"]]
            if len(rows) == 1:
                ds["selected"] = rows[0]["id"]
        else:
            say(("no_saved_product" if domain == 'shopping' else "no_snapshot_match") if self.real else "no_match")
            ds["results"] = []
            ds["selected"] = None
        return section, events
