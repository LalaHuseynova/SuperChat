"""Collect public CineMastercard movie, venue and dated showtime listings."""

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

BASE = 'https://cinemastercard.az'
TZ = ZoneInfo('Asia/Baku')
MOVIE_PATH = re.compile(r'^/az/(films|coming-soon)/[^/]+/$')
VENUE_PATH = re.compile(r'^/az/cinema/about-cinemaplus/[^/]+/$')


class ScraperError(RuntimeError):
    pass


class AccessStopped(ScraperError):
    pass


def text(node):
    return ' '.join(node.get_text(' ', strip=True).split()) if node else None


def absolute(url):
    result = urljoin(BASE, url)
    parts = urlsplit(result)
    if parts.scheme not in ('http', 'https'):
        raise ValueError('Unsupported URL scheme')
    return result


def identity(prefix, value):
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:16]


def entity_id(prefix, url):
    # A coming-soon page can later move to /films/ without changing its ID.
    return identity(prefix, urlsplit(url).path.rstrip('/').split('/')[-1])


def discover(soup, pattern):
    return list(dict.fromkeys(absolute(a['href'].split('#')[0]) for a in soup.select('a[href]')
                             if pattern.fullmatch(urlsplit(a['href']).path)
                             and urlsplit(absolute(a['href'])).netloc == urlsplit(BASE).netloc))


def formats_and_languages(node):
    labels = list(dict.fromkeys(text(x) for x in node.select('.cc_tooltip') if text(x))) if node else []
    formats, languages, subtitles = [], [], []
    for label in labels:
        for pattern, target in [(r'Film (.+?) formatında', formats),
                                (r'Film (.+?) dilində', languages),
                                (r'Film (.+?) subtitr', subtitles)]:
            match = re.search(pattern, label)
            if match and match[1] not in target:
                target.append(match[1])
    return {'formats': formats, 'languages': languages, 'subtitles': subtitles, 'format_labels': labels}


def parse_movie(html, url, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')
    synopsis = soup.select_one('.desc_film')
    if synopsis is None:
        raise ScraperError('Movie detail section missing')
    details = {text(e.parent.find('span', recursive=False)): text(e) for e in soup.select('li > .detail')}
    title = text(soup.select_one('h1 .container')) or (text(soup.title) or '').split(' • ')[0]
    if not title:
        raise ScraperError('Movie title missing')
    duration = re.search(r'\d+', details.get('Müddət') or '')
    age = details.get('Yaş həddi')
    dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', details.get('Kinotearda') or '')
    dates = [datetime.strptime(d, '%d.%m.%Y').date().isoformat() for d in dates]
    poster = soup.select_one('.left_banner > img[src]')
    media = formats_and_languages(soup.select_one('li .poster_icons2'))
    movie = {
        'id': entity_id('CM-M-', url), 'title': title,
        'genre': [g.strip() for g in (details.get('Janr') or '').split(',') if g.strip()],
        'language': media['languages'][0] if len(media['languages']) == 1 else None,
        'duration_min': int(duration[0]) if duration else None,
        'age_rating': age if age and re.fullmatch(r'\d+\+', age) else None,
        'rating': None, 'synopsis': text(synopsis), 'content_language': 'az',
        'listing_status': 'coming_soon' if '/coming-soon/' in url else 'current_or_presale',
        **media, 'country': details.get('Ölkə'), 'directors': details.get('Rejissor'),
        'cast': details.get('Rollarda'), 'release_date': dates[0] if dates else None,
        'listed_until': dates[1] if len(dates) > 1 else None,
        'poster_url': absolute(poster['src']) if poster else None, 'poster_file': None,
        'trailer_urls': [absolute(e['src']) for e in soup.select('iframe.yt_iframe[src]')],
        'source_details': details, 'source_url': url, 'fetched_at': fetched_at,
    }
    return movie


def parse_price(value):
    match = re.fullmatch(r'\s*(\d+(?:[.,]\d{1,2})?)\s*AZN\s*', value)
    if not match:
        raise ValueError(f'Unrecognized displayed price: {value}')
    return float(Decimal(match[1].replace(',', '.')))


def parse_showtimes(html, url, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')
    records, errors = [], []
    for index, row in enumerate(soup.select('.sessions_table tbody tr[data-date]')):
        try:
            cells = row.find_all('td', recursive=False)
            if len(cells) != 7:
                raise ValueError('Unexpected schedule column count')
            movie_link, cinema_link = cells[0].select_one('a[href]'), cells[2].select_one('a[href]')
            if not movie_link or not cinema_link:
                raise ValueError('Movie or cinema link missing')
            movie_url, cinema_url = absolute(movie_link['href']), absolute(cinema_link['href'])
            if not MOVIE_PATH.fullmatch(urlsplit(movie_url).path) or not VENUE_PATH.fullmatch(urlsplit(cinema_url).path):
                raise ValueError('Unexpected entity link')
            day = datetime.strptime(row['data-date'], '%d.%m.%Y').date().isoformat()
            clock = text(cells[1])
            start = datetime.fromisoformat(day + 'T' + clock).replace(tzinfo=TZ)
            if not re.fullmatch(r'\d{2}:\d{2}', clock):
                raise ValueError('Invalid showtime clock')
            price = parse_price(text(cells[5]))
            attributes = row.select_one('.zone_input')
            attrs = {k[5:]: v for k, v in attributes.attrs.items() if k.startswith('data-')} if attributes else {}
            media = formats_and_languages(cells[4])
            movie_id, cinema_id = entity_id('CM-M-', movie_url), entity_id('CM-C-', cinema_url)
            key = json.dumps([movie_id, cinema_id, day, clock, text(cells[3]), media['languages'], media['formats']])
            records.append({
                'id': identity('CM-S-', key), 'movie_id': movie_id, 'cinema_id': cinema_id,
                'date': day, 'time': clock, 'hall': text(cells[3]), 'price_azn': price,
                'seats_total': None, 'seats_available': None, 'currency': 'AZN',
                'start_local': start.isoformat(), 'timezone': 'Asia/Baku', **media,
                'price_kind': 'displayed_session_price', 'price_scope': 'per_ticket_before_seat_selection',
                'price_verified_at_checkout': False, 'price_conflict': False,
                'source_session_id': attrs.get('session'), 'source_attributes': attrs,
                'movie_title': text(cells[0]), 'cinema_name': text(cells[2]),
                'movie_url': movie_url, 'cinema_url': cinema_url, 'booking_url': movie_url + '#sessions',
                'source_url': url, 'fetched_at': fetched_at,
                'source_type': 'movie_page' if MOVIE_PATH.fullmatch(urlsplit(url).path) else 'cinema_page',
                'price_observations': [{'price_azn': price, 'source_url': url, 'fetched_at': fetched_at}],
            })
        except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
            errors.append({'source_url': url, 'row': index, 'error': str(exc)})
    return records, errors


def parse_cinema(html, url, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')
    desc = soup.select_one('.description')
    if desc is None:
        raise ScraperError('Cinema description section missing')
    name = (text(soup.title) or '').split(' • ')[0]
    contact = soup.select_one('.tab.contact')
    contact_text = text(contact)
    contact_details = {}
    if contact:
        for paragraph in contact.select('li > p'):
            label = paragraph.previous_sibling
            while label is not None and not (text(label) if getattr(label, 'name', None) else str(label).strip()):
                label = label.previous_sibling
            label_text = text(label) if getattr(label, 'name', None) else (str(label).strip() if label is not None else '')
            if label_text:
                contact_details[label_text] = text(paragraph)
        for li in contact.select('li'):
            if not li.find('p'):
                parts = list(li.stripped_strings)
                if len(parts) >= 2:
                    contact_details[parts[0]] = ' '.join(parts[1:])
    address = next((v for k, v in contact_details.items() if 'ünvan' in k.casefold()
                    and not any(w in k.casefold() for w in ('elektron', 'e-poçt'))), None)
    phone = next((v for k, v in contact_details.items() if 'telefon' in k.casefold() or 'телефон' in k.casefold()), None)
    hours = next((v for k, v in contact_details.items() if 'iş saat' in k.casefold().replace('\u0307', '') or 'рабочи' in k.casefold()), None)
    map_node = contact.select_one('iframe[src]') if contact else None
    map_url = absolute(map_node['src']) if map_node else None
    coordinates = None
    if map_url:
        q = parse_qs(urlsplit(map_url).query).get('q', [''])[0]
        if re.fullmatch(r'-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', q):
            lat, lon = map(float, q.split(','))
            if (lat, lon) != (0, 0) and -90 <= lat <= 90 and -180 <= lon <= 180:
                coordinates = {'latitude': lat, 'longitude': lon}
    return {
        'id': entity_id('CM-C-', url), 'name': name, 'district': None, 'address': address,
        'phone': phone, 'opening_hours': hours, 'contact_details': contact_details,
        'description': text(desc), 'contact_text': contact_text, 'map_url': map_url,
        'coordinates': coordinates, 'coordinates_verified': False,
        'gallery_urls': list(dict.fromkeys(absolute(e['href']) for e in soup.select('.photogallery a[href]'))),
        'tariff_image_urls': list(dict.fromkeys(absolute(e['src']) for e in soup.select('.tariffs img[src]'))),
        'tariff_image_files': [], 'source_url': url, 'fetched_at': fetched_at,
    }


def merge_showtimes(records):
    merged = {}
    for row in records:
        old = merged.get(row['id'])
        if old is None:
            merged[row['id']] = dict(row)
            continue
        observations = old['price_observations'] + row['price_observations']
        if row['source_type'] == 'movie_page' and old['source_type'] != 'movie_page':
            merged[row['id']] = dict(row)
        merged[row['id']]['price_observations'] = list({json.dumps(o, sort_keys=True): o for o in observations}.values())
    for row in merged.values():
        row['price_conflict'] = len({o['price_azn'] for o in row['price_observations']}) > 1
    return sorted(merged.values(), key=lambda x: (x['date'], x['time'], x['cinema_id'], x['movie_id']))


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            cleaned = {}
            for key, val in row.items():
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)
                elif isinstance(val, str) and val.startswith(('=', '+', '-', '@')):
                    val = "'" + val
                cleaned[key] = val
            writer.writerow(cleaned)


def scrape_cinema(output='SuperChat_Real_Data', delay=0.75, download_images=True):
    if delay < 0:
        raise ValueError('delay must be nonnegative')
    root = Path(output)
    folder = root / 'cinema'
    started = datetime.now(TZ)
    run = folder / 'runs' / started.strftime('%Y%m%d_%H%M%S_%f')
    (run / 'sources').mkdir(parents=True)
    (run / 'images').mkdir()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'az'})
    last_request = 0
    sources, errors, images = [], [], []
    movies, cinemas, observations = {}, {}, []
    movie_urls, cinema_urls = [], []

    def fetch(url):
        nonlocal last_request
        if urlsplit(url).netloc != urlsplit(BASE).netloc:
            raise ScraperError('Only CineMastercard-hosted resources are downloaded')
        for attempt in range(3):
            time.sleep(max(0, delay - (time.monotonic() - last_request)))
            last_request = time.monotonic()
            response = session.get(url, timeout=(10, 40))
            if response.status_code in (403, 429):
                raise AccessStopped(f'HTTP {response.status_code}: stopped at {url}')
            if response.status_code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            response.raise_for_status()
            return response

    def page(url):
        response = fetch(url)
        if urlsplit(response.url).path.rstrip('/') != urlsplit(url).path.rstrip('/'):
            raise ScraperError(f'Unexpected redirect: {response.url}')
        stamp = datetime.now(TZ).isoformat()
        file = run / 'sources' / (identity('', url) + '.html')
        file.write_text(response.text, encoding='utf-8')
        sources.append({'url': url, 'fetched_at': stamp, 'file': str(file.relative_to(root))})
        return response.text, stamp

    try:
        home, _ = page(BASE + '/')
        home_soup = BeautifulSoup(home, 'html.parser')
        movie_urls = discover(home_soup, MOVIE_PATH)
        if not movie_urls:
            raise ScraperError('No movies found on the homepage')
        about, _ = page(BASE + '/az/cinema/about-cinemaplus/')
        cinema_urls = discover(BeautifulSoup(about, 'html.parser'), VENUE_PATH)
        for url in cinema_urls:
            try:
                html, stamp = page(url)
                cinema = parse_cinema(html, url, stamp)
                cinemas[cinema['id']] = cinema
                rows, issues = parse_showtimes(html, url, stamp)
                observations.extend(rows)
                errors.extend(issues)
                for row in rows:
                    if row['movie_url'] not in movie_urls:
                        movie_urls.append(row['movie_url'])
                print(f"Cinema: {cinema['name']} ({len(rows)} schedule rows)", flush=True)
            except AccessStopped:
                raise
            except (requests.RequestException, ScraperError, ValueError) as exc:
                errors.append({'source_url': url, 'error': str(exc)})
        for url in movie_urls:
            try:
                html, stamp = page(url)
                movie = parse_movie(html, url, stamp)
                movies[movie['id']] = movie
                rows, issues = parse_showtimes(html, url, stamp)
                observations.extend(rows)
                errors.extend(issues)
                print(f"Movie: {movie['title']} ({len(rows)} schedule rows)", flush=True)
            except AccessStopped:
                raise
            except (requests.RequestException, ScraperError, ValueError) as exc:
                errors.append({'source_url': url, 'error': str(exc)})
        if download_images:
            targets = [(m, 'poster_file', m['poster_url']) for m in movies.values() if m['poster_url']]
            targets += [(c, 'tariff_image_files', u) for c in cinemas.values() for u in c['tariff_image_urls']]
            for record, field, url in targets:
                try:
                    response = fetch(url)
                    content_type = response.headers.get('Content-Type', '').split(';')[0]
                    if not content_type.startswith('image/'):
                        raise ScraperError('Expected an image response')
                    suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}.get(content_type, '.img')
                    path = run / 'images' / (identity('', url) + suffix)
                    path.write_bytes(response.content)
                    relative = str(path.relative_to(root))
                    if field == 'tariff_image_files':
                        record[field].append(relative)
                    else:
                        record[field] = relative
                    images.append({'url': url, 'file': relative, 'bytes': len(response.content),
                                   'sha256': hashlib.sha256(response.content).hexdigest()})
                except AccessStopped:
                    raise
                except (requests.RequestException, ScraperError) as exc:
                    errors.append({'source_url': url, 'error': str(exc), 'stage': 'image'})
    except (requests.RequestException, ScraperError, ValueError) as exc:
        errors.append({'error': str(exc)})
    finally:
        session.close()

    # Failed entity pages still get explicit minimal records so references never dangle.
    for row in observations:
        if row['movie_id'] not in movies:
            movies[row['movie_id']] = {'id': row['movie_id'], 'title': row['movie_title'],
                'genre': [], 'language': None, 'duration_min': None, 'age_rating': None,
                'rating': None, 'synopsis': None, 'source_url': row['movie_url'],
                'fetched_at': row['fetched_at'], 'detail_status': 'unavailable'}
        if row['cinema_id'] not in cinemas:
            cinemas[row['cinema_id']] = {'id': row['cinema_id'], 'name': row['cinema_name'],
                'district': None, 'address': None, 'source_url': row['cinema_url'],
                'fetched_at': row['fetched_at'], 'detail_status': 'unavailable'}
    showtimes = merge_showtimes(observations)
    for row in showtimes:
        row['is_future_at_collection'] = datetime.fromisoformat(row['start_local']) >= started
    manifest = {'source': BASE, 'schema_version': '1.0', 'fetched_at': started.isoformat(),
        'run_directory': str(run.relative_to(root)), 'timezone': 'Asia/Baku', 'currency': 'AZN',
        'coverage': 'partial' if errors else 'discovered_public_listings_collected',
        'counts': {'movies': len(movies), 'cinemas': len(cinemas), 'showtimes': len(showtimes),
                   'images': len(images), 'price_conflicts': sum(s['price_conflict'] for s in showtimes)},
        'dates': sorted({s['date'] for s in showtimes}), 'movie_pages_requested': len(movie_urls),
        'cinema_pages_requested': len(cinema_urls), 'errors': errors,
        'limitations': [
            'Public listings only: no seat selection, reservation, checkout or login performed.',
            'Prices are displayed session prices; seat-specific charges, promotions and availability are not verified.',
            'Conflicting movie/venue prices are retained in price_observations; movie-page price takes precedence.',
            'Movie ratings, exact seat counts and absent duration/age/address/district values remain null.',
            'Only dates published on fetched pages are collected. Missing sessions do not establish sold-out status.',
            'Movie language is null for multiple/unknown languages; use each showtime languages/subtitles instead.',
            'Coordinates are unverified source map values; 0,0 placeholders are discarded.',
            'Tariff images are preserved separately, not interpreted as a session price or discount.',
            'Content is Azerbaijani as published; no synthetic translations or mock values are added.',
        ]}
    write_json(run / 'manifest.json', manifest)
    write_json(run / 'sources.json', sources)
    write_json(run / 'images.json', images)
    if not movies or not cinemas:
        raise ScraperError(f'Incomplete collection: previous exports preserved. See {run / "manifest.json"}')
    tables = {'movies': list(movies.values()), 'cinemas': list(cinemas.values()), 'showtimes': showtimes}
    for name, records in tables.items():
        for destination in (folder, run):
            write_json(destination / (name + '.json'), records)
            write_csv(destination / (name + '.csv'), records)
    write_json(folder / 'manifest.json', manifest)
    from validate_cinema import validate_dataset
    validation = validate_dataset(root)
    write_json(folder / 'validation.json', validation)
    write_json(run / 'validation.json', validation)
    if not validation['passed']:
        raise ScraperError(f'Dataset validation failed; see {folder / "validation.json"}')
    print('Saved: ' + json.dumps(manifest['counts']), flush=True)
    return {'folder': folder, 'run': run, **tables, 'manifest': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='SuperChat_Real_Data')
    parser.add_argument('--delay', type=float, default=0.75)
    parser.add_argument('--no-images', action='store_true')
    args = parser.parse_args()
    try:
        result = scrape_cinema(args.output, args.delay, not args.no_images)
    except (ScraperError, OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    if result['manifest']['coverage'] == 'partial':
        parser.exit(2, 'Partial export saved; see cinema/manifest.json.\n')


if __name__ == '__main__':
    main()
