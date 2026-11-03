"""Collect detailed Birmarket products in the Superchat JSON schema."""

import argparse
import csv
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urljoin, urlsplit, parse_qs
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from birmarket_product import parse_product, apply_translation
from birmarket_errors import ScraperError, FetchBlocked


BASE_URL = "https://birmarket.az"
DEFAULT_CATEGORY = "/categories/15-noutbuklar-ve-komputer-texnikasi"
FIELDS = ["name", "price_azn", "original_price_azn", "url"]


def parse_price(text):
    """Parse AZN amounts, including spaces, nonbreaking spaces and commas."""
    normalized = re.sub(r"\s+", "", text).replace(",", ".")
    match = re.fullmatch(r"(\d+(?:\.\d{1,2})?)₼", normalized)
    if not match:
        raise ScraperError(f"Unrecognized price: {text!r}")
    return Decimal(match.group(1))


def parse_products(html, *, discovery_only=False):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('a[data-info="product-item-link"]')
    if not cards:
        raise ScraperError(
            "No product cards found. The page may be blocked, empty, or changed. "
            "No CSV was written."
        )

    products = []
    for card in cards:
        title = card.select_one('[data-info="product-item-title"]')
        new_price = card.select_one('[data-info="item-desc-price-new"]')
        old_price = card.select_one('[data-info="item-desc-price-old"]')
        # On full-price products the site uses the 'old' field for the price.
        current_price = new_price if new_price is not None else old_price
        href = card.get("href", "")
        link = urljoin(BASE_URL, href)
        if discovery_only:
            # Category cards can hydrate names/prices after their links appear.
            # Detailed collection validates those facts on the product page;
            # discovery needs only a genuine same-site product ID and URL.
            if (urlsplit(link).netloc != urlsplit(BASE_URL).netloc
                    or not re.match(r'^/product/\d+(?:-|$)', urlsplit(link).path)):
                raise ScraperError('A product card has an invalid product URL.')
            products.append({'url': link.split('?', 1)[0].split('#', 1)[0]})
            continue
        if (
            title is None or not title.get_text(strip=True)
            or current_price is None
            or urlsplit(link).netloc != urlsplit(BASE_URL).netloc
            or not urlsplit(link).path.startswith("/product/")
        ):
            raise ScraperError("A product is missing its name, price, or valid URL.")
        products.append({
            "name": title.get_text(" ", strip=True),
            "price_azn": parse_price(current_price.get_text(" ", strip=True)),
            "original_price_azn": (
                parse_price(old_price.get_text(" ", strip=True))
                if new_price is not None and old_price is not None else None
            ),
            "url": link.split("?", 1)[0].split("#", 1)[0],
        })
    return products, soup


def scrape_products(category=DEFAULT_CATEGORY, pages=2, delay=2):
    """Fetch at most `pages` pages, stopping at the last pagination link."""
    if pages < 1 or delay < 0:
        raise ValueError("pages must be positive and delay must be nonnegative")
    if not category.startswith("/categories/") or "?" in category or "#" in category:
        raise ValueError("category must be a /categories/... path without a query")

    products = []
    seen = set()
    with requests.Session() as session:
        for page in range(1, pages + 1):
            if page > 1:
                time.sleep(delay)
            url = f"{BASE_URL}{category}?page={page}"
            try:
                response = session.get(url, timeout=(10, 30))
                if response.status_code in (403, 429):
                    raise ScraperError(
                        f"HTTP {response.status_code} at {url}. The site refused "
                        "or rate-limited the request. Stop and try later; "
                        "no CSV was written."
                    )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ScraperError(f"Could not fetch {url}: {exc}") from exc

            rows, soup = parse_products(response.text)
            added = 0
            for product in rows:
                if product["url"] not in seen:
                    seen.add(product["url"])
                    products.append(product)
                    added += 1
            if added == 0:
                raise ScraperError(f"Page {page} repeated earlier products; check pagination.")
            print(f"Page {page}: {added} new products")

            next_path = f"{category}?page={page + 1}"
            if not any(
                urljoin(BASE_URL, a.get("href", "")) == BASE_URL + next_path
                for a in soup.select("a[href]")
            ):
                break
    return products


def save_csv(products, output="birmarket_products.csv"):
    if not products:
        raise ScraperError("No products to save; existing CSV left unchanged.")
    output = Path(output)
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(products)
    return output


class Client:
    def __init__(self, delay):
        self.delay = delay
        self.last = 0.0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'})

    def get(self, url, headers=None):
        for attempt in range(3):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            response = self.session.get(url, headers=headers, timeout=(10, 40))
            if response.status_code in (403, 429):
                raise FetchBlocked(f'HTTP {response.status_code}: {url}. Run stopped; try later.')
            if response.status_code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            return response

    def close(self):
        self.session.close()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def save_products_csv(path, products):
    fields = list(products[0])
    with path.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for product in products:
            row = {}
            for key, value in product.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
                    value = "'" + value
                row[key] = value
            writer.writerow(row)


def has_next_page(soup, path, page):
    for anchor in soup.select('a[href]'):
        link = urlsplit(urljoin(BASE_URL, anchor['href']))
        if link.netloc == 'birmarket.az' and link.path.rstrip('/') == path.rstrip('/'):
            if parse_qs(link.query).get('page') == [str(page + 1)]:
                return True
    return False


def scrape_catalog(categories=None, per_category=100, pages=10, delay=2.0,
                   output='SuperChat_Real_Data', russian=True, download_images=False,
                   product_urls=None, max_images=1, browser=False, existing_products=None):
    """Collect full product records. Use per_category=0 for all products in `pages`."""
    if pages < 1 or per_category < 0 or delay < 0 or max_images < 0:
        raise ValueError('pages must be positive; per_category and delay must be nonnegative')
    if categories is None:
        categories = json.loads(Path(__file__).with_name('birmarket_categories.json').read_text())
    for name, path in categories.items():
        if not path.startswith('/categories/') or '?' in path or '#' in path:
            raise ValueError(f'Invalid category path for {name}: {path}')
    product_urls = product_urls or []
    for url in product_urls:
        if urlsplit(url).netloc != 'birmarket.az' or not urlsplit(url).path.startswith('/product/'):
            raise ValueError('Product URLs must start with https://birmarket.az/product/')
    root = Path(output)
    folder = root / 'birmarket'
    image_cache = {}
    previous_export = folder / 'products.json'
    if download_images and previous_export.exists():
        for previous in json.loads(previous_export.read_text(encoding='utf-8')):
            for image in previous.get('images', []):
                if image.get('local_file'):
                    local = (root / image['local_file']).resolve()
                    if local.is_relative_to(root.resolve()) and local.is_file() and local.stat().st_size:
                        image_cache[image['url']] = local
    stamp = datetime.now(ZoneInfo('Asia/Baku'))
    run = folder / 'runs' / stamp.strftime('%Y%m%d_%H%M%S_%f')
    (run / 'sources').mkdir(parents=True)
    products = json.loads(Path(existing_products).read_text()) if existing_products else []
    retained_count = len(products)
    errors, seen = [], {p['id'] for p in products}
    counts = {key: sum(p['category'] == key for p in products) for key in categories}
    page_counts, stop_reasons = {}, {}
    if browser:
        from birmarket_browser import BrowserClient
        client = BrowserClient(delay)
    else:
        client = Client(delay)
    stopped = False

    def collect(url, group, category_url=None):
        response = client.get(url)
        if urlsplit(response.url).netloc != 'birmarket.az' or '/product/' not in urlsplit(response.url).path:
            raise ScraperError(f'Unexpected product redirect: {response.url}')
        fetched = datetime.now(ZoneInfo('Asia/Baku')).isoformat()
        product, raw = parse_product(response.text, response.url, group, fetched)
        if product['id'] in seen:
            return
        product['category_url'] = category_url
        product['image_files'] = []
        source_path = run / 'sources' / (product['id'] + '.json')
        write_json(source_path, raw)
        product['source_file'] = str(source_path.relative_to(root))
        if russian:
            soup = BeautifulSoup(response.text, 'html.parser')
            ru_link = soup.select_one('a[data-info="footer-lang-ru"]')
            ru_url = urljoin(BASE_URL, ru_link['href']) if ru_link else BASE_URL + '/ru' + urlsplit(response.url).path
            try:
                if urlsplit(ru_url).netloc != 'birmarket.az':
                    raise ScraperError('Unexpected Russian translation host')
                translation = client.get(ru_url)
                apply_translation(product, translation.text, translation.url)
            except FetchBlocked:
                # Keep the successfully collected AZ product before stopping.
                products.append(product)
                seen.add(product['id'])
                counts[group] = counts.get(group, 0) + 1
                raise
            except (requests.RequestException, ValueError, ScraperError) as exc:
                product['data_warnings'].append(f'Russian translation unavailable: {exc}')
                errors.append({'url': ru_url, 'stage': 'translation', 'error': str(exc)})
        if download_images:
            for index, image in enumerate(product['images'][:max_images] if max_images else product['images'], 1):
                image_url = image['url']
                try:
                    cached = image_cache.get(image_url)
                    if cached:
                        path = run / 'images' / product['id'] / f'{index:02}{cached.suffix}'
                        path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(cached, path)
                        local = str(path.relative_to(root))
                        image['local_file'] = local
                        product['image_files'].append(local)
                        continue
                    if urlsplit(image_url).hostname not in {'strgimgr.umico.az', 'strgimgr.b-cdn.net'}:
                        raise ScraperError('Image host not in the configured Birmarket image hosts')
                    photo = client.get(image_url, headers={
                        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                        'Referer': product['url'],
                    })
                    media_type = photo.headers.get('Content-Type', '').split(';')[0]
                    suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/avif': '.avif'}.get(media_type)
                    if suffix is None:
                        raise ScraperError(f'Unsupported image response: {media_type}')
                    path = run / 'images' / product['id'] / f'{index:02}{suffix}'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(photo.content)
                    local = str(path.relative_to(root))
                    image['local_file'] = local
                    product['image_files'].append(local)
                except FetchBlocked:
                    products.append(product)
                    seen.add(product['id'])
                    counts[group] = counts.get(group, 0) + 1
                    raise
                except (requests.RequestException, ScraperError) as exc:
                    status = exc.response.status_code if isinstance(exc, requests.HTTPError) and exc.response is not None else None
                    image['download_status'] = 'unavailable' if status in (404, 410) else 'failed'
                    image['download_error'] = str(exc)
                    errors.append({'url': image_url, 'stage': 'image', 'error': str(exc)})
        products.append(product)
        seen.add(product['id'])
        counts[group] = counts.get(group, 0) + 1
        print(f"{len(products)} | {group} | {product['name']['az']} | {product['price_azn']} AZN", flush=True)

    try:
        for group, path in categories.items():
            page_counts[group] = 0
            stop_reasons[group] = 'page_limit'
            visited_listings = set()
            for page in range(1, pages + 1):
                if per_category and counts[group] >= per_category:
                    stop_reasons[group] = 'product_limit'
                    break
                category_url = f'{BASE_URL}{path}?page={page}'
                try:
                    response = client.get(category_url)
                    listings, soup = parse_products(response.text, discovery_only=True)
                    page_counts[group] += 1
                except FetchBlocked:
                    raise
                except (requests.RequestException, ScraperError) as exc:
                    errors.append({'url': category_url, 'stage': 'category', 'error': str(exc)})
                    stop_reasons[group] = 'fetch_error'
                    break
                page_listing_urls = frozenset(listing['url'] for listing in listings)
                if page_listing_urls in visited_listings:
                    stop_reasons[group] = 'repeated_page'
                    errors.append({'url': category_url, 'stage': 'category', 'error': 'Pagination repeated a previously visited page'})
                    break
                visited_listings.add(page_listing_urls)
                for listing in listings:
                    if per_category and counts[group] >= per_category:
                        break
                    source_id = re.search(r'/product/(\d+)', listing['url'])
                    if source_id and 'BM-' + source_id[1] in seen:
                        continue
                    try:
                        collect(listing['url'], group, category_url)
                    except FetchBlocked:
                        raise
                    except (requests.RequestException, ValueError, ScraperError) as exc:
                        errors.append({'url': listing['url'], 'stage': 'product', 'error': str(exc)})
                        print(f"Skipped {listing['url']}: {exc}", flush=True)
                if per_category and counts[group] >= per_category:
                    stop_reasons[group] = 'product_limit'
                    break
                if not has_next_page(soup, path, page):
                    stop_reasons[group] = 'end_of_category'
                    break
        for url in product_urls:
            try:
                collect(url, 'other')
            except FetchBlocked:
                raise
            except (requests.RequestException, ValueError, ScraperError) as exc:
                errors.append({'url': url, 'stage': 'product', 'error': str(exc)})
    except FetchBlocked as exc:
        errors.append({'stage': 'request', 'error': str(exc)})
        stopped = True
    finally:
        client.close()

    # Link already-fetched variants without inventing their price or availability.
    lookup = {p['id']: p for p in products}
    for product in products:
        for variant in product['variants']:
            if variant['id'] in lookup:
                actual = lookup[variant['id']]
                variant.update(price_azn=actual['price_azn'], in_stock=actual['in_stock'])
    manifest = {
        'source': BASE_URL, 'fetched_at': stamp.isoformat(), 'run_directory': str(run.relative_to(root)),
        'product_count': len(products), 'counts_by_category': counts,
        'requested_per_category': per_category, 'max_pages_per_category': pages,
        'pages_collected_by_category': page_counts, 'category_stop_reasons': stop_reasons,
        'max_images_per_product': max_images,
        'collection_transport': 'chrome_browser' if browser else 'http',
        'retained_product_count': retained_count, 'new_product_count': len(products) - retained_count,
        'category_mapping': categories, 'explicit_product_urls': product_urls,
        'stopped_by_site': stopped, 'errors': errors,
        'coverage': 'partial' if stopped or any(e.get('stage') != 'image' for e in errors) else 'configured_sample_collected',
        'image_count': sum(len(p['images']) for p in products),
        'downloaded_images': sum(len(p['image_files']) for p in products),
        'image_coverage': ('not_requested' if not download_images else
                           'complete' if all(len(p['images']) == len(p['image_files']) for p in products) else 'partial'),
        'russian_names': sum(bool(p['name']['ru']) for p in products),
        'limitations': [
            'This is the configured category/page sample, not the entire Birmarket inventory.',
            'English translations and exact stock quantities are unknown and remain null.',
            'Sizes/colors describe listed variants; prices and stock of unfetched variants remain null.',
            'Delivery, promotions and seller prices are snapshots and may depend on location or checkout.',
            'Missing dimensions, warranty or descriptions mean the source did not publish them in the fetched data.',
            'Image URLs are remote unless local_file is present. Mock files are preserved.',
        ],
    }
    write_json(run / 'manifest.json', manifest)
    if not products:
        raise ScraperError(f'No products collected; see {run / "manifest.json"}. Previous exports are unchanged.')
    write_json(run / 'products.json', products)
    save_products_csv(run / 'products.csv', products)
    # Stable paths for the Superchat application; the run folder preserves history.
    write_json(folder / 'products.json', products)
    save_products_csv(folder / 'products.csv', products)
    write_json(folder / 'manifest.json', manifest)
    print(f'Saved {len(products)} products to {folder.resolve() / "products.json"}', flush=True)
    return {'products': products, 'manifest': manifest, 'folder': folder, 'dataset_root': root, 'run': run}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--categories-file', type=Path, default=Path(__file__).with_name('birmarket_categories.json'))
    parser.add_argument('--category', action='append', help='Override mapping: category_name=/categories/...')
    parser.add_argument('--product-url', action='append', help='Fetch a specific Birmarket product URL')
    parser.add_argument('--per-category', type=int, default=100, help='0 collects all products within --pages')
    parser.add_argument('--pages', type=int, default=10)
    parser.add_argument('--delay', type=float, default=2.0)
    parser.add_argument('--max-images', type=int, default=1, help='Images to download per product; 0 downloads all gallery images')
    parser.add_argument('--output', default='SuperChat_Real_Data')
    parser.add_argument('--no-russian', action='store_true')
    parser.add_argument('--download-images', action='store_true')
    parser.add_argument('--browser', action='store_true', help='Use installed Chrome in an isolated visible browser session')
    parser.add_argument('--existing-products', type=Path, help='Expand a validated existing catalogue, preserving earlier record timestamps')
    args = parser.parse_args()
    try:
        categories = json.loads(args.categories_file.read_text())
        if args.category:
            categories = dict(item.split('=', 1) for item in args.category)
        elif args.product_url:
            categories = {}
        result = scrape_catalog(categories, args.per_category, args.pages, args.delay,
                                args.output, not args.no_russian, args.download_images, args.product_url, args.max_images, args.browser, args.existing_products)
    except (ScraperError, ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    if result['manifest']['coverage'] == 'partial':
        parser.exit(2, 'Partial export saved; see manifest.json.\n')


if __name__ == "__main__":
    main()
