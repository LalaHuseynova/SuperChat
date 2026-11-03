"""Scrape Birbank public Azerbaijani product pages and tariff documents."""
import argparse
from collections import deque
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

BASE_URL = 'https://birbank.az'
SEEDS = ['/debet-kartlar', '/kredit-kartlar', '/kreditler', '/deposits',
         '/yigim-hesabi', '/avans', '/avtomobil-krediti', '/istiqraz',
         '/sigortalar', '/pul-kocurmeleri', '/tariffs', '/bokt/lizinq']
ROOTS = ('/cards/', '/kreditler/', '/deposits/', '/sigortalar/',
         '/pul-kocurmeleri/', '/transfers/', '/bokt/')
EXTRA_PAGES = {'/transfers', '/birbank-private', '/currency-rates'}
CATALOGS = {'/debet-kartlar', '/kredit-kartlar', '/kreditler', '/sigortalar', '/pul-kocurmeleri'}
MONEY = re.compile(r'₼|\b(?:AZN|USD|EUR)\b|\d\s*%|pulsuz|komissiya|qiymət|faiz|tarif', re.I)


class ScraperError(RuntimeError):
    pass


def text_of(element):
    return element.get_text(' ', strip=True) if element is not None else ''


def canonical_url(href, base=BASE_URL):
    parts = urlsplit(urljoin(base, href))
    if parts.scheme not in ('http', 'https'):
        return ''
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip('/') or '/', '', ''))


def in_scope(url):
    p = urlsplit(url)
    return p.netloc == 'birbank.az' and (p.path in SEEDS or p.path in EXTRA_PAGES or p.path.startswith(ROOTS))


def category(url):
    path = urlsplit(url).path
    for value, markers in [
        ('insurance', ('sigorta',)),
        ('cards', ('kartlar', '/cards/')), ('loans', ('kredit', 'avans')),
        ('deposits', ('deposits', 'yigim')),
        ('transfers', ('kocur', 'transfers')), ('leasing_and_payments', ('bokt',)),
        ('tariffs', ('tariffs',)), ('bonds', ('istiqraz',)),
    ]:
        if any(marker in path for marker in markers):
            return value
    return 'other_services'


def money_contexts(element):
    """Keep surrounding source text; do not infer a single product price."""
    text = text_of(element)
    spans = []
    for match in MONEY.finditer(text):
        start, end = max(0, match.start() - 100), min(len(text), match.end() + 160)
        if spans and start <= spans[-1][1]:
            spans[-1][1] = max(end, spans[-1][1])
        else:
            spans.append([start, end])
    return [text[a:b] for a, b in spans]


def parse_page(html, url, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.select_one('main') or soup.select_one('[class*="styles_private-bank__"]')
    if main is None or len(text_of(main)) < 30:
        raise ScraperError('No readable main content; blocked, empty, or changed page')
    breadcrumb = main.select('[class*="breadcrumbs-text"]')
    breadcrumb_name = text_of(breadcrumb[-1]) if breadcrumb else ''
    # Keep server-rendered FAQs/accordions; remove forms and calculator examples.
    for node in main.select('script, style, svg, nav, form, [class*="calculator"]'):
        node.decompose()
    title = text_of(main.select_one('h1')) or text_of(soup.title)
    links = [{'label': text_of(a), 'url': canonical_url(a['href'], url)}
             for a in main.select('a[href]') if canonical_url(a['href'], url)]
    tables = [[[text_of(c) for c in row.select('th, td')] for row in t.select('tr')]
              for t in main.select('table')]
    attributes = []
    for node in main.select('[class*="infoLabel__"]'):
        key, value = node.select_one('h3'), node.select_one('p')
        if key and value:
            attributes.append({'label': text_of(key), 'value': text_of(value)})
    for node in main.select('[class*="tariffs__item__head"]'):
        label = node.parent.select_one('[class*="tariffs__item__desc"]')
        if label:
            attributes.append({'label': text_of(label), 'value': text_of(node)})
    page = {'title': title, 'category': category(url), 'source_url': url,
            'fetched_at': fetched_at, 'text': main.get_text('\n', strip=True),
            'price_rate_mentions': money_contexts(main), 'attributes': attributes,
            'tables': tables, 'links': links}
    # Preserve published data for tabs not rendered in the initial HTML.
    embedded = soup.select_one('script#__NEXT_DATA__')
    if embedded and embedded.string:
        try:
            page['embedded_page_data'] = json.loads(embedded.string).get('props', {}).get('pageProps', {})
        except json.JSONDecodeError:
            page['embedded_data_error'] = 'Invalid JSON in __NEXT_DATA__'
    products = []
    path = urlsplit(url).path
    if path in CATALOGS:
        selectors = ('[class*="product-hero-info__header"], '
                     '[class*="product-list-item__info__head"], '
                     '[class*="card-product-item-content-title"], '
                     '[class*="credits-overview-cards-item-content"] h2')
        headings = list(main.select(selectors))
        if path == '/kreditler':
            headings += [h for h in main.select('h1') if 'page-heading' not in ' '.join(h.get('class', []))]
        for name_node in headings:
            block = name_node.parent
            while block is not main and block.find('a', href=True) is None:
                block = block.parent
            if block is main:
                continue
            link = block.find('a', href=True)
            name = 'Nağd pul krediti' if name_node.name == 'h1' else text_of(name_node)
            products.append({'name': name, 'category': category(url), 'source_url': url,
                             'product_url': canonical_url(link['href'], url),
                             'record_type': 'catalog_listing', 'details': text_of(block),
                             'price_rate_mentions': money_contexts(block), 'fetched_at': fetched_at})
    elif path not in {'/tariffs', '/currency-rates'} and '/services/' not in path and 'safety-rules' not in path:
        products.append({'name': breadcrumb_name or title, 'category': category(url),
                         'source_url': url, 'product_url': url, 'record_type': 'product_page',
                         'details': page['text'], 'price_rate_mentions': page['price_rate_mentions'],
                         'fetched_at': fetched_at})
    return page, products


def extract_document(path):
    """Read originals without editing them or calculating formulas."""
    if path.suffix.lower() == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(path, data_only=False)
        try:
            sheets = []
            for sheet in book:
                cells = [{'cell': cell.coordinate, 'value': cell.value,
                          'number_format': cell.number_format, 'type': cell.data_type}
                         for row in sheet.iter_rows() for cell in row if cell.value is not None]
                sheets.append({'name': sheet.title, 'cells': cells,
                               'merged_ranges': [str(r) for r in sheet.merged_cells.ranges]})
            return {'sheets': sheets}
        finally:
            book.close()
    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        pages = [{'page': i, 'text': p.extract_text(extraction_mode='layout') or ''}
                 for i, p in enumerate(PdfReader(path).pages, 1)]
        if not any(p['text'].strip() for p in pages):
            raise ScraperError('PDF has no extractable text; original saved, OCR needed')
        return {'pages': pages}
    raise ScraperError('Unsupported document type; original saved')


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def scrape_birbank(output='birbank_data', max_pages=100, delay=1.0, documents=True):
    if max_pages < 1 or delay < 0:
        raise ValueError('max_pages must be positive and delay nonnegative')
    started = datetime.now(ZoneInfo('Asia/Baku'))
    folder = Path(output) / started.strftime('run_%Y%m%d_%H%M%S_%f')
    (folder / 'html').mkdir(parents=True)
    (folder / 'documents').mkdir()
    pages, products, errors, attachments = [], [], [], {}
    queue = deque(BASE_URL + p for p in SEEDS)
    visited = set()
    last_request = 0.0
    rate_limited = False
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'})

    def fetch(url):
        nonlocal last_request
        time.sleep(max(0, delay - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        response = session.get(url, timeout=(10, 40))
        if response.status_code in (403, 429):
            raise ScraperError(f'HTTP {response.status_code}: site refused/rate-limited request')
        response.raise_for_status()
        return response

    try:
        try:
            sitemap = ET.fromstring(fetch(BASE_URL + '/sitemap-az.xml').content)
            queue.extend(canonical_url(e.text) for e in sitemap.iter()
                         if e.tag.endswith('loc') and e.text and in_scope(canonical_url(e.text)))
        except (requests.RequestException, ScraperError, ET.ParseError) as exc:
            errors.append({'url': BASE_URL + '/sitemap-az.xml', 'error': str(exc)})
        while queue and len(visited) < max_pages:
            url = queue.popleft()
            if url in visited or not in_scope(url):
                continue
            visited.add(url)
            try:
                response = fetch(url)
                resolved = canonical_url(response.url)
                if not in_scope(resolved):
                    raise ScraperError(f'Redirected outside product scope: {response.url}')
                if resolved != url and resolved in visited:
                    continue
                visited.add(resolved)
                stamp = datetime.now(ZoneInfo('Asia/Baku')).isoformat()
                page, items = parse_page(response.text, resolved, stamp)
                filename = hashlib.sha256(resolved.encode()).hexdigest()[:16] + '.html'
                (folder / 'html' / filename).write_text(response.text, encoding='utf-8')
                page['html_file'] = 'html/' + filename
                pages.append(page)
                products.extend(items)
                for link in page['links']:
                    target = link['url']
                    if in_scope(target):
                        queue.append(target)
                    if urlsplit(target).netloc == 'birbank.az' and Path(urlsplit(target).path).suffix.lower() in {'.xlsx', '.pdf'}:
                        if target not in attachments:
                            attachments[target] = {'url': target, 'label': link['label'], 'source_pages': [], 'status': 'linked'}
                        attachments[target]['source_pages'].append(resolved)
                print(f'Page {len(pages)}: {resolved}', flush=True)
            except (requests.RequestException, ScraperError) as exc:
                errors.append({'url': url, 'error': str(exc)})
                print(f'Skipped {url}: {exc}', flush=True)
                if '429' in str(exc):
                    rate_limited = True
                    break
        if documents and not rate_limited:
            for url, item in attachments.items():
                try:
                    response = fetch(url)
                    suffix = Path(urlsplit(url).path).suffix.lower()
                    if not response.content.startswith(b'%PDF' if suffix == '.pdf' else b'PK'):
                        raise ScraperError('Response is not the expected document format')
                    filename = hashlib.sha256(url.encode()).hexdigest()[:16] + suffix
                    path = folder / 'documents' / filename
                    path.write_bytes(response.content)
                    item.update({'local_file': str(path.relative_to(folder)), 'status': 'downloaded',
                                 'fetched_at': datetime.now(ZoneInfo('Asia/Baku')).isoformat()})
                    item['content'] = extract_document(path)
                    item['status'] = 'extracted'
                    print(f"Document: {item['label'] or filename}", flush=True)
                except Exception as exc:
                    # A single failed attachment must not discard successful pages.
                    item['error'] = str(exc)
                    errors.append({'url': url, 'error': str(exc)})
                    if '429' in str(exc):
                        break
    finally:
        session.close()
    detail_urls = {p['product_url'] for p in products if p['record_type'] == 'product_page'}
    unique = {}
    for product in products:
        if product['record_type'] == 'catalog_listing' and product['product_url'] in detail_urls:
            continue
        unique[(product['category'], product['name'], product['product_url'])] = product
    products = list(unique.values())
    remaining = sorted({u for u in queue if u not in visited and in_scope(u)})
    manifest = {
        'started_at': started.isoformat(), 'scope': 'Public Azerbaijani product sections on birbank.az',
        'pages_saved': len(pages), 'products_saved': len(products), 'documents_found': len(attachments),
        'documents_extracted': sum(d['status'] == 'extracted' for d in attachments.values()),
        'errors': errors, 'unvisited_pages': remaining,
        'coverage': 'partial' if errors or remaining or (attachments and not documents) else 'completed_configured_scope',
        'limitations': [
            'External order/private/business/investment sites are linked but not crawled.',
            'Only returned HTML is extracted; interactive calculator values are excluded.',
            'Amounts and rates retain context; they are not normalized into a single price.',
            'Document cells retain coordinates, formulas and number formats; formulas are not recalculated.',
            'PDF extraction may not preserve table layout; original documents are saved.',
        ],
    }
    write_json(folder / 'pages.json', pages)
    write_json(folder / 'products.json', products)
    write_json(folder / 'documents.json', list(attachments.values()))
    write_json(folder / 'manifest.json', manifest)
    fields = ['name', 'category', 'record_type', 'price_rate_mentions', 'details', 'product_url', 'source_url', 'fetched_at']
    with (folder / 'products.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for product in products:
            row = dict(product)
            row['price_rate_mentions'] = '\n\n'.join(row['price_rate_mentions'])
            # Keep source strings literal when opened in Excel.
            row = {k: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v for k, v in row.items()}
            writer.writerow(row)
    if not pages:
        raise ScraperError(f"No pages collected. See {folder / 'manifest.json'}")
    print(f"Saved {len(products)} product records, {len(pages)} pages, and {manifest['documents_extracted']} documents to {folder}")
    return {'folder': folder, 'products': products, 'manifest': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='birbank_data')
    parser.add_argument('--max-pages', type=int, default=100)
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--no-documents', action='store_true')
    args = parser.parse_args()
    try:
        result = scrape_birbank(args.output, args.max_pages, args.delay, not args.no_documents)
    except (ScraperError, ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    if result['manifest']['coverage'] == 'partial':
        parser.exit(2, 'Partial export: see manifest.json for missing pages/documents.\n')


if __name__ == '__main__':
    main()
