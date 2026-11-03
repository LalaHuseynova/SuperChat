"""Check cinema exports, relationships and downloaded image references."""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path


def validate_dataset(root):
    root = Path(root)
    folder = root / 'cinema'
    tables = {n: json.loads((folder / (n + '.json')).read_text()) for n in ('movies', 'cinemas', 'showtimes')}
    errors = []
    checks = 0

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    required = {'movies': ['id', 'title', 'genre', 'language', 'duration_min', 'age_rating', 'rating', 'synopsis'],
                'cinemas': ['id', 'name', 'district', 'address'],
                'showtimes': ['id', 'movie_id', 'cinema_id', 'date', 'time', 'hall', 'price_azn', 'seats_total', 'seats_available']}
    ids = {name: {row['id'] for row in rows} for name, rows in tables.items()}
    for name, rows in tables.items():
        check(len(ids[name]) == len(rows), f'{name}: duplicate IDs')
        with (folder / (name + '.csv')).open(encoding='utf-8-sig', newline='') as file:
            csv_rows = list(csv.DictReader(file))
        check(len(csv_rows) == len(rows), f'{name}: CSV row count differs')
        for row, csv_row in zip(rows, csv_rows):
            check(set(required[name]) <= set(row), f'{name}/{row["id"]}: mock-compatible fields missing')
            for key, value in row.items():
                actual = csv_row.get(key)
                if isinstance(value, (dict, list)):
                    valid = json.loads(actual) == value
                else:
                    expected = '' if value is None else str(value)
                    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
                        expected = "'" + value
                    valid = actual == expected
                check(valid, f'{name}/{row["id"]}/{key}: CSV differs')
            for path in ([row['poster_file']] if row.get('poster_file') else []) + row.get('tariff_image_files', []):
                check((root / path).is_file() and (root / path).stat().st_size > 0, f'Missing image: {path}')
    for row in tables['showtimes']:
        key = row['id']
        check(row['movie_id'] in ids['movies'], f'{key}: unknown movie')
        check(row['cinema_id'] in ids['cinemas'], f'{key}: unknown cinema')
        check(isinstance(row['price_azn'], (float, int)) and row['price_azn'] >= 0, f'{key}: invalid price')
        start = datetime.fromisoformat(row['start_local'])
        check(start.date().isoformat() == row['date'] and start.strftime('%H:%M') == row['time']
              and start.utcoffset().total_seconds() == 14400, f'{key}: inconsistent local datetime')
        prices = {o['price_azn'] for o in row['price_observations']}
        check(row['price_azn'] in prices, f'{key}: price not supported by observation')
        check(row['price_conflict'] == (len(prices) > 1), f'{key}: incorrect conflict flag')
    manifest = json.loads((folder / 'manifest.json').read_text())
    for name, rows in tables.items():
        check(manifest['counts'][name] == len(rows), f'{name}: manifest count differs')
    return {'passed': not errors, 'checks': checks, 'errors': errors,
            'run_directory': manifest['run_directory'], 'validated_at': datetime.now().astimezone().isoformat(),
            'counts': {k: len(v) for k, v in tables.items()},
            'scope': 'Structure, IDs, joins, JSON/CSV parity, price provenance, timestamps, local image files; not live availability.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', default='SuperChat_Real_Data')
    args = parser.parse_args()
    result = validate_dataset(args.dataset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
