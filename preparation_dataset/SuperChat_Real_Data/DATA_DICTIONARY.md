# Data dictionary

All JSON tables are arrays of records. Additional source-specific fields may
be added over time. `null` values should display as “not published” or be hidden.

## Cinema: movies

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable movie key, prefix `CM-M-` |
| `title`, `synopsis` | string / null | Source title and description |
| `genre` | string array | Published genre labels |
| `language` | string / null | Single published language; null for multiple or unknown |
| `languages`, `subtitles`, `formats` | string arrays | Page-wide options; check the specific showtime |
| `duration_min` | integer / null | Published runtime in minutes |
| `age_rating` | string / null | Such as `12+`; a bare `+` is treated as missing |
| `rating` | null | No audience score is invented |
| `country`, `directors`, `cast` | string / null | Published production details |
| `release_date`, `listed_until` | date / null | Source exhibition window, not a guarantee of daily sessions |
| `listing_status` | string | `coming_soon` or `current_or_presale` |
| `poster_url`, `poster_file` | string / null | Source image and downloaded file relative to dataset root |
| `trailer_urls` | string array | Published trailer links; videos are not downloaded |
| `source_details` | object | Original detail labels and values |
| `content_language` | string | `az`; this describes page content, not dubbing |

## Cinema: venues

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable cinema key, prefix `CM-C-` |
| `name` | string | Source venue name |
| `address`, `district` | string / null | Null when no structured value was collected |
| `description`, `contact_text` | string / null | Published location/facility prose and contact section |
| `phone`, `opening_hours` | string / null | Published contact number and operating hours |
| `contact_details` | object | Original contact labels and values; protected email placeholders are not usable addresses |
| `map_url`, `coordinates` | string / object / null | Source map and latitude/longitude; not independently verified |
| `gallery_urls` | string array | Venue pictures, retained as remote URLs |
| `tariff_image_urls`, `tariff_image_files` | string arrays | Published tariff charts and local copies |

Do not infer street addresses from venue names. Descriptions may include floor
or mall information even when `address` is null. Source maps with `0,0` are
discarded. Tariff charts are images; their contents have not been transcribed.

## Cinema: showtimes

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Session identity, prefix `CM-S-` |
| `movie_id`, `cinema_id` | string | Foreign keys to the other two cinema tables |
| `date`, `time`, `hall` | string | Published local date, time and hall |
| `start_local`, `timezone` | string | ISO datetime with offset; `Asia/Baku` |
| `price_azn` | number | Displayed ticket price; movie page preferred over venue page |
| `price_kind`, `price_scope` | string | Schedule price before seat selection |
| `price_verified_at_checkout` | boolean | False; no checkout was performed |
| `price_conflict` | boolean | Sources displayed different amounts for this session |
| `price_observations` | object array | Each observed price, source URL and timestamp |
| `languages`, `subtitles`, `formats` | string arrays | Options explicitly shown for this session |
| `seats_total`, `seats_available` | integer / null | Null; no live seat inventory was collected |
| `is_future_at_collection` | boolean | Session had not started at collection time; recompute at display time |
| `booking_url` | string | Movie schedule link, not a preselected ticket or reservation |
| `source_session_id`, `source_attributes` | string / object | Published source identifiers and raw metadata |

`source_attributes` preserves flags without inferring a discount or availability.
For a conflict, display “price needs confirmation” and link to the source.
Movie and venue pages can disagree even when fetched close together.

## Products

Files: `birmarket/products.json` and `birmarket/products.csv`.

The product table retains the shopping mock fields plus rich source data.
Use `name.az` or `name.ru` when English is null. Current/original prices and
discount values are source snapshots. Sizes/colors may describe linked variants
that were not separately checked. Check `in_stock`, `condition` and
`refurbished`, and use downloaded images with a successful `local_file`.
Consult the project README for the complete product collection settings.

## Flights

Files are in `aviasales/`.

`flights.json` contains one-way fares. `round_trip_flights.json` contains total
return prices with `return_leg`; `offers.json` combines both.
Check `trip_type` and `price_scope` before comparing prices.

`origin` / `destination` are search locations, not confirmed flight airports.
For example, BAK means Baku and MOW means Moscow. Offers searching Sharjah are
labeled Sharjah even if discovered on a Dubai route page; the latter remains
under `source_route`. Check `nearby_airport_search` and `data_warnings`.

`departure_local` and `arrival_local` are local datetimes. Arrival dates are
derived only when duration/timezone calculations agree with the displayed
arrival clock. `flight_number`, `cabin`, `baggage_kg` and `seats_available`
remain null unless published. `baggage_included: true` comes from a source
badge; null does not mean baggage is excluded. All collected flight prices
have `price_kind: cached_advertised_fare` and `live_price_verified: false`.

