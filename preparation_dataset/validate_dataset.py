"""Validate the organized SuperChat dataset without fetching new data."""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from validate_cinema import validate_dataset as validate_cinema


def validate_dataset(root):
    root = Path(root).resolve()
    errors, checks, counts = [], 0, {}

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def reference(value, context):
        candidate = root / value
        check(not Path(value).is_absolute() and candidate.resolve().is_relative_to(root)
              and candidate.exists(), f'{context}: missing or invalid path {value}')

    def references(value, context):
        if isinstance(value, list):
            for item in value:
                references(item, context)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in ('source_file', 'local_file', 'poster_file', 'run_directory', 'file') and isinstance(item, str) and item:
                    reference(item, context)
                elif key in ('image_files', 'tariff_image_files') and isinstance(item, list):
                    for path in item:
                        reference(path, context)
                else:
                    references(item, context)

    index = json.loads((root / 'dataset_index.json').read_text())
    for doc in index['documentation']:
        reference(doc, 'documentation')
    for domain, entry in index['datasets'].items():
        reference(entry['manifest'], domain)
        reference(entry['archives'], domain)
        manifest = json.loads((root / entry['manifest']).read_text())
        run = root / manifest['run_directory']
        counts[domain] = {}
        for table, path in entry['tables'].items():
            reference(path, domain)
            file = root / path
            records = json.loads(file.read_text())
            counts[domain][table] = len(records)
            check(len({r['id'] for r in records}) == len(records), f'{path}: duplicate IDs')
            archived = run / file.name
            check(archived.is_file() and json.loads(archived.read_text()) == records,
                  f'{path}: differs from latest run')
            if file.with_suffix('.csv').exists():
                with file.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as handle:
                    rows = list(csv.DictReader(handle))
                check(len(rows) == len(records), f'{path}: CSV count differs')
                check([r['id'] for r in rows] == [r['id'] for r in records], f'{path}: CSV IDs differ')
    for domain in ('birmarket', 'aviasales', 'cinema'):
        for file in (root / domain).rglob('*.json'):
            # Raw source payloads use the original site's own conventions.
            if 'sources' in file.relative_to(root / domain).parts:
                continue
            references(json.loads(file.read_text()), str(file.relative_to(root)))
    cinema = validate_cinema(root)
    checks += cinema['checks']
    errors.extend(cinema['errors'])
    allowed = {'README.md', 'DATA_DICTIONARY.md', 'dataset_index.json', 'validation.json',
               'birmarket', 'aviasales', 'cinema'}
    check({p.name for p in root.iterdir() if p.name != '.DS_Store'} <= allowed,
          'Unexpected dataset-root files; source exports belong inside their source folder')
    return {'passed': not errors, 'validated_at': datetime.now().astimezone().isoformat(),
            'checks': checks, 'counts': counts, 'errors': errors,
            'scope': 'Current/archive parity, IDs, CSV counts/IDs, all archived local references, cinema field checks and folder layout. No live availability checks.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', default='SuperChat_Real_Data')
    args = parser.parse_args()
    result = validate_dataset(args.dataset)
    (Path(args.dataset) / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
