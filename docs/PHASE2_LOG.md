# Phase 2 implementation log

## Styled chat deletion dialog - 3 November 2026

- Replaced the browser confirmation popup with an accessible native HTML dialog
  styled to match the purple interface. It separates the chat title, deletion
  explanation and irreversible-action notice, with Cancel and Delete chat buttons.
- EN/AZ/RU labels, safe text-only titles, initial Cancel focus, native modal focus
  trapping, Escape and backdrop cancellation; duplicate dialog openings are ignored.
- Fifteen UI script tests passed. Isolated Chrome checks verified desktop and
  mobile layouts, initial focus, Escape, Cancel and confirmed deletion with stubbed
  API responses. Both screenshots were visually inspected; no user chats were deleted.

## Resumable category expansion - 3 November 2026

- Published **150 additional products: 170 → 320**, with 40 each in audio,
  computers, phones, wearables, sport, accessories, home and gifts. This remains
  a bounded sample. The original 170 records and collection timestamps remain.
- Downloaded main images for all 320 products. One timed-out backpack photo was
  subsequently fetched and verified; its download provenance is recorded under
  `birmarket/image_repairs/`, without changing the product's collection timestamp.
- Added `scripts/expand_birmarket.py`: each category grows in bounded batches,
  retaining all prior products. Each successful batch is validated and published
  separately, so a later failure does not discard completed work. Re-running the
  command resumes from published counts. Exhausted categories/page budgets stop
  without looping, and any failed batch stops further collection.
- Browser navigation skips decorative images, fonts and media while preserving
  HTML/scripts and explicit main-image downloads. Two-second request pacing,
  robots checks, bounded server-error retries and refusal handling remain active.
- Added checks for batch order, resuming, early failure, exhausted categories,
  invalid limits and preservation of main-image requests.
- The run reached 260 products before a category-card parsing error stopped a
  laptop batch. Category discovery now validates same-site numeric product URLs
  and defers product names/prices to the detail-page parser. This handles category
  cards whose fields have not rendered yet without inventing missing facts.
  Strict name/price parsing remains available for standalone listing exports.
  The next run resumed from the published counts instead of collecting them again.
- Expanded-data smoke checks found that a catalogue match could turn “Show more”
  into a fresh product query. Exact pagination commands now bypass product hints.
  Regression checks cover EN/AZ/RU; a live-catalogue check returned 20 phones on
  each of two pages with no repeated IDs and preserved filters.
- Indexed 320 main images and verified all new image endpoints. The headphone
  smoke exposed an overlap between source names and the model's “earbuds” label;
  those two related types now share candidates before cosine ranking. The saved
  Celebrat G13 image returns `BM-130593` first (0.9999 cosine similarity).
- Final catalogue version: `345c31f21cbe4421`. All 320 records are accessible via
  API pagination; EN/AZ/RU chat checks find the added Celebrat listing and use its
  exact source URL. Evidence: `docs/birmarket-batches-smoke.json`.
- Restart the app to load the pagination and audio-image filtering fixes. The
  published database and cached image embeddings already persist locally.
- Validation: 241 pytest tests, nine standalone parser tests and the live local
  catalogue smoke passed. `git diff --check` passed.

## Browser collection and published expansion - 3 November 2026

- Added opt-in `--browser` collection using installed Chrome in an isolated
  visible context. Normal browser requests returned 200 and passed the robots
  check; ordinary HTTP requests had returned 403. No existing browser profile,
  credentials, CAPTCHA bypass, or proxy rotation is used.
- Added `--expand` to retain existing records and their collection timestamps.
  Pagination now distinguishes pages of retained products from repeated pages.
- An eight-category expansion failed before publication; its staged additions
  were not published. A smaller retry exposed HTTP 502. Browser/CLI exceptions
  now share the same classes, temporary 500/502/503/504 responses have at most
  three attempts, and refused/rate-limited requests stop without retrying.
  Failed inputs and subprocess diagnostics are retained under ignored `.failed/`
  folders outside the live database.
- Successfully published a phone-only expansion: **160 → 170 products**, with
  10 new phone details, AZ/RU source content, direct links and main images.
  Other categories remain unchanged. This is bounded coverage, not the full
  Birmarket inventory. Catalogue version: `5ad7880820c67fa9`.
- Indexed 170 product images. EN/AZ/RU queries for Redmi Note 15 return the new
  `BM-1836292` listing and valid Birmarket links. Fixed the model's `Note` token
  and prevented its numeric suffix from being mistaken for a requested count.
  Malformed numeric requests and nonexistent model requests still return no cards.
  Evidence: `docs/birmarket-expansion-smoke.json`.
- The original seed export remains unchanged; the new complete source bundle is
  archived under `birmarket/runs/` and published to the local SQLite database.
  Data updates appear on the next chat turn. Restart the app to load parser fixes.

## Expanded Birmarket collector - 3 November 2026

- Replaced hard-coded 20-product/two-page refresh limits with defaults of 100
  products and 10 pages per category, configurable via CLI/environment. Eight
  current categories give a target ceiling of 800 products, not a promised count.
  Per-category zero allows all discovered products within the page limit.
  Custom category mapping files are supported by the refresh wrapper.
- Downloads one main product image by default, preserving the visual-search
  input while reducing gallery requests. Collection remains paced at two seconds
  and bounded by a two-hour subprocess timeout.
- Pagination recognizes additional query parameters. A naturally exhausted
  category below the requested count is no longer incorrectly rejected as
  partial. Manifests record pages visited and why each category stopped; page
  errors or repeated pagination remain partial and cannot replace the database.
- Attempted an actual expanded refresh: Birmarket access check returned HTTP 403.
  Product count remained 160 before and after. Archived runs contained no extra
  IDs. No additional live listings have been collected or fabricated.
- Automated fixture checks exercise more than 20 products, smaller completed
  categories, blocked subsequent pages, URL pagination, limit validation and
  atomic publication. Actual broader coverage needs successful permitted access
  or a supplier-provided catalogue export/feed; increasing limits alone cannot
  remove an HTTP refusal.

## B logo and chat deletion - 3 November 2026

- Changed the sidebar and assistant logo marks, plus the SVG favicon, from S to B.
- Added a keyboard-accessible trash button per chat with EN/AZ/RU confirmation.
  Confirmed deletion removes the selected JSONL log under the existing transaction
  lock. UUID validation and same-origin write checks also apply to DELETE requests.
- Deleting the active chat clears its local selection and opens another chat if
  available. Deleting the last chat clears messages and context; a new conversation
  is created when the user starts again. Failed deletion keeps the chat visible.
- Verification: 12 API tests and 14 UI script tests passed, including confirmation
  cancellation, API failure, remaining/last chat behavior, restart persistence,
  inaccessible deleted exports, rejection of later writes to a deleted chat,
  invalid IDs, cross-origin requests, localized controls and B logo markup.
  Existing user conversations were not deleted during development.

## Saved flight/cinema plans and branding - 3 November 2026

- Real flight and showtime cards now have localized Save to plans controls.
  The sidebar shows saved titles, venue/route details, saved prices and direct
  source links, with a remove button and an explicit not-booked label.
- Plans persist in session JSONL state with `status=saved_local`; they have no
  supplier confirmation code and do not decrement inventory. Duplicate saves
  update a single entry. Removal works even when a source listing disappears.
  Unknown prices remain unknown, and ambiguous selections ask which option.
- Real-mode reserve wording saves a local plan and explains the distinction.
  Mock reservations remain simulated bookings. Source-only movie information
  without a showtime does not offer a save/showtime action.
- Visible branding changed to **BIr SuperChat**, including the sidebar, header,
  assistant messages, document title and message input label. Existing storage
  keys and session logs remain compatible.
- Verification: 192 backend tests and 10 UI script tests passed. Coverage includes
  both domains and EN/AZ/RU, duplicate requests, restart replay, removal after
  inventory changes, nullable prices and source-link safety. UI checks use a
  controlled DOM harness; no browser rendering claim.

## Product model names and malformed numeric requests - 3 November 2026

- Reproduced the incorrect clarification for `iphone 18 pro max`. Recognizable
  phone model names are now treated as one product reference by the fragment
  guard, retaining the exact requested model for database matching. Added phone
  category filtering so matching accessory names cannot stand in for a phone.
- A long standalone numeric fragment followed by an arithmetic operator, such as
  `339383994848+ ticket istanbul baku`, now returns localized clarification without
  searching or calling Gemini. Catalogue hints and model plans cannot bypass the
  guard; saved search state and pending actions remain unchanged. Normal dates,
  prices, result counts and alphanumeric provider/model IDs are preserved.
- Live Gemini/database verification: `iphone 18 pro max` is shopping with no match;
  `iphone 17 pro` returns one actual Birmarket listing; the malformed ticket query
  returns no cards and does not invoke Gemini. No product data was fabricated or
  added, and the saved Birmarket catalogue remains a partial sample.

## Birmarket coverage and stationery requests - 3 November 2026

- Inspected the actual screenshot turns in local logs: both were interpreted by
  Gemini. The running service was in database mode. The 160 saved Birmarket
  products contain no pens/pencils; this is sampled coverage, not the full store.
- Corrected the planner guidance: requests for any physical product are shopping
  even outside the sampled categories. Added offline EN/AZ/RU pen/pencil and red
  colour mappings, including Azerbaijani without diacritics (`qirmizi qelem`).
- Empty shopping searches now explain the partial saved Birmarket catalogue;
  they no longer suggest changing dates or imply the seller has no stock.
- Live Gemini + database checks: Azerbaijani, English and Russian stationery
  requests correctly yielded no cards and the shopping-specific explanation.
  `Show Samsung phones` yielded 13 products with Birmarket source URLs.

## Conversation and Gemini connection repair - 3 November 2026

- Reproduced the screenshot failures: list counts were retained as title queries;
  generic ticket wording lost the cinema context or missed a named flight route.
- Count requests in EN/AZ/RU now select up to 20 results. Cinema film requests
  group actual showtimes by film before pagination. Numeric titles such as `44`
  remain searchable. Resending a counted list request clears the old malformed
  title filter. Pagination follows the selected count in all three languages.
- A vague ticket follow-up retains a single active cinema/flight topic; fresh or
  mixed contexts still ask for clarification. Baku/Istanbul ticket wording routes
  to flights. These changes do not authorize or manufacture bookings.
- The user confirmed Google AI Studio as the chat-key issuer. Local configuration
  was switched from OpenRouter to Gemini's compatible endpoint and model name.
  Initial requests used the wrong credential and were rejected. Final verification
  found different values in both key fields; Gemini now exclusively selects
  `AI_API_KEY`, preserving the other credential without sending it to Google.
  Google rejected the old 2.5 model as unavailable to new users and recommended
  `gemini-3.5-flash-lite`. Local model configuration was updated and an actual
  JSON completion succeeded. The running server must restart to load these changes.
- Authentication failures have a distinct localized notice. The UI now says AI
  is configured rather than claiming that OpenRouter is connected merely because
  a key exists. Planner traces identify Gemini when it supplies a valid plan.
- Verification: 162 backend tests and 9 controlled-DOM UI tests passed, including
  the exact screenshot conversation, count/pagination in all three languages,
  recovery from saved malformed filters, and authentication failure notices.
  Live Gemini plans also succeeded in EN/AZ/RU; a three-turn hosted-planner and
  local-catalogue smoke reproduced the screenshot prompts successfully. Provider
  tests were rerun after the credential-selection fix (11 passed).

## Current platform update - 3 November 2026

The user clarified that organisers will not supply access and authorised our own
scraper-backed shopping/cinema APIs, a refreshable database, EN/AZ/RU conversations,
source links, strict no-match behaviour, and image similarity search. The earlier
snapshot implementation below is retained as development history.

Implemented in this update:

1. `database.py`: SQLite WAL catalogue, atomic source bundles, schema/join validation,
   per-turn consistent versions, durable refresh status. Seeded the 160 products
   and existing movies/cinemas/showtimes. Successful refreshes need no app restart.
2. `refresh.py` / `scripts/refresh_catalogue.py`: reuse original scrapers in isolated
   staging folders, check robots rules, bound runs, space requests, retain good data
   on failure, promote complete source bundles, and refresh periodically in background.
3. `travelpayouts.py`: official Data API via server-side token; explicit AZN validation,
   fare-scope mapping, at most three pages, 15-minute persistent response cache,
   one transient-server retry, persistent 429 cooldown, bounded timeouts and safe logs.
4. Three-language query normalization preserves unknown names/models instead of
   dropping them into a broad search. Ordinary source names and date/venue requests
   still resolve. Unknown/irrelevant input shows localized guidance without cards.
5. English product labels use recorded name/brand/model; original names remain in
   provenance. Source AZ/RU descriptions are retained, and structured genres/colours/
   languages have localized UI labels. The explicit language choice remains stable.
6. CLIP image embeddings indexed for 160 products. Category gate plus cosine ranking
   returns up to six actual product IDs with score >=0.65. Uncertainty and no similar
   item return text only. Raw uploads are not stored. Local processing is the default.
7. Source buttons open exact provider listing/search URLs. Cards include collection
   times, unknown stock/seats, stale data and price conflicts. Real-mode shopping
   lists remain local and no supplier reservation is implied.
8. `./run.sh --real` installs scraper and vision extras and starts database mode.
   `--mock` preserves Phase 1; `--snapshot` keeps the frozen, restart-based mode.
   Added read-only status, products and showtimes APIs. Updated README and report.

Live evidence:

- Travelpayouts token authenticated successfully; a Baku-Istanbul query for
  6 November returned one cached AZN fare. No token is written to this log.
- CinemaPlus refreshed on 3 November at 00:06 Asia/Baku and published 28 movies,
  11 cinemas and 488 showtimes. Database version: `cc7fd72169d5c490`.
- Birmarket robots endpoint returned HTTP 403. Collection stopped and a failed
  refresh was recorded. The 160 prior product records and their original timestamps
  were preserved. No access-control bypass or claim of fresh Birmarket stock.
- Recompressed source photos: earbuds/laptop/footwear/backpack had their matching
  record first; a phone's same-image variants tied near the top. Blank image rejected.
- 148 Python tests and 8 UI script tests passed. A temporary HTTP server completed
  eight conversation turns, a similar-product photo and a rejected blank image, with
  eleven exported log events. Source links and all three reply languages were checked.
- The routing benchmark remains 102/106 (96.2%). These are
  authored regressions, not broad language/vision accuracy claims.

Boundary: Aviasales is an actual official cached-data API. Birmarket/CinemaPlus
are our own APIs over collected public pages. Official supplier sandboxes, stock/
seat rechecks, confirmed transactions, public visitor isolation and distributed
persistence are still outside this implementation. This does not certify literal
completion of the original Phase 2 provider-API requirement.

## Scope and current status

Started 2 November 2026. The project brief (page 3) requires real provider
APIs with organiser-supplied documentation and credentials. The user confirmed
these are not available yet and authorised preparation using scraped snapshots.
Snapshot integration is an intermediate deliverable, not completed live Phase 2.

## Ordered plan

1. Record prerequisites and preserve the working mock mode.
2. Validate and load Birmarket, Aviasales and cinema snapshots behind repository interfaces.
3. Support real IDs, catalogue names, multilingual search and unknown values.
4. Display provenance, collection time, stale/conflicting prices and source links.
5. Keep local shopping lists separate from supplier orders; prevent snapshot bookings.
6. Publish validated datasets atomically and isolate snapshot conversation logs.
7. Test real-data conversations, failure cases, image results and existing mock behavior.
8. After API access: implement provider contracts/authentication, pagination,
   rate limits, timeouts/retries, cache policy and redacted request logging.
9. After sandbox access: verify availability/price rechecks, supported reservation
   operations, idempotency and complete cross-domain conversations.

## Baseline inspection

- 160 products; 19 one-way and 20 round-trip cached fares.
- 28 movies, 11 cinemas, 531 showtimes; 93 conflicting displayed prices.
- English product names and exact inventory counts are unknown.
- 34 scraper tests and 24,751 structural checks passed during the review.
- Existing mock repositories crashed on real nulls and used mock-only identifiers.
- Snapshots do not establish live availability, bookability or checkout prices.

## Progress

| Step | Status | Result |
| --- | --- | --- |
| 1. Prerequisites and mock mode | Complete | `--mock` retains the competition data and behavior. Organiser access is pending. |
| 2. Models and repositories | Complete for snapshots | Pydantic records validate all six tables; three repository adapters load archived source data. |
| 3. Search and languages | Complete for snapshot scope | Real IDs, source brands/titles, language/genre/colour mappings, null handling, one-way/return separation and 20-result pages. |
| 4. Honest result cards | Complete | Source links, collection timestamps, archived images, unknown inventory, price conflicts and expired/old notices. |
| 5. Actions | Complete for snapshots | Shopping lists are local estimates; supplier reservations/orders are disabled. Mock reservations remain in mock mode only. |
| 6. Publication and memory | Complete | Validated atomic descriptor publication, content hashes, in-memory pinned version and separate snapshot session directory. |
| 7. Local validation | Complete | Tests and HTTP smoke below. |
| 8. Live API adapters/infrastructure | Pending organiser contracts | No endpoints, authentication scheme, rate-limit policy or live availability response is guessed. |
| 9. Supplier sandbox verification | Pending organiser sandbox | No live provider authentication or booking has been tested. |

### Implementation details

- `superchat/catalogue.py`: shared models; finite nonnegative prices, nullable
  inventory, timestamps, fare scope and showtime consistency.
- `superchat/snapshots.py`: Birmarket, Aviasales and cinema repository adapters;
  duplicate IDs, missing joins, path escapes and modified publications fail closed.
- `scripts/publish_snapshot.py`: validates archived runs before changing one active
  descriptor. It does not rewrite the scraper's original files. A process pins
  a validated version until restart, including before the first explicit publication.
- `superchat/engine.py`: real-source matching, pagination/ordinal references,
  source-only booking guidance and local lists. Upcoming films can show their
  published details without inventing a showtime or ticket price.
- `superchat/app.py`: source/version metadata in JSONL turns and safe local image
  serving. Mock and snapshot logs are separate; switching modes cannot spend mock
  seat inventory against a real record. Record IDs are re-resolved in the current
  catalogue; logged card prices remain historical evidence.
- `superchat/static/app.js`: visible snapshot mode, source language fallbacks,
  unknown values, source links, price scope and collection/conflict notices.
- AI context retains recent exact IDs/order/prices but omits large scraped
  descriptions and galleries. Existing explicit language selection is preserved.

### Validation, 2 November 2026

- `python -m pytest -q`: **97 passed** (76 previous tests plus 21 snapshot cases).
- `node --test tests/language-ui.test.cjs`: **7 passed**. These exercise the page
  script with a controlled DOM/API harness, not a rendered browser screenshot.
- `node --check superchat/static/app.js`, `bash -n run.sh`, `git diff --check`: passed.
- A temporary HTTP server in snapshot mode completed eight conversation turns
  across shopping, flights and cinema; served catalogue images and static assets;
  and exported nine JSONL events. No supplier reservations were recorded. The
  temporary server and smoke logs were removed after the check.
- Initial publication: **ceefd58f9e31a796**, with 160 products, 19 one-way fares,
  20 return fares, 28 movies, 11 cinemas and 531 showtimes. The active descriptor
  is in ignored `runtime/catalogue/active.json`.
- Verification used no paid AI calls and no live supplier API calls. Live
  authentication, rate limiting, network retries and supplier transactions remain
  unverified until the organisers provide contracts and access.

### Remaining API work, in order

1. Obtain base URLs, OpenAPI/schema documentation, auth scopes/token renewal,
   sandbox credentials, allowed data use, quotas and example success/error payloads.
2. Map documented provider search/detail responses into the shared records;
   confirm pagination, location identifiers, timezones, currencies and missing fields.
3. Implement the documented authentication, bounded timeouts, retry rules,
   Retry-After handling, cache freshness/revalidation and redacted request logging.
   Never automatically retry a mutation unless the provider guarantees idempotency.
4. Confirm reservation/cart semantics with the organisers. Only provider-confirmed
   outcomes may be called supplier bookings. The brief prohibits real personal
   and payment data; use organiser-approved sandbox flows.
5. Test expired offers, changing inventory, 401/429/5xx responses, page boundaries,
   duplicate action attempts, rollback and multi-domain conversations against the sandbox.
6. Before shared public deployment, add visitor isolation, durable storage and
   concurrency controls suitable for multiple workers. The current app remains
   a single-user demo and uses a process-safe local log lock.

### Follow-up fixes, 2 November 2026

- Fixed `run.sh` for macOS Bash 3.2: the argument array is always nonempty
  under `set -u`. Six launcher combinations were checked with a stub `uv`.
- Fixed false ambiguity for “gives me today film in deniz mall” and
  “give me today's films”. Request prefixes, possessive apostrophes and the
  location preposition “in” no longer count as disconnected topic words.
- Added real-snapshot regressions for the date and Deniz Mall filters, curly
  apostrophes, and hosted planner access; unrelated keyword lists still clarify.
- Updated Python test run: **106 passed**. No live AI/provider calls were used.

### Practical limits

Snapshots are not live availability. The current cinema dates are November 2–4;
prices may conflict and unknown ratings cannot satisfy rating filters. English
product source translations are absent; the app identifies the displayed source
language instead of inventing a translation. Offline routing still has vocabulary
limits. Snapshot age over 24 hours is a display warning, not an accuracy guarantee.
Scraper refresh commands must be followed by publication and restart; supplier
API caching and automatic refresh are not implemented by this snapshot mode.
No provider credentials or private message text belong in this document.
