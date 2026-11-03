# CineMastercard cinema dataset

Source: https://cinemastercard.az/ — Azerbaijani public listings.

Use `movies.json`, `cinemas.json` and `showtimes.json` together. Their CSV
versions contain the same information. This is the only current copy of each cinema table; earlier snapshots are in
`runs/`. Use these paths when replacing the mock-data loader.

```python
import json
from pathlib import Path

root = Path("SuperChat_Real_Data")
data = root / "cinema"
movies = {m["id"]: m for m in json.loads((data / "movies.json").read_text())}
cinemas = {c["id"]: c for c in json.loads((data / "cinemas.json").read_text())}
showtimes = json.loads((data / "showtimes.json").read_text())

for session in showtimes[:5]:
    print(movies[session["movie_id"]]["title"],
          cinemas[session["cinema_id"]]["name"],
          session["date"], session["time"], session["price_azn"])
```

The scraper discovers current/presale and coming-soon movie pages from the
homepage, venues from the cinema directory, and additional movies from venue
schedules. It reads all dates present in those pages. Upcoming movies may have
no showtimes yet; that does not mean tickets are sold out.

For conflicting prices, `price_azn` uses the movie page and `price_observations`
retains both movie and venue values. `price_conflict` flags the disagreement.
The displayed amount may change with seat selection, a promotion, or checkout.
No seats are reserved, and seat totals/availability remain unknown.

Downloaded movie posters and venue tariff images live in the dated run's
`images/` folder. All file references resolve relative to `SuperChat_Real_Data/`.
Venue galleries and trailers are retained as URLs. `sources.json` maps each
fetched page to its original HTML; `images.json` includes image checksums.

Check `manifest.json` for actual counts, schedule dates, failures and price
conflicts. `validation.json` records structural checks, foreign-key checks,
CSV/JSON parity and local image existence. A passing validation does not prove
that a source price is bookable.

Refresh from the project folder:

```bash
.venv/bin/python cinema_scraper.py
.venv/bin/python cinema_scraper.py --no-images
```

Requests are paced, transient server errors get limited retries, and HTTP
403/429 stops collection. A partial export returns exit code 2 with errors in
the manifest. If no usable movie/venue dataset is collected, the previous
export stays in place. Earlier runs are preserved.

Read `../DATA_DICTIONARY.md` for field types and missing-value conventions.
