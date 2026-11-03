"""Browser-mode access checks and collection failure boundaries, without live requests."""
import importlib
import time
from types import SimpleNamespace

import pytest
import requests

from superchat.config import ROOT


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'preparation_dataset'))
    return importlib.import_module('birmarket_browser'), importlib.import_module('birmarket_scraper')


@pytest.mark.parametrize('status,body,content_type,allowed', [
    (200, 'User-agent: *\nAllow: /', 'text/plain', True),
    (404, '', 'text/html', True),
    (200, 'User-agent: *\nDisallow: /product/', 'text/plain', False),
    (200, '<html>Verification required</html>', 'text/html', False),
])
def test_browser_robot_rules_remain_enforced(modules, status, body, content_type, allowed):
    browser, scraper = modules
    client = browser.BrowserClient.__new__(browser.BrowserClient)
    response = requests.Response()
    response.status_code = status
    response._content = body.encode()
    response.headers['Content-Type'] = content_type
    client.get = lambda *args, **kwargs: response
    if allowed:
        client.check_access()
    else:
        with pytest.raises(scraper.FetchBlocked):
            client.check_access()


@pytest.mark.parametrize('status,title', [(403, 'Denied'), (429, 'Too many requests'), (200, 'Just a moment...')])
def test_browser_stops_on_refusal_or_challenge(modules, status, title):
    pytest.importorskip('playwright.sync_api')
    browser, scraper = modules
    client = browser.BrowserClient.__new__(browser.BrowserClient)
    client.delay, client.last = 0, time.monotonic()
    response = SimpleNamespace(status=status, headers={'content-type':'text/html'}, body=lambda: b'<html></html>')
    client.page = SimpleNamespace(goto=lambda *args, **kwargs:response, url='https://birmarket.az/categories/3-phones', title=lambda:title)
    with pytest.raises(scraper.FetchBlocked):
        client.get(client.page.url)


def test_cli_and_browser_share_error_types(modules):
    import runpy
    browser, scraper = modules
    cli = runpy.run_path(str(ROOT / 'preparation_dataset/birmarket_scraper.py'), run_name='scraper_cli_test')
    assert cli['FetchBlocked'] is browser.FetchBlocked is scraper.FetchBlocked
    assert cli['ScraperError'] is browser.ScraperError is scraper.ScraperError


@pytest.mark.parametrize('recovers', [True, False])
def test_temporary_server_errors_have_bounded_retries(modules, monkeypatch, recovers):
    browser, _ = modules
    client = browser.BrowserClient.__new__(browser.BrowserClient)
    attempts = []
    sleeps = []
    def request(*args, **kwargs):
        attempts.append(1)
        if recovers and len(attempts) == 2:
            return 'product page'
        raise browser.TemporaryServerError('HTTP 502')
    client._get_once = request
    monkeypatch.setattr(browser.time, 'sleep', sleeps.append)
    if recovers:
        assert client.get('https://birmarket.az/product/1') == 'product page'
        assert len(attempts) == 2 and sleeps == [2]
    else:
        with pytest.raises(browser.TemporaryServerError):
            client.get('https://birmarket.az/product/1')
        assert len(attempts) == 3 and sleeps == [2, 4]


@pytest.mark.parametrize('resource,navigation,expected', [
    ('image', False, 'abort'), ('image', True, 'continue'),
    ('document', True, 'continue'), ('script', False, 'continue'),
    ('font', False, 'abort'),
])
def test_decorative_assets_skipped_but_product_image_navigation_allowed(modules, resource, navigation, expected):
    browser, _ = modules
    calls = []
    route = SimpleNamespace(request=SimpleNamespace(resource_type=resource, is_navigation_request=lambda: navigation),
                            abort=lambda: calls.append('abort'), continue_=lambda: calls.append('continue'))
    browser.BrowserClient.route_asset(route)
    assert calls == [expected]
