"""Official Aviasales Data API adapter: cached fares, never live reservations.

Contract: https://support.travelpayouts.com/hc/en-us/articles/203956163
"""
import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx
from .catalogue import Flight
from .repositories import JsonFlightRepository, normalize

log = logging.getLogger(__name__)
API = 'https://api.travelpayouts.com/aviasales/v3/prices_for_dates'
CITIES = {'Baku': 'BAK', 'Istanbul': 'IST', 'Dubai': 'DXB', 'Moscow': 'MOW',
          'Tbilisi': 'TBS', 'Tashkent': 'TAS', 'London': 'LON', 'Paris': 'PAR', 'Ganja': 'GNJ'}
CITY_ALIASES = {'GYD': 'BAK', 'SVO': 'MOW', 'DME': 'MOW', 'VKO': 'MOW'}


class ProviderUnavailable(OSError):
    pass


def code(value):
    for city, iata in CITIES.items():
        if normalize(value) == normalize(city):
            return iata
    value = (value or '').upper()
    if len(value) == 3 and value.isascii() and value.isalpha():
        return CITY_ALIASES.get(value, value)
    return None


class TravelpayoutsRepository(JsonFlightRepository):
    mode = 'api'

    def __init__(self, database, token, client=None, ttl=900):
        self.database, self.token = database, token
        self.client, self.ttl = client, ttl
        self.lock = threading.Lock()
        with database.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS flight_offers(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def get(self, item_id):
        with self.database.connect() as db:
            row = db.execute('SELECT payload FROM flight_offers WHERE id=? COLLATE NOCASE', (item_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self):
        # Search uses a specific provider response, never combines unrelated cached searches.
        with self.database.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT payload FROM flight_offers')]

    def fetch(self, params):
        key = 'aviasales:' + json.dumps(params, sort_keys=True)
        with self.lock, self.database.connect() as db:
            cached = db.execute('SELECT expires,payload FROM api_cache WHERE key=?', (key,)).fetchone()
            if cached and cached[0] > time.time():
                return json.loads(cached[1])
            cooldown = db.execute("SELECT value FROM metadata WHERE key='aviasales:cooldown'").fetchone()
            if cooldown and float(cooldown[0]) > time.time():
                raise ProviderUnavailable('Provider cooldown')
            client = self.client or httpx.Client(timeout=httpx.Timeout(8, connect=5))
            started = time.monotonic()
            try:
                for attempt in range(2):
                    response = client.get(API, params=params, headers={'X-Access-Token': self.token})
                    log.info('provider=aviasales status=%d duration_ms=%d', response.status_code, int((time.monotonic()-started)*1000))
                    if response.status_code == 429:
                        try:
                            delay = max(60, min(86400, float(response.headers.get('Retry-After', '60'))))
                        except ValueError:
                            delay = 60
                        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('aviasales:cooldown', str(time.time()+delay)))
                        db.commit()
                        raise ProviderUnavailable('Provider rate limit')
                    if response.status_code in (500, 502, 503, 504) and attempt == 0:
                        time.sleep(0.5)
                        continue
                    response.raise_for_status()
                    break
                payload = response.json()
                if payload.get('success') is not True or not isinstance(payload.get('data'), list):
                    raise ValueError('Invalid provider response')
                if str(payload.get('currency', '')).lower() != 'azn':
                    raise ValueError('Provider returned an unverified currency')
                result = {'data': payload['data'], 'fetched_at': datetime.now(timezone.utc).isoformat()}
                db.execute('INSERT OR REPLACE INTO api_cache VALUES (?,?,?)', (key, time.time()+self.ttl, json.dumps(result)))
                return result
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                log.warning('provider=aviasales error=%s', type(exc).__name__)
                raise ProviderUnavailable('Flight data provider unavailable') from None
            finally:
                if self.client is None:
                    client.close()

    def adapt(self, row, fetched, round_trip):
        departure = row['departure_at']
        origin, destination = row['origin'], row['destination']
        trip = 'round_trip' if round_trip else 'one_way'
        identity = json.dumps([origin, destination, departure, row.get('return_at'), row.get('airline'), row.get('flight_number'), row['price']], sort_keys=True)
        link = urljoin('https://www.aviasales.com', row.get('link', ''))
        if urlsplit(link).hostname not in ('www.aviasales.com', 'aviasales.com'):
            link = 'https://www.aviasales.com/'
        return Flight.model_validate({
            'id': 'AV-' + hashlib.sha256(identity.encode()).hexdigest()[:16],
            'origin': {'city': next((c for c, v in CITIES.items() if v == origin), origin), 'code': origin},
            'destination': {'city': next((c for c, v in CITIES.items() if v == destination), destination), 'code': destination},
            'departure_local': departure, 'airline': row.get('airline'),
            'flight_number': str(row['flight_number']) if row.get('flight_number') is not None else None,
            'duration_min': row.get('duration_to') or (row.get('duration') if not round_trip else None),
            'stops': row.get('transfers'), 'price_azn': row['price'], 'fetched_at': fetched,
            'trip_type': trip, 'price_scope': 'entire_round_trip' if round_trip else 'entire_one_way_itinerary',
            'return_date': row['return_at'][:10] if round_trip and row.get('return_at') else None,
            'source': 'Aviasales Data API (cached fares)', 'search_url': link,
            'provider_cached': True,
        }).model_dump(mode='json')

    def search(self, filters):
        origin, destination = code(filters.get('origin', 'Baku')), code(filters.get('destination'))
        if not origin or not destination:
            return []
        round_trip = filters.get('trip_type') == 'round_trip'
        params = {'origin': origin, 'destination': destination, 'currency': 'azn',
                  'one_way': str(not round_trip).lower(), 'sorting': 'price', 'limit': 100,
                  'unique': 'false'}
        if filters.get('date'):
            params['departure_at'] = filters['date']
        if round_trip and filters.get('return_date'):
            params['return_at'] = filters['return_date']
        if filters.get('max_stops') == 0:
            params['direct'] = 'true'
        rows = []
        for page in range(1, 4):
            payload = self.fetch({**params, 'page': page})
            try:
                rows += [self.adapt(r, payload['fetched_at'], round_trip) for r in payload['data']]
            except (ValueError, KeyError, TypeError):
                raise ProviderUnavailable('Invalid flight records') from None
            if len(payload['data']) < 100:
                break
        unique = {r['id']: r for r in rows}
        with self.database.connect() as db:
            db.executemany('INSERT OR REPLACE INTO flight_offers VALUES (?,?)',
                           [(i, json.dumps(r)) for i, r in unique.items()])
        # Reuse field filters while restricting them to this response only.
        class ResultRepository(JsonFlightRepository):
            def all(self):
                return list(unique.values())
        clean = {k: v for k, v in filters.items() if k not in ('origin', 'destination')}
        results = ResultRepository('.').search(clean)
        if filters.get('return_date'):
            results = [r for r in results if r.get('return_date') == filters['return_date']]
        return results
