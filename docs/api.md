# API reference and integration

FastAPI serves `http://127.0.0.1:58123`; interactive documentation is at `/docs`, the live contract is `/openapi.json`, and the checked-in contract is [openapi.json](../backend/openapi.json). Frontend DTOs are generated from this contract. Do not use frontend state as an authorization boundary.

## Sessions and scope

`GET /personas` lists synthetic personas; `POST /session` with `{"person_id":"admin"}` returns a session token. Send `Authorization: Bearer TOKEN` on scoped routes. `/session/scope` returns current role/domain access. This is intentionally a selectable demo persona, not production login. Domain filters narrow access; denied domains and sources remain denied even if their IDs are guessed.

```sh
# Obtain a demo token; keep the returned value in your client environment.
curl -s http://127.0.0.1:58123/session -H 'Content-Type: application/json' \
  -d '{"person_id":"admin"}'
# Use the token for ordinary search without generating a model answer.
curl -s -H "Authorization: Bearer $KPM_SESSION_TOKEN" \
  'http://127.0.0.1:58123/discovery/search?q=treasury&type=all&page=1&page_size=20'
```

## Endpoint map

| Operation | Endpoint | Behavior |
|---|---|---|
| Readiness | `GET /health` | Actual store readiness; unavailable service is not a working mock |
| Catalog | `GET /catalog` | Scoped products with filtering, sorting and paging |
| Discovery | `GET /discovery/search` | Ranked products/data/documents/definitions, domain/type/page filters |
| Domains | `GET /domains`, `/overview` | Governed domain and catalog summaries |
| Product | `GET /products/{id}` | Metadata, assets, ontology, quality and project context |
| Asset | `GET /assets/{id}` | Authorized metadata/context |
| Source content | `GET /content/{kind}/{id}` | Actual document sections, SQL rows or RDF definition, bounded cursor |
| Product content | `GET /products/{id}/content` | Source manifest + preferred primary content |
| Legacy preview | `GET /assets/{id}/preview`, `/rows` | Bounded preview compatibility routes |
| Saved evidence | `GET /evidence/{id}` | Scoped evidence and provenance |
| Ontology | `GET /ontology/concepts`, `/neighborhood` | Bounded graph neighborhood, source-backed relationships |
| Maintenance inspection | `GET /ontology/rdf`, `/findings` | Explicit scoped RDF/SHACL inspection; not automatic estate reads |
| Catalog edits | `PATCH /records/{kind}/{id}` | Validated permitted edits, current steward/admin scope |
| Start search | `POST /search/runs` | Persist/admit one bounded agentic run |
| Run state | `GET /search/runs/{id}` | Owned run result, outcome, public progress and usage |
| Stream progress | `GET /search/runs/{id}/events` | SSE events; no private model reasoning |
| Cancel | `POST /search/runs/{id}/cancel` | Persist cancellation; stale workers cannot overwrite it |
| Resume | `POST /search/runs/{id}/resume` | Reuse safe saved checkpoints/receipts; never replay uncertain paid calls |
| Indexing | `POST /index/jobs`, `GET /index/jobs/{id}` | Admin-only durable source projection job and status |

Use OpenAPI for exact query enums and response DTOs. IDs and cursors are opaque handles. A graph class ID and an asset ID are different types of object; neither implies a permission grant.

## Agentic run lifecycle

```sh
curl -s http://127.0.0.1:58123/search/runs \
  -H "Authorization: Bearer $KPM_SESSION_TOKEN" -H 'Content-Type: application/json' \
  -d '{"query":"Which policies govern treasury liquidity?","mode":"llm","intent_id":"client-request-001"}'
```

Poll the returned `run_id` or use its SSE route. `mode:"extractive"` explicitly requests actual source excerpts without model calls. Reusing the same persona/intent ID returns the same request only when its intent matches; a conflicting payload is rejected. Queue overload returns an explicit error. Completed results contain coherent `statements`, `answer_sections`, named `supporting_locators`, `evidence`, `graph_paths`, verification counts, usage and versions. `partial` is meaningful missing coverage; `no_evidence` is not an invented answer. Provider failures leave ordinary discovery available.

## Content and citations

Kinds are `asset`, `product`, `record`, `definition` and `evidence`. Query parameters carry `cursor`, `locator`, `version`, `run_id` and `preferred_asset_id` where applicable. Cursors bind object, scope and version; malformed cursors return 422 and a changed source during paging returns 409. A source citation can be opened with its exact version/locator and owned run. Recorded snapshot excerpts are labeled; actual current source content has independent freshness.

`ContentPage` separates `sections`/`rows`/`text` from `context`, `relationships`, `source_refs`, `manifest`, `next_cursor`, `truncated` and freshness/error information. Reads do not materialize an entire SQL dataset or arbitrary object blob. SQL tools use managed fields and typed filters/aggregation, not raw query strings.

## Errors and integration expectations

Validation errors use 422; absent/inaccessible objects use controlled 403/404 responses; changed source/scope and intent conflicts use 409; admission limits are explicit. Search results also carry terminal failure/configuration states. Clients should show available discovery/content alongside generation errors, preserve run IDs, abort obsolete content fetches, and never regenerate an answer on paging/filter changes. Restart services after server configuration changes. Provider/network failures are observable and may occur despite passing deterministic tests.

## Calculated source results

A saved aggregate citation supplies its owned `run_id`, `evidence_id`, source asset, version and `aggregate:` locator. The content reader validates its stored typed operation and reexecutes it. `ContentPage.aggregate` includes the current operation, field, filters, calculated values/unit/count and source reference; `rows` contains a bounded page of the underlying selection. A bare aggregate hash without the authorized saved operation returns 422 rather than being interpreted as a row ID. Current results and saved excerpts retain separate freshness. Individual row versions and aggregate result versions do not promise a transaction snapshot of an entire externally changing dataset.
