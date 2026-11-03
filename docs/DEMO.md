# Five-minute demonstration

## Real catalogue version

Start `./run.sh --real`, open http://localhost:8000 and use a new chat.

1. Choose English and ask “Show Samsung phones”; open a product source link.
2. Choose Russian and ask “Второй, подробнее”; show that the selected record is preserved.
3. Choose Azerbaijani and ask “Bu gün Dəniz Mallda hansı filmlər var?”; open a cinema source link.
4. Choose English and ask “Flights from Baku to Istanbul on 2026-11-06”; explain the cached-fare label. Results depend on the provider cache.
5. Ask “Back to headphones”; show shopping context and a local shopping-list action.
6. Ask “Show Samsung Galaxy S999 phones”, then “film ticket negativity exam university depression”; show no-match and clarification without cards.
7. Upload a clear product photo; show catalogue similarity scores and direct source links. An unrelated/blank image should not return products.
8. Reload and reopen the conversation; inspect the exported JSONL state/version history.

Use current cinema dates. Do not describe sample inventory or cached fares as live availability. Birmarket refresh is currently blocked from this environment and retains its previous collection.

## Original Phase 1 version


Run `./run.sh --vision`, open http://localhost:8000, and start a new conversation. Use the fixed demo date 2 November 2026. If repeating the demonstration, previous mock bookings still consume seats; choose a different available showtime/flight or use a separate log directory for rehearsal.

| Time | Say / do | Show |
|---|---|---|
| 0:00–0:35 | “Find me a flight from Baku to Istanbul on Friday.” | Three options: F013 175 AZN (one stop), F002 245 AZN, F001 289 AZN. Source IDs and exact baggage/time fields. |
| 0:35–1:00 | “What is playing tonight?” | Cinema switch #1; Orbit Zero, Deep Signal, Laugh Track. Deep Signal's S003 is sold out. |
| 1:00–1:25 | “Do you have wireless headphones under 100 AZN?” | Shopping switch #2; P001 at 89.90 AZN. Add it using the card. |
| 1:25–1:55 | “Back to flights.” Then “The cheaper one, is it direct?” | Flights switch #3; earlier route/date restored. F013 has one stop via TBS; no fabricated direct flight. |
| 1:55–2:20 | “Compare F001 and F002.” | Side-by-side grounded comparison. |
| 2:20–2:45 | “Show sci-fi films on Saturday.” Then “Reserve two seats for S011.” | Cinema switch #4; mock confirmation and updated seats. No payment. |
| 2:45–3:15 | “Покажи ноутбуки”. Then “İkinci, stokda var?” | Shopping switch #5 and two language changes; P004 has 12 in stock. |
| 3:15–3:40 | “I need a flight to Istanbul on 6 November and a backpack for the trip.” Then “Book it.” | Two domain sections, followed by a clarification because the referent is ambiguous. |
| 3:40–4:00 | “What is the weather in Ganja?” | Helpful scope response. |
| 4:00–4:25 | Reload the browser, reopen the saved conversation, ask “Back to headphones.” | The log restores state; the cart is intact. Export JSONL to inspect the route and state. |
| 4:25–4:45 | Upload a clear photo of headphones. | Product category, confidence and real catalogue result, without a brand claim. An unclear image should ask a question. |
| 4:45–5:00 | Enable microphone once; say “Show me black backpacks”, then pause. | Browser speech detection sends the final transcript through the same routing pipeline. |

Before a disconnected demo, prepare the CLIP model with `uv run --extra vision python scripts/prepare_vision.py`, set `VISION_OFFLINE=true`, and confirm browser voice availability. Voice may require internet even when catalogue and local visual search do not. If OpenRouter is enabled, the language model needs internet.
