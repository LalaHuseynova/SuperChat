import json
import logging

import httpx
import pytest
from superchat.database import CatalogueDatabase
from superchat.travelpayouts import TravelpayoutsRepository, ProviderUnavailable


def fare(**updates):
    return {'origin': 'BAK', 'destination': 'IST', 'price': 123.45,
            'airline': 'J2', 'flight_number': 75, 'departure_at': '2026-11-06T10:00:00+04:00',
            'transfers': 0, 'duration': 180, 'duration_to': 180,
            'link': '/search/BAK0611IST1', **updates}


def repository(tmp_path, handler):
    return TravelpayoutsRepository(CatalogueDatabase(tmp_path/'catalogue.sqlite3', tmp_path),
                                  'test-token-private', httpx.Client(transport=httpx.MockTransport(handler)))


def test_auth_cache_mapping_and_followup(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        assert request.headers['X-Access-Token'] == 'test-token-private'
        assert 'test-token' not in str(request.url)
        assert request.url.params['currency'] == 'azn'
        return httpx.Response(200, json={'success': True, 'currency': 'azn', 'data': [fare()]})
    r = repository(tmp_path, handler)
    query = {'origin': 'Baku', 'destination': 'Istanbul', 'date': '2026-11-06'}
    a, b = r.search(query), r.search(query)
    assert a == b and len(requests) == 1
    row = a[0]
    assert row['price_azn'] == 123.45 and row['seats_available'] is None and row['arrival_local'] is None
    assert row['provider_cached'] and row['search_url'].startswith('https://www.aviasales.com/')
    assert r.get(row['id']) == row
    assert r.search({'destination': 'Atlantis'}) == []


def test_currency_failure_is_not_a_false_azn_price(tmp_path):
    r = repository(tmp_path, lambda _: httpx.Response(200, json={'success': True, 'currency': 'rub', 'data': [fare()]}))
    with pytest.raises(ProviderUnavailable):
        r.search({'destination': 'Istanbul'})
    assert not r.all()


def test_429_backoff_survives_next_request_and_logs_no_secret(tmp_path, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={'Retry-After': '3600'})
    r = repository(tmp_path, handler)
    with caplog.at_level(logging.INFO):
        for _ in range(2):
            with pytest.raises(ProviderUnavailable):
                r.search({'destination': 'Istanbul'})
    assert len(calls) == 1
    assert 'test-token-private' not in caplog.text


def test_transient_error_retries_once_empty_is_valid(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls)==1 else httpx.Response(200, json={'success': True, 'currency': 'azn', 'data': []})
    assert repository(tmp_path, handler).search({'destination': 'Istanbul'}) == []
    assert len(calls) == 2


def test_pagination_and_return_total(tmp_path):
    pages = []
    def handler(request):
        page = int(request.url.params['page']); pages.append(page)
        assert request.url.params['one_way'] == 'false'
        rows = [fare(flight_number=n, return_at='2026-11-12T12:00:00+03:00') for n in range(100)] if page == 1 else []
        return httpx.Response(200, json={'success': True, 'currency': 'azn', 'data': rows})
    rows = repository(tmp_path, handler).search({'destination': 'Istanbul', 'trip_type': 'round_trip', 'return_date': '2026-11-12'})
    assert pages == [1, 2] and len(rows) == 100
    assert {r['price_scope'] for r in rows} == {'entire_round_trip'}
    assert all(r['return_date'] == '2026-11-12' for r in rows)


def test_auth_failure_never_retried(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(401)
    with pytest.raises(ProviderUnavailable):
        repository(tmp_path, handler).search({'destination': 'Istanbul'})
    assert len(calls) == 1
