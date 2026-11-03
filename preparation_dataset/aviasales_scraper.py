"""Export public Aviasales route-page fare snapshots for Superchat.

These are advertised cached offers, not a live search or confirmed inventory.
"""

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

BASE_URL = 'https://www.aviasales.az'
REFERENCE_URLS = {kind: f'https://api.travelpayouts.com/data/en/{kind}.json'
                  for kind in ('cities', 'airports', 'airlines')}


class ScraperError(RuntimeError):
    pass


class AccessStopped(ScraperError):
    pass


def normalize_text(text):
    return re.sub(r'\s+', ' ', text.replace('\u2060', '').replace('\u200b', '')).strip()


def parse_price(text):
    if '₼' not in text:
        raise ValueError('Expected an explicitly displayed AZN price')
    value = re.sub(r'[\s\u2060₼]', '', text)
    if ',' in value:
        value = value.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', value):
        value = value.replace('.', '')
    price = Decimal(value)
    if not price.is_finite() or price <= 0:
        raise ValueError('Invalid fare price')
    return float(price.quantize(Decimal('.01')))


def parse_duration(text):
    text = normalize_text(text).casefold()
    total, found = 0, False
    for pattern, factor in [(r'(\d+)\s*gün', 1440), (r'(\d+)\s*saat', 60), (r'(\d+)\s*dəq', 1)]:
        match = re.search(pattern, text)
        if match:
            total += int(match[1]) * factor
            found = True
    if not found or total <= 0:
        raise ValueError(f'Unrecognized duration: {text}')
    return total


def parse_stops(text):
    text = normalize_text(text).casefold()
    if 'birbaşa' in text:
        return 0
    match = re.search(r'(\d+)\s*tranzit', text)
    return int(match[1]) if match else None


def decode_astro(props):
    """Decode JSON property wrappers; never execute the page's scripts."""
    def item(value):
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError('Unrecognized Astro property wrapper')
        kind, payload = value
        if kind == 0:
            return obj(payload) if isinstance(payload, dict) else payload
        if kind == 1:
            return [item(v) for v in payload]
        if kind == 3:
            return payload
        raise ValueError(f'Unsupported Astro data type: {kind}')
    def obj(value):
        return {k: item(v) for k, v in value.items()}
    return obj(json.loads(props))


def location(code, reference, scope='city'):
    city = reference['cities'].get(code)
    airport = reference['airports'].get(code)
    if city:
        return {'code': code, 'city': city['name'], 'code_type': 'city',
                'timezone': city.get('time_zone'), 'country_code': city.get('country_code'),
                'airport_code': None, 'scope': scope}
    if airport:
        city = reference['cities'].get(airport['city_code'], {})
        return {'code': code, 'city': city.get('name'), 'code_type': 'airport_search_code',
                'timezone': airport.get('time_zone'), 'country_code': airport.get('country_code'),
                'airport_code': None, 'scope': scope}
    return {'code': code, 'city': None, 'code_type': 'unknown', 'timezone': None,
            'country_code': None, 'airport_code': None, 'scope': scope}


def parse_leg(element, departure_date, origin, destination, reference):
    date.fromisoformat(departure_date)
    clock_node = element.select_one('.ticket-date')
    clocks = re.findall(r'\b\d{2}:\d{2}\b', clock_node.get_text(' ', strip=True) if clock_node else '')
    if len(clocks) != 2:
        raise ValueError('Expected displayed departure and arrival times')
    duration_node = element.select_one('.ticket-duration')
    duration_text = duration_node.get_text(' ', strip=True) if duration_node else ''
    duration = parse_duration(duration_text)
    departure = datetime.fromisoformat(departure_date + 'T' + clocks[0])
    arrival, departure_utc, arrival_utc = None, None, None
    warnings = []
    if origin.get('timezone') and destination.get('timezone'):
        aware = departure.replace(tzinfo=ZoneInfo(origin['timezone']))
        departure_utc = aware.astimezone(timezone.utc).isoformat()
        arrival_instant = aware.astimezone(timezone.utc) + timedelta(minutes=duration)
        candidate = arrival_instant.astimezone(ZoneInfo(destination['timezone']))
        if candidate.strftime('%H:%M') == clocks[1]:
            arrival = candidate.replace(tzinfo=None).isoformat(timespec='minutes')
            arrival_utc = arrival_instant.isoformat()
        else:
            warnings.append('Displayed arrival time disagrees with duration/timezones; arrival date left unknown.')
    else:
        warnings.append('Unknown route timezone; arrival date left unknown.')
    carriers = []
    for logo in element.select('astro-airline-logo[data-alt]'):
        code = logo['data-alt']
        if code not in [c['code'] for c in carriers]:
            carriers.append({'code': code, 'name': reference['airlines'].get(code, {}).get('name'),
                             'logo_url': urljoin(BASE_URL, logo.get('data-logo-url', ''))})
    return {
        'origin': origin, 'destination': destination,
        'departure_local': departure.isoformat(timespec='minutes'), 'arrival_local': arrival,
        'departure_utc': departure_utc, 'arrival_utc': arrival_utc,
        'arrival_time_displayed': clocks[1], 'duration_min': duration,
        'stops': parse_stops(duration_text), 'via': None, 'airlines': carriers,
        'arrival_date_source': 'derived_from_displayed_duration_and_timezones' if arrival else None,
        'data_warnings': warnings,
    }


def parse_search_route(url, departure_date, return_date):
    match = re.fullmatch(r'/search/([A-Z]{3})(\d{4})([A-Z]{3})(\d{4})?1', urlsplit(url).path)
    if not match:
        return None
    if date.fromisoformat(departure_date).strftime('%d%m') != match[2]:
        return None
    if return_date and (not match[4] or date.fromisoformat(return_date).strftime('%d%m') != match[4]):
        return None
    return {'origin_code': match[1], 'destination_code': match[3]}


def parse_route(html, route, reference, fetched_at, source_url):
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('a.ticket[data-analytics-click-data]')
    if not cards:
        raise ScraperError('No advertised fare cards found; empty route or changed page')
    origin, destination = location(route['origin'], reference), location(route['destination'], reference)
    page = {'source_url': source_url, 'fetched_at': fetched_at,
            'title': soup.h1.get_text(' ', strip=True) if soup.h1 else None,
            'origin': origin, 'destination': destination, 'price_history': []}
    for island in soup.select('astro-island[props]'):
        if 'PricesDynamicContainer' in island.get('component-url', ''):
            try:
                page['price_history'] = decode_astro(island['props']).get('data', [])
            except ValueError as exc:
                page['price_history_error'] = str(exc)
    results, errors = [], []
    for index, card in enumerate(cards):
        try:
            metadata = json.loads(card['data-analytics-click-data'])
            depart_date = metadata['depart_date']
            return_date = metadata.get('return_date') or None
            if metadata.get('origin_airport_iata') != route['origin'] or metadata.get('destination_airport_iata') != route['destination']:
                raise ValueError('Fare route does not match the requested city route')
            price_node = card.select_one('.ticket-price')
            if price_node is None:
                raise ValueError('Displayed fare price is missing')
            price = parse_price(price_node.get_text())
            href = urljoin(BASE_URL, card['href'])
            if urlsplit(href).netloc != urlsplit(BASE_URL).netloc:
                raise ValueError('Unexpected search-link host')
            leg_nodes = card.select('.ticket-info')
            expected = 2 if return_date else 1
            if len(leg_nodes) != expected:
                raise ValueError('Fare dates and displayed leg count disagree')
            search_route = parse_search_route(href, depart_date, return_date)
            if search_route is None:
                raise ValueError('Search link route or dates could not be verified')
            nearby = bool(search_route and (search_route['origin_code'] != route['origin'] or search_route['destination_code'] != route['destination']))
            offer_origin = location(search_route['origin_code'], reference, 'search_location')
            offer_destination = location(search_route['destination_code'], reference, 'search_location')
            outbound = parse_leg(leg_nodes[0], depart_date, offer_origin, offer_destination, reference)
            inbound = parse_leg(leg_nodes[1], return_date, offer_destination, offer_origin, reference) if return_date else None
            parameters = parse_qs(urlsplit(href).query)
            search_date = parameters.get('search_date', [None])[0]
            try:
                search_date = datetime.strptime(search_date, '%d%m%Y').date().isoformat() if search_date else None
            except ValueError:
                search_date = None
            carriers = outbound['airlines']
            badge = metadata.get('badge') or ''
            identity = json.dumps([route['origin'], route['destination'], depart_date, return_date,
                                   outbound['departure_local'], price, badge, parameters.get('itinerary_key')], sort_keys=True)
            warnings = list(outbound['data_warnings'])
            if inbound:
                warnings.extend(inbound['data_warnings'])
            if nearby:
                warnings.append('The search link uses a nearby/different city or airport; check search_route before displaying destinations.')
            result = {
                'id': 'AV-' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                'airline': ' / '.join(c['name'] or c['code'] for c in carriers) or None,
                'flight_number': None, 'origin': offer_origin, 'destination': offer_destination,
                'source_route': {'origin': origin, 'destination': destination},
                'departure_local': outbound['departure_local'], 'arrival_local': outbound['arrival_local'],
                'duration_min': outbound['duration_min'], 'stops': outbound['stops'], 'via': None,
                'price_azn': price, 'cabin': None, 'baggage_kg': None, 'seats_available': None,
                'currency': 'AZN', 'trip_type': 'round_trip' if return_date else 'one_way',
                'price_scope': 'entire_round_trip' if return_date else 'entire_one_way_itinerary',
                'baggage_included': True if 'baqaj daxil' in badge.casefold() else None,
                'fare_label': badge, 'airlines': carriers, 'return_date': return_date,
                'departure_utc': outbound['departure_utc'], 'arrival_utc': outbound['arrival_utc'],
                'arrival_time_displayed': outbound['arrival_time_displayed'],
                'arrival_date_source': outbound['arrival_date_source'], 'return_leg': inbound,
                'location_scope': 'city_route_area_not_confirmed_airports',
                'search_route': ({'origin': location(search_route['origin_code'], reference, 'search_location'),
                                  'destination': location(search_route['destination_code'], reference, 'search_location')}
                                 if search_route else None),
                'nearby_airport_search': nearby, 'search_url': href,
                'price_kind': 'cached_advertised_fare', 'live_price_verified': False,
                'source_search_date': search_date, 'fetched_at': fetched_at, 'source_url': source_url,
                'source': 'aviasales.az', 'source_card_text': normalize_text(card.get_text(' ', strip=True)),
                'data_warnings': warnings,
                'missing_fields': ['flight_number', 'cabin', 'baggage_kg', 'seats_available', 'confirmed_airports'] + (['via'] if outbound['stops'] else []),
            }
            results.append(result)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append({'source_url': source_url, 'card_index': index, 'error': str(exc)})
    if not results:
        raise ScraperError(f'No fare cards could be parsed: {errors}')
    return results, page, errors


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


FLIGHT_FIELDS = ['id', 'airline', 'flight_number', 'origin', 'destination', 'departure_local',
                 'arrival_local', 'duration_min', 'stops', 'via', 'price_azn', 'cabin',
                 'baggage_kg', 'seats_available', 'trip_type', 'price_scope', 'baggage_included',
                 'search_route', 'nearby_airport_search', 'return_date', 'return_leg',
                 'source_search_date', 'fetched_at', 'source_url', 'search_url', 'price_kind',
                 'currency', 'airlines', 'fare_label', 'departure_utc', 'arrival_utc',
                 'arrival_time_displayed', 'arrival_date_source', 'source_route', 'location_scope',
                 'live_price_verified', 'source_card_text', 'data_warnings', 'missing_fields']


def write_csv(path, flights):
    with path.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=FLIGHT_FIELDS)
        writer.writeheader()
        for flight in flights:
            row = {k: flight.get(k) for k in FLIGHT_FIELDS}
            for k, value in row.items():
                if isinstance(value, (dict, list)):
                    row[k] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
                    row[k] = "'" + value
            writer.writerow(row)


def scrape_flights(config_path=None, output='SuperChat_Real_Data', delay=1.0,
                   from_date=None, to_date=None):
    config_path = Path(config_path) if config_path else Path(__file__).with_name('aviasales_routes.json')
    config = json.loads(config_path.read_text())
    if config.get('currency') != 'AZN' or delay < 0:
        raise ValueError('This scraper supports AZN only; delay must be nonnegative')
    if from_date:
        date.fromisoformat(from_date)
    if to_date:
        date.fromisoformat(to_date)
    if from_date and to_date and from_date > to_date:
        raise ValueError('from_date must not be after to_date')
    routes = config['routes']
    for route in routes:
        if not all(re.fullmatch('[A-Z]{3}', route.get(k, '')) for k in ('origin', 'destination')):
            raise ValueError('Route codes must be three uppercase letters')
    root = Path(output)
    folder = root / 'aviasales'
    start = datetime.now(ZoneInfo('Asia/Baku'))
    run = folder / 'runs' / start.strftime('%Y%m%d_%H%M%S_%f')
    (run / 'sources').mkdir(parents=True)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/json'})
    last_request = 0.0

    def fetch(url):
        nonlocal last_request
        for attempt in range(3):
            time.sleep(max(0, delay - (time.monotonic() - last_request)))
            last_request = time.monotonic()
            response = session.get(url, timeout=(10, 40))
            if response.status_code in (403, 429):
                raise AccessStopped(f'HTTP {response.status_code} at {url}; stopped')
            if response.status_code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            return response

    offers, pages, errors, route_counts = [], [], [], {}
    reference = {}
    try:
        for kind, url in REFERENCE_URLS.items():
            response = fetch(url)
            reference[kind] = {row['code']: row for row in response.json()}
            write_json(run / 'sources' / (kind + '.json'), response.json())
        for route in routes:
            key = route['origin'] + '-' + route['destination']
            url = BASE_URL + '/routes/' + route['origin'].lower() + '/' + route['destination'].lower()
            try:
                response = fetch(url)
                if urlsplit(response.url).path.rstrip('/') != urlsplit(url).path:
                    raise ScraperError(f'Unexpected route redirect: {response.url}')
                stamp = datetime.now(ZoneInfo('Asia/Baku')).isoformat()
                records, page, issues = parse_route(response.text, route, reference, stamp, url)
                filename = key + '.html'
                (run / 'sources' / filename).write_text(response.text, encoding='utf-8')
                page['source_file'] = str((run / 'sources' / filename).relative_to(root))
                offers.extend(records)
                pages.append(page)
                errors.extend(issues)
                route_counts[key] = len(records)
                print(f'{key}: {len(records)} advertised dated fares', flush=True)
            except AccessStopped:
                raise
            except (requests.RequestException, ScraperError, ValueError) as exc:
                route_counts[key] = 0
                errors.append({'source_url': url, 'error': str(exc)})
    except (requests.RequestException, ScraperError, ValueError) as exc:
        errors.append({'error': str(exc)})
    finally:
        session.close()

    offers = list({offer['id']: offer for offer in offers}.values())
    all_offers = list(offers)
    offers = [o for o in offers if (not from_date or o['departure_local'][:10] >= from_date)
              and (not to_date or o['departure_local'][:10] <= to_date)
              and o['departure_local'][:10] >= start.date().isoformat()]
    flights = [o for o in offers if o['trip_type'] == 'one_way']
    round_trips = [o for o in offers if o['trip_type'] == 'round_trip']
    manifest = {
        'source': BASE_URL, 'fetched_at': start.isoformat(), 'run_directory': str(run.relative_to(root)),
        'mode': 'published_cached_fares', 'live_search_performed': False,
        'routes_requested': routes, 'routes_collected': len(pages), 'fares_by_route_before_filters': route_counts,
        'one_way_fares': len(flights), 'round_trip_fares': len(round_trips), 'all_fares': len(offers),
        'filtered_out': len(all_offers) - len(offers), 'date_filter': {'from': from_date, 'to': to_date},
        'coverage': 'partial' if errors or len(pages) != len(routes) else 'published_route_cards_collected',
        'errors': errors, 'reference_sources': REFERENCE_URLS,
        'limitations': [
            'These are advertised cached examples, not live search results or guaranteed availability.',
            'Dates are the real dates published on route pages; the mock dates are not substituted.',
            'City route codes are not confirmed flight airport codes. Search links may use nearby cities/airports.',
            'Flight numbers, exact airports, cabin, baggage kilograms, seat counts and stopover airports are not inferred.',
            'Round-trip prices cover the complete itinerary and are exported separately from one-way flights.',
            'Arrival dates are derived from displayed duration and official city timezones, only when the displayed clock matches.',
            'Link search dates can be older than the page headline describing recent prices.',
            'Date options filter published cards; they do not initiate a fresh flight search.',
        ],
    }
    write_json(run / 'manifest.json', manifest)
    if not pages:
        raise ScraperError(f'No route pages collected. See {run / "manifest.json"}; previous flight exports are unchanged.')
    for destination in (folder, run):
        write_json(destination / 'flights.json', flights)
        write_csv(destination / 'flights.csv', flights)
        write_json(destination / 'round_trip_flights.json', round_trips)
        write_json(destination / 'offers.json', offers)
        write_csv(destination / 'offers.csv', offers)
        write_json(destination / 'routes.json', pages)
        write_json(destination / 'manifest.json', manifest)
    print(f'Saved {len(flights)} one-way fares and {len(round_trips)} round-trip fares to {folder.resolve()}', flush=True)
    return {'folder': folder, 'dataset_root': root, 'run': run, 'flights': flights, 'round_trips': round_trips, 'manifest': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', default='SuperChat_Real_Data')
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--from-date', help='Filter published departure dates, YYYY-MM-DD')
    parser.add_argument('--to-date', help='Filter published departure dates, YYYY-MM-DD')
    args = parser.parse_args()
    try:
        result = scrape_flights(args.config, args.output, args.delay, args.from_date, args.to_date)
    except (ScraperError, ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    if result['manifest']['coverage'] == 'partial':
        parser.exit(2, 'Partial export saved; see aviasales/manifest.json.\n')


if __name__ == '__main__':
    main()
