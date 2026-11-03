# SuperChat - technical report

## 1. Architecture and scope

SuperChat unifies flight, shopping and cinema assistance in one responsive chat. FastAPI serves a buildless JavaScript interface. The domain engine uses interchangeable repositories, deterministic result cards and append-only conversation logs. Users do not choose a domain. Mock mode preserves the official five JSON files and competition date; database mode uses the current Asia/Baku date.

The agreed real-data implementation uses our own Birmarket and CinemaPlus catalogue APIs backed by scraped public listings in SQLite. Flights connect to the official Aviasales Data API when a Travelpayouts token is configured. This API returns cached fares, not live inventory. These integrations are usable, but the shopping/cinema sources are not official partner APIs. Full Phase 2 under the original brief still requires organiser acceptance of this substitution or supported provider contracts and sandbox access.

The request flow is text, speech transcript or photo, then routing, domain filters, repository lookup, grounded response and a durable session event. Mixed requests invoke each relevant domain and produce labelled sections. Supplier orders, seat holds, payments and confirmed reservations are never performed in real mode; result links open the original product, movie/schedule or flight search page.

## 2. Routing, multilingual search and grounding

The offline router normalizes English, Azerbaijani and Russian vocabulary, dates, IDs and context. It identifies flights, shopping, cinema, mixed requests, follow-ups, ambiguity and unsupported topics. An optional hosted model produces only a validated typed plan. It cannot author prices, records, stock, totals or confirmation codes. Invalid model output and network failure fall back to deterministic rules.

Unknown requested product models and film titles remain search constraints. A known brand or category cannot erase an unknown model and turn an empty match into broad recommendations. Obvious disconnected keyword lists clarify; explicitly unsupported content requests do not return catalogue cards. Clear academic or emotional context around a valid search is allowed. Rules cannot understand every paraphrase and are not a general semantic classifier.

The language selector controls new replies, images and UI and persists across refreshes and session changes. API requests without an explicit language retain input-language detection. Responses, no-match messages and controls cover EN/AZ/RU. Existing Azerbaijani and Russian product descriptions are preserved. Missing English names use concise labels derived from recorded product fields, not generated marketing claims. Original source titles remain visible in the provenance disclosure. Film titles and addresses remain proper names; known genres, colours and audio languages are localized.

## 3. Conversation state and durability

Each conversation has a canonical UUID and an append-only JSONL log. Events record the user message, assistant reply, route, actions, data mode/catalogue version and complete post-turn state. State contains separate domain filters, result ordering and selection, shared language/preferences, cart, pending clarifications and mock reservations. No generated memory summary is authoritative.

Resuming a conversation restores exact logged state. Explicit context continuation copies preferences and searches, excluding cart and reservations. Current actions resolve source IDs again; old messages remain historical evidence. UUID request IDs make retries idempotent. An OS file lock and fsync protect writes; corrupt logs fail closed. Mock seat inventory is reconstructed from recorded mock reservations. Real mode never consumes that simulated inventory.

SQLite uses WAL and atomic transactions. Each database chat turn pins one catalogue version so a refresh cannot mix movie and showtime generations. A later turn sees a completed update without restarting. Birmarket and CinemaPlus bundles publish independently, after schema, ID and relationship validation. Failed or partial refreshes retain the last good source. Runtime records, archives and conversation logs require persistent storage on deployment.

## 4. Collection and provider integration

Existing scrapers retain original public page records, product images, provider URLs and collection timestamps. A background worker checks freshness, normally every 24 hours per source, with a six-hour minimum. It checks robots rules, spaces requests by two seconds, bounds transient retries and stops on HTTP 403/429. An operator CLI can refresh one source. Refresh logs record safe status categories, not credentials or private request content. No public refresh-write endpoint is exposed.

Our read APIs expose catalogue status, paginated products and showtimes. The database seeds from the existing validated archives. Birmarket's catalogue is a configured sample of 160 products, not the full marketplace. Movie and venue price disagreements remain explicit; unknown inventory and ratings stay null. Product images and posters are served through constrained local paths. Direct links let users confirm current prices and checkout options with the provider.

The Aviasales adapter sends the token in X-Access-Token, validates AZN currency and fare shape, preserves one-way versus return totals, limits pagination to three 100-row pages, caches successful responses for 15 minutes and persists rate-limit cooldowns. Requests have bounded timeouts, with one retry for transient server errors. Authentication errors are not retried. Errors return a localized service-unavailable response rather than made-up offers. Cached responses do not establish current availability or reservation capability.

## 5. Visual and voice bonuses

Photo input is decoded with size/dimension limits. Local CLIP classifies ten supported product types plus an unrelated category. Acceptance requires score at least 0.65 and a 0.20 margin; uncertainty asks a question. Optional hosted classification requires explicit configuration and a score of 0.75. These confidence scores are not calibrated probabilities. Local processing is the default and makes no AI API call.

Accepted photos are embedded and compared against main catalogue product images using normalized CLIP vectors and cosine similarity. Image embeddings are cached by model ID and image-content hash. Candidates must match the detected product type; only real catalogue IDs with similarity at least 0.65 appear, up to six results. No sufficiently similar candidate means no cards. The score is labelled similarity, not probability or exact brand identification. A missing local encoder can provide an explicit category-only fallback after hosted recognition. Uploaded image bytes and EXIF are not retained.

Voice uses continuous browser speech recognition, speech start/end events and a silence timer after initial microphone enable. Recognized text enters the same pipeline; optional speech synthesis reads replies. Availability and Azerbaijani accuracy depend on browser and speech service. The feature is implemented, but no live microphone validation is claimed.

## 6. Validation and limits

The expanded backend suite passes 148 tests covering three-language real-data searches, language switching, absent products/films, irrelevant prompts, database publication and refresh failure, source links, visual ranking, API authentication/cache/pagination/currency/rate limits, plus original mock conversations and log replay. The offline router scores 102/106 (96.2%) on the author-written regression set. Four indirect/slang examples clarify; this is not an independent accuracy benchmark.

Live checks verified the user's Travelpayouts token with a cached Baku-Istanbul fare. CinemaPlus collection published 28 movies, 11 cinemas and 488 showtimes on 3 November 2026. Birmarket's robots endpoint returned 403 from this environment; collection stopped and its 160 prior products were retained. Recompressed catalogue photos of earbuds, laptops, phones, footwear and backpacks retrieved corresponding products near the top; a blank image produced no cards. These small smoke checks do not establish broad visual accuracy.

The application remains a local single-user demonstration. Public multi-user deployment needs visitor isolation/authentication and durable storage. SQLite and global session locking are not a distributed transaction design. CLIP requires more memory than tiny free hosting plans. Source websites can block access or change markup. No Birmarket/CinemaPlus partner sandbox, live stock/seat confirmation, actual supplier transaction, browser visual test or microphone test is claimed.

The supplied LangChain router example informed the architecture. The RAG research template and LangGraph Supervisor were reviewed but were not suitable implementation bases for exact catalogue actions; none was cloned. The application uses existing project scrapers and original repository/engine code. Runtime dependencies are locked. Source links, evaluation inputs and detailed implementation evidence are recorded in REFERENCES.md, TEST_LOG.md, VALIDATION.md and PHASE2_LOG.md.
