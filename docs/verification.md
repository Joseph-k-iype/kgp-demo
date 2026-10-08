# Current graph-centered verification (2026-10-08)

This section supersedes the historical fixed-engine notes below. The new engine is an **experimental feature flag**, disabled in release defaults. Passing code/integration/browser tests does not mean that the live answer-quality rollout gates passed.

## Reproducible checks

Run backend/source mutation tests, then browser tests sequentially. The command environment must select the intended API/worker configuration; contract tests use mocked provider boundaries and explicit configuration rather than a developer's private model settings.

```sh
PYTHONPATH=backend uv run --project backend pytest backend/tests -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
npm --prefix frontend audit
uv pip freeze --python backend/.venv/bin/python > /tmp/kpm-requirements.txt
uvx pip-audit -r /tmp/kpm-requirements.txt --disable-pip --no-deps
PYTHONPATH=backend uv run --project backend python scripts/demo_data.py validate
```

The suite covers actual PostgreSQL/MinIO/Fuseki/OpenSearch integration, precise source/version citations, scope revocation and hidden graph intermediates, malformed/unsupported tool arguments, cancellation/deadline/idempotency/lease recovery, no uncertain paid replay, known receipt reuse, exact Decimal aggregation, typed units/dates, injection, content cursors and current-versus-snapshot opening. HTTP and stdio MCP tests use actual SDK initialization/tool/resource/prompt calls. Browser tests cover search generation boundaries, reload/filter behavior, failure/cancellation, all workspace destinations, responsive content-first opening, safe Markdown, React Flow/ELK, domain filtering and selected paths, cyclic/disconnected/empty graphs, focus/Escape and reduced motion.

## Provider and answer quality

The native plan/source/multi-turn and final server-schema probes passed for OpenRouter `deepseek/deepseek-v4.1-flash`, pinned to `Fireworks`, thinking disabled, SDK retries zero, explicit JSON-object output and strict Pydantic validation. Successful development policy runs returned named current policies with actual citations, including the policy-name case in 18.353 seconds/four attempts and TF-POL-002 applicability in 20.257 seconds/five attempts.

First held-out live iteration: twenty cases; one failed run; answerable-case retrieval recall 92.86%, required-fact coverage 60.71%, gold-pattern claim relevance 28.41%, expected outcome 50%. Second disclosed iteration: twenty cases; three failed runs; answerable recall 71.43%, required-fact coverage 57.14%, gold-pattern claim relevance 37.5%, expected outcome 50%. Its missing-evidence, ambiguous and injection cases behaved appropriately, and the treasury governing-policy case returned both current policies with accepted citations. The gold-pattern precision field is a task relevance measure, not an independent factual-precision certificate. Read every per-case error/statement, not only the aggregate. Both iterations remain in [the artifact directory](evaluations/README.md); repeated evaluation is disclosed and is not fresh hold-out certification.

The targets (90% recall, 85% facet coverage, 95% independently supported factual precision and all negative/ambiguous cases correct) are **not met**. No default rollout or claim of error-free AI generation is made. One additional isolated schema diagnostic on recorded synthetic context failed strict response validation; development cross-source diagnostics also succeeded. SDK bodies, keys and private reasoning are excluded. Safe failure categories and known completed usage are preserved for subsequent runs; older failed reports lack known receipt token totals. Historical interim reports record a base commit plus prompt/model/source versions, rather than claiming an exact release-tree SHA for uncommitted patches.

## Scale and data evidence

The isolated scale fixture contained 10,000 RDF entities and 100,000 PostgreSQL rows. The graph returned 49 items/20 paths/12,459 bytes; SQL returned 20 rows/9,540 bytes. Five latency samples and indexed query plans are retained in [the scale report](evaluations/2026-10-08-scale.json). Real PostgreSQL ownership checks covered exclusive claim, expired lease reclaim, rejection of the old owner and cancellation. This is a bounded local operation benchmark, not a production throughput or process-kill certification. Only the temporary database/container were removed.

The published snapshot contains 359 catalog records (including 11 domains/33 subdomains/44 products/150 assets), 880 actual business rows, 40 documents, 126 vocabulary triples and 3,427 instance triples. An isolated database, bucket and Fuseki container restored and re-exported the snapshot with equal catalog, row and object bytes; [restore report](evaluations/2026-10-08-data-restore.json). Its temporary resources were removed. Content ANN schema-v3 was populated with 849 fragments from 150 assets; the prior exact-score content index remains available locally for rollback. Readers reject stale versions.

## Build, audit and publication evidence

Frontend typecheck and production build passed after the graph additions. npm audit reported zero vulnerabilities. The Python environment audit covered 143 installed dependencies and reported zero known vulnerabilities. Working-tree and all 49 pre-publication commits passed credential-pattern scanning; `.env` is ignored and has no tracked history. Final suite counts, review fixes and pushed SHA are recorded at completion below.

---

# Historical fixed-engine verification record

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

## Search-first and FastMCP delivery (8 October 2026)

The redesign replaces the dashboard home with a question field and combines independent AI and catalog responses. Catalog opens without a preselected product, supports URL-persistent grid/list/filter state and progressive product tabs. Real SQL/MinIO preview and stewardship, concepts, coverage and linked project data remain accessible. FastMCP 4 uses actual HTTP and stdio clients; `search_knowledge` shares discovery and permission narrowing with the web API. The terminal run status and final event are published atomically.

The redesigned live DeepSeek request for Aster Capital exposure and due diligence completed with 10 evidence entries, 2 statements and 5 citation links (run `dca14ae0-6135-4923-96ad-004b8f5c3815`). Evidence opened from the UI. An earlier strict-planning response failed validation while ordinary results remained usable; there is no automatic paid replay. These are synthetic records. Discovery uses bounded candidate retrieval and reports returned counts/has-more rather than inventing an exhaustive estate total.

Dependencies: GSAP and @gsap/react own only the home text introduction; Framer Motion owns shared search layout, limited row reveals and dialog fade. Reduced-motion and route-return checks exercise keyboard interaction. Paper WebGL pauses for hidden/offscreen surfaces. Production build/typecheck and npm audit passed; the new full backend run passed 44 tests. Final browser/review results follow below. Screenshots live in `design/search-first/`.

Implementation decisions: the generated catalog export failed, so the library follows the coherent exported home/results shell. Generated detail sidebar/charts/fictional figures were omitted to preserve the approved search-first behavior. Independent UI work progressed while the backend full suite ran against already verified contracts. Session nonces/debouncing prevent duplicate generation; an uncertain request without a saved ID requires explicit retry. Catalog search inherits its visible domain filter rather than adding a second conflicting selector. Closely related catalog/dialog/motion changes share a delivery commit. The home alignment kit had only 34.4% anchor overlap and mapped search inputs to example buttons: unsafe substitutions were rejected; safe typography/nav deltas were applied and native Paper shaders/mark retained. Each visual choice trades exact raster fidelity for working requested behavior.

Motion references: [GSAP matchMedia cleanup](https://gsap.com/docs/v3/GSAP/gsap.matchMedia%28%29/) and [Motion accessibility](https://motion.dev/docs/react-accessibility).

Final review found restored-run cancellation and hidden mobile ontology context; both regressions failed before their fixes and passed in the full 24-test browser suite (3.4 minutes). Service readiness was regraded from Minor because misleading green status impedes recovery; loading/error and per-service states now have a failing-then-passing regression. No Critical or Important review findings remain; no new deferred minors. The shader visibility hook runtime regression also passed its home/motion checks after correction. Four live dependencies report ready. Credential scanning found no OpenRouter token in tracked/non-ignored files.

The results/detail alignment kits completed with 30.2%/28.6% overlap, including semantic controls mapped to text, invented aggregate fields, and incompatible dashboard imagery. Those substitutions were declined; safe typography was retained. Original exported designs and kits are preserved as visual evidence, with no claim of exact fidelity. Desktop screenshots were inspected; 768px/390px routes were checked for overflow. Final focused motion/tab checks and build follow the full suite.

Final focused checks passed 3 tests after tab/stagger refinements (48.2 seconds), followed by another successful production build. All fourteen tablet/mobile route-width checks passed. Work remains on `codex/knowledge-catalog`; local preview is kept running.
