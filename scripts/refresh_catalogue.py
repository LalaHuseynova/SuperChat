"""Import or refresh the real catalogue without restarting the application."""
import argparse
from superchat.config import CATALOGUE_DB, REAL_DATA_DIR
from superchat.database import CatalogueDatabase
from superchat.refresh import refresh_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['birmarket', 'cinema', 'all'], default='all')
    parser.add_argument('--import-only', action='store_true')
    parser.add_argument('--per-category', type=int, help='Birmarket products per category (0 = all within page limit; default 100 or BIRMARKET_PER_CATEGORY)')
    parser.add_argument('--pages', type=int, help='Birmarket pages per category (default 10 or BIRMARKET_PAGES)')
    parser.add_argument('--categories-file', help='JSON mapping of product categories to Birmarket /categories/... paths')
    parser.add_argument('--browser', action='store_true', help='Use installed Chrome for Birmarket (requires the browser extra)')
    parser.add_argument('--expand', action='store_true', help='Keep existing Birmarket records and collect additional products; old timestamps remain unchanged')
    args = parser.parse_args()
    database = CatalogueDatabase(CATALOGUE_DB, REAL_DATA_DIR)
    database.seed()
    ok = True
    if not args.import_only:
        for source in (['birmarket', 'cinema'] if args.source == 'all' else [args.source]):
            ok = refresh_source(database, source, per_category=args.per_category, pages=args.pages,
                                categories_file=args.categories_file, browser=args.browser, expand=args.expand) and ok
    import json
    print(json.dumps(database.status(), indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
