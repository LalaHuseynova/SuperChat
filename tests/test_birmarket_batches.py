import json
from types import SimpleNamespace

import pytest

from scripts.expand_birmarket import expand


def test_batches_publish_incrementally_and_resume_without_recollecting():
    rows = [{'category': 'phones'}] * 3 + [{'category': 'audio'}]
    database = SimpleNamespace(records=lambda _: rows)
    calls = []
    def refresh(db, source, **kwargs):
        assert source == 'birmarket' and kwargs['expand'] and kwargs['browser']
        mapping = json.loads(kwargs['categories_file'].read_text())
        category = next(iter(mapping))
        before = sum(r['category'] == category for r in rows)
        calls.append((category, kwargs['per_category']))
        rows.extend({'category': category} for _ in range(kwargs['per_category'] - before))
        return True
    assert expand(database, {'phones': '/categories/3-phones', 'audio': '/categories/6-audio'},
                  target=5, batch_size=2, browser=True, refresh=refresh)
    assert calls == [('phones', 5), ('audio', 3), ('audio', 5)]
    assert len(rows) == 10
    calls.clear()
    assert expand(database, {'phones': '/categories/3-phones'}, target=5, refresh=refresh)
    assert calls == []


def test_failure_stops_later_requests_and_keeps_previous_batch():
    rows = []
    calls = []
    def refresh(db, source, **kwargs):
        calls.append(json.loads(kwargs['categories_file'].read_text()))
        if len(calls) == 2:
            return False
        rows.extend([{'category': 'phones'}] * 2)
        return True
    database = SimpleNamespace(records=lambda _: rows)
    assert not expand(database, {'phones': '/categories/3-phones', 'audio': '/categories/6-audio'},
                      target=5, batch_size=2, refresh=refresh)
    assert len(calls) == 2 and len(rows) == 2


def test_exhausted_category_does_not_loop():
    calls = []
    database = SimpleNamespace(records=lambda _: [])
    def refresh(*args, **kwargs):
        calls.append(kwargs)
        return True
    assert expand(database, {'phones': '/categories/3-phones'}, refresh=refresh)
    assert len(calls) == 1


@pytest.mark.parametrize('kwargs', [{'target': 0}, {'batch_size': 0}, {'pages': 0}, {'pages': 101}])
def test_invalid_limits_rejected_before_collection(kwargs):
    with pytest.raises(ValueError):
        expand(None, {'phones': '/categories/3-phones'}, **kwargs)
