# Knowledge Product Manager

A search-first enterprise knowledge catalog over **11 domains, 33 subdomains, 44 knowledge products and 150 assets**. Search shows an AI answer and ordinary results together. Opening a result shows actual PostgreSQL rows, MinIO document passages or RDF definitions first, with metadata and relationships kept as context.

The local demo combines PostgreSQL, MinIO (S3-compatible), Jena Fuseki RDF, OpenSearch lexical/vector retrieval, OpenRouter DeepSeek, LangGraph and a FastMCP server. The UI is light-only with red accents, subtle rose glass, a Swiss typographic grid, restrained motion and a React Flow/ELK ontology explorer.

## Run from the supplied mock data

Requires Docker, Node.js 22+ and uv; Python 3.12 is pinned by setup.

```sh
cp .env.example .env
make install
make up
make migrate
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py validate
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py restore --execute
make index
make dev
```

Open [the app](http://127.0.0.1:53000), [API docs](http://127.0.0.1:58123/docs) or [health](http://127.0.0.1:58123/health). Restore requires an empty catalog and does not delete existing data. For a newly generated fixture set, use `make seed` instead of restore. `make down` preserves Docker volumes. The first index run downloads the pinned 384-dimensional all-MiniLM-L6-v2 model; allow several minutes and about 4 GB of Docker memory.

Set `OPENROUTER_API_KEY` only in the ignored server `.env`, then restart the API. Never put provider keys in a `NEXT_PUBLIC_` variable. The graph-centered search flag and provider route are explicit configuration; see the verification record for measured rollout status. **Answer options → Use source excerpts** is an explicit no-model mode. Missing keys and provider errors remain visible while catalog results stay available.

## Documentation

- [System architecture](docs/architecture.md): components, stores, domain model, read flow, scale controls and deployment boundaries.
- [Agentic architecture](docs/agentic-architecture.md): graph routing, dynamic prompts, typed tools, coverage, drafting, claim verification, durable execution and treasury example.
- [API reference](docs/api.md): session, discovery, content/citation, run lifecycle, editing and ingestion routes; [OpenAPI contract](backend/openapi.json).
- [MCP](docs/mcp.md): HTTP/stdio setup, fourteen tools, resources, prompts and permission model.
- [Mock data](docs/data.md): snapshot contents, checksums, export/restore and excluded runtime data.
- [Implementation decisions](docs/implementation-decisions.md): scope adaptations and final review fixes.
- [Verification](docs/verification.md): test commands, measured evaluations, local scale/restore evidence and limitations.
- [Research](docs/research/2026-10-08-graph-centered-agentic-search.md): primary-source reasoning behind graph-centered adaptive retrieval.

## Use the application

Ask a question from Home. Search presents a coherent cited answer and matching knowledge products, tables and documents. URL filters, pagination and opening content reconnect to the saved run without another paid generation. A named citation opens its exact supporting section/row and distinguishes current content from a saved versioned excerpt.

Catalog is a grid/list library. Workspace offers Domains, Sources, Ontology, Projects and Roles. Projects include sponsor, budget, status and domain/subdomain; gaps include coverage, description, tags and quality issue counts. The ontology explorer supports node/alias search, domain/type/relation filters, fit/zoom/minimap, layout direction, selected neighborhoods, evidence paths, source opening and an accessible list. Markdown/GFM source rendering disables raw HTML and executable/remote embeds.

All source names, persons, amounts and policies are synthetic. The persona selector simulates Administrator, Analyst, Steward and Delegate permissions. It is deliberately not production login. The RDF fixture includes a deliberate missing stewardship assertion for SHACL inspection. Internal `atlas-*` storage identifiers are retained for stable source bindings; the application name is Knowledge Product Manager.

## Services and operations

| Service | Local port |
|---|---:|
| Web | 53000 |
| API / HTTP MCP | 58123 |
| PostgreSQL | 56432 |
| MinIO / console | 59010 / 59011 |
| Fuseki | 53030 |
| OpenSearch | 59200 |

Run API/web separately with `make api` and `make web`. Dedicated workers:

```sh
PYTHONPATH=backend uv run --project backend python -m app.agent.worker
PYTHONPATH=backend uv run --project backend python -m app.worker
PYTHONPATH=backend uv run --project backend python -m app.mcp.stdio
```

Disable `LOCAL_SEARCH_WORKER` on API instances when running dedicated search workers. Shared PostgreSQL admission/leases coordinate ownership. Bounded tool reads, source streaming, indexed lookups and HNSW projection avoid full estate/dataset reads on interactive paths. These controls and local scale tests do not certify production throughput. Model judgments remain fallible; public deployment, enterprise connectors, production identity/OAuth and autonomous writes are outside the demo.

## Test and evaluate

Run source/index mutation tests before browser tests, sequentially:

```sh
make test
npm --prefix frontend run typecheck
npm --prefix frontend run build
make test-e2e
npm --prefix frontend audit
PYTHONPATH=backend uv run --project backend python scripts/evaluate_search.py \
  --engine adaptive --split development --output /tmp/kpm-offline-report.json
PYTHONPATH=backend uv run --project backend python scripts/benchmark_search_scale.py \
  --execute --output /tmp/kpm-scale-report.json
PYTHONPATH=backend uv run --project backend python scripts/verify_demo_restore.py
```

Evaluation defaults to offline. Live evaluation is an explicit `--provider live` action limited to twenty adaptive cases; reports refuse overwrites and preserve per-case progress. The benchmark creates a separate database/container and cleans only its own resources. See the verification document for exact completed gates, failed attempts and model-quality denominators.
