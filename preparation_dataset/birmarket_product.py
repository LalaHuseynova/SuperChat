"""Normalize public product details into the Superchat product schema."""

from decimal import Decimal, InvalidOperation
from html import unescape
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from birmarket_state import decode_state

BASE_URL = 'https://birmarket.az'


def clean(value):
    return BeautifulSoup(str(value or ''), 'html.parser').get_text(' ', strip=True)


def description_images(value):
    fragment = BeautifulSoup(unescape(str(value or '')), 'html.parser')
    return list(dict.fromkeys(urljoin(BASE_URL, image['src']) for image in fragment.select('img[src]')
                             if urlsplit(urljoin(BASE_URL, image['src'])).scheme in {'http', 'https'}))


def number(value):
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        result = Decimal(re.sub(r'[\s₼]', '', str(value)).replace(',', '.'))
        return float(result) if result.is_finite() else None
    except InvalidOperation:
        return None


def discount(price, old_price):
    if price is None or old_price is None or old_price <= price or old_price <= 0:
        return {'has_discount': False, 'discount_amount_azn': None, 'discount_percent': None}
    saving = Decimal(str(old_price)) - Decimal(str(price))
    return {'has_discount': True, 'discount_amount_azn': float(saving.quantize(Decimal('.01'))),
            'discount_percent': float((saving / Decimal(str(old_price)) * 100).quantize(Decimal('.01')))}


def source_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    schema = {}
    def find_product(obj):
        if isinstance(obj, list):
            for value in obj:
                found = find_product(value)
                if found:
                    return found
        elif isinstance(obj, dict):
            types = obj.get('@type', [])
            if types == 'Product' or isinstance(types, list) and 'Product' in types:
                return obj
            return find_product(obj.get('@graph', []))
        return None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            found = find_product(json.loads(script.get_text()))
            if found:
                schema = found
                break
        except json.JSONDecodeError:
            continue
    state, warnings = {}, []
    for script in soup.select('script'):
        if script.string and re.match(r'\s*window\.__(?:UMICO|NUXT)__\s*=', script.string):
            try:
                state = decode_state(script.string)
            except Exception as exc:
                warnings.append(f'Embedded product data could not be decoded: {type(exc).__name__}: {exc}')
            break
    market = state.get('pinia', {}).get('market', {})
    product = market.get('product') or {}
    if not product and not schema:
        raise ValueError('No product data found; page may be blocked or changed')
    return soup, schema, state, market, product, warnings


def labeled_fields(fields, labels):
    return [{'id': field.get('master_field_id'),
             'name': labels.get(field.get('master_field_id'), str(field.get('master_field_id'))),
             'values': [clean(v) for v in field.get('values', [])]}
            for field in fields]


def matching_values(specs, predicate):
    return list(dict.fromkeys(v for field in specs if predicate(field['name'].casefold())
                              for v in field['values'] if v))


def is_size(label):
    # Physical dimensions and display sizes are separate from clothing sizes.
    return label in {'ölçü', 'ölçüsü', 'razmer', 'размер'} or any(
        term in label for term in ['ayaqqabı ölçü', 'geyim ölçü', 'размер обув', 'размер одеж'])


def is_color(label):
    return label in {'rəng', 'rəngi', 'цвет'}


def normalize_offer(offer, delivery):
    seller = offer.get('seller') or {}
    marketing = seller.get('marketing_name') or {}
    price, old = number(offer.get('retail_price')), number(offer.get('old_price'))
    discounted = discount(price, old)
    return {
        'id': offer.get('uuid'), 'seller_id': offer.get('supplier_id'),
        'seller_name': marketing.get('name') if isinstance(marketing, dict) else str(marketing),
        'seller_rating': seller.get('rating'), 'price_azn': price,
        'original_price_azn': old if discounted['has_discount'] else None,
        **discounted, 'installment_enabled': offer.get('installment_enabled'),
        'max_installment_months': offer.get('max_installment_months'),
        'discount_start': offer.get('discount_effective_start_date') or None,
        'discount_end': offer.get('discount_effective_end_date') or None,
        'labels': offer.get('product_offer_labels', []), 'comment': clean(offer.get('comment')),
        'delivery_methods': delivery.get(offer.get('supplier_id'), []),
    }


def parse_product(html, url, category, fetched_at):
    soup, schema, state, market, product, warnings = source_data(html)
    product_id = product.get('id') or schema.get('sku')
    if not product_id:
        raise ValueError('Product ID is missing')
    category_data = market.get('productCategory') or {}
    labels = {f['master_field_id']: f['name'] for f in
              category_data.get('custom_fields', []) + category_data.get('variations', [])}
    specs = labeled_fields(product.get('custom_fields', []), labels)
    # DOM is also useful when one label isn't included in embedded metadata.
    for row in soup.select('[data-info="product-features-row"]'):
        key = row.select_one('[data-info="product-features-name"]')
        val = row.select_one('[data-info="product-features-value"]')
        if key and val:
            name = key.get_text(' ', strip=True).rstrip(':')
            if not any(f['name'] == name for f in specs):
                specs.append({'id': None, 'name': name, 'values': [val.get_text(' ', strip=True)]})
    colors = matching_values(specs, is_color)
    sizes = matching_values(specs, is_size)
    variants = []
    for variant in market.get('productVariations') or []:
        fields = labeled_fields(variant.get('custom_fields', []), labels)
        variant_colors = matching_values(fields, is_color)
        variant_sizes = matching_values(fields, is_size)
        colors.extend(v for v in variant_colors if v not in colors)
        sizes.extend(v for v in variant_sizes if v not in sizes)
        variants.append({
            'id': f"BM-{variant['id']}", 'source_product_id': str(variant['id']),
            'name': variant.get('name'), 'attributes': fields,
            'colors': variant_colors, 'sizes': variant_sizes,
            'url': f"{BASE_URL}/product/{variant['id']}-{variant['slugged_name']}",
            'image_url': (variant.get('main_img') or {}).get('big'),
            'listing_status': variant.get('status'),
            'price_azn': None, 'in_stock': None,
        })
    offer = product.get('default_offer') or {}
    schema_offer = schema.get('offers') or {}
    if isinstance(schema_offer, list):
        schema_offer = schema_offer[0] if schema_offer else {}
    price = number(offer.get('retail_price'))
    if price is None:
        price = number(schema_offer.get('price', schema_offer.get('lowPrice')))
    old = number(offer.get('old_price'))
    price_block = soup.select_one('[data-info="product-price-main"]')
    if price_block:
        current = price_block.select_one('[data-info="item-desc-price-new"]')
        previous = price_block.select_one('[data-info="item-desc-price-old"]')
        if price is None:
            price = number((current or previous).get_text()) if current or previous else None
        if old is None and current and previous:
            old = number(previous.get_text())
    deal = discount(price, old)
    discount_node = price_block.select_one('[data-info="discount-label"]') if price_block else None
    availability = schema_offer.get('availability')
    status = availability.rsplit('/', 1)[-1] if availability else None
    in_stock = True if status == 'InStock' else False if status in {'OutOfStock', 'SoldOut', 'Discontinued'} else None
    image_list = product.get('imgs') or []
    if not image_list:
        urls = schema.get('image', [])
        urls = [urls] if isinstance(urls, str) else urls
        image_list = [{'big': u} for u in urls if isinstance(u, str)]
    images = []
    for img in image_list:
        src = img.get('big') or img.get('medium') or img.get('small')
        if src and src not in [i['url'] for i in images]:
            images.append({'url': src, 'thumbnail_url': img.get('small'), 'medium_url': img.get('medium')})
    brand = product.get('brand') or schema.get('brand') or {}
    brand = brand.get('name') if isinstance(brand, dict) else str(brand)
    ratings = product.get('ratings') or {}
    aggregate = schema.get('aggregateRating') or {}
    rating = number(ratings.get('rating_value', aggregate.get('ratingValue')))
    if rating == 0 and ratings.get('session_count', 0) == 0:
        rating = None
    delivery = state.get('pinia', {}).get('product', {}).get('list_offers_delivery', {})
    offers = [normalize_offer(o, delivery) for o in market.get('productOffers') or []]
    if offer and not any(o['id'] == offer.get('uuid') for o in offers):
        offers.insert(0, normalize_offer(offer, delivery))
    breadcrumbs = []
    parent = category_data
    while parent:
        breadcrumbs.insert(0, {'id': parent.get('id'), 'name': parent.get('name')})
        parent = parent.get('parent')
    name = clean(product.get('name') or schema.get('name'))
    description = clean(product.get('description') or schema.get('description'))
    description_pictures = description_images(product.get('description') or schema.get('description'))
    for src in description_pictures:
        if src not in [image['url'] for image in images]:
            images.append({'url': src, 'thumbnail_url': None, 'medium_url': None, 'kind': 'description'})
    result = {
        'id': f'BM-{product_id}', 'source_product_id': str(product_id),
        'name': {'en': None, 'az': name, 'ru': None}, 'category': category,
        'brand': brand, 'price_azn': price, 'rating': rating,
        'stock': None, 'color': matching_values(specs, is_color)[0] if matching_values(specs, is_color) else None,
        'description': description, 'descriptions': {'en': None, 'az': description or None, 'ru': None},
        'description_images': description_pictures,
        'original_price_azn': old if deal['has_discount'] else None, **deal,
        'discount_label': discount_node.get_text(' ', strip=True) if discount_node else None,
        'discount_start': offer.get('discount_effective_start_date') or None,
        'discount_end': offer.get('discount_effective_end_date') or None,
        'currency': schema_offer.get('priceCurrency', 'AZN'), 'in_stock': in_stock,
        'availability': status, 'stock_note': 'Exact quantity is not verified; page qty fields may be placeholders.',
        'rating_count': ratings.get('session_count'),
        'review_count': ratings.get('review_count', aggregate.get('reviewCount')),
        'image_url': images[0]['url'] if images else None, 'images': images,
        'image_urls': [i['url'] for i in images], 'videos': product.get('videos') or [],
        'size': matching_values(specs, is_size)[0] if matching_values(specs, is_size) else None,
        'sizes': sizes, 'colors': colors, 'variants': variants,
        'variant_price_note': 'Variant prices and stock are unknown unless the variant was fetched as a product.',
        'specifications': specs,
        'dimensions': [s for s in specs if re.search(r'ölçülər|eni|uzunlu|hündür|çəki|diametr|объем|габарит|ширин|высот|длин|вес', s['name'], re.I)],
        'warranty': [s for s in specs if re.search(r'zəmanət|гарант', s['name'], re.I)],
        'model': product.get('mpn') or schema.get('mpn'), 'gtin': product.get('gtin') or schema.get('gtin'),
        'condition': schema.get('itemCondition'), 'refurbished': product.get('is_refurbished'),
        'source_category': {'id': category_data.get('id'), 'name': category_data.get('name'), 'breadcrumbs': breadcrumbs},
        'seller': normalize_offer(offer, delivery) if offer else None, 'offers': offers,
        'offer_count': schema_offer.get('offerCount', len(offers)),
        'offer_price_range': {'low_azn': number(schema_offer.get('lowPrice')), 'high_azn': number(schema_offer.get('highPrice'))},
        'shipping': schema_offer.get('shippingDetails'), 'return_policy': schema_offer.get('hasMerchantReturnPolicy'),
        'refundable': product.get('is_refundable'), 'minimum_order_quantity': product.get('min_qty'),
        'promotions': product.get('product_labels') or [], 'size_chart': market.get('sizeChart'),
        'url': url, 'source': 'birmarket.az', 'fetched_at': fetched_at,
        'source_urls': {'az': url}, 'data_warnings': warnings,
    }
    for variant in variants:
        if variant['id'] == result['id']:
            variant.update(price_azn=price, in_stock=in_stock)
    result['missing_fields'] = [k for k in ['brand', 'price_azn', 'rating', 'stock', 'color', 'description', 'image_url', 'size']
                                if result[k] is None or result[k] == '']
    raw = {'product': product, 'category': category_data, 'offers': market.get('productOffers'),
           'variations': market.get('productVariations'), 'size_chart': market.get('sizeChart'),
           'schema': {k: v for k, v in schema.items() if k != 'review'}}
    return result, raw


def apply_translation(result, html, url):
    soup, schema, state, market, product, warnings = source_data(html)
    if str(product.get('id') or schema.get('sku')) != result['source_product_id']:
        raise ValueError('Translation page points to a different product')
    if not soup.html or not str(soup.html.get('lang', '')).startswith('ru'):
        raise ValueError('Russian URL did not return a Russian page')
    result['name']['ru'] = clean(product.get('name') or schema.get('name')) or None
    result['descriptions']['ru'] = clean(product.get('description') or schema.get('description')) or None
    result['source_urls']['ru'] = url
    result['data_warnings'].extend(warnings)
