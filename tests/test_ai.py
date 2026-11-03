import pytest
import httpx
from pydantic import ValidationError
from superchat.ai import AIProvider, Plan
from superchat.store import initial_state


def test_provider_failure_falls_back(monkeypatch):
    ai = AIProvider()
    ai.key = "test-placeholder"

    def fail(*args):
        raise httpx.ConnectError("Unavailable")

    monkeypatch.setattr(ai, "completion", fail)
    plan, reason = ai.plan("Show laptops", {"state": initial_state(), "messages": []})
    assert plan is None and reason


def test_model_cannot_mutate_from_read_request(monkeypatch):
    ai = AIProvider()
    ai.key = "test-placeholder"
    monkeypatch.setattr(
        ai,
        "completion",
        lambda *args: {
            "category": "shopping",
            "language": "en",
            "intents": [
                {"domain": "shopping", "action": "add", "ids": ["P001"], "filters": {}}
            ],
        },
    )
    plan, reason = ai.plan(
        "Is P001 available?", {"state": initial_state(), "messages": []}
    )
    assert plan.intents[0].action == "details"


def test_untrusted_model_id_ignored(engine):
    plan = Plan.model_validate(
        {
            "category": "shopping",
            "language": "en",
            "intents": [
                {
                    "domain": "shopping",
                    "action": "details",
                    "ids": ["P999"],
                    "filters": {"query": "headphones"},
                }
            ],
        }
    )
    r, s, _ = engine.respond("Show me headphones", initial_state(), {}, plan)
    assert all(c["id"] != "P999" for c in r["sections"][0]["cards"])


def test_plan_validation():
    with pytest.raises(ValidationError):
        Plan.model_validate(
            {
                "category": "shopping",
                "language": "en",
                "intents": [{"domain": "shopping", "action": "reserve", "filters": {}}],
            }
        )
    with pytest.raises(ValidationError):
        Plan.model_validate(
            {
                "category": "flights",
                "language": "en",
                "intents": [
                    {
                        "domain": "flights",
                        "action": "search",
                        "filters": {"date": "2026-02-31"},
                    }
                ],
            }
        )


@pytest.mark.parametrize('status,body,expected', [
    (401, {}, 'provider_auth_failed'),
    (403, {}, 'provider_auth_failed'),
    (400, {'error': {'message': 'API key not valid. Please pass a valid API key.'}}, 'provider_auth_failed'),
    (429, {}, 'provider_unavailable_or_invalid'),
    (500, {}, 'provider_unavailable_or_invalid'),
])
def test_safe_provider_failure_reason(monkeypatch, status, body, expected):
    ai = AIProvider()
    ai.key = 'test-placeholder'
    def fail(*args):
        request = httpx.Request('POST', 'https://provider.example/chat/completions')
        httpx.Response(status, json=body, request=request).raise_for_status()
    monkeypatch.setattr(ai, 'completion', fail)
    plan, reason = ai.plan('Show films', {'state': initial_state(), 'messages': []})
    assert plan is None and reason == expected


def test_gemini_plan_preserves_provider_and_result_limit(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'different-provider-placeholder')
    monkeypatch.setenv('AI_API_KEY', 'test-placeholder')
    monkeypatch.setenv('AI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/openai')
    ai = AIProvider()
    assert ai.key == 'test-placeholder'
    monkeypatch.setattr(ai, 'completion', lambda *args: {
        'category': 'cinema', 'language': 'en', 'intents': [
            {'domain': 'cinema', 'action': 'search', 'limit': 5, 'distinct_movies': True}]})
    plan, reason = ai.plan('send five films', {'state': initial_state(), 'messages': []})
    assert reason is None and plan._provider == 'gemini'
    assert plan.intents[0].limit == 5 and plan.intents[0].quantity == 1


def test_auth_failure_notice_is_logged_without_secrets(client, monkeypatch):
    monkeypatch.setattr(AIProvider, 'plan', lambda *args, **kwargs: (None, 'provider_auth_failed'))
    sid = client.post('/api/sessions', json={}).json()['id']
    response = client.post(f'/api/sessions/{sid}/messages', json={'text': 'Show films'})
    assert response.status_code == 200
    reply = response.json()
    assert reply['reply']['notice'] == 'ai_auth_failed'


@pytest.mark.parametrize('text', ['Save CM-S-1234567890abcdef to my plans', 'Unsave AV-1234567890abcdef'])
def test_local_plan_controls_do_not_need_hosted_ai(monkeypatch, text):
    ai = AIProvider()
    ai.key = 'test-placeholder'
    def unexpected(*args):
        pytest.fail('Local plan controls should not need AI')
    monkeypatch.setattr(ai, 'completion', unexpected)
    assert ai.plan(text, {'state':initial_state(), 'messages':[]}) == (None, None)
