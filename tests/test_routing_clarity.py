import copy
import uuid

import httpx
import pytest

from superchat.ai import AIProvider, Plan
from superchat.store import initial_state


@pytest.mark.parametrize(
    "text,language",
    [
        ("film ticket negativity exam university depression", "en"),
        ("Show me film ticket negativity exam university depression", "en"),
        ("Give me film ticket negativity exam university depression", "en"),
        ("university, film, exam, ticket, depression, negativity", "en"),
        ("flight laptop cinema quantum homework sadness", "en"),
        ("film bilet neqativlik imtahan universitet depressiya", "az"),
        ("фильм билет негатив экзамен университет депрессия", "ru"),
    ],
)
def test_disconnected_keywords_ask_before_searching(engine, text, language):
    before = initial_state(language)
    reply, state, actions = engine.respond(text, before, {})
    assert reply["route"]["category"] == "ambiguous"
    assert not reply["route"]["domains"] and not reply["sections"]
    assert "?" in reply["text"]
    assert not actions and state == before


@pytest.mark.parametrize(
    "text,category",
    [
        ("film tickets", "cinema"),
        ("Headphones and cinema tickets", "mixed"),
        ("A flight, a laptop and a movie", "mixed"),
        ("English sci-fi films this Saturday", "cinema"),
        ("Show me a comedy after my university exam", "cinema"),
        ("I feel depressed after exams. Show me a comedy tonight", "cinema"),
        ("Find me a laptop for university exams", "shopping"),
        ("İmtahandan sonra komediya filmi göstər", "cinema"),
        ("Покажи комедии после экзаменов в университете", "cinema"),
        ("Showtimes for The Unknown University Exam Story", "cinema"),
        ('film called "Negativity Exam University Depression"', "cinema"),
    ],
)
def test_clear_requests_still_search(engine, text, category):
    reply, _, _ = engine.respond(text, initial_state(), {})
    assert reply["route"]["category"] == category
    assert reply["sections"]


def test_clarification_preserves_pending_booking_and_can_recover(engine):
    _, state, _ = engine.respond("Flights to Istanbul on Friday", initial_state(), {})
    _, state, _ = engine.respond("Book two seats", state, {})
    before = copy.deepcopy(state)
    reply, state, actions = engine.respond(
        "F002 film ticket negativity exam university depression", state, {}
    )
    assert reply["route"]["category"] == "ambiguous"
    assert not actions and state == before
    _, state, actions = engine.respond("F002", state, {})
    assert len(actions) == 1
    assert state["reservations"][0]["quantity"] == 2


def test_model_plan_cannot_override_unclear_fragment(engine):
    plan = Plan.model_validate({
        "category": "cinema", "language": "en",
        "intents": [{"domain": "cinema", "action": "reserve", "ids": ["S001"]}],
    })
    before = initial_state()
    reply, state, actions = engine.respond(
        "film ticket negativity exam university depression", before, {}, plan
    )
    assert reply["route"]["category"] == "ambiguous"
    assert not reply["sections"] and not actions and state == before


def test_obvious_fragment_does_not_call_provider(monkeypatch):
    provider = AIProvider()
    provider.key = "test-placeholder"

    def unexpected_call(*args):
        pytest.fail("An obvious keyword fragment should not spend an AI call")

    monkeypatch.setattr(provider, "completion", unexpected_call)
    assert provider.plan(
        "film ticket negativity exam university depression",
        {"state": initial_state(), "messages": []},
    ) == (None, None)


@pytest.mark.parametrize('text', ["give me today's films", 'gives me today film in deniz mall'])
def test_ordinary_cinema_request_reaches_hosted_planner(monkeypatch, text):
    provider = AIProvider()
    provider.key = 'test-placeholder'
    calls = []

    def completion(messages):
        calls.append(messages)
        return {'category': 'cinema', 'language': 'en',
                'intents': [{'domain': 'cinema', 'action': 'search'}]}

    monkeypatch.setattr(provider, 'completion', completion)
    plan, error = provider.plan(text, {'state': initial_state(), 'messages': []})
    assert calls and error is None and plan.category == 'cinema'


def test_provider_failure_still_clarifies(engine, monkeypatch):
    provider = AIProvider()
    provider.key = "test-placeholder"

    def fail(*args):
        raise httpx.ConnectError("Unavailable")

    monkeypatch.setattr(provider, "completion", fail)
    # Check the actual fallback path on an ordinary ambiguous request too.
    text = "Show me something good"
    plan, reason = provider.plan(text, {"state": initial_state(), "messages": []})
    assert plan is None and reason
    reply, _, actions = engine.respond(text, initial_state(), {}, plan)
    assert reply["route"]["category"] == "ambiguous" and not actions


def test_unclear_turn_is_logged_without_replacing_search_context(client):
    sid = client.post("/api/sessions", json={}).json()["id"]

    def send(text):
        response = client.post(
            f"/api/sessions/{sid}/messages",
            json={"text": text, "request_id": str(uuid.uuid4())},
        )
        assert response.status_code == 200
        return response.json()

    first = send("Show me laptops")
    unclear = send("film ticket negativity exam university depression")
    assert unclear["reply"]["route"]["category"] == "ambiguous"
    assert unclear["session"]["state"] == first["session"]["state"]
    reloaded = client.get(f"/api/sessions/{sid}").json()
    assert reloaded["messages"][-1]["route"]["category"] == "ambiguous"
    result = send("The second one")
    assert result["reply"]["sections"][0]["cards"][0]["id"] == "P004"


def test_ticket_without_single_relevant_context_still_clarifies():
    from superchat import nlu
    for domains in [[], ['shopping'], ['flights', 'cinema']]:
        state = initial_state()
        state['active_domains'] = domains
        assert nlu.route('ticket maybe', state)['category'] == 'ambiguous'


@pytest.mark.parametrize('language,text', [
    ('en', '339383994848+ ticket istanbul baku'),
    ('az', '339383994848+ istanbul bakı bilet'),
    ('ru', '339383994848+ билет Стамбул Баку'),
    ('en', 'Show flights 1234567890 * Baku Istanbul'),
])
def test_malformed_numbers_cannot_search_or_override_with_plan(engine, monkeypatch, language, text):
    from superchat.i18n import tr
    _, before, _ = engine.respond('Flights to Istanbul', initial_state(language), {}, language=language)
    plan = Plan.model_validate({'category': 'flights', 'language': language,
        'intents': [{'domain': 'flights', 'action': 'search', 'filters': {'origin': 'Istanbul', 'destination': 'Baku'}}]})
    def no_search(*args):
        pytest.fail('Malformed requests must not query a provider or repository')
    for repo in engine.repos.values():
        monkeypatch.setattr(repo, 'search', no_search)
    reply, state, actions = engine.respond(text, before, {}, plan, language=language)
    assert reply['route']['reason'] == 'malformed numeric fragment'
    assert not reply['sections'] and not actions and state == before
    assert reply['text'] == tr('malformed_request', language)
    provider = AIProvider()
    provider.key = 'test-placeholder'
    monkeypatch.setattr(provider, 'completion', no_search)
    assert provider.plan(text, {'state': before, 'messages': []}) == (None, None)


@pytest.mark.parametrize('text', [
    'iPhone 18 Pro Max', 'Samsung Galaxy S25 Ultra', 'flight 2026-11-03',
    'phones under 1500 AZN', '2 tickets Baku Istanbul', 'Show BM-1234567890',
    'iPhone 17 Pro 256GB', 'Samsung S25+',
])
def test_meaningful_numbers_are_not_malformed(text):
    from superchat import nlu
    assert not nlu.malformed_request(text)
    assert not nlu.unclear_keyword_fragment(text)


def test_phone_name_does_not_hide_unrelated_keyword_fragment(engine):
    reply, _, _ = engine.respond('iphone 18 pro max negativity exam depression', initial_state(), {})
    assert reply['route']['reason'] == 'unclear keyword fragment'
    assert not reply['sections']


@pytest.mark.parametrize('text', [
    'Find Xiaomi Redmi Note 15',
    'Xiaomi Redmi Note 15 telefon göstər',
    'Покажи телефон Xiaomi Redmi Note 15',
])
def test_note_phone_model_is_not_an_unrelated_keyword_fragment(text):
    from superchat import nlu
    assert not nlu.unclear_keyword_fragment(text)
    assert nlu.route(text, initial_state())['domains'] == ['shopping']
    assert nlu.PRODUCT_MODEL.search(text.lower()).group() == 'redmi note 15'


@pytest.mark.parametrize('text', ['Xiaomi Redmi Note 15 telefon göstər', 'Find iPhone 17 phones'])
def test_model_number_before_product_noun_is_not_a_result_count(text):
    from superchat.search_text import result_request
    count, _, cleaned = result_request(text, 'shopping')
    assert count is None
    assert '15' in cleaned or '17' in cleaned


def test_result_count_and_model_number_can_coexist():
    from superchat.search_text import result_request
    count, _, cleaned = result_request('Show 5 phones like Redmi Note 15', 'shopping')
    assert count == 5 and 'note 15' in cleaned
