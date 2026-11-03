"""Localize known attributes without generating unverified product claims."""
import re
from .repositories import color_key, language_key, normalize

PRODUCT_TYPES = {
    'audio': ('Audio product', 'Audio məhsul', 'Аудиотовар'),
    'computers': ('Computer', 'Kompüter', 'Компьютер'),
    'phones': ('Smartphone', 'Smartfon', 'Смартфон'),
    'wearables': ('Wearable device', 'Geyilə bilən cihaz', 'Носимое устройство'),
    'sport': ('Footwear', 'Ayaqqabı', 'Обувь'),
    'accessories': ('Bag', 'Çanta', 'Сумка'),
    'home': ('Home appliance', 'Məişət texnikası', 'Бытовая техника'),
    'gifts': ('Game', 'Oyun', 'Игра'),
}


def english_product_name(row):
    source = row['name'].get('az') or row['name'].get('ru') or ''
    prefixes = {'simsiz qulaqlıq': 'Wireless headphones', 'qulaqlıq': 'Headphones',
                'smartfon': 'Smartphone', 'notbuk': 'Laptop', 'noutbuk': 'Laptop',
                'fitnes qolbaq': 'Fitness band', 'ağıllı saat': 'Smartwatch',
                'qəhvəbişirən': 'Coffee maker', 'qəhvə maşını': 'Coffee machine',
                'bel çantası': 'Backpack', 'portativ dinamik': 'Portable speaker'}
    for prefix, translated in prefixes.items():
        if source.lower().startswith(prefix):
            name = translated + source[len(prefix):]
            for word, value in [('qara', 'black'), ('ağ', 'white'), ('mavi', 'blue'), ('boz', 'grey'), ('parça', 'fabric'), ('ölçü', 'size')]:
                name = re.sub(r'\b' + word + r'\b', value, name, flags=re.I)
            if not re.search(r'[əğıüşçöа-я]', name, re.I):
                return name
    # A concise label derived solely from recorded fields, not a guessed translation.
    brand = row.get('brand')
    if brand and normalize(brand) == 'no brand':
        brand = None
    return ' · '.join(str(v) for v in [PRODUCT_TYPES.get(row['category'], ('Product',))[0], brand, row.get('model') or row['id']] if v)


def localize_card(card, row, domain, lang):
    """Database UI uses local labels, with original names retained for provenance."""
    if domain == 'shopping':
        card['source_title'] = row['name'].get(lang) or row['name'].get('az') or row['name'].get('ru')
        if lang == 'en' and not row['name'].get('en'):
            card['title'] = english_product_name(row)
            card['content_language'] = 'en'
            # Source marketing prose is not an English translation. Display factual fields.
            for field in card['fields']:
                if field['label'] == 'description':
                    field['value'] = f"Model: {row['model']}" if row.get('model') else None
        for field in card['fields']:
            if field['label'] == 'color' and field['value']:
                field['value'] = color_key(field['value'])
    elif domain == 'cinema':
        from .nlu import GENRES, has
        for field in card['fields']:
            if field['label'] == 'genre':
                field['value'] = ', '.join(next((k for k, names in GENRES.items() if has(normalize(g), names)), g) for g in row['movie']['genre'])
            if field['label'] == 'language':
                field['value'] = ', '.join(language_key(v) for v in row.get('languages', []) or [row['movie'].get('language') or '']) or None
    return card
