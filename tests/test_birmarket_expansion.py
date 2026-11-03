"""Bounded expansion, pagination and incomplete-run handling with fixture pages."""
import copy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from bs4 import BeautifulSoup

from superchat.config import REAL_DATA_DIR, ROOT
from superchat.refresh import collection_limits


@pytest.fixture
def scraper(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'preparation_dataset'))
    return importlib.import_module('birmarket_scraper')


def test_limits_are_configurable_and_bounded(monkeypatch):
    monkeypatch.delenv('BIRMARKET_PER_CATEGORY', raising=False)
    monkeypatch.delenv('BIRMARKET_PAGES', raising=False)
    assert collection_limits() == (100, 10)
    monkeypatch.setenv('BIRMARKET_PER_CATEGORY', '150')
    monkeypatch.setenv('BIRMARKET_PAGES', '15')
    assert collection_limits() == (150, 15)
    assert collection_limits(0, 20) == (0, 20)
    for limits in [(-1, 5), (10, 0), (1001, 1), (100, 101)]:
        with pytest.raises(ValueError):
            collection_limits(*limits)


def test_pagination_keeps_extra_query_parameters_but_rejects_external_links(scraper):
    soup = BeautifulSoup('<a href="/categories/3-phones?sort=popular&amp;page=2">Next</a>', 'html.parser')
    assert scraper.has_next_page(soup, '/categories/3-phones', 1)
    assert not scraper.has_next_page(soup, '/categories/3-phones', 2)
    for href in ['https://unrelated.example/categories/3-phones?page=2', '/categories/4-watches?page=2']:
        soup = BeautifulSoup(f'<a href="{href}">Next</a>', 'html.parser')
        assert not scraper.has_next_page(soup, '/categories/3-phones', 1)


@pytest.mark.parametrize('blocked', [False, True])
@pytest.mark.parametrize('retain_existing', [False, True])
def test_expansion_collects_beyond_twenty_and_accepts_smaller_complete_category(scraper, monkeypatch, tmp_path, blocked, retain_existing):
    original = json.loads((REAL_DATA_DIR / 'birmarket/products.json').read_text())[0]
    class Client:
        def __init__(self, delay):
            pass
        def get(self, url, **kwargs):
            if '/categories/' in url:
                page = int(parse_qs(urlsplit(url).query)['page'][0])
                if blocked and page == 2:
                    raise scraper.FetchBlocked('HTTP 403: fixture')
                ids = range(1, 21) if page == 1 else range(21, 26)
                html = ''.join(f'<a data-info="product-item-link" href="/product/{i}-phone"><span data-info="product-item-title">Phone {i}</span><span data-info="item-desc-price-new">10₼</span></a>' for i in ids)
                if page == 1:
                    html += '<a href="/categories/3-phones?sort=popular&amp;page=2">Next</a>'
                return SimpleNamespace(text=html, url=url)
            return SimpleNamespace(text='', url=url)
        def close(self):
            pass
    def parse(html, url, category, fetched):
        product = copy.deepcopy(original)
        product.update(id='BM-' + urlsplit(url).path.split('/')[2].split('-')[0], category=category,
                       fetched_at=fetched, url=url, variants=[], images=[], data_warnings=[])
        return product, {}
    monkeypatch.setattr(scraper, 'Client', Client)
    monkeypatch.setattr(scraper, 'parse_product', parse)
    existing = None
    if retain_existing:
        retained = copy.deepcopy(original)
        retained.update(id='BM-1', category='phones', variants=[])
        existing = tmp_path / 'existing.json'
        existing.write_text(json.dumps([retained]))
    result = scraper.scrape_catalog({'phones':'/categories/3-phones'}, per_category=100, pages=10,
                                   output=tmp_path, russian=False, existing_products=existing)
    if retain_existing:
        assert result['products'][0]['fetched_at'] == original['fetched_at']
        assert result['products'][0]['image_files'] == original['image_files']
        assert len({p['id'] for p in result['products']}) == len(result['products'])
        assert result['manifest']['retained_product_count'] == 1
    manifest = result['manifest']
    assert manifest['product_count'] == (20 if blocked else 25)
    assert manifest['coverage'] == ('partial' if blocked else 'configured_sample_collected')
    assert manifest['stopped_by_site'] is blocked
    if not blocked:
        assert manifest['pages_collected_by_category'] == {'phones':2}
        assert manifest['category_stop_reasons'] == {'phones':'end_of_category'}


@pytest.mark.parametrize('repeat_page', [False, True])
def test_incremental_expansion_traverses_retained_pages_but_rejects_repeated_page(scraper, monkeypatch, tmp_path, repeat_page):
    original = json.loads((REAL_DATA_DIR / 'birmarket/products.json').read_text())[0]
    def record(i):
        row = copy.deepcopy(original)
        row.update(id=f'BM-{i}', category='phones', variants=[], images=[], image_files=[])
        return row
    existing = tmp_path / 'existing.json'
    existing.write_text(json.dumps([record(1), record(2)]))
    fetched = []
    class Client:
        def __init__(self, delay):
            pass
        def get(self, url, **kwargs):
            if '/categories/' in url:
                page = int(parse_qs(urlsplit(url).query)['page'][0])
                fetched.append(page)
                item = 1 if repeat_page else page
                html = f'<a data-info="product-item-link" href="/product/{item}-phone"><span data-info="product-item-title">Phone {item}</span><span data-info="item-desc-price-new">10₼</span></a>'
                if page < 3:
                    html += f'<a href="/categories/3-phones?page={page+1}">Next</a>'
                return SimpleNamespace(text=html, url=url)
            return SimpleNamespace(text='', url=url)
        def close(self):
            pass
    def parse(html, url, category, fetched):
        return record(int(urlsplit(url).path.split('/')[2].split('-')[0])), {}
    monkeypatch.setattr(scraper, 'Client', Client)
    monkeypatch.setattr(scraper, 'parse_product', parse)
    result = scraper.scrape_catalog({'phones': '/categories/3-phones'}, per_category=3, pages=5,
                                   output=tmp_path, russian=False, existing_products=existing)
    assert fetched == ([1, 2] if repeat_page else [1, 2, 3])
    assert len(result['products']) == (2 if repeat_page else 3)
    assert result['manifest']['coverage'] == ('partial' if repeat_page else 'configured_sample_collected')


def test_detail_discovery_does_not_require_category_card_price_or_name(scraper):
    html = '<a data-info="product-item-link" href="/product/123-laptop?ref=category"></a>'
    rows, _ = scraper.parse_products(html, discovery_only=True)
    assert rows == [{'url': 'https://birmarket.az/product/123-laptop'}]
    with pytest.raises(scraper.ScraperError):
        scraper.parse_products(html)
    for url in ['https://unrelated.example/product/123-laptop', '/product/not-an-id', '/categories/123-laptop']:
        with pytest.raises(scraper.ScraperError):
            scraper.parse_products(f'<a data-info="product-item-link" href="{url}"></a>', discovery_only=True)
