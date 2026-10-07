# Verification record

The local demo uses running PostgreSQL, MinIO, Fuseki and OpenSearch services with actual synthetic data and local sentence-transformer embeddings.

Verified during implementation:

- 11 business domains, 33 subdomains, 44 products, 150 assets; real rows and objects in every domain.
- Repeatable seeds and stored metadata edits.
- RDF graph neighborhoods, scope filtering, concept paths and SHACL findings.
- Real 384-dimensional vector indexing, keyword/vector fusion and attributable evidence.
- LangGraph search, citations, cancellation, changed access scope and completed-run resume.
- OpenAI-compatible provider contracts for OpenRouter/DeepSeek, with runtime schema validation.
- A live OpenRouter DeepSeek V3.2 planning request and full cited search completed. The final UI run returned 10 evidence entries and 6 cited statements in 51.2 seconds; citation buttons opened the scoped evidence dialog (run `ecb110de-1e33-445e-80d3-5c54d249bec0`). No credentials are recorded here.
- MCP HTTP and stdio SDK initialization, tools, resources, prompts and restricted access.
- Desktop and mobile catalog flows, source preview, graph/list navigation, persistent project edits and extractive search.
- Light-only red/rose visual direction, actual Paper Design WebGL shaders with reduced-motion/static fallback.

The production frontend build, type check, and npm audit passed (zero reported vulnerabilities). Final suite and live search results are recorded below. Historical visual references include superseded dark panels; the implementation follows the user's final light-only instruction. The 12ui catalog alignment kit completed after a monorepo source-path correction. A partial eight-screen branch export was retained; the working UI integrates generated references rather than claiming exact pixel fidelity for failed exports.

Local demo identity is intentionally simulated. Public deployment, SSO, OAuth for remote MCP, arbitrary query execution, autonomous writes, and enterprise source connectors are outside this request.

## Review fixes and implementation choices

A fresh review reported no Critical findings and four Important findings. Regressions reproduced and fixed: startup cancellation is terminal, ingestion exceptions mark assets failed, completion cannot bypass the database deadline, and global catalog search/back navigation follows current URL filters. Model timeouts use the remaining search budget and do not automatically retry ambiguous paid requests.

DeepSeek sometimes emitted tokenizer whitespace glyphs in JSON syntax. The server uses OpenRouter response-healing plus narrow decoding outside quoted strings, followed by strict Pydantic validation. Malformed responses show a sanitized error. The API loads its pinned local embedding model before accepting searches; evidence provenance is validated in bounded bulk reads while retaining domain and readiness checks.

The demo uses separate local ports to preserve existing services, flexible JSONB catalog records with validated DTOs and relational domain integrity, and generated visual references adapted to the final light-only direction. Historical exports include incomplete screens and superseded dark panels; exact fidelity to those exports is not claimed.

Deferred minor review observations: interrupted index jobs need a new job/manual reindex rather than automatic lease recovery; seed associations currently exercise within-domain products; exhaustive provider-refusal and interrupted-checkpoint scenarios remain beyond the existing scope, cancellation, resume and malformed-output checks. Identity is explicitly simulated; production SSO and public MCP hosting are outside the local demo.

Final checks: the full backend suite passed 31 tests, and 11 focused provider, bulk provenance, cancellation, deadline and ingestion regressions passed after the final fixes. Production frontend build/type checking passed; npm audit reported zero vulnerabilities. Desktop and mobile screenshots are in `design/red/`; the mobile layout has no horizontal overflow.

Final browser run: all 6 tests passed, including persisted project edits/access restrictions, mobile navigation/dialogs, reload-persistent catalog filters, real SQL previews, ontology navigation, browser back/global search, and cited extractive search. Assertions allow 20 seconds for local-service hydration, and reload persistence waits for URL commit.
