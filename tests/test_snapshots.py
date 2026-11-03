import copy
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from superchat.app import create_app
from superchat.config import REAL_DATA_DIR
from superchat.engine import Engine
from superchat.snapshots import SnapshotDataset, SnapshotError, TABLES, repositories
from superchat.store import initial_state


def clock():
    return datetime(2026, 11, 2, 12, tzinfo=ZoneInfo('Asia/Baku'))


@pytest.fixture
def dataset():
    return SnapshotDataset(REAL_DATA_DIR)


@pytest.fixture
def real_engine(dataset):
    return Engine(REAL_DATA_DIR, repositories(dataset), clock=clock)


@pytest.fixture
def real_client(tmp_path, offline):
    return TestClient(create_app(tmp_path / 'logs', provider=offline,
                                data_mode='snapshot', real_data_dir=REAL_DATA_DIR, clock=clock))


@pytest.mark.parametrize('query', [
    'Show me headphones under 100 AZN', '100 manatdan ucuz simsiz qulaqlıq',
    'Беспроводные наушники до 100 AZN', 'Show Samsung phones', 'Show iPhone',
])
def test_real_multilingual_products_without_english_names(real_engine, query):
    reply, _, _ = real_engine.respond(query, initial_state(), {}, language='en')
    cards = reply['sections'][0]['cards']
    assert cards and all(c['id'].startswith('BM-') for c in cards)
    assert all(c['title'] and c['available'] is None for c in cards)
    assert all(c['snapshot'] and c['source_url'].startswith('https://birmarket.az/') for c in cards)
    assert all(c['content_language'] == 'az' for c in cards)
    if 'Samsung' in query:
        assert all(c['subtitle'] == 'Samsung' for c in cards)


def test_null_ratings_colors_and_prices_do_not_crash(dataset):
    repo = repositories(dataset)['shopping']
    assert repo.search({'sort': 'rating'})[-1]['rating'] is None
    assert repo.search({'color': 'black'})
    row = dataset.tables['products'][0]
    row['price_azn'] = None
    assert row['id'] not in [p['id'] for p in repo.search({'max_price': 100})]
    assert repo.search({'sort': 'price'})[-1]['id'] == row['id']


def test_unknown_stock_supports_local_list_but_no_order(real_engine):
    reply, state, _ = real_engine.respond('Show headphones', initial_state(), {})
    pid = reply['sections'][0]['cards'][0]['id']
    reply, state, actions = real_engine.respond(f'Add two {pid} to cart', state, {}, language='en')
    assert state['cart'] == {pid: 2}
    assert 'No order was placed' in reply['sections'][0]['text']
    assert all(a['type'] == 'cart_added' for a in actions)
    reply, state, _ = real_engine.respond(f'Remove {pid} from cart', state, {})
    assert state['cart'] == {pid: 1}


@pytest.mark.parametrize('question', ['Flights from Baku to Istanbul', 'What is playing tonight?'])
def test_snapshot_cannot_create_supplier_reservation(real_engine, question):
    reply, state, _ = real_engine.respond(question, initial_state(), {})
    card = reply['sections'][0]['cards'][0]
    reply, state, actions = real_engine.respond(f"Reserve {card['id']}", state, {}, language='en')
    assert actions[0]['type'] == 'plan_saved'
    assert state['reservations'][0]['status'] == 'saved_local'
    assert 'code' not in state['reservations'][0]
    assert 'not a confirmed booking' in reply['sections'][0]['text']
    assert reply['sections'][0]['cards'][0]['source_url']
    assert card['available'] is None and card['action'] == 'save_plan'


def test_fare_scopes_never_mix(real_engine):
    reply, state, _ = real_engine.respond('Flights from Baku to Istanbul', initial_state(), {})
    assert {c['price_scope'] for c in reply['sections'][0]['cards']} == {'entire_one_way_itinerary'}
    reply, state, _ = real_engine.respond('Round trip flights from Baku to Istanbul', state, {})
    assert {c['price_scope'] for c in reply['sections'][0]['cards']} == {'entire_round_trip'}
    state['domains']['flights']['filters']['return_date'] = '2026-12-01'
    reply, state, _ = real_engine.respond('One way flights from Baku to Istanbul', state, {})
    assert {c['price_scope'] for c in reply['sections'][0]['cards']} == {'entire_one_way_itinerary'}
    assert 'return_date' not in state['domains']['flights']['filters']


def test_cinema_source_conflicts_and_real_ids(real_engine, dataset):
    row = next(r for r in dataset.tables['showtimes'] if r['price_conflict'])
    reply, _, _ = real_engine.respond(row['id'], initial_state(), {})
    card = reply['sections'][0]['cards'][0]
    assert card['price_conflict'] and len({p['price_azn'] for p in card['price_observations']}) > 1
    assert card['price'] == row['price_azn'] and card['available'] is None


def test_cinema_genre_language_and_title_resolution(real_engine):
    reply, _, _ = real_engine.respond('Russian comedy films tomorrow', initial_state(), {})
    assert reply['sections'][0]['cards']
    assert reply['sections'][0]['filters']['date'] == '2026-11-03'
    reply, _, _ = real_engine.respond('Showtimes for 44 at Deniz Mall', initial_state(), {})
    assert reply['sections'][0]['cards']
    assert all(c['title'] == '44' and 'Deniz Mall' in c['subtitle'] for c in reply['sections'][0]['cards'])
    reply, _, _ = real_engine.respond('Films rated above 8', initial_state(), {}, language='en')
    assert not reply['sections'][0]['cards'] and 'saved snapshot' in reply['sections'][0]['text']


@pytest.mark.parametrize('text,venue', [
    ('gives me today film in deniz mall', True),
    ("give me today's films", False),
    ("give me today’s films", False),
    ("Could you please give me today's films in Deniz Mall?", True),
    ('recommend me films today in Deniz Mall', True),
    ('list today films Deniz Mall', True),
])
def test_ordinary_cinema_requests_are_not_keyword_fragments(real_engine, text, venue):
    reply, _, actions = real_engine.respond(text, initial_state(), {}, language='en')
    assert reply['route']['category'] == 'cinema'
    section = reply['sections'][0]
    assert section['filters']['date'] == '2026-11-02'
    assert section['cards'] and not actions
    assert all(next(f['value'] for f in c['fields'] if f['label'] == 'date') == '2026-11-02'
               for c in section['cards'])
    if venue:
        assert all('Deniz Mall' in c['subtitle'] for c in section['cards'])


def test_upcoming_movie_details_do_not_invent_showtimes(real_engine, dataset):
    scheduled = {s['movie_id'] for s in dataset.tables['showtimes']}
    movie = next(m for m in dataset.tables['movies'] if m['id'] not in scheduled)
    reply, state, actions = real_engine.respond(f"Showtimes for {movie['title']}", initial_state(), {})
    card = reply['sections'][0]['cards'][0]
    assert card['id'] == movie['id'] and card['price'] is None and card['available'] is None
    assert card['source_url'] and not state['domains']['cinema']['results'] and not actions


def test_real_clock_and_stale_expired_flags(real_engine):
    real_engine.clock = lambda: datetime(2026, 11, 9, 12, tzinfo=ZoneInfo('Asia/Baku'))
    reply, _, _ = real_engine.respond('Movies tonight', initial_state(), {})
    assert reply['sections'][0]['filters']['date'] == '2026-11-09'
    assert not reply['sections'][0]['cards']
    reply, _, _ = real_engine.respond('CM-S-77bae425453e4d25', initial_state(), {})
    assert reply['sections'][0]['cards'][0]['stale'] and reply['sections'][0]['cards'][0]['expired']


def test_mixed_request_and_context_return(real_engine):
    reply, state, _ = real_engine.respond('Flights to Istanbul and a backpack', initial_state(), {})
    assert reply['route']['category'] == 'mixed' and all(s['cards'] for s in reply['sections'])
    earlier = copy.deepcopy(state['domains']['shopping'])
    _, state, _ = real_engine.respond('Movies tonight', state, {})
    reply, state, _ = real_engine.respond('Back to backpacks', state, {})
    assert state['domains']['shopping']['results'] == earlier['results']
    assert state['domains']['shopping']['filters'] == earlier['filters']


def test_visible_results_match_followup_order(real_engine):
    reply, state, _ = real_engine.respond('Movies tomorrow', initial_state(), {})
    section = reply['sections'][0]
    assert section['total_matches'] > len(section['cards']) == 20
    assert state['domains']['cinema']['results'] == [c['id'] for c in section['cards']]
    second = section['cards'][1]['id']
    reply, _, _ = real_engine.respond('The second one', state, {})
    assert reply['sections'][0]['cards'][0]['id'] == second


def test_snapshot_pagination_preserves_filters_and_selection(real_engine):
    reply, state, _ = real_engine.respond('Movies tomorrow', initial_state(), {})
    first = {c['id'] for c in reply['sections'][0]['cards']}
    reply, state, _ = real_engine.respond('Show more cinema', state, {})
    page = reply['sections'][0]
    assert page['offset'] == 20 and page['has_more']
    assert not first.intersection(c['id'] for c in page['cards'])
    assert page['filters']['date'] == '2026-11-03'
    chosen = page['cards'][1]['id']
    reply, state, _ = real_engine.respond('The second one', state, {})
    assert reply['sections'][0]['cards'][0]['id'] == chosen


def test_api_provenance_replay_and_images(real_client):
    cfg = real_client.get('/api/config').json()
    assert cfg['data_mode'] == 'snapshot' and not cfg['mock_data'] and not cfg['supplier_bookings']
    sid = real_client.post('/api/sessions', json={}).json()['id']
    import uuid
    body = {'text': 'Show headphones', 'language': 'en', 'request_id': str(uuid.uuid4())}
    result = real_client.post(f'/api/sessions/{sid}/messages', json=body).json()
    card = result['reply']['sections'][0]['cards'][0]
    picture = real_client.get(card['image_url'])
    assert picture.status_code == 200 and picture.headers['content-type'].startswith('image/')
    replay = real_client.post(f'/api/sessions/{sid}/messages', json=body).json()
    assert replay['replayed'] and replay['reply'] == result['reply']
    log = real_client.get(f'/api/sessions/{sid}/export').text
    turn = json.loads(log.splitlines()[-1])
    assert turn['trace']['snapshot_version'] == cfg['snapshot_version']
    assert turn['trace']['data_mode'] == 'snapshot'
    assert real_client.get('/api/catalogue/images/not-an-item').status_code == 404


def test_logs_do_not_mix_with_mock(tmp_path, offline):
    mock = TestClient(create_app(tmp_path, provider=offline, data_mode='mock'))
    sid = mock.post('/api/sessions', json={}).json()['id']
    real = TestClient(create_app(tmp_path, provider=offline, data_mode='snapshot', real_data_dir=REAL_DATA_DIR))
    assert real.get('/api/sessions').json() == []
    assert real.get(f'/api/sessions/{sid}').status_code == 404
    assert mock.get(f'/api/sessions/{sid}').status_code == 200


def small_source(tmp_path, dataset):
    root = tmp_path / 'source'
    for source in ['birmarket', 'aviasales', 'cinema']:
        run = root / source / 'runs/test'
        run.mkdir(parents=True)
        (root / source / 'manifest.json').write_text(json.dumps({'run_directory': f'{source}/runs/test'}))
    for name, (source, filename, _) in TABLES.items():
        rows = dataset.tables[name]
        rows = rows if name in ['movies', 'cinemas'] else rows[:1]
        (root / source / 'runs/test' / filename).write_text(json.dumps(rows))
    return root


def test_published_snapshot_integrity_and_failed_validation_keeps_active(tmp_path, dataset):
    root = small_source(tmp_path, dataset)
    dest = tmp_path / 'active.json'
    good = SnapshotDataset(root)
    good.publish(dest)
    before = dest.read_bytes()
    assert SnapshotDataset(root, dest).version == good.version
    broken = root / 'birmarket/runs/test/products.json'
    records = json.loads(broken.read_text())
    records[0]['price_azn'] = -5
    broken.write_text(json.dumps(records))
    with pytest.raises(ValueError):
        SnapshotDataset(root).publish(dest)
    assert dest.read_bytes() == before
    with pytest.raises(SnapshotError, match='changed'):
        SnapshotDataset(root, dest)


def test_invalid_relationship_and_path_rejected(tmp_path, dataset):
    root = small_source(tmp_path, dataset)
    path = root / 'cinema/runs/test/showtimes.json'
    records = json.loads(path.read_text())
    records[0]['movie_id'] = 'missing'
    path.write_text(json.dumps(records))
    with pytest.raises(SnapshotError, match='relationship'):
        SnapshotDataset(root)
    manifest = root / 'cinema/manifest.json'
    manifest.write_text(json.dumps({'run_directory': '../../escape'}))
    with pytest.raises(SnapshotError, match='reference'):
        SnapshotDataset(root)
