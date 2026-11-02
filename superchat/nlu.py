"""Explainable multilingual router and slot parser; no external data lookup."""

import re
from datetime import timedelta, date
from .repositories import normalize
from .config import REFERENCE_DATE

PRODUCTS = {
    "headphones": ["headphone", "qulaqliq", "наушник"],
    "earbuds": ["earbud", "qulaqciq", "вкладыш"],
    "laptop": ["laptop", "notebook", "noutbuk", "ноутбук"],
    "smartphone": ["smartphone", "phone", "smartfon", "telefon", "смартфон", "телефон"],
    "smartwatch": ["smartwatch", "watch", "saat", "часы"],
    "speaker": ["speaker", "dinamik", "колонк"],
    "running shoes": ["shoe", "sneaker", "ayaqqabi", "кроссов", "обув"],
    "backpack": ["backpack", "canta", "рюкзак"],
    "coffee machine": ["coffee machine", "espresso", "qehve", "кофемашин"],
    "board game": ["board game", "stolustu", "настольн"],
}
CATEGORY = {
    "audio": ["audio", "аудио"],
    "computers": ["computer", "komputer", "компьютер"],
    "phones": ["phones"],
    "wearables": ["wearable"],
    "sport": ["sport", "idman", "спорт"],
    "accessories": ["accessor", "aksesuar", "аксессуар"],
    "home": ["home appliance", "meiset", "бытов"],
    "gifts": ["gift", "hediyye", "подар"],
}
GENRES = {
    "sci-fi": ["sci-fi", "sci fi", "science fiction", "fantastik", "фантаст"],
    "comedy": ["comedy", "komedi", "комеди"],
    "horror": ["horror", "qorxu", "ужас"],
    "animation": ["animation", "animasiya", "cizgi", "мульт"],
    "family": ["family", "aile", "семейн"],
    "action": ["action", "doyus", "боевик"],
    "romance": ["romance", "romantik", "романт"],
    "thriller": ["thriller", "triller", "триллер"],
    "drama": ["drama", "драм"],
    "mystery": ["mystery", "sirr", "детектив"],
    "adventure": ["adventure", "macera", "приключен"],
    "crime": ["crime", "cinayet", "криминал"],
}
CITIES = {
    "Baku": ["baku", "baki", "баку", "gyd"],
    "Istanbul": ["istanbul", "истамбул", "стамбул", "ist"],
    "Dubai": ["dubai", "dubay", "дубаи", "дубай", "dxb"],
    "Moscow": ["moscow", "moskva", "москв", "svo"],
    "Tbilisi": ["tbilisi", "тбилиси", "tbs"],
    "Tashkent": ["tashkent", "daskend", "ташкент", "tas"],
    "London": ["london", "лондон"],
    "Paris": ["paris", "paris", "париж"],
    "Ganja": ["ganja", "gence", "гянджа"],
}
WEEKDAYS = [
    ["monday", "bazar ertesi", "понедельник"],
    ["tuesday", "cersenbe axsami", "вторник"],
    ["wednesday", "cersenbe", "сред"],
    ["thursday", "cume axsami", "четверг"],
    ["friday", "cume", "пятниц"],
    ["saturday", "senbe", "суббот"],
    ["sunday", "bazar", "воскресен"],
]
MOVIE_TITLES = [
    "Orbit Zero",
    "The Last Caravan",
    "Laugh Track",
    "Midnight Archive",
    "Paper Kites",
    "Iron Ledger",
    "Spring in Baku",
    "Deep Signal",
]


def has(text, variants):
    return any(re.search(r"(?<!\w)" + re.escape(normalize(w)), text) for w in variants)


def language(text, previous="en"):
    t = normalize(text)
    if has(t, ["in english", "english please"]):
        return "en"
    if has(t, ["по-русски", "на русском"]):
        return "ru"
    if has(t, ["azerbaycanca", "azeri", "azerbaycan dilinde"]):
        return "az"
    if re.search("[а-яА-ЯёЁ]", text):
        return "ru"
    if re.search("[əƏıİğĞşŞçÇüÜöÖ]", text) or has(
        t,
        [
            "salam",
            "mene",
            "ucus",
            "bilet",
            "goster",
            "sabah",
            "cume",
            "senbe",
            "nece",
            "isteyirem",
            "simsiz",
            "qulaqliq",
            "noutbuk",
            "sebet",
            "qiymet",
            "ucuz",
        ],
    ):
        return "az"
    if has(
        t,
        [
            "find",
            "show",
            "the",
            "what",
            "flight",
            "book",
            "hello",
            "under",
            "back",
            "compare",
            "yes",
            "no",
            "please",
            "add",
            "remove",
            "cheap",
            "tonight",
        ],
    ):
        return "en"
    return previous


def parse_date(text):
    t = normalize(text)
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", t)
    if iso:
        try:
            return date.fromisoformat(iso[1]).isoformat()
        except ValueError:
            return "invalid"
    if has(t, ["day after tomorrow", "birisi gun", "послезавтра"]):
        return (REFERENCE_DATE + timedelta(days=2)).isoformat()
    if has(t, ["tomorrow", "sabah", "завтра"]):
        return (REFERENCE_DATE + timedelta(days=1)).isoformat()
    if has(t, ["today", "tonight", "bu gun", "bugun", "bu axsam", "сегодня"]):
        return REFERENCE_DATE.isoformat()
    # Long weekday names must win before their shorter substrings.
    for name, index in sorted(
        [(n, i) for i, ns in enumerate(WEEKDAYS) for n in ns], key=lambda x: -len(x[0])
    ):
        if has(t, [name]):
            offset = (index - REFERENCE_DATE.weekday()) % 7
            if has(t, ["next", "gelecek", "следующ"]):
                offset = offset or 7
            return (REFERENCE_DATE + timedelta(days=offset)).isoformat()
    months = [
        ("january", "yanvar", "январ"),
        ("february", "fevral", "феврал"),
        ("march", "mart", "март"),
        ("april", "aprel", "апрел"),
        ("may", "may", "мая"),
        ("june", "iyun", "июн"),
        ("july", "iyul", "июл"),
        ("august", "avqust", "август"),
        ("september", "sentyabr", "сентябр"),
        ("october", "oktyabr", "октябр"),
        ("november", "noyabr", "ноябр"),
        ("december", "dekabr", "декабр"),
    ]
    for i, names in enumerate(months, 1):
        for n in names:
            match = re.search(r"(\d{1,2})\s+" + n, t) or re.search(
                n + r"\w*\s+(\d{1,2})", t
            )
            if match:
                year = re.search(r"\b(20\d{2})\b", t)
                try:
                    return date(
                        int(year[1]) if year else REFERENCE_DATE.year, i, int(match[1])
                    ).isoformat()
                except ValueError:
                    return "invalid"
    return None


def route(text, state):
    t = normalize(text)
    domains = []
    flight = has(
        t,
        [
            "flight",
            "fly",
            "airline",
            "baggage",
            "airport",
            "aviasales",
            "ucus",
            "teyyare",
            "baqaj",
            "рейс",
            "авиабилет",
            "полет",
            "багаж",
            "авиакомпан",
        ],
    ) or re.search(r"\bf\d{3}\b", t)
    shopping = (
        has(
            t,
            [
                "shop",
                "product",
                "cart",
                "buy",
                "stock",
                "mehsul",
                "sebet",
                "alis",
                "товар",
                "корзин",
                "купить",
                "наличии",
            ],
        )
        or any(has(t, v) for v in list(PRODUCTS.values()) + list(CATEGORY.values()))
        or has(t, ["sonivo", "nexar", "veltra", "stridex", "brewa", "playo"])
        or re.search(r"\bp\d{3}\b", t)
    )
    cinema = (
        has(
            t,
            [
                "cinema",
                "movie",
                "film",
                "showtime",
                "playing",
                "kino",
                "seans",
                "кино",
                "фильм",
                "сеанс",
            ],
        )
        or any(has(t, v) for v in GENRES.values())
        or any(normalize(n) in t for n in MOVIE_TITLES)
        or re.search(r"\b[msc]\d{3}\b", t)
    )
    # A city on its own is a flight request only with directional/travel language.
    if (
        not cinema
        and any(has(t, v) for v in CITIES.values())
        and has(t, ["to ", "from ", " ucun", "ged", "bilet", " в ", "из ", "лет"])
    ):
        flight = True
    if flight:
        domains.append("flights")
    if shopping:
        domains.append("shopping")
    if cinema:
        domains.append("cinema")
    if domains:
        return {
            "category": "mixed" if len(domains) > 1 else domains[0],
            "domains": domains,
            "reason": "explicit domain vocabulary",
            "engine": "rules",
        }
    if has(
        t,
        [
            "weather",
            "hava",
            "погод",
            "politic",
            "president",
            "code",
            "python",
            "recipe",
            "football",
            "bitcoin",
            "siyaset",
            "рецепт",
            "президент",
            "футбол",
        ],
    ):
        return {
            "category": "out_of_scope",
            "domains": [],
            "reason": "unsupported topic",
            "engine": "rules",
        }
    if has(
        t,
        [
            "hello",
            "hi",
            "salam",
            "привет",
            "здравств",
            "help",
            "komek",
            "помощ",
            "thank",
            "sag ol",
            "спасибо",
        ],
    ):
        return {
            "category": "greeting",
            "domains": [],
            "reason": "greeting or help",
            "engine": "rules",
        }
    follow = (
        has(
            t,
            [
                "cheaper",
                "cheapest",
                "expensive",
                "first",
                "second",
                "third",
                "one",
                "it",
                "them",
                "these",
                "those",
                "both",
                "compare",
                "direct",
                "book",
                "reserv",
                "seat",
                "add",
                "remove",
                "clear",
                "more",
                "yes",
                "no",
                "back",
                "show all",
                "earlier",
                "later",
                "under",
                "over",
                "black",
                "white",
                "blue",
                "silver",
                "ucuz",
                "birinci",
                "ikinci",
                "ucuncu",
                "birini",
                "onu",
                "onlar",
                "birbasa",
                "yer",
                "bron",
                "elave",
                "sil",
                "muqayise",
                "qara",
                "ag",
                "mavi",
                "до ",
                "дешев",
                "перв",
                "втор",
                "трет",
                "его",
                "ее",
                "их",
                "оба",
                "сравни",
                "прям",
                "брон",
                "мест",
                "добав",
                "удал",
                "черн",
                "бел",
                "син",
                "да",
                "нет",
            ],
        )
        or parse_date(t)
        or re.fullmatch(r"\d+", t)
    )
    if follow and len(state["active_domains"]) == 1:
        return {
            "category": "follow_up",
            "domains": state["active_domains"][:],
            "reason": "active domain + explicit follow-up",
            "engine": "rules",
        }
    return {
        "category": "ambiguous",
        "domains": [],
        "reason": "no confident single domain",
        "engine": "rules",
    }


def clauses(text, domains):
    if len(domains) < 2:
        return {d: text for d in domains}
    parts = re.split(r"\s+(?:and|also|ve|və|и|а также)\s+|[;\n]", text, flags=re.I)
    assigned = {d: [] for d in domains}
    last = None
    for part in parts:
        ds = route(part, {"active_domains": []})["domains"]
        matches = [d for d in ds if d in domains]
        if matches:
            for d in matches:
                assigned[d].append(part)
            last = matches[-1]
        elif last:
            assigned[last].append(part)
    return {d: " ".join(assigned[d]) or text for d in domains}


def quantity(text):
    t = normalize(text)
    m = re.search(
        r"\b(\d+)\s*(?:seats?|tickets?|items?|pieces?|eded|bilet|yer|мест|билет|штук)",
        t,
    )
    if not m:
        m = re.search(r"(?:add|reserve|book|elave|bron|добавь|забронируй)\s+(\d+)\b", t)
    if m:
        return int(m[1])
    for n, words in [
        (2, ["two", "iki", "два", "две"]),
        (3, ["three", "uc eded", "uc yer", "uc bilet", "три"]),
        (4, ["four", "dord", "четыре"]),
    ]:
        if has(t, words):
            return n
    return 1


def action(text, domain):
    t = normalize(text)
    if has(
        t,
        [
            "how do",
            "how can",
            "how to",
            "can i",
            "could i",
            "what happens if",
            "nece",
            "как",
            "можно ли",
        ],
    ):
        return "details"
    if has(
        t,
        [
            "don't",
            "do not",
            "not yet",
            "alma",
            "elave etme",
            "bron etme",
            "silme",
            "не брониру",
            "не добав",
            "не покуп",
            "не удал",
        ],
    ):
        return "details"
    if domain == "shopping":
        if has(t, ["remove", "delete", "sil", "cixar", "удал", "убер"]):
            return "remove"
        if has(t, ["clear cart", "empty cart", "sebeti temizle", "очисти корзин"]):
            return "clear_cart"
        if has(t, ["add", "buy", "elave", "almaq", "добав", "купить"]):
            return "add"
        if has(t, ["cart", "sebet", "корзин"]):
            return "cart"
    if has(t, ["my reservation", "my booking", "bronlarim", "мои брон"]):
        return "reservations"
    if domain != "shopping" and has(t, ["book", "reserve", "bron", "брон"]):
        return "reserve"
    if has(t, ["compare", "muqayise", "сравн"]):
        return "compare"
    if has(
        t,
        [
            "first",
            "second",
            "third",
            "cheaper",
            "cheapest",
            "the one",
            "that one",
            "birinci",
            "ikinci",
            "ucuncu",
            "ucuz olan",
            "перв",
            "втор",
            "трет",
            "дешев",
            "selected",
            "details",
            "detail",
            "etrafli",
            "подроб",
            "baggage",
            "baqaj",
            "багаж",
        ],
    ):
        return "details"
    return "search"


def parse_filters(text, domain):
    t = normalize(text)
    f = {}
    dt = parse_date(t)
    if dt and domain != "shopping":
        f["date"] = dt
    max_p = re.search(
        r"(?:under|below|less than|up to|maximum|max|budget|до|дешевле|не дороже)\s*(\d+(?:[.,]\d+)?)",
        t,
    )
    if not max_p:
        max_p = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:azn|manat)?\s*(?:-?dan|-?den)?\s*(?:asagi|ucuz|az|qeder)",
            t,
        )
    if max_p and t[max_p.end() : max_p.end() + 1] != ":":
        f["max_price"] = float(max_p[1].replace(",", "."))
    min_p = re.search(r"(?:over|above|at least|minimum|от)\s*(\d+(?:[.,]\d+)?)", t)
    if min_p and not has(t, ["rated", "rating", "reytinq", "рейтинг"]):
        f["min_price"] = float(min_p[1].replace(",", "."))
    range_p = re.search(r"(?:between|от)\s*(\d+)\s*(?:and|to|до|-)\s*(\d+)", t)
    if range_p:
        f.update(min_price=float(range_p[1]), max_price=float(range_p[2]))
    if has(t, ["cheap", "price", "ucuz", "qiymet", "дешев", "цен"]):
        f["sort"] = "price"
    if has(t, ["expensive", "bahali", "дорог"]):
        f.update(sort="price", descending=True)
    if has(t, ["rating", "rated", "reytinq", "рейтинг"]):
        f["sort"] = "rating"
    if domain in ["flights", "cinema"]:
        for k, words in [("after", "after|sonra|после"), ("before", "before|evvel|до")]:
            m = re.search(r"(?:" + words + r")\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
            if m:
                h = int(m[1])
                minute = int(m[2] or 0)
                if m[3] == "pm" and h < 12:
                    h += 12
                if m[3] == "am" and h == 12:
                    h = 0
                if h < 24 and minute < 60:
                    f[k] = f"{h:02}:{minute:02}"
        if has(t, ["morning", "seher", "утром"]):
            f.update(after="00:00", before="11:59")
        if has(t, ["evening", "tonight", "axsam", "вечер"]):
            f["after"] = "18:00"
    if domain == "flights":
        positions = []
        for city, names in CITIES.items():
            hits = [
                m.start()
                for n in names
                for m in re.finditer(r"(?<!\w)" + re.escape(n), t)
            ]
            if hits:
                positions.append((min(hits), city))
        positions.sort()
        if len(positions) >= 2:
            f.update(origin=positions[0][1], destination=positions[1][1])
        elif positions:
            if has(t, ["from", "dan", "den", "из "]) and not has(t, ["to ", " в "]):
                f["origin"] = positions[0][1]
            else:
                f["destination"] = positions[0][1]
        # Preserve unknown explicit destinations so they cannot become a broad match.
        m = re.search(r"\bto\s+([a-z]+)", t)
        if m and m[1] not in [
            "flights",
            "flight",
            "shopping",
            "cinema",
            "movies",
            "headphones",
            "the",
            "a",
        ]:
            known = next(
                (
                    city
                    for city, names in CITIES.items()
                    if any(m[1] == n for n in names)
                ),
                None,
            )
            f["destination"] = known or m[1].title()
        origin_match = re.search(r"\bfrom\s+([a-z]+)", t)
        if origin_match:
            known = next(
                (city for city, names in CITIES.items() if origin_match[1] in names),
                None,
            )
            f["origin"] = known or origin_match[1].title()
        if has(t, ["direct", "nonstop", "non-stop", "birbasa", "прям", "без пересад"]):
            f["max_stops"] = 0
        m = re.search(r"(\d+)\s*(?:stop|пересад)", t)
        if m:
            f["max_stops"] = int(m[1])
        if has(t, ["any stops", "with stops", "layover", "пересадками"]):
            f["max_stops"] = 10
        if has(t, ["sort by stops", "fewest stops"]):
            f["sort"] = "stops"
        if has(t, ["earliest", "departure time", "earlier", "tez", "раньше", "вылету"]):
            f["sort"] = "departure"
        if has(t, ["fastest", "shortest", "duration", "быстр"]):
            f["sort"] = "duration"
        if has(
            t,
            [
                "sort by airline",
                "airline name",
                "aviakompaniyaya gore",
                "по авиакомпании",
            ],
        ):
            f["sort"] = "airline"
        for airline in ["Caspian Air", "Bosphor Air", "SkyBridge", "Azerwings"]:
            if normalize(airline) in t:
                f["airline"] = airline
        for cabin in ["economy", "business"]:
            if cabin in t:
                f["cabin"] = cabin
    if domain == "shopping":
        for query, variants in PRODUCTS.items():
            if has(t, variants):
                f["query"] = query
                break
        for cat, variants in CATEGORY.items():
            if has(t, variants):
                f["category"] = cat
                break
        for brand in ["Sonivo", "Nexar", "Veltra", "Stridex", "Brewa", "Playo"]:
            if normalize(brand) in t:
                f["brand"] = brand
        for color, variants in {
            "black": ["black", "qara", "черн"],
            "white": ["white", "ag", "бел"],
            "silver": ["silver", "gumus", "серебр"],
            "grey": ["grey", "gray", "boz", "серый", "серые"],
            "blue": ["blue", "mavi", "син"],
            "multicolor": ["multicolor", "rengli", "разноцвет"],
        }.items():
            if has(t, variants):
                f["color"] = color
        if has(t, ["in stock", "stokda", "наличии"]):
            f["in_stock"] = True
        if not any(k in f for k in ["query", "category", "brand"]):
            unknown = re.search(
                r"(?:products? (?:called|named)|buy|shop for|search for|find me|show me)\s+(.+)",
                t,
            )
            if unknown and not has(
                t,
                [
                    "cart",
                    "all products",
                    "all items",
                    "cheaper",
                    "second",
                    "first",
                    "under",
                    "products",
                    "sebet",
                    "корзин",
                ],
            ):
                f["query"] = unknown[1].strip(" .?!")
    if domain == "cinema":
        for genre, variants in GENRES.items():
            if has(t, variants):
                f["genre"] = genre
                break
        for i, title in enumerate(MOVIE_TITLES, 1):
            if normalize(title) in t:
                f["movie_id"] = f"M{i:03}"
        for lang, variants in {
            "English": ["english", "ingilis", "английск"],
            "Azerbaijani": ["azerbaijani", "azerbaycan", "азербайджан"],
            "Russian": ["russian", "rus dil", "русск"],
        }.items():
            if has(t, variants):
                f["language"] = lang
        for cid, variants in {
            "C001": ["ganjlik", "genclik", "гянджлик"],
            "C002": ["28 mall", "28 mol"],
            "C003": ["sumgayit", "sumqayit", "сумгаит"],
        }.items():
            if has(t, variants):
                f["cinema_id"] = cid
        m = re.search(
            r"(?:rated|rating|reytinq|рейтинг)\s*(?:above|over|at least|выше|от)?\s*(\d+(?:\.\d+)?)",
            t,
        )
        if m:
            f["min_rating"] = float(m[1])
        m = re.search(r"\b(m\d{3}|c\d{3})\b", t)
        if m:
            f["movie_id" if m[1][0] == "m" else "cinema_id"] = m[1].upper()
    if domain == "cinema" and not any(k in f for k in ["movie_id", "genre"]):
        unknown = re.search(
            r"(?:showtimes for|movie called|film called|film named)\s+([a-z ]+)", t
        )
        if unknown:
            f["query"] = unknown[1].strip()
    return f


def selected_ids(text, domain, result_ids, repository):
    t = normalize(text)
    prefix = {"flights": "f", "shopping": "p", "cinema": "s"}[domain]
    ids = [i.upper() for i in re.findall(r"\b" + prefix + r"\d{3}\b", t)]
    if ids:
        return list(dict.fromkeys(ids))
    ordinals = [
        (["first", "birinci", "перв"], 0),
        (["second", "ikinci", "втор"], 1),
        (["third", "ucuncu", "трет"], 2),
    ]
    for words, index in ordinals:
        if has(t, words):
            if index < len(result_ids):
                ids.append(result_ids[index])
            else:
                return ["INVALID"]
    if ids:
        return ids
    if has(t, ["cheaper", "cheapest", "ucuz", "дешев"]) and result_ids:
        rows = [repository.get(i) for i in result_ids]
        rows = [r for r in rows if r]
        if rows:
            return [min(rows, key=lambda r: r["price_azn"])["id"]]
    return []
