# Aviasales flight fares

Source: https://www.aviasales.az

| File | Purpose |
| --- | --- |
| `flights.json`, `flights.csv` | One-way fares for SuperChat |
| `round_trip_flights.json` | Return itineraries with both legs and total prices |
| `offers.json`, `offers.csv` | Combined fares; check trip_type and price_scope |
| `routes.json` | Route descriptions and historical price context |
| `manifest.json` | Collection time, route counts, dates, errors and limitations |
| `runs/<timestamp>/` | Archived exports, original route HTML and reference data |

These are cached advertised fares on the configured city routes, not a live
search or verified availability. The source's real dates are retained.
`../../aviasales_routes.json` configures the routes.

City/search codes are not confirmed airport codes. Some Dubai route offers
search Sharjah; the records retain this distinction. Flight numbers, seat
counts, cabin and baggage kilograms remain null when unpublished. Arrival
dates are derived only when duration/timezone calculations match the displayed
arrival clock. Historical monthly prices are context, not bookable offers.

All source and run paths resolve from **`SuperChat_Real_Data/`**.

Refresh from the project folder:

```bash
.venv/bin/python aviasales_scraper.py
```

Detailed field guidance is in `../DATA_DICTIONARY.md`.
