# Knowledge Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent local enterprise knowledge catalog with PostgreSQL, MinIO, RDF governance, OpenSearch vector retrieval, OpenAI synthesis, LangGraph orchestration, and MCP access.

**Architecture:** Next.js consumes a Python/FastAPI API with generated TypeScript schemas. Application services own authorization and provenance; REST, LangGraph tools, and MCP call those services. PostgreSQL, MinIO, Fuseki, and OpenSearch run through Docker Compose, with a Python ingestion worker and checkpointed search execution.

**Tech Stack:** TypeScript, React/Next.js, Python, FastAPI, SQLAlchemy/Alembic, PostgreSQL, MinIO, Apache Jena Fuseki, RDFLib/pySHACL, OpenSearch, sentence-transformers, official OpenAI SDK, LangGraph, official MCP Python SDK, pytest, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-07-knowledge-catalog-design.md`

## Global Constraints

- Include exactly the 11 business domains listed in the specification.
- Seed 33 subdomains, 44 products, and 150 assets; every domain has stored SQL and document examples.
- PostgreSQL owns catalog metadata; MinIO owns original objects; Fuseki owns semantic definitions and relationships. OpenSearch is a rebuildable derived index.
- Synthetic data and registered-only sources are labeled explicitly.
- Server-side credentials only; OpenAI model is configured through OPENAI_MODEL.
- Default agent uses the OpenAI Responses API; extractive mode is explicitly selected and labeled.
- Limit each run to two retrieval passes, 12 tool calls, and 90 seconds.
- No arbitrary SQL/SPARQL, agent writes, production SSO, or public MCP hosting.
- Scope checks apply to REST, graph traversal, vector retrieval, checkpoints, citations, and MCP resources/tools.
- Preserve the historical October 6 documents; this plan implements the October 7 specification.
- Plan commands describe future verification, not checks already executed.

## Review Focus

1. Cross-domain products and graph paths must never expose denied asset identifiers or excerpts; owned by Tasks 2, 4, 5, and 7.
2. Changed role assignments between run creation and resume must invalidate inaccessible checkpoints/evidence; owned by Tasks 6 and 7.
3. Partial multi-store seeding and indexing failures must be retryable without duplicate or falsely ready records; owned by Tasks 3 and 5.
4. Provider refusal, invalid citations, budget exhaustion, and disconnect/reconnect must not fabricate answers or repeat completed synthesis; owned by Task 6.
5. Malformed filters, malicious object paths, and arbitrary tool query strings must fail validation before reaching adapters; owned by Tasks 2, 3, and 7.

## File structure and contracts

- `frontend/src/app/`: eight application destinations and Next.js route layouts.
- `frontend/src/components/`: shell, filters, tables, drawers, status labels, graph/list components.
- `frontend/src/api/generated.ts`: generated API DTOs; `client.ts`: REST and SSE client.
- `backend/app/contracts.py`: Pydantic DTOs shared by routes and tools.
- `backend/app/auth.py`: server-derived ScopeContext and permission policies.
- `backend/app/catalog/`: models, queries, scoped edits, overview aggregates.
- `backend/app/storage/`: MinIO objects and allowlisted structured previews.
- `backend/app/ontology/`: RDF vocabulary, graph adapter, SHACL validation.
- `backend/app/retrieval/`: extraction, chunks, embeddings, OpenSearch adapter, ranking.
- `backend/app/agent/`: OpenAI provider, LangGraph state/nodes, checkpointing, run service.
- `backend/app/mcp/`: transport authentication and tool/resource/prompt registration.
- `backend/app/main.py`: API composition; `worker.py`: persisted job/run execution.
- `backend/fixtures/`: repeatable synthetic data and document originals.
- `backend/tests/`: unit, adapter integration, and end-to-end acceptance tests.
- `infra/`: Dockerfiles, Fuseki dataset configuration, service startup configuration.
- `compose.yaml`, `.env.example`, `Makefile`, `README.md`: local operation.
- `design/`: 12ui concepts, selected references, and exported prototypes.

DTOs in contracts.py: ScopeContext(person_id, role, domain_ids, product_ids, scope_version); CatalogQuery(text, domain_id, subdomain_id, kind, source_id, owner_id, status, classification, quality, sort, page, page_size); Page(items, total, page, page_size); ProductDetail; AssetDetail; DomainDetail; GraphNeighborhood(nodes, edges, truncated); Evidence(id, asset_id, text, provenance, concept_iris); SearchRequest(query, mode); SearchResult(run_id, status, statements, evidence, gaps, events); SearchEvent(sequence, stage, status, summary); HealthReport(services); SeedReport(counts, stages).

ScopeContext is never a client-submitted DTO. Resolve it from a server-issued demo session for browser requests, fixed bearer-token mapping for MCP HTTP, or configured identity for stdio. Clients may choose a demo persona through the browser session endpoint; transport callers cannot impersonate another identity by supplying tool arguments.

### Task 1: Runtime, contracts, and service readiness

**Files:** Create compose.yaml, .env.example, Makefile, infra/backend.Dockerfile, infra/fuseki/config.ttl, backend/pyproject.toml, backend/app/main.py, backend/app/config.py, backend/app/contracts.py, backend/app/health.py, frontend/package.json, frontend/tsconfig.json, frontend/src/api/generated.ts, backend/tests/integration/test_health.py.

**Interfaces:** Produces Settings with validated service endpoints and model settings; `service_health() -> HealthReport`; GET /health; OpenAPI schema. Establish npm/uv lockfiles and generate TypeScript types from OpenAPI.

- [ ] Write test_health.py: assert all four service adapters report ready against real services; stopped OpenSearch reports unavailable while PostgreSQL remains ready; public configuration contains no credentials.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_health.py -q`; expect missing implementation failure, not a Docker setup failure.
- [ ] Verify official compatibility guidance and registry availability; pin exact image tags/digests and dependency versions in lockfiles. Build Compose with loopback ports, volumes, service health checks, and project-scoped configuration.
- [ ] Implement Settings, contracts, service_health, and API schema generation. Add `make up`, `make migrate`, `make seed`, `make dev`, `make test`, and `make test-e2e` targets for their owning later tasks.
- [ ] Run the named test with real services and verify generated types match the OpenAPI response schema.
- [ ] Commit this deliverable as `chore: establish catalog runtime and service contracts`.

### Task 2: Persistent catalog, scope, and governance metadata

**Files:** Create backend/app/auth.py, backend/app/catalog/models.py, backend/app/catalog/service.py, backend/app/catalog/routes.py, backend/alembic.ini, backend/alembic/env.py, backend/alembic/versions/001_catalog.py, backend/tests/integration/test_catalog.py.

**Interfaces:** Produces `resolve_scope(session_token: str) -> ScopeContext`; `list_catalog(scope: ScopeContext, query: CatalogQuery) -> Page`; `get_product(scope, product_id: str) -> ProductDetail`; `get_asset(scope, asset_id: str) -> AssetDetail`; `list_domains(scope) -> list[DomainDetail]`; `update_metadata(scope, entity_type: str, entity_id: str, patch: dict) -> dict`. Routes /session, /catalog, /products/{id}, /assets/{id}, /domains, /sources, /projects, /gaps, /roles, /overview; metadata PATCH endpoints.

- [ ] Write test_catalog.py asserting seed fixture relationships persist, combined filters paginate correctly, project subdomain/domain mismatches fail, analyst edits return 403, scoped steward edits survive reload, gap issue counts and coverage basis are computed, and malformed pagination returns 422.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_catalog.py -q` and verify behavioral failures.
- [ ] Implement normalized models, migrations, parameterized catalog queries, aggregates, scopes, and validated patch allowlists. Resolve project/product domain consistency. Browser sessions bind fixed synthetic identities; edits invalidate affected indexing readiness and increment scope_version on role changes.
- [ ] Run the tests; confirm denied asset IDs are omitted even when an accessible product aggregates assets from another domain.
- [ ] Commit as `feat: persist scoped catalog and governance metadata`.

### Task 3: Repeatable fixtures, MinIO originals, and structured previews

**Files:** Create backend/fixtures/catalog.json, backend/fixtures/documents/, backend/app/seed.py, backend/app/storage/objects.py, backend/app/storage/structured.py, backend/app/storage/routes.py, backend/alembic/versions/002_fixtures_jobs.py, backend/tests/integration/test_seed_storage.py.

**Interfaces:** Consumes Task 2 services. Produces `seed_demo() -> SeedReport`; `preview_rows(scope, asset_id: str, limit: int = 20) -> list[dict]`; `preview_object(scope, asset_id: str) -> dict`; persisted stage jobs; GET /assets/{id}/rows and /assets/{id}/preview. Manifest contains stable UUIDs, IRIs, object keys, SQL row IDs, and hashes.

- [ ] Write test_seed_storage.py asserting exactly 11/33/44/150 domain/subdomain/product/asset counts, representative SQL rows and MinIO objects in every domain, byte-for-byte source content retrieval, seed rerun stability, preservation of edited catalog metadata, recovery after an injected MinIO failure, and denied/path-traversal preview rejection.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_seed_storage.py -q`; verify failed assertions before implementation.
- [ ] Create useful synthetic records and documents, real business tables with allowlisted preview queries, and stage-aware idempotent seeding. Upload private MinIO originals and extracted artifact keys with hashes. Generate authorized short-lived object links. Regular seed preserves user edits; an explicit reset targets only this demo namespace.
- [ ] Run tests against PostgreSQL and MinIO, restart services, and repeat count/persistence checks.
- [ ] Commit as `feat: seed synthetic domains and stored source evidence`.

### Task 4: RDF governance and ontology exploration

**Files:** Create backend/app/ontology/vocabulary.ttl, backend/app/ontology/shapes.ttl, backend/app/ontology/service.py, backend/app/ontology/routes.py, backend/tests/integration/test_ontology.py.

**Interfaces:** Produces `sync_ontology() -> dict`; `explore_ontology(scope, concept_id: str, depth: int = 1, limit: int = 50) -> GraphNeighborhood`; `resolve_concepts(scope, labels: list[str]) -> list[str]`; `validate_ontology() -> list[dict]`. Routes /ontology/concepts, /ontology/neighborhood, /ontology/rdf, /ontology/findings.

- [ ] Write test_ontology.py asserting vocabulary/instance named graphs remain separate, product→asset→source paths resolve manifest IDs, Counterparty maps to structured/document evidence, seeded violations produce named SHACL findings, depth/node limits are enforced, and denied nodes plus their edges are absent.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_ontology.py -q` and verify behavioral failures.
- [ ] Implement Fuseki persistence and parameterized allowlisted SPARQL templates, scope-aware bounded neighborhoods, RDFLib serialization, and pySHACL checks. Return readable relationship definitions, asserted provenance, and truncation status.
- [ ] Run tests against Fuseki, re-seed without graph duplicates, and verify RDF inspection is scope-filtered.
- [ ] Commit as `feat: expose governed RDF ontology and asset relationships`.

### Task 5: Embeddings, indexing, and hybrid evidence retrieval

**Files:** Create backend/app/retrieval/extract.py, backend/app/retrieval/embed.py, backend/app/retrieval/index.py, backend/app/retrieval/service.py, backend/app/worker.py, backend/tests/integration/test_retrieval.py.

**Interfaces:** Produces `index_assets(asset_ids: list[str]) -> dict`; `retrieve(scope, query: str, concept_ids: list[str], limit: int = 10) -> list[Evidence]`; `get_evidence(scope, evidence_id: str) -> Evidence`; `expand_evidence(scope, evidence: list[Evidence]) -> list[Evidence]`. OpenSearch stores model/dimensions/hash/scope metadata; ingestion jobs persist stages in PostgreSQL.

- [ ] Write test_retrieval.py asserting actual vectors have the configured model dimension, keyword and semantic queries find fixtures, cross-source evidence retains table-row/chunk-offset provenance, authorization filters apply to both query types, incompatible dimensions reject the index, deletion removes evidence, and retries after OpenSearch failure do not duplicate chunks.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_retrieval.py -q`; missing model/service setup is a setup issue rather than the expected red test.
- [ ] Pin and load a local sentence-transformer model; implement chunking, real embeddings, cosine vector search, keyword retrieval, and reciprocal-rank fusion. Scope filter before ranking; ontology IDs guide expansion without excluding untagged relevant permitted evidence. Mark partial, stale, failed, and ready states honestly.
- [ ] Run the integration tests with actual model and OpenSearch; inject source content edits and demonstrate hash-based reindexing.
- [ ] Commit as `feat: index and retrieve ontology-linked vector evidence`.

### Task 6: OpenAI Responses integration and LangGraph search

**Files:** Create backend/app/agent/provider.py, backend/app/agent/state.py, backend/app/agent/graph.py, backend/app/agent/service.py, backend/app/agent/routes.py, backend/alembic/versions/003_search_runs.py, backend/tests/test_agent.py, backend/tests/integration/test_agent_runs.py.

**Interfaces:** Consumes Tasks 2/4/5. Produces `start_search(scope, request: SearchRequest) -> SearchResult`; `get_search(scope, run_id: str) -> SearchResult`; `cancel_search(scope, run_id: str) -> SearchResult`; `stream_search(scope, run_id: str, after_sequence: int = 0) -> AsyncIterator[SearchEvent]`. POST /search/runs, GET /search/runs/{id}, GET /search/runs/{id}/events, POST /search/runs/{id}/cancel. PlanOutput(concept_labels, query_variants, strategies); AnswerOutput(statements[{text,evidence_ids}], gaps, uncertainty).

- [ ] Write test_agent.py/test_agent_runs.py asserting strict Responses request schemas, configured model use, refusal/missing key/429/timeout states, rejection of unknown citation IDs, denied evidence exclusion, no-evidence termination before synthesis, two-pass/12-call/90-second bounds, cancellation, and no repeated synthesis after reconnect.
- [ ] Run `uv run --project backend pytest backend/tests/test_agent.py backend/tests/integration/test_agent_runs.py -q` with fake provider outputs and real retrieval/checkpoint adapters.
- [ ] Implement official OpenAI SDK requests with store=false, server-side credentials, bounded retries and output limits; parse and validate typed output. Use LangGraph StateGraph nodes authorize→plan→resolve→retrieve→expand→assess→synthesize→validate→finish, with at most one coverage-driven retrieval loop. Persist checkpoints and run ownership; revalidate current scope on resume. Record tool outcome events, never private reasoning.
- [ ] Implement explicitly selected extractive mode for no-key demos. Completed generation is persisted before finishing; ambiguous provider timeouts are surfaced and never automatically replayed as a claimed successful resume. Optional manual retry starts a separate run.
- [ ] Run the tests; add changed-role checkpoint and malicious document instruction cases. Perform a small live API smoke test only when credentials exist; otherwise report LLM integration verification as credential-blocked, while mocked contract tests remain available.
- [ ] Commit as `feat: orchestrate cited OpenAI search with LangGraph`.

### Task 7: MCP tools, resources, and transport access

**Files:** Create backend/app/mcp/server.py, backend/app/mcp/auth.py, backend/app/mcp/stdio.py, backend/tests/integration/test_mcp.py, docs/mcp.md.

**Interfaces:** Register tools list_domains, search_catalog, get_knowledge_product, get_asset, explore_ontology, get_evidence, agentic_search; resources knowledge://domains, knowledge://products/{id}, knowledge://ontology; prompt search_knowledge. agentic_search accepts query for creation or run_id for polling, mutually exclusive, and returns SearchResult. Mount Streamable HTTP /mcp and provide `uv run --project backend python -m app.mcp.stdio` from configured package context.

- [ ] Write test_mcp.py with a real SDK client: initialize, discover all seven tools, list/read resources, retrieve prompt, search/create/poll, inspect attributable evidence, and reject forbidden assets. Check missing bearer credentials, malformed arguments, caller-supplied persona, foreign run polling, changed-scope polling, and invalid host/origin.
- [ ] Run `uv run --project backend pytest backend/tests/integration/test_mcp.py -q`; verify absent registration/behavior failures.
- [ ] Implement the official MCP SDK transport and registrations using shared application DTOs/services. Map local bearer tokens to server-fixed scope; configure stdio identity server-side. Tools return readable summaries and structured payloads; resource enumeration itself is scoped. Do not return credentials or unrestricted signed links.
- [ ] Run real client tests over HTTP and stdio. Document local connection configuration, demo identity, long-run polling, and explicit local-only limitations.
- [ ] Commit as `feat: expose scoped catalog and agentic search over MCP`.

### Task 8: Enterprise UI and integrated delivery

**Files:** Create frontend/src/app/layout.tsx, frontend/src/app/page.tsx, frontend/src/app/catalog/page.tsx, frontend/src/app/domains/page.tsx, frontend/src/app/sources/page.tsx, frontend/src/app/ontology/page.tsx, frontend/src/app/search/page.tsx, frontend/src/app/projects/page.tsx, frontend/src/app/roles/page.tsx, frontend/src/components/, frontend/src/api/client.ts, frontend/tests/e2e/catalog.spec.ts, frontend/tests/e2e/search.spec.ts, frontend/tests/e2e/accessibility.spec.ts, backend/tests/acceptance/test_demo.py, README.md, scripts/verify.sh, design/.

**Interfaces:** Uses generated contracts and scoped APIs from previous tasks. Provides eight destinations, shared shell/filter/detail components, graph/list alternatives, source previews, search SSE progress and citations, scoped persistent metadata edits, and visible service/index readiness.

- [ ] Write Playwright catalog/search tests: combined filters survive reload; a product reveals SQL and MinIO evidence; RDF node navigation opens matching assets; project/gap edits persist; analyst cannot edit; no-key search reports configuration status and selected extractive mode is labeled; citation links open only authorized evidence; event reconnect does not restart search. Include narrow-screen and keyboard drawer/graph-list journeys.
- [ ] Run `npm --prefix frontend exec playwright test` with running API and services; verify meaningful absent UI failures.
- [ ] Invoke required 12ui-design skill, generate and inspect at least four design directions, choose a screenshot-informed enterprise direction, and retain selected references/exports. Build all eight views with loading/empty/error states, readable tables, graph navigation, project budgets/coverage, role simulation, and actual API actions.
- [ ] Implement live search progress, cancellation, evidence cards, cited answer statements, graph paths, gaps, and MCP connection instructions. Regenerate types and compare completed desktop/narrow layouts to selected visual references.
- [ ] Write test_demo.py covering all 11 domains, cross-store provenance, scoped retrieval, MCP parity, idempotent seeds, edited-record restart persistence, failure recovery, and citation validation. Add local startup, credentials, service resource requirements, model download, seed/reset, recovery, and MCP documentation.
- [ ] Run `uv run --project backend pytest backend/tests -q`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`, and Playwright. Confirm all named tests pass; separately record whether live OpenAI calls ran. Run final smoke checks through the UI and MCP client against real services.
- [ ] Commit as `feat: deliver enterprise knowledge catalog and verified demo journeys`.

## Coverage and handoff

Tasks 1–3 establish the runnable catalog and real source fixtures; Task 4 implements ontology governance; Task 5 implements real indexing; Task 6 owns LangGraph/OpenAI behavior; Task 7 exposes the same services through MCP; Task 8 completes every user-facing destination and verifies the integrated journey. No acceptance requirement depends on a fabricated service fallback.

Self-review: every specification destination and acceptance check has an owning task; shared interfaces use the same DTO names; each review-focus failure has a named test in its owning task. Dependency order is sequential because stable IDs, scope, and evidence contracts cross all services.

Recommend native execution in this session because the eight deliverables share authorization and provenance contracts. The user reviews this plan and selects execution method before implementation begins.

