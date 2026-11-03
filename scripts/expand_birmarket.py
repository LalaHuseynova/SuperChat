"""Expand Birmarket in small validated batches; resume from published counts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from superchat.config import CATALOGUE_DB, REAL_DATA_DIR, ROOT
from superchat.database import CatalogueDatabase
from superchat.refresh import refresh_source


def expand(database, categories, target=40, batch_size=10, pages=5, browser=False,
           refresh=refresh_source):
    if not 1 <= target <= 1000 or not 1 <= batch_size <= 100 or not 1 <= pages <= 100:
        raise ValueError('Target must be 1..1000, batch size 1..100, and pages 1..100')
    if not categories or any(not isinstance(path, str) or not path.startswith('/categories/')
                             or '?' in path or '#' in path for path in categories.values()):
        raise ValueError('Provide a nonempty mapping of category names to category paths')
    # Each batch retains all other categories. A failed batch stops this command,
    # while earlier validated publications remain available to chat.
    active = dict(categories)
    with tempfile.TemporaryDirectory(prefix='birmarket-categories-') as folder:
        mapping = Path(folder) / 'category.json'
        while active:
            for category, path in list(active.items()):
                counts = Counter(p['category'] for p in database.records('products'))
                before = counts[category]
                if before >= target:
                    del active[category]
                    continue
                limit = min(target, before + batch_size)
                mapping.write_text(json.dumps({category: path}))
                print(f'Collecting {category}: {before} -> {limit}', flush=True)
                if not refresh(database, 'birmarket', per_category=limit, pages=pages,
                               categories_file=mapping, browser=browser, expand=True):
                    print(f'Stopped at {category}; earlier published batches retained.', flush=True)
                    return False
                after = Counter(p['category'] for p in database.records('products'))[category]
                print(f'Published {category}: {after}; catalogue total: {len(database.records("products"))}', flush=True)
                if after < limit or after <= before or after >= target:
                    # Exhausted category/page budget: do not repeatedly scrape it.
                    del active[category]
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-category', type=int, default=40)
    parser.add_argument('--batch-size', type=int, default=10)
    parser.add_argument('--pages', type=int, default=5)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--categories-file', type=Path,
                        default=ROOT / 'preparation_dataset/birmarket_categories.json')
    args = parser.parse_args()
    database = CatalogueDatabase(CATALOGUE_DB, REAL_DATA_DIR)
    database.seed()
    success = expand(database, json.loads(args.categories_file.read_text()),
                     args.per_category, args.batch_size, args.pages, args.browser)
    print(json.dumps(database.status(), ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
