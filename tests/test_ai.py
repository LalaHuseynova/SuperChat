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
