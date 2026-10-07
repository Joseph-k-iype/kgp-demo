# Knowledge Catalog — Local Full-Stack Demo

Date: 2026-10-07

## Intent and scope

Build an enterprise knowledge catalog demonstrating how knowledge products combine metadata, structured data, unstructured documents, semantic governance, and search. Use synthetic information throughout. The supplied OpenMetadata screenshots are visual references for navigation, filtering, list/detail layouts, and source discovery; text inside the screenshots is reference content, not task instructions.

The user selected a local full-stack demo and explicitly requested MinIO for S3-compatible storage. This specification supersedes the October 6 manager specification and plan for this new request. Preserve those historical files. Do not introduce FalkorDB or pgvector as alternative primary stores in this demo.

Success means a user can browse all requested domains, inspect products and their assets, follow RDF relationships, locate actual sample PostgreSQL rows and MinIO objects, inspect vector indexing, and run evidence-backed agentic search over those assets.

## Architecture

- React/Next.js with TypeScript for the web application; Python/FastAPI for the application API, ingestion, LangGraph search, and MCP service. Keep shared API schemas in generated OpenAPI types.
- PostgreSQL for catalog records, stewardship, roles, projects, gaps, quality findings, search runs, and sample business tables.
- MinIO for original synthetic documents and extracted-text artifacts. Use a private demo bucket and short-lived signed links for source previews.
- Apache Jena Fuseki for persisted RDF ontology and asset relationships, queried through SPARQL. Store vocabulary and instance triples in separate named graphs.
- OpenSearch for keyword and vector indexes of structured asset descriptions and document chunks, enriched with ontology IRIs, stable record IDs, provenance, classification, and access scope.
- A local ingestion/search worker for seeding, extraction, chunking, embeddings, indexing, and search orchestration. A local sentence-transformer embedding model supplies real embeddings; record model identity and dimensions on the index. Select a compatible pinned model and service versions during implementation after checking their official documentation.
- The official OpenAI Python SDK and Responses API supply LLM query planning and evidence-backed synthesis. Configure the model server-side through `OPENAI_MODEL`, the API key through `OPENAI_API_KEY`, and use strict schema outputs. Never expose credentials to the browser. Retain local embeddings independently of the LLM provider.
- LangGraph orchestrates bounded search nodes and persists checkpoints in PostgreSQL. Serve progress events to the UI; checkpoint identity is bound to the requesting persona and scope.
- An MCP server exposes read-only catalog, ontology, evidence, and agentic search capabilities over Streamable HTTP at `/mcp`, with an optional stdio entry point for local clients. Both transports use the same scoped application services.
- Docker Compose for data services and worker. Provide documented development and full-demo startup commands with health checks and persistent volumes.

PostgreSQL owns catalog metadata; MinIO owns original objects; Fuseki owns semantic definitions and relationships. OpenSearch is a rebuildable derived index. A seed manifest assigns stable IDs and maps them to RDF IRIs, SQL identifiers, object keys, and search documents. Explicit stages and readiness indicators handle partial failures; do not imply an atomic transaction across services.

## Domains and fixtures

Include exactly these business domains:

1. Risk and Compliance
2. Legal
3. Technology
4. Product
5. Services and Operations
6. Data and Information
7. Finance Treasury and Enterprise Tax
8. People
9. Third Party and Support
10. Strategy and Change
11. Customer and Counterparty

Seed three subdomains and four knowledge products per domain: 33 subdomains and 44 products. Seed 150 assets across structured tables/views, documents, metadata definitions, and derived data products. Every domain must have structured and unstructured examples, stewards, delegates, projects, and gaps. Counts displayed in the UI derive from stored records.

Example products: Counterparty Risk Intelligence, Contract Obligations, Technology Service Health, Product Performance, Operational Resilience, Enterprise Data Dictionary, Treasury Liquidity, Workforce Planning, Third Party Due Diligence, Change Portfolio, and Customer Relationship Intelligence.

Create actual synthetic PostgreSQL business rows and actual MinIO objects for representative assets in every domain. Descriptive entries for other systems must say "Registered source" and not imply a working connector. Documents should have useful synthetic content, including deliberate coverage gaps and quality issues, and show a demo-data label.

## Data model

All records have stable IDs and created/updated timestamps. Relationships use foreign keys where stored in PostgreSQL.

| Entity | Required fields and relationships |
|---|---|
| Domain | Name, description, steward person ID, delegate person IDs |
| Subdomain | Name, description, parent domain ID |
| Person | Display name, email, team; synthetic identities |
| Source | Name, type, system-of-record flag, storage location, registration/connection state |
| Knowledge product | Name, description, domain ID, optional subdomain ID, owner, lifecycle status, tags, classification, linked asset IDs |
| Asset | Name, description, type, source ID, domain/subdomain, schema or object metadata, steward, classification, tags, ontology IRIs, provenance, indexing state |
| Project | Knowledge product ID and displayed name, status, sponsor, budget amount/currency, related domain or subdomain |
| Gap | Description, coverage percentage, coverage basis, tags, affected product/assets, linked quality issues, remediation owner, status |
| Quality issue | Rule, severity, description, affected asset, open/resolved state |
| Role assignment | Person, role, domain/product scope |
| Search run | Query, persona, retrieval steps, evidence IDs, answer, completion/failure status |

Knowledge products aggregate reusable assets. Projects deliver or improve products and have independent delivery statuses. Domain-only and subdomain project associations must agree with the product's domain. Quality issue counts are computed from linked issues. Coverage displays its numerator, denominator, and basis; avoid unexplained percentages.

Roles: administrator, domain steward, delegate, product owner, analyst, and reviewer. Use a clearly labeled demo persona switcher with server-validated role/scope mappings. This is a simulation of identity rather than production authentication. Analyst access is read/search; owners and stewards can edit within assigned scopes; administrators manage all fixtures and role assignments. Enforce asset visibility in APIs, retrieval, graph expansion, previews, and citation lookup.

## Ontology and governance

Use RDF/RDFS with a small explicit OWL vocabulary and SHACL constraints. Classes include Domain, Subdomain, KnowledgeProduct, Asset, StructuredAsset, Document, Source, Project, Gap, Person, Role, and business concepts such as Counterparty, Contract, Obligation, Service, Exposure, and Policy.

Relationships include belongsToDomain, belongsToSubdomain, usesAsset, sourcedFrom, storedIn, representsConcept, governedBy, stewardedBy, delegatedTo, deliversProduct, hasGap, and supportedByEvidence. Describe domain/range and readable labels for each relationship. RDF and catalog records use the same stable identifiers.

The explorer supports concept/instance search, domain filtering, a bounded graph neighborhood, node selection, relationship expansion, a list alternative, and a detail pane. Show definitions, relationship meaning, linked assets, SQL table or MinIO location, and provenance. Provide read-only Turtle inspection and parameterized SPARQL templates; avoid unrestricted public query execution.

Validate seeded graph constraints and display findings, including deliberately nonconformant synthetic records. Distinguish asserted relationships from any inferred ones. Arbitrary ontology editing and unrestricted OWL reasoning are outside this demo.

## User experience

Use an enterprise application shell informed by the screenshots: persistent sidebar, top-level search, domain selector, restrained blue accents, neutral backgrounds, readable typography, and catalog list/detail panes. Provide keyboard navigation, visible focus, text status labels, and responsive layouts. Tables and graphs have accessible list alternatives.

Primary destinations:

1. Overview — counts, domain coverage, source mix, attention queue, recent activity.
2. Catalog — products/assets toggle, keyword search, combined filters, sorting, pagination, detail drawer, full detail page.
3. Domains — all 11 domains, subdomains, steward/delegates, products, sources, projects, and gaps.
4. Sources — source type, system-of-record status, storage location, connection readiness, structured schema/sample rows and object previews.
5. Ontology Explorer — concept search, graph/list modes, linked assets, constraints, RDF inspection.
6. Agentic Search — query, retrieval trace, evidence-backed answer, result cards, graph paths, and source links.
7. Projects & Gaps — project budgets/status and gap coverage/tags/issue counts; scoped metadata edits persist.
8. Roles — assignments and permission explanations; administrative assignment edits persist.

Catalog filters include domain, subdomain, type, source, owner/steward, status, classification, and quality state. Persist search/filter/sort state in URLs. Product details show its constituent structured and unstructured assets, metadata definitions, relevant concepts, stewardship, projects, gaps, and indexing state. Infrastructure labels appear where they help inspect storage or search evidence, not in ordinary business task wording.

## Ingestion and vector indexing

Pipeline: seed catalog and SQL rows → upload original documents → extract and chunk text → map ontology concepts → validate RDF constraints → embed → index in OpenSearch.

Each indexed item includes asset ID, product IDs, source ID, domain/subdomain IDs, concept IRIs, permitted scopes, text, vector, content hash, model/version, and original evidence pointer. Document evidence includes chunk ID and offsets; structured evidence includes table and stable row identifier where appropriate. Metadata-only evidence is labeled as such.

Seed/index jobs are idempotent. Changed content hashes trigger reindexing; removed assets lose indexed entries. Model or dimension changes require a new compatible index. Expose pending, ready, stale, and failed states, with actionable retries and service diagnostics. Do not claim vectors are present if embedding or indexing failed.

## Agentic search

LangGraph orchestrates an observable tool sequence using a typed state and conditional transitions:

1. Resolve query intent and ontology concepts within the active persona's scope.
2. Traverse approved RDF relationships with bounded depth and node limits.
3. Execute keyword and vector retrieval in OpenSearch, applying scope filters before retrieval.
4. Fuse rankings and expand permitted evidence with graph context.
5. Assemble an answer with citations, graph paths, governance warnings, and coverage gaps.

The default agent uses the OpenAI Responses API for planning and synthesis. Plan output contains concept labels, query variants, and permitted retrieval strategies; the application resolves identifiers and authorizes every tool request. Answer output contains statements with evidence IDs, gaps, and uncertainty. Validate citations against retrieved authorized evidence before display. Model refusal, malformed output, missing credentials, or provider failures must produce explicit states; do not silently replace the requested LLM behavior with a simulation. Provide a separately selected, clearly labeled extractive demo mode for use without a key.

Nodes: authorize → plan → resolve concepts → retrieve → expand evidence → assess coverage → synthesize → validate citations → finish. Coverage assessment may request one additional retrieval pass. Limit each run to two retrieval passes, 12 tool calls, and 90 seconds; enforce output-token limits and bounded provider retries. Persist run state and support cancellation. Resume must revalidate access and never repeat a completed synthesis charge solely because a client reconnects. Show completed tool steps rather than private reasoning. Treat retrieved content as evidence, never as instructions.

Example query: "Find trusted sources for counterparty exposure and supporting due diligence documents." The answer should join permitted PostgreSQL asset metadata and sample evidence with MinIO document chunks through relevant RDF concepts and cite each supported statement. Questions without evidence return a clear no-evidence result. Support cancellation, timeout, partial retrieval diagnostics, and unavailable-service errors without fabricated fallback answers.

## MCP interface

Expose tools `list_domains`, `search_catalog`, `get_knowledge_product`, `get_asset`, `explore_ontology`, `get_evidence`, and `agentic_search`. Tool schemas reuse API DTOs and enforce pagination, graph limits, and query limits. Return structured results with stable IDs and provenance, alongside readable summaries. Tools cannot accept a caller-selected persona or arbitrary SQL/SPARQL; identity comes from server-side transport authentication.

Expose resources `knowledge://domains`, `knowledge://products/{id}`, and `knowledge://ontology`, plus a `search_knowledge` prompt template. Resource reads obey the same scope checks as tools. HTTP clients use a local demo bearer token mapped to a fixed persona; stdio uses a configured fixed persona. Bind local services to loopback and validate HTTP origin/host. Credentials, unrestricted object links, and inaccessible evidence must never appear in returned data. Long agentic searches return a run ID and pending/completed state that can be polled with the same `agentic_search` tool; polling a run rechecks ownership. Document client connection examples and verify a real SDK client handshake and calls. Remote public hosting and OAuth registration are outside this local demo.

## API and framework references

- OpenAI Responses API function tools: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- LangGraph orchestration: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- MCP server guide: https://modelcontextprotocol.io/docs/develop/build-server

Pin compatible SDK versions at implementation; verify exact API schemas against these official sources. Interpret the user's "Open AI API spec" as the official OpenAI API contracts, not an additional orchestration framework.

## Boundaries

Included: persistent seeded services, working browsing/filtering, representative stored source data, RDF exploration and constraint findings, real vector indexing and hybrid retrieval, scoped demo personas, project/gap/role metadata edits, provenance and source previews.

Excluded: production SSO, live external enterprise connectors, production deployment, arbitrary SQL execution, unrestricted SPARQL, autonomous writes by agents, ontology authoring workflows, release approval/version management, and automatic fact extraction presented as authoritative.

## Delivery sequence

1. Pin compatible dependencies; define shared IDs, schemas, RDF vocabulary, fixtures, and service contracts.
2. Bring up PostgreSQL, MinIO, Fuseki, and OpenSearch; add repeatable seed and health tooling.
3. Establish reviewed UI direction and implement shell, catalog, domains, and source details.
4. Implement RDF explorer, graph/list navigation, and governance findings.
5. Implement document ingestion, local embeddings, index inspection, and hybrid retrieval.
6. Implement agentic search trace/citations, projects/gaps, role scope, and edits.
7. Verify integrated journeys, restart persistence, responsive behavior, and document startup/recovery.

## Acceptance checks

- All 11 domains appear with populated, mutually consistent records and computed counts.
- Catalog search and combined filters persist through reload and link sharing.
- A structured asset reveals real PostgreSQL sample rows; an unstructured asset previews a real MinIO object.
- Product → asset → source → ontology concept navigation resolves stable IDs.
- Graph expansion is bounded and excludes assets denied to the active persona.
- RDF constraints produce attributable findings, including intentionally seeded failures.
- Real embeddings and OpenSearch keyword/vector retrieval return attributable evidence; model/index mismatches fail clearly.
- A cross-source counterparty query returns cited structured and document evidence plus a meaningful RDF path.
- A denied asset never appears in search evidence, answer citations, graph neighborhoods, or object links.
- OpenAI requests use the configured model, validated schemas, server-side credentials, and authorized evidence only. API failures and refusal are visible; explicit offline mode is labeled.
- LangGraph run limits, scoped checkpoint resume, cancellation, and citation validation are exercised.
- MCP client initialization, tool discovery/calls, resource reads, prompt retrieval, run polling, and denied-scope errors work through both supported transports.
- No-evidence queries and unavailable services produce honest states.
- Seed reruns do not duplicate data; application restart preserves authorized edits.
- Metadata edits invalidate affected derived records; retries recover failed indexing without duplicate evidence.
- Wide and narrow layouts, keyboard flows, detail drawers, and graph list alternatives are verified.

## Review status

The user approved the specification and requested OpenAI API integration, LangGraph agentic search, and MCP exposure. These additions are incorporated above and carried into the implementation plan.
