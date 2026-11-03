# Requirement mapping

## Real-data update, 3 November 2026

| Requirement | Current implementation | Limit |
|---|---|---|
| Replaceable data adapters | JSON, snapshot, updating SQLite, official Aviasales Data API | Shopping/cinema collect public pages, not partner APIs |
| Authentication and network handling | Travelpayouts token, pagination, cache, timeouts, retry/cooldown, logs | No supplier booking sandbox |
| Fresh real catalogue | Scheduled scrapers, atomic publication, last-good retention | Birmarket currently refuses access from this environment |
| EN/AZ/RU grounded replies | Preserved query constraints and language selection, localized attributes | Source proper names retained; offline paraphrase limits |
| Visual search | Confidence gate and 160-image CLIP similarity index | Similarity is not exact identity/probability |
| No matches or irrelevant prompts | Localized text with no arbitrary cards | Semantic fallback is conservative |
| Source navigation | Exact provider listing/search links | Checkout stays at provider |

The original Phase 1 mapping follows; newer evidence is in PHASE2_LOG.md.


Source: `SuperChat_Project_Brief-2 (1).pdf`, all five pages reviewed. Official JSON data is unchanged.

| Requirement | Implementation | Verification |
|---|---|---|
| One chat, no manual domain mode | Shared transcript, inferred routes, prompt suggestions | API conversations; UI source/syntax checked |
| Flights, shopping, cinema, mixed, follow-up, ambiguous, out of scope | `nlu.py`; optional `ai.py` structured planner | 106-case offline routing evaluation |
| Separate domain context and shared language/preferences | `engine.py`, exact replay in `store.py` | Domain switches, ordinal follow-ups, explicit preferences |
| Flights: origin/destination/date, price/stops/time/airline, details, compare, mock reservation | `JsonFlightRepository`, engine actions, cards/comparison | Friday route, stops/time/price filters, comparison, concurrent bookings |
| Shopping: text/category/brand/price/colour, detail/compare, availability, add/remove/total | `JsonProductRepository`, cart state and validation | Two laptops, brand/colour/budget, out-of-stock denial, cart totals |
| Cinema: genre/rating/language/date, cinemas/showtimes, price/seats, reservations | Joined movie/cinema/showtime repository | Saturday sci-fi, language/rating, sold-out and successful reservations |
| No invented catalogue facts | Exact record IDs, deterministic cards and totals, empty-match responses | Unknown records/destinations, altered source revalidation |
| Recoverable errors | Typed API validation, provider fallback, mixed-turn rollback | Data-source failure and malformed log tests |
| Swappable data interface | Protocols plus JSON adapters | Phase 2 extension notes |
| Multi-session log files | Append-only JSONL, fsync, replay, UUID paths, explicit continuation | Restart, isolation, export, idempotent retries |
| Voice bonus | Continuous browser speech events and silence timer; optional synthesis | Implemented; live microphone test blocked by host permission |
| Visual bonus | OpenRouter vision or local CLIP; confidence/margin gate | Real headphone photo accepted (0.9209); blank image rejected (0.2461); upload/API tests |
| EN/AZ/RU and mixed language bonus | Localized UI/results, vocabulary/date parsing, optional multilingual model | Translated search/operations; language switches; per-language routing results |
| Source + setup + one-command run | `README.md`, `run.sh`, `uv.lock` | Service HTTP checks |
| Technical report, max four pages | `docs/TECHNICAL_REPORT.pdf` | Four-page render/inspection |
| Five-minute demonstration | `docs/DEMO.md` | Script with five domain switches |
| Test log + accuracy + error analysis | `docs/TEST_LOG.md`, machine-readable results | 102/106 (96.2%) on author-written offline set |

Limitations are explicit: no real APIs/payments; not multi-user hosting; uncommon offline paraphrases require clarification; browser locale support varies; no OpenRouter live call without a user key; no browser visual/microphone QA because Computer Use permission was unavailable.
