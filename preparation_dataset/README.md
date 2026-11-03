# SuperChat data scrapers

All real data lives in `SuperChat_Real_Data/`, grouped into `birmarket/`,
`aviasales/` and `cinema/`. Each source has its own tables, manifest, notes
and dated `runs/` archive. Local file references resolve from the dataset root.
Run `.venv/bin/python validate_dataset.py` to check the full dataset.

## CineMastercard movies, cinemas and tickets

```bash
.venv/bin/python cinema_scraper.py
.venv/bin/python validate_cinema.py
```

The cinema scraper collects current/presale and upcoming movie details,
descriptions, posters, trailers, cinemas, published contact/location information,
dated showtimes, halls, formats, audio/subtitle languages and ticket prices.
It downloads movie posters and venue tariff images. Venue galleries and
trailers remain links. Use `--no-images` to skip downloads.

Use `SuperChat_Real_Data/cinema/{movies,cinemas,showtimes}.json` together.
Matching CSV exports are included inside the same cinema folder.
`showtimes.movie_id` joins to `movies.id`; `showtimes.cinema_id` joins to
`cinemas.id`. The original mock files remain unchanged.

Some movie and venue pages disagree on session prices. Both amounts are
retained in `price_observations`, with `price_conflict: true`; the movie-page
price is preferred. Prices are not verified at checkout. Unknown seat counts,
ratings, durations and other unpublished information remain null. Each dated
run contains original HTML, image checksums and a validation report.

See **`SuperChat_Real_Data/README.md`**, **`DATA_DICTIONARY.md`** in that folder,
and **`cinema/README.md`** for the organized dataset layout and field notes.
`dataset_index.json` provides table paths and relationships for applications.
The final section of `web.ipynb` runs and previews the cinema scraper.

```bash
.venv/bin/python -m unittest test_cinema.py test_aviasales.py test_birmarket.py test_web.py
```

## Aviasales flight fares for Superchat

```bash
.venv/bin/python aviasales_scraper.py
```

`aviasales_routes.json` maps the nine directed routes in the flight mock data
to Aviasales city routes: Baku, Istanbul, Dubai, Moscow, Tbilisi and Tashkent.
The scraper collects the available dated fare cards from public route pages,
using their actual travel dates and displayed AZN prices. These are **cached
advertised fares, not live availability or guaranteed booking prices**.

Outputs in `SuperChat_Real_Data/aviasales/`:

- `flights.json` and `flights.csv`: one-way fares with the mock's field names.
- `round_trip_flights.json`: return itineraries with both legs and total prices.
- `offers.json` and `.csv`: all collected offers together.
- `routes.json`: route context and published price history.
- `manifest.json`: counts, dates, source coverage, errors and limitations.
- `runs/`: dated copies, original route HTML and reference data.

Each fare includes airline names/logos, departure date/time, arrival time,
duration, stops, any published baggage badge, source and search links, and
collection time. Flight numbers, cabin, baggage kilograms, seat counts and
stopover airports remain `null` when not published. Arrival dates are derived
from duration and timezones only if the result matches the displayed clock.

`origin` and `destination` describe the search locations, not confirmed
airports: BAK means Baku and MOW means Moscow, not necessarily GYD and SVO.
Some Dubai route cards actually search Sharjah; these records use Sharjah
as their destination/origin and retain Dubai under `source_route`. Check
`nearby_airport_search` and `data_warnings` when presenting them.

One-way and round-trip fares are separate so the application does not treat
a return total as a single-leg price. For the combined file, check `trip_type`
and `price_scope`. Fare labels may describe multiple options for the same
departure; they are not necessarily distinct scheduled flights. Historical
monthly prices are context, not dated bookable offers.

```bash
# Optional filters on the published departure dates; this is not a live search
.venv/bin/python aviasales_scraper.py --from-date 2026-11-03 --to-date 2026-11-12

# Run parser checks along with the existing scraper tests
.venv/bin/python -m unittest test_aviasales.py test_birmarket.py test_web.py
```

The Aviasales section of `web.ipynb` provides the same controls and a preview.
Requests are paced and stop on HTTP 403/429. A failed route is recorded in the
manifest; partial exports exit with code 2. If no route can be collected,
previous exports are preserved. A successful date filter may produce zero
matches. Mock files and the Birmarket product exports are preserved.

This public-page scraper needs no API key. Broader date-based cached fare
queries can also use the official
[Aviasales Data API](https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API),
which requires your Travelpayouts API credentials and is not implemented here.

## Real Birmarket products for Superchat

For the database-backed application, run the refresh wrapper from the repository
root. It validates and publishes the collection without changing the original
seed exports. If HTTP collection receives 403 but ordinary Chrome opens the
site, the optional browser mode uses a fresh Chrome session:

```bash
PYTHONPATH=. uv run --extra scraper --extra browser python scripts/refresh_catalogue.py --source birmarket --browser --expand --per-category 30 --pages 3
```

This requires installed Google Chrome. Keep the collection window open until
completion. Robots checks, request spacing, and refusal handling still apply.
`--expand` preserves existing records and timestamps while collecting additional
IDs; the per-category limit includes retained products. Without `--expand`, a
successful complete collection replaces the product table. Browser mode is
manual and local; the background worker continues using HTTP.

The standalone scraper below creates exports rather than publishing to SQLite:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python birmarket_scraper.py
```

This targets up to 100 products per category using `birmarket_categories.json`,
which maps the eight mock categories to Birmarket categories. The initial
selection includes headphones, laptops, phones, wearables, men's sneakers,
backpacks, coffee makers and board games. Edit the mapping to choose other
categories. `SuperChat_Mock_Data/products.json` is preserved.

Use **`SuperChat_Real_Data/birmarket/products.json`** as the application's product source.
It retains every original mock field and adds:

- Original/current prices, calculated discount amount/percentage, and the
  site's displayed discount label (which may round differently).
- Image URL, full gallery, thumbnail URLs and videos where published.
- Descriptions, brand/model, specifications, dimensions, size charts,
  warranty, colors, sizes and links to individual variants.
- Availability, ratings/review counts, seller offers, installments,
  delivery/return information, product links and collection timestamps.

Names and descriptions are fetched in Azerbaijani and Russian. English is
`null` because an English source was not fetched. In the application, use
`product.name[language] ?? product.name.az ?? product.name.ru`.
Exact stock quantity remains `null`; use `in_stock` for availability. A
missing size or warranty is unknown/not published, not an invented value.
Use `refurbished` and `condition` to distinguish refurbished products.

`sizes` and `colors` include linked variants. That does not establish that
every variant is currently available. Variant prices/availability remain
`null` unless that variant was fetched as a product. Seller prices, promotions
and delivery terms are snapshots, not a checkout quote.

The output folder also contains CSV, a manifest, and dated runs with raw
product source records. `manifest.json` records counts, errors, category scope
and missing coverage. These are samples, not the entire Birmarket inventory.
An image that cannot be downloaded retains its source URL with a
`download_status` and error. Use images with `local_file` for an offline gallery.

```bash
# Default sample: up to 20 products per category
.venv/bin/python birmarket_scraper.py --per-category 20 --pages 2

# All listed products within five pages of each configured category
.venv/bin/python birmarket_scraper.py --per-category 0 --pages 5

# Download every gallery picture in addition to retaining its source URL
.venv/bin/python birmarket_scraper.py --download-images

# One specific product (no category crawl)
.venv/bin/python birmarket_scraper.py --product-url 'https://birmarket.az/product/326774-usb-hub-xboss-c8-4-port-usb-3-0-hub-high-speed'

# Change category scope
.venv/bin/python birmarket_scraper.py --category 'computers=/categories/16-noutbuklar'
```

The Birmarket section at the end of `web.ipynb` offers the same settings and
an image preview. Requests are paced, transient server errors get limited
retries, and HTTP 403/429 stops the crawl with successful records preserved.
The page's embedded data is decoded through a restricted syntax parser;
website JavaScript is not executed.

Run checks with `.venv/bin/python -m unittest test_birmarket.py test_web.py`.

## Birbank banking information

Run from this folder with Python 3.10 or newer:

```bash
python -m pip install -r requirements.txt
python web.py
```

With the existing environment, use `.venv/bin/python web.py`. Alternatively,
open `web.ipynb`, select the `.venv` kernel, and run the cells in order.

The scraper discovers Azerbaijani product pages from Birbank's sitemap and
links within the configured product sections. It collects cards, loans,
deposits, insurance, leasing/payment products, transfers, and tariffs.
It downloads linked PDF and XLSX documents and extracts their contents.

Each run creates a new directory under `birbank_data/`:

- `products.csv`: product names, categories, fee/rate mentions with context,
  full details, product links, source links, and collection timestamps.
- `products.json`: the same product records with structured lists.
- `pages.json`: page text, labeled attributes, HTML tables, outgoing links,
  and embedded page data, including data for tabs absent from initial HTML.
- `documents.json`: document source URLs, download status, extracted PDF pages,
  and spreadsheet cells with coordinates, number formats, and merged ranges.
- `documents/`: original tariff/terms documents, unchanged.
- `html/`: original fetched HTML for checking extraction.
- `manifest.json`: counts, errors, unvisited pages, and coverage limitations.

Examples:

```bash
python web.py --max-pages 150 --delay 2
python web.py --no-documents
```

Bank products do not have one universal price. The export preserves the
published wording around fees, interest, limits, currencies, and conditions.
Missing price mentions stay empty; they do not mean a product is free. Catalog
listings are labeled separately from detailed product pages. When both exist,
the detailed record replaces its catalog teaser.

Coverage is limited to the configured public sections on `birbank.az`.
Separate business, investment, private and application sites remain links.
The scraper does not log in, submit forms, place orders, or run calculators.
Content loaded only after interactions may be absent. Spreadsheet formulas
are retained without recalculation. PDF text may lose table alignment; refer
to the saved original for layout. Completion of the configured scope does
not certify every Birbank offering or every applicable fee has been collected.

Successful exports return exit code 0. Partial exports return 2 and retain
collected data with errors in the manifest. A run with no readable pages
returns 1. Each run uses a separate folder, so failures cannot overwrite
previous successful exports.

The banking scraper stays in `web.py`; the separate Birmarket scraper is
`birmarket_scraper.py`.
