# SuperChat real dataset

Data is organized by source. Each source folder contains its current tables,
collection manifest, notes and historical runs.

```text
SuperChat_Real_Data/
├── README.md                   Folder guide
├── DATA_DICTIONARY.md          Field meanings and missing-value rules
├── dataset_index.json          Table paths and relationships
├── validation.json             Latest full-dataset validation report
├── birmarket/
│   ├── README.md
│   ├── products.json / .csv
│   ├── manifest.json
│   └── runs/<timestamp>/       Archived exports, source records and images
├── aviasales/
│   ├── README.md
│   ├── flights.json / .csv     One-way fares
│   ├── round_trip_flights.json Return itineraries and total prices
│   ├── offers.json / .csv      Both fare types together
│   ├── routes.json            Route context and historical prices
│   ├── manifest.json
│   └── runs/<timestamp>/       Archived exports and original source pages
└── cinema/
    ├── README.md
    ├── movies.json / .csv
    ├── cinemas.json / .csv
    ├── showtimes.json / .csv
    ├── manifest.json
    ├── validation.json
    └── runs/<timestamp>/       Archived exports, source pages and images
```

## Which files to load

| Feature | Current table | Notes |
| --- | --- | --- |
| Shopping | [birmarket/products.json](birmarket/products.json) | Category sample with details and galleries |
| One-way flights | [aviasales/flights.json](aviasales/flights.json) | Cached advertised fares |
| Return flights | [aviasales/round_trip_flights.json](aviasales/round_trip_flights.json) | Total round-trip prices |
| Movies | [cinema/movies.json](cinema/movies.json) | Current, presale and upcoming movies |
| Venues | [cinema/cinemas.json](cinema/cinemas.json) | Location and facility information |
| Cinema tickets | [cinema/showtimes.json](cinema/showtimes.json) | Join movie_id and cinema_id to the other cinema tables |

Use JSON for the application. CSV contains the same exported records with
nested values encoded as JSON strings. Read each source's `manifest.json`
for collection time, counts, coverage and errors. Historical `runs/` folders
are audit snapshots; do not combine them with current tables as new inventory.

## Paths and values

- **All stored local file paths resolve from `SuperChat_Real_Data/`.** This
  includes `source_file`, `local_file`, `image_files`, `poster_file`,
  `tariff_image_files`, source/image index `file` entries and `run_directory`.
- Example: `root / product["images"][0]["local_file"]` opens a downloaded image.
  Do not prepend `birmarket/` again; it is already included in the value.
- IDs are strings. Real IDs do not match fictional mock IDs.
- Currency is AZN. Dates are `YYYY-MM-DD`. Cinema timezone is `Asia/Baku`;
  flight local times use the respective origin/destination timezone.
- `null` means unknown or unpublished, not zero, free, or sold out.
- Source prose and language labels are retained. No missing translations,
  ratings, seat counts or other facts are filled from mock data.
- `source_url` and `fetched_at` provide provenance, not a guarantee of live
  availability or a checkout price.

```python
import json
from pathlib import Path

root = Path("SuperChat_Real_Data")
products = json.loads((root / "birmarket/products.json").read_text())
flights = json.loads((root / "aviasales/flights.json").read_text())
showtimes = json.loads((root / "cinema/showtimes.json").read_text())
```

## Refresh and validate

Run from the project folder, one directory above this dataset:

```bash
.venv/bin/python birmarket_scraper.py --download-images
.venv/bin/python aviasales_scraper.py
.venv/bin/python cinema_scraper.py
.venv/bin/python validate_dataset.py
```

For all three scrapers, `--output` specifies the **dataset root**; the scraper
creates its own source folder underneath it. Each run preserves earlier
snapshots. The original `SuperChat_Mock_Data/` folder is separate and unchanged.
Run the full validator after refreshing to update the root validation report.

## Changes from the previous layout

The old root `products.*`, `manifest.json` and `runs/` moved into `birmarket/`.
Flight files moved into `aviasales/`; `aviasales_offers.*` became `offers.*`,
`aviasales_routes_data.json` became `routes.json`, and `aviasales_runs/` became
`runs/`. The flight manifest is now `aviasales/manifest.json`.
Duplicate root cinema exports were removed after confirming they matched
files in `cinema/`. Update external loaders to the paths listed above.

Archived source files and images were preserved. References in current and
historical exports were updated to match their new locations.
