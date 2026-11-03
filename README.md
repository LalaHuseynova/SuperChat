# Bir SuperChat

Use the trash button beside a conversation to delete it. A localized confirmation
explains that this permanently removes that chat's messages, shopping list,
saved plans and JSONL log. Other conversations remain available. Export a chat
before deleting it if you want to keep a copy.

A local, multilingual chat for flights, shopping, and cinema, built against the five official JSON files. One conversation can move between all three domains. It includes mock reservations, a cart, saved chat sessions, voice input, and visual product search.

## Real catalogue platform

Flight and cinema cards include **Save to plans**. Saved plans appear in the
sidebar with their title, saved price and original source link, and persist in
the session's JSONL log. Use × to remove a plan. Repeated saves update the same
entry. These are local bookmarks, not supplier-confirmed reservations; open
the source to book. Mock mode retains its separate simulated reservation flow.

Start the database-backed app, including the scraper and local visual-search dependencies:

```bash
./run.sh --real
```

Open **http://localhost:8000**. The header says **REAL CATALOGUE**. Stop with Ctrl+C
before restarting. Your `.env` credentials remain local and are never sent to the browser.

- **Birmarket:** 160 previously collected products seed SQLite. Local Chrome
  collection on 3 November 2026 expanded the current database to **320 products**:
  40 in each of eight categories. The latest expansion added 150 to the previous
  170. Refreshes use the
  expanded scraper, validate a complete source bundle, and publish atomically.
  Collection now targets up to 100 products in each of the eight configured
  categories (up to 800 total), within 10 pages per category. These are collection
  limits, not a claim that 800 records have already been fetched. Ordinary HTTP
  requests received 403; the optional browser mode successfully published smaller
  batches and resumed after a category-card parsing failure. The full store is
  not indexed.
- **CinemaPlus / CineMastercard:** movies, cinemas and dated showtimes use the same
  database. A successful live collection on 3 November 2026 published 488 showtimes.
- **Flights:** set `TRAVELPAYOUTS_API_TOKEN` in `.env` to use the official Aviasales
  Data API. These are cached fares, not guaranteed live prices or seat inventory.
  Without a token, flights use the labelled archived route listings.
- **EN / AZ / RU:** selected-language responses, filters, no-match messages and
  controls; source AZ/RU product descriptions are used where available. English
  product labels are derived from recorded names/brand/model, not invented prose.
  Original source names remain in the data-source disclosure. Movie titles and
  addresses remain source proper names; genre and language attributes are localized.
- **Photos:** local CLIP first checks category/confidence, then compares the photo
  against saved product images (320 indexed locally) using normalized image embeddings and cosine
  similarity. Only catalogue IDs above the similarity threshold are returned.
  Uncertain/unrelated images ask a question; no sufficiently similar items means
  no product cards. Scores are not probabilities or exact brand identification.
- **Sources:** result links open the exact Birmarket product, CinemaPlus movie/
  schedule, or Aviasales search page. Shopping lists are local; no supplier order,
  seat hold, payment or confirmed reservation is created.

The catalogue initializes at `runtime/catalogue/catalogue.sqlite3`. Each chat turn
reads a consistent database version; completed refreshes become visible on the next
turn **without a restart**. Chat memory stays in append-only JSONL logs. Existing
snapshot conversations remain under `runtime/sessions/snapshot/`.

Automatic refresh checks run in the background, normally once per source per 24
hours (`SUPERCHAT_AUTO_REFRESH=true`, `SUPERCHAT_REFRESH_HOURS=24`, minimum 6).
Collection checks robots rules, uses two-second request spacing, bounded retries,
and stops on access refusal/rate limits. An incomplete or invalid run keeps the last
good database. On this machine ordinary HTTP requests to Birmarket's robots
endpoint returned 403. Normal Chrome access passed the check and collected data;
browser collection also handles temporary server failures with bounded retries.
A refresh schedule does not guarantee the provider permits access or has new data.

Manual maintenance:

```bash
# Expand all configured categories, publishing each ten-product batch
PYTHONPATH=. uv run --extra scraper --extra browser python scripts/expand_birmarket.py --browser --per-category 40 --batch-size 10 --pages 5
# Import the existing validated collection if the database is not initialized
PYTHONPATH=. uv run --extra scraper python scripts/refresh_catalogue.py --import-only
# Refresh one provider, without restarting the chat
PYTHONPATH=. uv run --extra scraper python scripts/refresh_catalogue.py --source cinema
PYTHONPATH=. uv run --extra scraper python scripts/refresh_catalogue.py --source birmarket
# Larger bounded run (up to 150 products/category, 15 pages/category)
PYTHONPATH=. uv run --extra scraper python scripts/refresh_catalogue.py --source birmarket --per-category 150 --pages 15
# Expand using installed Chrome when ordinary HTTP requests are refused
PYTHONPATH=. uv run --extra scraper --extra browser python scripts/refresh_catalogue.py --source birmarket --browser --expand --per-category 30 --pages 3
# Download the vision model and warm the product-image index
PYTHONPATH=. uv run --extra vision python scripts/prepare_vision.py --catalogue
```

The batch expansion command resumes from the counts already published in SQLite.
Increase `--per-category` for a larger target and `--pages` for a larger page budget.
It retains earlier products and stops on a failed batch; previously completed
batches remain available in chat. A category that runs out of products within its
page budget is not repeatedly requested. The target is a limit, not a guarantee.

`--browser` uses installed Google Chrome in a separate, visible session. It checks
robots rules through Chrome and stops on access refusals or verification pages.
It does not read your existing browser profile. Keep its window open until the
command finishes. This mode is for manual local collection; scheduled refreshes
continue to use HTTP. `--expand` retains current products and their original
collection timestamps, adding unseen products until each category reaches the
requested total. Omit `--expand` for a fresh replacement collection. Publication
occurs only after collection and validation finish; the app serves the previous
database while the command runs.
Failed-run inputs and scraper diagnostics are kept under
`preparation_dataset/SuperChat_Real_Data/.failed/` (ignored by Git), separate from
the live catalogue. Remove those folders after diagnosis if they are no longer
needed. Temporary HTTP 500/502/503/504 responses get at most three attempts;
access refusals and rate limits stop the run immediately.

For scheduled runs configure `BIRMARKET_PER_CATEGORY=100` and `BIRMARKET_PAGES=10`
in `.env` and restart. Set per-category to `0` to collect all products found within
the configured page limit. To cover additional categories, pass `--categories-file`
or set `BIRMARKET_CATEGORIES_FILE` to a JSON mapping like the existing
`preparation_dataset/birmarket_categories.json`, using verified category paths.
Keep the existing mappings when adding categories; each successful run replaces
the shopping catalogue. The default downloads one main image per product for
visual search, retains two-second request spacing, and allows at most two hours
per Birmarket run. Smaller fully collected categories are valid; refused,
rate-limited or incomplete runs do not replace the database. Product counts are
not guaranteed and this remains bounded coverage, not the whole marketplace.

The model is already cached on this machine. For offline use keep `VISION_OFFLINE=true`.
On a new machine prepare it first; a failed image model load produces a clear fallback.
`VISION_BACKEND=local` is the default and does not send photos to an AI provider.
Explicit `VISION_BACKEND=hosted` opts into hosted category recognition; local image
ranking still requires the vision extra. Category-only fallback is recorded as such.

Read-only APIs: `/api/catalogue/status`, `/api/catalogue/products?q=smartphone&page=1&limit=20&language=en`,
and `/api/catalogue/showtimes?date=2026-11-03&page=1&limit=20&language=ru`.
Refresh is an operator CLI/background task, not an unauthenticated public write endpoint.
`SUPERCHAT_CATALOGUE_DB` and `SUPERCHAT_REAL_DATA_DIR` override storage locations.

Use `./run.sh --mock` for the original competition data and mock bookings.
Use `./run.sh --snapshot --vision` for the older, frozen snapshot mode. Its descriptor
can still be published with `scripts/publish_snapshot.py` and requires a restart.

For deployment set `SUPERCHAT_DATA_MODE=database`, install the scraper extra and
provide persistent storage for the database, archives/images and session logs.
Local CLIP needs substantially more resources than a tiny free hosting instance.
This remains a single-user demonstration: shared public use still needs visitor
isolation/authentication and durable deployment storage.

This implements the agreed real-data approach. Birmarket/CinemaPlus are **our API
backends over collected public listings**, not official partner APIs. Full Phase 2
under the original brief still needs acceptance of that substitution or official
provider contracts and a sandbox. See [the implementation log](docs/PHASE2_LOG.md).

## Run

Requires Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/). From this folder:

```bash
./run.sh --vision
```

Open **http://localhost:8000**. The command installs the locked dependencies and starts the application. `./run.sh` starts the lighter core without installing the local image model dependencies. Hosted text understanding is optional. For hosted photo classification explicitly set VISION_BACKEND=hosted; local image similarity requires the vision extra.

For a different port: `PORT=8001 ./run.sh --vision`. Stop with Ctrl+C. To develop with automatic reload: `uv run --extra vision uvicorn superchat.app:app --reload`.

The app binds to your computer's loopback interface. It is a single-user competition demo, not a public multi-user service. The PDF brief and official data remain unchanged.

## Chat AI (optional, for flexible natural language)

A local `.env` file has been prepared. Add your key **locally**, then restart the app:

```dotenv
OPENROUTER_API_KEY=your-key-here
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=google/gemini-2.5-flash-lite
```

For a key created in **Google AI Studio**, use this configuration instead:

```dotenv
OPENROUTER_API_KEY=
AI_API_KEY=your-google-ai-studio-key
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
AI_MODEL=gemini-3.5-flash-lite
```

Keys must match the provider endpoint. Gemini uses `AI_API_KEY` even if an OpenRouter key is also present. The key stays on the server and is excluded from Git and chat logs. Do not put it in the browser or commit it. Free models may have rate limits and differing capabilities; the app does not depend on a free tier. A configured key is not proof of a successful connection: a rejected credential produces a visible notice and the offline assistant handles the request. Replace an invalid key locally and restart. Travelpayouts credentials are separate and do not enable chat AI. During verification Google rejected `gemini-2.5-flash-lite` as unavailable to new users and recommended `gemini-3.5-flash-lite`; generation with that model succeeded.

The model translates requests into validated searches and actions. It **does not write prices, stock, seat counts, or reservation confirmations**. Those are assembled from local repositories. Invalid output, timeouts, and provider failures fall back to the offline router, with a visible notice. The provider receives your message, recent conversation context, and, only when VISION_BACKEND=hosted, the uploaded image. In real mode the independent Travelpayouts adapter requests cached fares and background scrapers collect public listings.

Without a key, the offline multilingual rules support the demonstrated catalogue and common follow-ups. Indirect descriptions and slang may require clarification; a hosted model is not silently simulated.

Unclear keyword lists such as “film ticket negativity exam university depression” ask for clarification before searching. This check leaves saved filters, selections, carts and bookings intact. It is a conservative rule for disconnected fragments, not a general semantic confidence score; the hosted planner also receives instructions to assess the whole request. Clear context such as “Show me a comedy after my university exam” remains supported.

## What to try

1. “Find me a flight from Baku to Istanbul on Friday.”
2. “What is playing tonight?”
3. “Do you have wireless headphones under 100 AZN?”
4. “Back to flights.”
5. “The cheaper one, is it direct?”
6. “Compare F001 and F002.”
7. “Reserve two seats for F002.”
8. “Add P001 to my cart.”

Try Azerbaijani: “100 manatdan ucuz simsiz qulaqlıq var?” or Russian: “Покажи ноутбуки”, followed by “Второй вариант”. Mixed requests work too: “I need a flight to Istanbul on 6 November and a backpack for the trip.”

The competition reference date is **Monday, 2 November 2026, Asia/Baku**. “Friday” means 6 November; “Saturday” means 7 November. This date is intentionally fixed, not the server's clock. Flight times are the airport-local strings supplied in the dataset; the provided duration is authoritative.

## Saved sessions and grounded memory

- Each conversation has an append-only `runtime/sessions/<UUID>.jsonl` log.
- Each completed turn stores user and assistant messages, the route, source IDs, actions, and a complete state snapshot. State includes separate filters/shortlists/selections for each domain, language, explicit preferences, cart, reservations, and pending clarification.
- Opening a saved chat replays its log. Restarting the server does not lose context. No LLM-generated memory summary replaces recorded facts.
- New chats are independent. **Start a new chat with this context** explicitly copies preferences and search state, using your selected language; it does not copy carts, bookings, or pending actions. The source chat is recorded.
- Saved prices in the transcript are historical evidence. Every new operation re-reads the catalogue and checks availability. Reservations across all sessions reduce remaining mock seats.
- An OS lock covers validation and commit. A single fsynced JSONL event commits the entire turn. Retrying the same request ID returns the original response, so a dropped connection does not duplicate a reservation.
- Corrupt logs fail closed. Back up `runtime/` and restore a damaged log from backup; never manually delete reservation lines to “repair” inventory.
- Logs are human-readable and exportable from the sidebar. Images, API keys and payment details are not logged. No payments or real bookings exist.

Logs reduce context loss; they do not make arbitrary natural-language interpretation infallible. Clarifications, validated IDs, fresh data reads, and explicit action checks provide the other safeguards.

## Bonus features

**Voice:** Click the microphone once and allow browser access. Speech start/end events and a silence timer support hands-free messages without holding a button. Final transcripts use the same message route. Optional spoken replies are available under “Your space”. Browser speech services may need internet; Azerbaijani recognition and synthesis depend on the browser/OS. Chrome is recommended; unavailable or denied recognition shows a fallback message. This feature was implemented but could not be microphone-tested in the task environment.

**Visual search:** Upload a JPEG, PNG, or WebP (up to 8 MB / 20 MP). Local CLIP is the default. Hosted classification is opt-in with `VISION_BACKEND=hosted`. CLIP classifies ten product types plus an “other” category, then database mode ranks stored product images. Its weights are downloaded on first use when offline mode is disabled and cached for later use:

```bash
uv run --extra vision python scripts/prepare_vision.py
```

Set `VISION_OFFLINE=true` after preparing the cache. Local acceptance requires score ≥ 0.65 and a margin ≥ 0.20 over the next label; hosted vision requires ≥ 0.75. These are model confidence scores, **not calibrated correctness probabilities**. Uncertain photos produce one clarification question. The app identifies a product type, never claims an exact brand match, and only returns actual catalogue rows. Uploaded images are not retained.

**Languages:** English, Azerbaijani, and Russian response templates, product descriptions, UI labels, routing vocabulary, dates, and actions. The language selector controls the interface, new replies, image results and speech locale. Your selection stays saved in this browser when sending messages, switching chats or refreshing; old messages retain their original text. API clients that omit the optional message `language` retain automatic reply-language detection. Mixed-language inputs are supported within the parser's vocabulary. Full open-ended understanding is stronger with OpenRouter enabled.

## Validation and deliverables

```bash
uv run --extra dev pytest -q
PYTHONPATH=. uv run python scripts/evaluate_routing.py
node --check superchat/static/app.js
node --test tests/language-ui.test.cjs
```

- [Technical report](docs/TECHNICAL_REPORT.pdf) — four pages covering architecture, state, data adapters, references and limitations.
- [Routing test log](docs/TEST_LOG.md) — reproducible accuracy figures and individual results.
- [Five-minute demo script](docs/DEMO.md) — includes more than three domain switches.
- [Verification record](docs/VALIDATION.md) — checks completed and explicit verification limits.
- [Source/reference review](docs/REFERENCES.md) — evaluation of the supplied repositories and alternative.
- [Requirement checklist](docs/REQUIREMENTS.md) — implementation and verification mapping.

## Layout

```text
superchat/
  app.py            FastAPI endpoints, idempotency, transaction boundary
  engine.py         Domain orchestration and grounded result construction
  nlu.py            Offline EN/AZ/RU router, filters, dates, references
  ai.py             Optional validated OpenRouter planner
  repositories.py   Swappable data interfaces and JSON adapters
  store.py          Durable append-only sessions and inventory replay
  vision.py         Confidence gate and cached CLIP image-similarity index
  database.py       Atomic SQLite catalogue and consistent per-turn reads
  refresh.py        Scheduled scraper collection and failure retention
  travelpayouts.py   Official cached-fare adapter and bounded request cache
  search_text.py    Multilingual query constraints, including unknown terms
  i18n.py           Localized responses and catalogue descriptions
  static/           Responsive web interface and hands-free voice
SuperChat_Mock_Data/ Official, unchanged competition data
runtime/sessions/   Private local logs (ignored by Git)
tests/             Conversation, API, persistence and provider tests
docs/              Report, demo, requirements, evaluation and references
```

## Phase 2 boundary

The three repository interfaces support mock JSON, frozen snapshots and the updating
SQLite catalogue. The Travelpayouts adapter implements official token authentication,
bounded pagination, timeout/retry, persistent cooldown/cache, currency validation and
redacted logging. Birmarket and CinemaPlus adapters serve scraped records through our
own APIs. Supplier checkout/seat availability and reservations remain unverified and
are never simulated as confirmed supplier actions. The report and Phase 2 log describe
this boundary explicitly.

No GitHub project was cloned: the reviewed templates are documented in the references,
and none was a better implementation base for this structured catalogue. The routing
architecture is informed by LangChain's router pattern; application code is original.
