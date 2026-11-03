"""Conservative multilingual query normalization; unknown requested terms survive."""
import re
from .repositories import normalize

NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'bir': 1, 'iki': 2, 'uc': 3, 'dord': 4, 'bes': 5, 'alti': 6,
    'yeddi': 7, 'sekkiz': 8, 'doqquz': 9, 'on': 10,
    'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5,
    'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9, 'десять': 10,
}


def result_request(text, domain):
    """Extract list size only next to a result noun; retain numeric titles/model IDs."""
    t = normalize(text)
    nouns = {
        'cinema': r'films?|movies?|filmler\w*|film|фильм\w*|showtimes?|seans\w*|сеанс\w*',
        'shopping': r'products?|items?|mehsul\w*|товар\w*|laptops?|phones?|headphones|noutbuk\w*|telefon\w*|ноутбук\w*',
        'flights': r'flights?|ucus\w*|рейс\w*',
    }[domain]
    model_spans = []
    if domain == 'shopping':
        from .nlu import PRODUCT_MODEL
        model_spans = [m.span() for m in PRODUCT_MODEL.finditer(t)]
    candidates = re.finditer(r'(?<![\w"«“])(?P<number>\d{1,3}|' + '|'.join(NUMBER_WORDS) + r')\s+(?P<noun>' + nouns + r')(?!\w)', t)
    match = next((m for m in candidates if not any(start <= m.start('number') < end for start, end in model_spans)), None)
    if not match:
        return None, False, t
    raw = match['number']
    count = int(raw) if raw.isdigit() else NUMBER_WORDS[raw]
    if not 1 <= count <= 100:
        return None, False, t
    movies = domain == 'cinema' and not re.match(r'showtime|seans|сеанс', match['noun'])
    return min(count, 20), movies, t[:match.start('number')] + t[match.end('number'):]


def remove_terms(text, terms, stems=False):
    for term in sorted(terms, key=len, reverse=True):
        ending = r'\w*' if stems and len(term) >= 4 else r'(?!\w)'
        text = re.sub(r'(?<!\w)' + re.escape(normalize(term)) + ending, ' ', text)
    return text


def request_terms(text, domain, known_names=()):
    from .nlu import PRODUCTS, CATEGORY, GENRES, WEEKDAYS
    _, _, t = result_request(text, domain)
    # IDs and ordinal/action turns already have authoritative selection semantics.
    if re.search(r'\b(?:bm-\d+|cm-[msc]-[a-f0-9]{16})\b', t):
        return ''
    # Context describes purpose, not an additional product/title constraint.
    t = re.split(r'\b(?:for my|for university|for school|after my|after exams|после экзам|для учеб|imtahan ucun|imtahandan sonra)\w*', t)[0]
    t = re.sub(r"(?<=\w)['’]s\b", '', t)
    t = re.sub(r'\b20\d{2}-\d{2}-\d{2}\b', ' ', t)
    t = re.sub(r'\b(?:under|below|over|above|up to|at least|maximum|max|minimum|min|до|от|выше|не дороже)\s*\d+(?:[.,]\d+)?', ' ', t)
    t = re.sub(r'\b\d+(?:[.,]\d+)?\s*(?:azn|manat)(?:dan|den)?(?:\s+(?:asagi|ucuz|az|qeder))?', ' ', t)
    t = re.sub(r'\b(?:after|before|sonra|evvel|после|до)\s*\d{1,2}(?::\d{2})?', ' ', t)
    vocab = (list(PRODUCTS.values()) + list(CATEGORY.values())) if domain == 'shopping' else list(GENRES.values()) + WEEKDAYS
    t = remove_terms(t, [v for words in vocab for v in words] + list(known_names), stems=True)
    t = remove_terms(t, ['film', 'movie', 'seans', 'kinoteatr', 'фильм', 'сеанс', 'товар', 'mehsul'], stems=True)
    t = remove_terms(t, ['wireless', 'simsiz', 'беспровод', 'black', 'qara', 'черн', 'white', 'ag', 'бел',
                         'blue', 'mavi', 'син', 'red', 'qirmizi', 'красн', 'silver', 'gumus', 'серебр', 'grey', 'gray', 'boz', 'серый'], stems=True)
    words = '''show find search send give gives list recommend suggest please can could you me i want need would like
    what which is are do does have has to good option options
    back return more next page again geri qayit daha cox novbeti sehife снова вернем еще следующая страница
    all any a an the something products product items item buy phones films film movie movies cinema showtime
    showtimes playing tickets ticket today tonight tomorrow now this in at on for with called named
    under azn price cheap cheaper cheapest expensive budget available stock details rating rated best
    mene men zehmet olmasa goster gonder tap axtar isteyirem lazim butun hamisi mehsul mehsullar almaq
    bu gun sabah axsam seher film filmler kino kinoteatr seans seanslar bilet dil dilinde ucuz qiymet
    stokda olan var hansi adi adli ve
    покажи покажите пришли пришлите отправь найди найдите ищи мне я хочу нужен нужна нужно нужны все любой товары товар
    какие какой какая что есть
    фильм фильмы кино кинотеатр сеанс сеансы билет билеты сегодня завтра вечером утром
    в на по и пожалуйста названием называется наличи цена дешев рейтинг
    english russian azerbaijani ingilis rus azerbaycan английск русск азербайджан
    '''.split()
    t = remove_terms(t, words)
    return ' '.join(re.findall(r'[\w-]+', t))


def product_query(text, known_brands):
    from .nlu import parse_filters
    filters = parse_filters(text, 'shopping')
    residual = request_terms(text, 'shopping')
    if not residual:
        return None
    # A short model/name request may contain unknown words. They must never be discarded.
    base = filters.get('query')
    return ' '.join([base, residual]) if base and base not in residual else residual
