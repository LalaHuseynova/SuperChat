# Verification record

## Resumable expansion to 320 products - 3 November 2026

- Final automated checks: **241 pytest tests passed**, nine standalone Birmarket
  parser tests passed, and `git diff --check` passed. Pytest reports the existing
  upstream Starlette deprecation warning.
- Published **150 new Birmarket products**, taking the local database from 170 to
  320: 40 in each configured category. Original IDs and collection timestamps
  remained intact. Every new row has an archived source file and a direct product
  URL; all new local images were served successfully by the image endpoint.
- The first run stopped at 260 on incomplete category-card fields. Prior batches
  remained published. After fixing URL discovery to defer facts to product
  details, collection resumed and reached 320.
- API pagination exposes all 320 unique IDs. Chat pagination returns two separate
  pages of 20 phones without replacing filters. EN/AZ/RU searches for the added
  Celebrat G13 listing return its exact ID and source link.
- **320 images indexed.** A timed-out backpack image was re-fetched and verified.
  The headphone smoke identified an overly narrow earbuds candidate filter;
  overlapping headphone/earbud candidates are now ranked together. The source
  image returns its own ID first at 0.9999 cosine similarity. This single-image
  check does not establish general image-recognition accuracy.
- Evidence: `birmarket-batches-smoke.json`, version `345c31f21cbe4421`.
  No hosted AI requests, supplier orders, or user-chat modifications were needed.

## Birmarket browser expansion - 3 November 2026

- `uv run --extra dev --extra scraper --extra browser --extra vision pytest -q`:
  **224 passed**, with one upstream Starlette deprecation warning.
- Nine standalone Birmarket parser tests passed; `git diff --check` passed.
- Chrome read actual public pages and passed the robots check. An initial larger
  run failed before publication. A subsequent retry returned HTTP 502; shared
  CLI/browser exceptions, bounded server-error retries, and retained failure
  diagnostics were added and tested.
- A complete phone-only expansion published 10 new products, increasing the local
  database from 160 to **170**. Prior records retained their timestamps. Source
  links and image paths remain backed by archived provider data.
- EN/AZ/RU offline conversation checks returned new product `BM-1836292` for
  Redmi Note 15. Malformed numeric input and an absent model returned no cards.
  The model number is no longer misread as a result count in Azerbaijani.
- **170 main images indexed.** One new catalogue phone image returned its own ID
  first with cosine similarity 0.9997. This is a single smoke check, not a claim
  of general recognition accuracy. Evidence: `birmarket-expansion-smoke.json`.
- This update did not test rendered chat UI or perform a hosted Gemini request.
  Birmarket coverage remains a sample, not its entire marketplace.

## Conversation repair - 3 November 2026

- `uv run --extra dev --extra vision --extra scraper pytest -q`: **162 passed**.
- `node --test tests/language-ui.test.cjs`: **9 passed** (controlled DOM, not browser rendering).
- New regressions cover five distinct films and pagination in EN/AZ/RU, stale
  query recovery, numeric film titles, contextual ticket follow-ups, Baku/Istanbul
  flight routing, provider identity and localized authentication failures.
- Live diagnosis: initial requests selected the wrong credential and failed.
  Both key fields were populated; Gemini now selects only `AI_API_KEY`. Google
  rejected the old 2.5 model as unavailable to new users and recommended
  `gemini-3.5-flash-lite`. A real JSON completion with that model succeeded.
  Local endpoint/model settings are updated; no credentials are changed or removed.
- Live Gemini planning succeeded for counted cinema requests in EN/AZ/RU and
  Baku/Istanbul ticket wording. A three-turn Gemini + local catalogue smoke returned
  five distinct films, retained cinema for `ticket maybe`, then selected flights
  for `ticket in baku istanbul`, with zero mutations. This check used archived
  flight repository rows, not a new Travelpayouts request.
- No API keys or raw credential-bearing requests are recorded here.

## Real catalogue update - 3 November 2026

- 148 backend tests passed; coverage includes database swaps, rejected partial refreshes, three languages, unknown queries, image ranking and the official API adapter.
- 102/106 authored offline routing cases remain correct (96.2%).
- Live Travelpayouts authentication succeeded and returned one cached AZN fare.
- Live CinemaPlus refresh published 488 showtimes; Birmarket HTTP 403 retained prior data.
- 160 product images indexed. Five recompressed product-image smoke tests returned relevant catalogue IDs; blank image rejected. No broad vision accuracy claim.
- HTTP smoke passed: eight conversation turns across EN/AZ/RU and all domains, a catalogue photo ranked with cosine similarity, a rejected blank image, direct source links and eleven JSONL events. Evidence: database-smoke-results.json.
- Eight UI script tests pass, including persistent language selection and localized direct source links. This is a controlled DOM harness, not browser rendering.
- The technical report was regenerated as four pages and all four rendered pages were visually inspected.
- Local/hosted classification paths are distinguished; no live hosted-model evaluation in this update.
- Browser rendering, mobile interaction, and microphone capture remain unverified.

The following is the original Phase 1 verification record, retained as history.


Run date: 2 November 2026.

- **45 automated tests passed** with `pytest -q` (1.20 seconds on the final run). One upstream Starlette warning notes that its HTTPX test adapter is deprecated; it did not affect execution.
- **102/106 offline routing cases correct (96.2%)**. See `TEST_LOG.md` and `routing-results.json`; four indirect/slang queries fell back to clarification.
- Python modules compile successfully. `node --check superchat/static/app.js` passes.
- The documented `./run.sh --vision` command starts the service successfully.
- HTTP smoke checks cover the HTML, JS, CSS, favicon and configuration endpoints, all returning 200; seven messages switch domains, restore previous flight filters, mutate a cart and save a mock reservation. A real headphone image passes through the upload endpoint into a catalogue search. The resulting JSONL export contains the expected nine events. Test data stays in `tmp/smoke/sessions/`, separate from user conversations.
- Local vision: real headphones photograph accepted as `headphones` (score 0.9209, margin 0.8443); blank image rejected (`other`, score 0.2461). Weights are cached. These smoke tests do not establish general visual-search accuracy.
- Technical report: exactly four pages, rendered and all four visually inspected; no clipped text or broken layout found.

## Not verified live

- Browser visual interaction, mobile layout and microphone capture: Computer Use permission was not granted on this machine. Responsive rules, accessible controls and speech paths are implemented; no live browser/microphone success is claimed.
- OpenRouter: no key supplied to the implementation session. Provider success/failure validation is covered with mocks; a real hosted-model request is not claimed. Set `OPENROUTER_API_KEY` locally in `.env`, restart and exercise the demo script.
- No real external data-provider APIs, payment flows or public-hosting deployment are in scope.
