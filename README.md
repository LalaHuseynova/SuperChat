# SuperChat

A local, multilingual chat for flights, shopping, and cinema, built against the five official JSON files. One conversation can move between all three domains. It includes mock reservations, a cart, saved chat sessions, voice input, and visual product search.

## Run

Requires Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/). From this folder:

```bash
./run.sh --vision
```

Open **http://localhost:8000**. The command installs the locked dependencies and starts the application. `./run.sh` starts the lighter core without installing the local image model dependencies. With an OpenRouter key, both text understanding and image search work without the local vision extra.

For a different port: `PORT=8001 ./run.sh --vision`. Stop with Ctrl+C. To develop with automatic reload: `uv run --extra vision uvicorn superchat.app:app --reload`.

The app binds to your computer's loopback interface. It is a single-user competition demo, not a public multi-user service. The PDF brief and official data remain unchanged.

## OpenRouter (optional, recommended for flexible natural language)

A local `.env` file has been prepared. Add your key **locally**, then restart the app:

```dotenv
OPENROUTER_API_KEY=your-key-here
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=google/gemini-2.5-flash-lite
```

The key stays on the server and is excluded from Git and chat logs. Do not put it in the browser or commit it. The model is configurable; use an OpenRouter model with JSON and image input support. Free models may have rate limits and differing capabilities; the app does not depend on a free tier.

The model translates requests into validated searches and actions. It **does not write prices, stock, seat counts, or reservation confirmations**. Those are assembled from local repositories. Invalid output, timeouts, and provider failures fall back to the offline router, with a visible notice. The provider receives your message, recent conversation context, and (only for image search) the uploaded image. No external flight, shopping, or cinema provider is contacted.

Without a key, the offline multilingual rules support the demonstrated catalogue and common follow-ups. Indirect descriptions and slang may require clarification; a hosted model is not silently simulated.

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
- New chats are independent. **Start a new chat with this context** explicitly copies language, preferences and search state; it does not copy carts, bookings, or pending actions. The source chat is recorded.
- Saved prices in the transcript are historical evidence. Every new operation re-reads the catalogue and checks availability. Reservations across all sessions reduce remaining mock seats.
- An OS lock covers validation and commit. A single fsynced JSONL event commits the entire turn. Retrying the same request ID returns the original response, so a dropped connection does not duplicate a reservation.
- Corrupt logs fail closed. Back up `runtime/` and restore a damaged log from backup; never manually delete reservation lines to “repair” inventory.
- Logs are human-readable and exportable from the sidebar. Images, API keys and payment details are not logged. No payments or real bookings exist.

Logs reduce context loss; they do not make arbitrary natural-language interpretation infallible. Clarifications, validated IDs, fresh data reads, and explicit action checks provide the other safeguards.

## Bonus features

**Voice:** Click the microphone once and allow browser access. Speech start/end events and a silence timer support hands-free messages without holding a button. Final transcripts use the same message route. Optional spoken replies are available under “Your space”. Browser speech services may need internet; Azerbaijani recognition and synthesis depend on the browser/OS. Chrome is recommended; unavailable or denied recognition shows a fallback message. This feature was implemented but could not be microphone-tested in the task environment.

**Visual search:** Upload a JPEG, PNG, or WebP (up to 8 MB / 20 MP). OpenRouter vision is preferred when configured. Otherwise the local CLIP model matches ten catalogue product types plus an “other” category. Its weights are downloaded on first use, and cached for later offline use:

```bash
uv run --extra vision python scripts/prepare_vision.py
```

Set `VISION_OFFLINE=true` after preparing the cache. Local acceptance requires score ≥ 0.65 and a margin ≥ 0.20 over the next label; hosted vision requires ≥ 0.75. These are model confidence scores, **not calibrated correctness probabilities**. Uncertain photos produce one clarification question. The app identifies a product type, never claims an exact brand match, and only returns actual catalogue rows. Uploaded images are not retained.

**Languages:** English, Azerbaijani, and Russian response templates, product descriptions, UI labels, routing vocabulary, dates, and actions. The current message determines reply language; the interface selector also controls speech locale. Mixed-language inputs are supported within the parser's vocabulary. Full open-ended understanding is stronger with OpenRouter enabled.

## Validation and deliverables

```bash
uv run --extra dev pytest -q
PYTHONPATH=. uv run python scripts/evaluate_routing.py
node --check superchat/static/app.js
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
  vision.py         Hosted/local image classification and confidence gate
  i18n.py           Localized responses and catalogue descriptions
  static/           Responsive web interface and hands-free voice
SuperChat_Mock_Data/ Official, unchanged competition data
runtime/sessions/   Private local logs (ignored by Git)
tests/             Conversation, API, persistence and provider tests
docs/              Report, demo, requirements, evaluation and references
```

## Phase 2 boundary

`FlightRepository`, `ProductRepository`, and `ShowtimeRepository` define the data boundary. Supply API-backed adapters with the same methods and replace the three injected repositories in `Engine`. Real inventory writes need provider reservation APIs and their idempotency keys; local mock inventory is not a substitute. Authentication, multi-user isolation, distributed locks, rate limits, provider timeouts/pagination, and real inventory consistency belong to Phase 2.

No GitHub project was cloned: the reviewed templates are documented in the references, and none was a better implementation base for this small, offline structured dataset. The routing architecture is informed by LangChain's published router pattern; application code is original for this task.
