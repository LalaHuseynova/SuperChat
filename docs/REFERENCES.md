# Reference review and attribution

Reviewed 2 November 2026. Application implementation is original; no template repository code was copied or vendored.

| Source | Findings | Decision |
|---|---|---|
| [LangChain router knowledge-base tutorial](https://github.com/langchain-ai/docs/blob/main/src/oss/langchain/multi-agent/router-knowledge-base.mdx) | Classifies a request, selects specialized domains, then combines results. Its examples concern GitHub/Notion/Slack, not inventory. | Adopt the architectural pattern. Use typed domain modules and deterministic synthesis for the small catalogue; no clone needed. |
| [RAG research agent template](https://github.com/langchain-ai/rag-research-agent-template) | Document indexing and iterative retrieval/research; vector stores and embeddings add setup. Repository metadata reported archived at inspection. | Not a good foundation for exact price, seat, cart and reservation operations. No clone. |
| [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) | Alternative hierarchical multi-agent library. Useful when specialist agents require autonomous tool loops. | Evaluated as an alternative, but a model-driven handoff loop adds complexity without improving this fixed dataset. No clone. |
| [OpenRouter structured output](https://openrouter.ai/docs/guides/features/structured-outputs) | JSON/JSON Schema responses vary by provider support. | Use JSON mode with independent Pydantic validation and deterministic fallback; model output is untrusted. |
| [OpenRouter image understanding](https://github.com/OpenRouterTeam/docs/blob/main/guides/overview/multimodal/image-understanding.mdx) | Multimodal chat accepts image_url with base64 image data. | Used only for classification, never authoritative catalogue facts or actions. |
| [Gemini 2.5 Flash Lite on OpenRouter](https://openrouter.ai/google/gemini-2.5-flash-lite) | Supports image input and structured text tasks. | Configurable default for optional hosted interpretation; no claim of a free tier. |
| [Hugging Face zero-shot image classification](https://huggingface.co/docs/transformers/tasks/zero_shot_image_classification) | CLIP compares an image with candidate text labels. | Local optional category recognition with confidence/margin rejection. |
| [CLIP model card](https://huggingface.co/openai/clip-vit-base-patch32) | Pretrained CLIP weights; MIT licence listed by the model repository. | Weights stay in the model cache, not in the source distribution. Scores are not calibrated probabilities. |
| [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) | Browser recognition/synthesis; support and locales vary. | Continuous speech events and pause timer; clear fallback if unavailable. |

Runtime dependencies are installed from registries and pinned in `uv.lock`: FastAPI (MIT), Uvicorn (BSD-3-Clause), Pydantic (MIT), HTTPX (BSD-3-Clause), python-multipart (Apache-2.0), Pillow (MIT-CMU), python-dotenv (BSD-3-Clause); optional Transformers (Apache-2.0), PyTorch (BSD-style). Transitive packages retain their own licences. No upstream source files are redistributed as application code.

A local, undistributed visual smoke-test photo came from [Headphones.jpg](https://commons.wikimedia.org/wiki/File:Headphones.jpg), by Atorero (Alexander Kozlov), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). It was used to validate category recognition, not included as an official catalogue asset. The application does not claim the photographed Koss headphones are the mock Sonivo product.


## Real-data integration sources (checked 3 November 2026)

- [Official Aviasales Data API contract](https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API): cached prices, X-Access-Token, currency, dates and pagination.
- [Data API access](https://support.travelpayouts.com/hc/en-us/articles/203956083-Requirements-for-Aviasales-data-API-access).
- [Live Search access requirements](https://support.travelpayouts.com/hc/en-us/articles/210995808-How-to-get-access-to-the-Aviasales-Search-API): a separate restricted product; not used here.
- [Birmarket seller documentation](https://edu.business.umico.az/space/knowledge/18514233/1/): seller API mentions are not consumer catalogue access.
- [CinemaPlus contact](https://web.cinemastercard.az/contacts): public website integration is not a supplied partner sandbox.
- Existing project scraper modules in `preparation_dataset/` are reused; original source archives remain auditable. SQLite and the CLIP embedding index are local derived stores.
