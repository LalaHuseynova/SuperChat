# Birmarket products

Source: https://birmarket.az

| File | Purpose |
| --- | --- |
| `products.json` | Current product records for SuperChat |
| `products.csv` | Same export in CSV format |
| `manifest.json` | Collection time, category counts, errors and scope |
| `runs/<timestamp>/` | Archived exports, raw product source records and downloaded images |

The configured sample covers audio, computers, phones, wearables, sport,
accessories, home and gifts. See `../../birmarket_categories.json` for the
source category mapping. This is not the entire Birmarket inventory.

Records include descriptions, current/original prices, discounts, images,
seller details, specifications, dimensions, sizes and colors where published.
English names, exact stock quantities and other unavailable fields remain null.
Linked variants may have prices or availability that were not independently
checked. Check image download status before assuming a local image exists.

Image and source paths resolve from **`SuperChat_Real_Data/`**, for example:
`birmarket/runs/<timestamp>/images/<product-id>/01.jpg`.
Do not resolve these paths from this source folder or a run folder.

Refresh from the project folder:

```bash
.venv/bin/python birmarket_scraper.py --download-images
```

Detailed field guidance is in `../DATA_DICTIONARY.md`.
