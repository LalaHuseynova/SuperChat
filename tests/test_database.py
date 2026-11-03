import copy
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from superchat.app import create_app
from superchat.config import REAL_DATA_DIR
from superchat.database import CatalogueDatabase
from superchat.engine import Engine
from superchat.i18n import tr
from superchat.refresh import refresh_source
from superchat.snapshots import repositories, SnapshotError
from superchat.store import initial_state


@pytest.fixture
def database(tmp_path):
    db = CatalogueDatabase(tmp_path / 'catalogue.sqlite3', REAL_DATA_DIR)
    db.seed()
    return db


@pytest.fixture
def db_engine(database):
    return Engine(REAL_DATA_DIR, repositories(database), clock=lambda: datetime(2026, 11, 3, 12, tzinfo=ZoneInfo('Asia/Baku')))


def test_atomic_refresh_visible_without_restart_and_pinned_per_turn(database):
    repo = repositories(database)['shopping']
    original = repo.all()[0]
    rows = database.records('products')
    rows[0]['price_azn'] = 1.23
    manifest = database.descriptor['manifests']['birmarket']
    with database.read():
        old_version = database.version
        database.publish({'products': rows}, {'birmarket': manifest})
        assert database.version == old_version
        assert repo.get(original['id'])['price_azn'] == original['price_azn']
    assert database.version != old_version
    assert repo.get(original['id'])['price_azn'] == 1.23
    reopened = CatalogueDatabase(database.path, REAL_DATA_DIR)
    assert reopened.version == database.version


def test_failed_publication_preserves_database(database):
    version = database.version
    rows = database.records('products')
    rows[0]['price_azn'] = -1
    with pytest.raises(ValueError):
        database.publish({'products': rows}, {'birmarket': database.descriptor['manifests']['birmarket']})
    with pytest.raises(SnapshotError):
        database.publish({'movies': []}, {'cinema': {}})
    assert database.version == version


@pytest.mark.parametrize('language,prompt', [
    ('en', 'Show Samsung phones'), ('az', 'Mənə Samsung telefonları göstər'), ('ru', 'Покажи телефоны Samsung'),
    ('en', 'What is playing today in Deniz Mall?'), ('az', 'Bu gün Dəniz Mallda hansı filmlər var?'), ('ru', 'Какие фильмы сегодня в Дениз Молл?'),
    ('en', 'Wireless headphones under 100 AZN'), ('az', '100 manatdan ucuz qulaqlıq göstər'), ('ru', 'Покажи наушники до 100 AZN'),
])
def test_three_languages_and_links(db_engine, language, prompt):
    reply, state, _ = db_engine.respond(prompt, initial_state(language), {}, language=language)
    assert reply['language'] == language
    assert reply['sections'] and reply['sections'][0]['cards']
    for section in reply['sections']:
        for card in section['cards']:
            host = 'birmarket.az' if section['domain'] == 'shopping' else 'cinemastercard.az'
            assert card['source_url'].startswith('https://' + host + '/')
            assert card['price'] is None or card['price'] >= 0
            if section['domain'] == 'shopping' and language == 'en':
                assert card['content_language'] == 'en'
                assert card['source_title']


@pytest.mark.parametrize('language,prompt', [
    ('en', 'Show Samsung Galaxy S999 phones'), ('az', 'Samsung Galaxy S999 telefon göstər'), ('ru', 'Покажи телефоны Samsung Galaxy S999'),
    ('en', 'Show me Titanic films'), ('az', 'Titanic filmini göstər'), ('ru', 'Покажи фильм Титаник'),
    ('en', 'Show products called unicorn'), ('az', 'Mənə unicorn adlı məhsul göstər'), ('ru', 'Покажи товары unicorn'),
    ('en', 'film ticket negativity exam university depression'), ('az', 'film bilet neqativlik imtahan universitet depressiya'), ('ru', 'фильм билет негатив экзамен университет депрессия'),
    ('en', 'Write an essay about movies'), ('az', 'Film haqqında esse yaz'), ('ru', 'Напиши эссе о фильмах'),
    ('en', 'Where is the nearest hospital?'), ('en', 'hiking museum elephant'),
])
def test_irrelevant_and_absent_never_show_random_results(db_engine, language, prompt):
    _, state, _ = db_engine.respond('Show headphones', initial_state(language), {}, language=language)
    reply, _, actions = db_engine.respond(prompt, state, {}, language=language)
    assert reply['language'] == language and not actions
    assert not any(s['cards'] for s in reply['sections'])
    assert reply['text'] or all(s['text'] for s in reply['sections'])


def test_failed_scrape_keeps_good_data_and_logs_category(database, tmp_path):
    database.root = tmp_path / 'sources'
    original = database.version
    def refused(source):
        raise RuntimeError('refused private-details-must-not-be-logged')
    assert refresh_source(database, 'birmarket', access_check=refused) is False
    assert database.version == original
    status = database.status()['refreshes'][0]
    assert status['status'] == 'failed' and 'private' not in status['detail']


@pytest.mark.parametrize('limit,pages,expected', [(None, None, ('100','10')), (150, 15, ('150','15')), (0, 20, ('0','20'))])
@pytest.mark.parametrize('browser', [False, True])
def test_successful_scrape_published_without_modifying_seed(database, tmp_path, monkeypatch, limit, pages, expected, browser):
    monkeypatch.delenv('BIRMARKET_PER_CATEGORY', raising=False)
    monkeypatch.delenv('BIRMARKET_PAGES', raising=False)
    rows = database.records('products')
    rows[0]['price_azn'] = 7
    manifest = copy.deepcopy(database.descriptor['manifests']['birmarket'])
    manifest.update(run_directory='birmarket/runs/test-success', errors=[], coverage='configured_sample_collected')
    database.root = tmp_path / 'new-sources'
    def collect(args, **kwargs):
        assert (args[args.index('--per-category')+1], args[args.index('--pages')+1]) == expected
        assert args[args.index('--max-images')+1] == '1'
        root = Path(args[args.index('--output')+1])
        assert ('--browser' in args) is browser
        if browser:
            retained = json.loads(Path(args[args.index('--existing-products')+1]).read_text())
            assert retained == database.records('products')
        run = root / manifest['run_directory']
        run.mkdir(parents=True)
        for folder in [root / 'birmarket', run]:
            (folder / 'manifest.json').write_text(json.dumps(manifest))
            (folder / 'products.json').write_text(json.dumps(rows))
        assert not any('TOKEN' in k or 'API_KEY' in k for k in kwargs['env'])
        return SimpleNamespace(returncode=0)
    access_calls = []
    assert refresh_source(database, 'birmarket', runner=collect, access_check=access_calls.append,
                          per_category=limit, pages=pages, browser=browser, expand=browser)
    assert access_calls == ([] if browser else ['birmarket'])
    assert database.records('products')[0]['price_azn'] == 7


def test_database_api_and_image_results_are_grounded(database, tmp_path, offline, monkeypatch):
    monkeypatch.delenv('TRAVELPAYOUTS_API_TOKEN', raising=False)
    app = create_app(tmp_path / 'logs', provider=offline, data_mode='database', database_path=database.path,
                     real_data_dir=REAL_DATA_DIR, refresh=False)
    client = TestClient(app)
    sid = client.post('/api/sessions', json={}).json()['id']
    assert client.get('/api/config').json()['data_mode'] == 'database'
    page = client.get('/api/catalogue/products', params={'q': 'smartphone', 'language': 'ru', 'limit': 3}).json()
    assert len(page['items']) == 3 and page['total'] > 3
    assert client.get('/api/catalogue/products?limit=99999').status_code == 400
    first = database.records('products')[0]
    monkeypatch.setattr(app.state.vision, 'search', lambda *args: {'accepted': True, 'label': 'headphones', 'confidence': .95,
        'engine': 'test', 'method': 'image_similarity', 'matches': [{'id': first['id'], 'score': .92}, {'id': 'BM-missing', 'score': .99}]})
    rid = str(uuid.uuid4())
    response = client.post(f'/api/sessions/{sid}/images', data={'request_id': rid, 'language': 'az'}, files={'file': ('test.png', b'placeholder', 'image/png')})
    assert response.status_code == 200
    data = response.json()
    cards = data['reply']['sections'][0]['cards']
    assert [c['id'] for c in cards] == [first['id']]
    assert cards[0]['similarity'] == .92 and data['reply']['language'] == 'az'
    assert data['session']['state']['domains']['shopping']['results'] == [first['id']]
    image = client.get(cards[0]['image_url'])
    assert image.status_code == 200 and image.headers['content-type'].startswith('image/')
    replay = client.post(f'/api/sessions/{sid}/images', data={'request_id': rid, 'language': 'az'}, files={'file': ('test.png', b'placeholder', 'image/png')})
    assert replay.json()['replayed']


def test_language_switch_and_no_match_recovery(db_engine):
    state = initial_state()
    for lang, text in [('en', 'Show Samsung phones'), ('ru', 'Второй, подробнее'), ('az', 'Bu gün Dəniz Mallda filmlər'), ('en', 'Back to Samsung phones')]:
        reply, state, _ = db_engine.respond(text, state, {}, language=lang)
        assert reply['language'] == lang and reply['sections'][0]['cards']


def test_return_to_different_product_does_not_keep_conflicting_filters(db_engine):
    _, state, _ = db_engine.respond('Show Samsung phones', initial_state(), {})
    _, state, _ = db_engine.respond('Movies today', state, {})
    reply, state, _ = db_engine.respond('Back to headphones', state, {})
    assert reply['sections'][0]['cards']
    assert 'brand' not in state['domains']['shopping']['filters']
    assert 'category' not in state['domains']['shopping']['filters']


@pytest.mark.parametrize('language,prompt', [
    ('en', 'send 5 films in deniz mall'),
    ('en', 'send five films in deniz mall'),
    ('az', 'Dəniz Mallda beş film göstər'),
    ('ru', 'Покажи пять фильмов в Дениз Молл'),
])
def test_counted_films_are_distinct_and_paginate(db_engine, language, prompt):
    state = initial_state(language)
    # Recover conversations saved by the earlier parser as well as new ones.
    state['active_domains'] = ['cinema']
    state['domains']['cinema']['filters'] = {'query': 'send five'}
    reply, state, actions = db_engine.respond(prompt, state, {}, language=language)
    section = reply['sections'][0]
    assert reply['route']['domains'] == ['cinema'] and not actions
    assert len(section['cards']) == 5
    titles = {c['title'] for c in section['cards']}
    assert len(titles) == 5
    assert 'query' not in section['filters']
    assert all('Deniz Mall' in c['subtitle'] for c in section['cards'])
    next_page = {'en': 'next page', 'az': 'növbəti səhifə', 'ru': 'следующая страница'}[language]
    reply, _, _ = db_engine.respond(next_page, state, {}, language=language)
    assert len(reply['sections'][0]['cards']) == 5
    assert titles.isdisjoint({c['title'] for c in reply['sections'][0]['cards']})


def test_screenshot_conversation_keeps_topic_then_switches_to_flights(db_engine):
    _, state, _ = db_engine.respond('send five films in deniz mall', initial_state(), {})
    reply, state, actions = db_engine.respond('ticket maybe', state, {})
    assert reply['route']['domains'] == ['cinema'] and not actions
    assert reply['sections'][0]['cards']
    reply, state, actions = db_engine.respond('ticket in baku istanbul', state, {})
    assert reply['route']['domains'] == ['flights'] and not actions
    assert reply['sections'][0]['filters']['origin'] == 'Baku'
    assert reply['sections'][0]['filters']['destination'] == 'Istanbul'
    assert state['active_domains'] == ['flights']


def test_result_count_does_not_select_numeric_movie(db_engine):
    reply, _, _ = db_engine.respond('show 44 films in Deniz Mall', initial_state(), {})
    assert 'movie_id' not in reply['sections'][0]['filters']
    assert len({c['title'] for c in reply['sections'][0]['cards']}) > 1
    reply, _, _ = db_engine.respond('Showtimes for 44 at Deniz Mall', initial_state(), {})
    assert reply['sections'][0]['cards']
    assert all(c['title'] == '44' for c in reply['sections'][0]['cards'])


@pytest.mark.parametrize('language,prompt,query', [
    ('az', 'qirmizi qelem', 'pen'), ('az', 'qırmızı qələm', 'pen'),
    ('en', 'give red pencil', 'pencil'), ('ru', 'красный карандаш', 'pencil'),
])
def test_unsampled_stationery_is_shopping_with_honest_empty_reply(db_engine, language, prompt, query):
    # Existing shopping filters must not turn an absent product into headphones.
    _, state, _ = db_engine.respond('Show headphones', initial_state(language), {}, language=language)
    reply, _, actions = db_engine.respond(prompt, state, {}, language=language)
    assert reply['route']['domains'] == ['shopping']
    section = reply['sections'][0]
    assert section['filters']['query'] == query
    assert section['filters']['color'] == 'red'
    assert section['cards'] == [] and not actions
    assert 'Birmarket' in section['text']
    assert section['text'] == tr('no_saved_product', language)


def test_stationery_matches_only_real_names_and_multilingual_color():
    from superchat.repositories import product_matches, color_key
    pen = {'name': {'az': 'Qırmızı qələm', 'en': None, 'ru': 'Красная ручка'}, 'category': 'stationery'}
    pencil = {'name': {'az': 'Qırmızı karandaş', 'en': None, 'ru': 'Красный карандаш'}, 'category': 'stationery'}
    assert product_matches(pen, 'pen', real=True)
    assert product_matches(pencil, 'pencil', real=True)
    assert not product_matches(pen, 'pencil', real=True)
    assert color_key('qırmızı') == color_key('Красный') == 'red'


def test_iphone_model_search_recovers_after_missing_models(db_engine):
    state = initial_state('en')
    for text in ['iphone 18 pro', 'iphone 18 pro max']:
        reply, state, actions = db_engine.respond(text, state, {}, language='en')
        assert reply['route']['domains'] == ['shopping']
        assert reply['sections'][0]['filters']['query'] == text
        assert reply['sections'][0]['cards'] == [] and not actions
        assert reply['sections'][0]['text'] == tr('no_saved_product', 'en')
    reply, _, _ = db_engine.respond('iphone 17 pro', state, {}, language='en')
    cards = reply['sections'][0]['cards']
    assert cards and all('birmarket.az' in c['source_url'] for c in cards)
    assert all('17 Pro' in c['source_title'] for c in cards)
    assert reply['sections'][0]['filters']['category'] == 'phones'


def test_malformed_request_never_reaches_database_hints(db_engine, monkeypatch):
    def no_lookup(*args):
        pytest.fail('Malformed requests must not resolve catalogue names')
    for repo in db_engine.repos.values():
        if hasattr(repo, 'hints'):
            monkeypatch.setattr(repo, 'hints', no_lookup)
    reply, _, _ = db_engine.respond('339383994848+ ticket istanbul baku', initial_state(), {})
    assert not reply['sections']
    assert reply['route']['reason'] == 'malformed numeric fragment'


@pytest.mark.parametrize('domain,search', [('cinema', 'films in Deniz Mall'), ('flights', 'flights Baku Istanbul')])
@pytest.mark.parametrize('lang', ['en','az','ru'])
def test_saved_plans_are_local_deduplicated_and_removable(db_engine, domain, search, lang, monkeypatch):
    reply, state, _ = db_engine.respond(search, initial_state(lang), {}, language=lang)
    item = reply['sections'][0]['cards'][0]
    save = {'en':f"Save {item['id']} to my plans", 'az':f"{item['id']} planlarda saxla", 'ru':f"Сохрани {item['id']} в планах"}[lang]
    used = {}
    for _ in range(2):
        reply, state, actions = db_engine.respond(save, state, used, language=lang)
        assert actions[0]['type'] == 'plan_saved'
        assert len(state['reservations']) == 1 and not used
        saved = state['reservations'][0]
        assert saved['domain'] == domain and saved['status'] == 'saved_local' and 'code' not in saved
        assert saved['source_url'] == item['source_url'] and saved['title'] == item['title']
    query = {'en':'My saved plans', 'az':'Saxlanılmış planlar', 'ru':'Мои сохранённые планы'}[lang]
    reply, state, _ = db_engine.respond(query, state, used, language=lang)
    assert len(reply['sections'][0]['reservations']) == 1
    # Removing a saved plan still works after its listing disappears from the feed.
    monkeypatch.setattr(db_engine.repos[domain], 'get', lambda _: None)
    remove = {'en':f"Unsave {item['id']}", 'az':f"Saxlanılmış planı sil {item['id']}", 'ru':f"Удали сохранённый план {item['id']}"}[lang]
    reply, state, actions = db_engine.respond(remove, state, used, language=lang)
    assert not state['reservations'] and actions[0]['type'] == 'plan_removed'


def test_saved_plan_survives_api_restart_and_duplicate_request(database, tmp_path, offline):
    from superchat.store import SessionStore
    def app():
        return create_app(tmp_path/'plan-logs', provider=offline, data_mode='database', real_data_dir=REAL_DATA_DIR,
                          database_path=database.path, refresh=False, flight_repository=repositories(database)['flights'])
    client = TestClient(app())
    sid = client.post('/api/sessions',json={}).json()['id']
    first = client.post(f'/api/sessions/{sid}/messages',json={'text':'Films in Deniz Mall'}).json()
    item = first['reply']['sections'][0]['cards'][0]
    payload = {'text':f"Save {item['id']} to my plans", 'request_id':str(uuid.uuid4())}
    for _ in range(2):
        response = client.post(f'/api/sessions/{sid}/messages',json=payload)
        assert response.status_code == 200
        assert len(response.json()['session']['state']['reservations']) == 1
    reopened = TestClient(app())
    saved = reopened.get(f'/api/sessions/{sid}').json()['state']['reservations']
    assert len(saved) == 1 and saved[0]['status'] == 'saved_local'
    assert reopened.app.state.store.inventory() == {}
    fork = reopened.post('/api/sessions',json={'source_id':sid}).json()
    assert fork['state']['reservations'] == []


def test_saved_plan_unknown_price_and_explicit_selection_required(db_engine, monkeypatch):
    reply, state, _ = db_engine.respond('Films in Deniz Mall', initial_state(), {})
    reply, state, actions = db_engine.respond('Save it', state, {})
    assert not state['reservations'] and not actions and state['pending']['action'] == 'save'
    item_id = state['domains']['cinema']['results'][0]
    row = copy.deepcopy(db_engine.repos['cinema'].get(item_id))
    row['price_azn'] = None
    monkeypatch.setattr(db_engine.repos['cinema'], 'get', lambda _: row)
    reply, state, actions = db_engine.respond(item_id, state, {})
    assert state['reservations'][0]['unit_price'] is None
    assert state['reservations'][0]['total'] is None
    assert state['pending'] is None and actions[0]['type'] == 'plan_saved'


def test_failed_collection_preserves_diagnostics_without_publishing(database, tmp_path):
    original = database.version
    database.root = tmp_path / 'sources'
    def collect(args, **kwargs):
        stage = Path(args[args.index('--output') + 1])
        (stage / 'collected.json').write_text('{"partial": true}')
        return SimpleNamespace(returncode=2, stdout='Public product collected', stderr='Incomplete collection')
    assert not refresh_source(database, 'birmarket', runner=collect, access_check=lambda _: None)
    assert database.version == original
    failed = list((database.root / '.failed').iterdir())
    assert len(failed) == 1
    assert (failed[0] / 'collected.json').exists()
    assert (failed[0] / 'scraper.stderr.log').read_text() == 'Incomplete collection'
    assert not list((database.root / '.staging').iterdir())


@pytest.mark.parametrize('language,initial,followup', [
    ('en', 'Show 5 phones', 'Show more'),
    ('az', '5 telefon göstər', 'Daha çox'),
    ('ru', 'Покажи 5 товаров Samsung', 'Еще результаты'),
])
def test_pagination_words_in_catalogue_do_not_replace_filters(database, db_engine, language, initial, followup):
    rows = database.records('products')
    rows[0]['brand'] = 'More'
    rows[0]['name'] = {'en': 'More headphones', 'az': 'More qulaqlıq', 'ru': 'Наушники More'}
    database.publish({'products': rows}, {'birmarket': database.descriptor['manifests']['birmarket']})
    reply, state, _ = db_engine.respond(initial, initial_state(language), {}, language=language)
    first = {c['id'] for s in reply['sections'] for c in s['cards']}
    before = copy.deepcopy(state['domains']['shopping']['filters'])
    reply, state, _ = db_engine.respond(followup, state, {}, language=language)
    second = {c['id'] for s in reply['sections'] for c in s['cards']}
    assert len(first) == 5 and len(second) == 5 and not first & second
    assert state['domains']['shopping']['filters'] == before
    assert state['domains']['shopping']['offset'] == 5
