# Verification record

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
