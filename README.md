# Knowledge Product Manager

A local enterprise knowledge catalog with 11 business domains, 33 subdomains, 44 knowledge products, and 150 assets. Synthetic metadata connects actual PostgreSQL rows and MinIO documents to RDF governance and OpenSearch keyword/vector indexes.

## Run

Requires Docker, Node.js 22+, and uv. The Python environment uses Python 3.12.

```sh
make install
make up
make seed
make index
make dev
```

Open `http://127.0.0.1:53000`. API documentation: `http://127.0.0.1:58123/docs`. Start the API and web separately with `make api` and `make web` if preferred. Use `make down` to stop this demo without deleting stored data.

The first indexing run downloads the pinned `sentence-transformers/all-MiniLM-L6-v2` model (384 dimensions). Allow several minutes and roughly 4 GB of Docker memory. Startup checks service readiness rather than treating an unavailable service as a working mock. The API loads the local embedding model before accepting searches, so startup can take longer on a heavily loaded machine.

## OpenRouter, DeepSeek, and agentic search

Copy `.env.example` to `.env` at the repository root and set `OPENROUTER_API_KEY`. `OPENROUTER_MODEL` defaults to `deepseek/deepseek-v3.2`. OpenRouter calls use the OpenAI-compatible Chat Completions contract with strict JSON schemas and its response-healing plugin. The server still validates every result and rejects malformed output and unsupported citations. A narrow decoder handles tokenizer whitespace markers outside JSON strings without changing source text. Restart the API after changing settings. Keys remain server-side; never use a `NEXT_PUBLIC_` credential variable.

Default search uses DeepSeek through OpenRouter with the official OpenAI SDK for schema-validated query planning and cited synthesis. LangGraph orchestrates authorization, planning, RDF concept resolution, keyword/vector retrieval, provenance expansion, coverage assessment, synthesis, and citation validation. PostgreSQL stores runs and checkpoints. Runs have a 90-second deadline, two retrieval passes, and 12 tool calls. The UI shows tool outcomes, not private model reasoning.

Without a key, select **Extractive demo** explicitly. This mode performs actual vector/keyword retrieval and returns source excerpts through the same LangGraph workflow; it is labeled and does not claim LLM synthesis.

## Architecture

| Service | Role | Local port |
|---|---|---|
| PostgreSQL 17 | Catalog, metadata, business rows, jobs, search/checkpoints | 56432 |
| MinIO | Private synthetic source documents | 59010; console 59011 |
| Jena Fuseki 5.4 | Persistent RDF named graphs and SPARQL | 53030 |
| OpenSearch 2.19 | Keyword and real vector index | 59200 |
| FastAPI | Scoped services, OpenRouter/LangGraph, MCP | 58123 |
| Next.js | Eight application destinations | 53000 |

The PostgreSQL catalog uses indexed JSONB records, a domain foreign key, validated application DTOs, and a separate business-row table. The seed manifest maps IDs across SQL, RDF, objects, and indexed evidence. An OpenSearch index is derived and can be rebuilt with `make index`; changing embedding model/dimensions requires a new index name. Metadata, structured rows, and document chunks are distinct evidence types.

MCP endpoint and connection instructions: [docs/mcp.md](docs/mcp.md). The API and MCP tools reuse the same permission checks.

## Demo identity and data

The persona selector simulates Administrator, Analyst, Domain steward, and Delegate access. The browser can deliberately select any demo persona; this is not a production login system. Administrator can edit projects, gap descriptions/status, roles, and product metadata. Domain stewards/delegates edit within their assigned scope. Scope changes invalidate access to previous search evidence.

All names, amounts, records, quality scores, and documents are synthetic. The RDF fixture deliberately omits one asserted stewardship relationship to demonstrate a SHACL finding. Coverage percentages show a defined numerator/denominator. Every domain has working stored rows and documents; locations refer to local services.

## Verification

With services and the API/web running:

```sh
make test
npm --prefix frontend run typecheck
npm --prefix frontend run build
make test-e2e
```

Backend integration checks use actual services and local embeddings; provider contract tests substitute the provider HTTP boundary. Live DeepSeek generation requires configured credentials and is reported separately. Browser checks cover catalog filters, real source previews, domains, ontology, and cited extractive search.

## Recovery

- `docker compose ps` and `/health` reveal unavailable services.
- `make seed` is idempotent and preserves catalog edits; it refreshes synthetic objects.
- `make index` rebuilds derived evidence without duplicate IDs; failed assets show failed readiness and can be retried.
- Failed provider calls show an explicit error. Completed runs are fetched rather than regenerated when a browser reconnects.
- Data volumes survive `make down`; no routine command deletes them.
- MinIO demo console credentials are in `.env.example`; keep the loopback demo private.

Production identity, external enterprise connectors, public MCP hosting/OAuth, autonomous agent writes, arbitrary SQL/SPARQL, and ontology authoring are outside this demo.

A standalone ingestion worker is available with `PYTHONPATH=backend uv run --project backend python -m app.worker`. Administrator requests to `POST /index/jobs` persist an index job; the API executor or standalone worker claims it once. `GET /index/jobs/{id}` exposes completion/failure. Retrying submits a new job against the same stable evidence IDs.

`POST /search/runs/{id}/resume` reuses scoped LangGraph checkpoints. Completed runs are returned without generation. An interrupted provider request with an uncertain outcome is not automatically replayed; expired runs require a new search.

UI direction: signal red, Swiss editorial typography, Nothing-inspired dot patterns, translucent liquid-glass surfaces, and real Paper Design WebGL shaders. Reduced-motion and non-WebGL fallbacks preserve readability and function.
