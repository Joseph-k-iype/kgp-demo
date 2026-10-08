# Graph-centered Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver adaptive graph-centered evidence search and content-first result inspection, proving relevance and factual support rather than only infrastructure success.

**Architecture:** RDF is the authoritative semantic source router. A bounded LangGraph decision loop uses shared read tools to follow relationships, retrieve real SQL/document content, assess required-facet coverage and validate claims. API/FastMCP/UI reuse source/content handles and scoped services.

**Tech Stack:** Existing Python/FastAPI/LangGraph/FastMCP, OpenRouter DeepSeek/OpenAI-compatible SDK, RDFLib/SHACL/Fuseki, PostgreSQL, MinIO, OpenSearch, Next/React, GSAP/Framer Motion/Paper.

**Spec:** `docs/superpowers/specs/2026-10-08-graph-centered-search-design.md` (proposed; user review precedes implementation).
**Research:** `docs/research/2026-10-08-graph-centered-agentic-search.md`.
**Execution:** Recommend native execution with one final fresh review; preserve the linked worktree. No product changes, dependency installation or paid model probes occurred while writing this plan.

## Global Constraints

- Keep Knowledge Product Manager, exact existing eleven domains, local PostgreSQL/MinIO/Fuseki/OpenSearch stack, LangGraph, standalone FastMCP, configured OpenRouter/DeepSeek, light-only red/tinted UI.
- Actual content first, metadata/context retained; simultaneous AI/results; opening or paging content never creates a paid answer.
- Identity, access version, source credentials and budgets are server-owned; all graph/source/evidence reads reauthorize, including new business-node namespaces.
- Inferred domain is a soft hint; explicit domain is a hard bound. Graph paths cannot reveal unauthorized labels, source IDs or counts.
- No unrestricted SQL/SPARQL, file shell, autonomous writes, public deployment or implicit model/provider switch.
- New run defaults:120 seconds, sixteen source-tool invocations, four decision calls (including initial interpretation and coverage/relevance judgments) plus synthesis/verification within six model calls total, maximum two independent concurrent read tools. Old runs keep their stored deadline.
- Graph bounds:depth3, fifty nodes/one hundred edges per run, twenty paths; forty retrieval candidates, twenty selected fragments; evidence packing target ten thousand estimated tokens.
- Stop after two consecutive decision/tool rounds with no new evidence; reserve twenty seconds for synthesis/verification. No blind paid retry on an uncertain request outcome.
- Version/hash all new source fragments and edge assertions; metadata cannot substantiate source-content claims. Exact numbers/dates/units need deterministic checks.
- Sixty labeled tasks split40development/20held-out before tuning; held-out14answerable/3unanswerable/2ambiguous/1injection.
- Held-out targets:>=90% gold-fragment recall, >=95% supported factual-claim precision, >=85% facet coverage for answerable cases; exact deterministic calculations; appropriate handling of all no-answer/ambiguous/injection tasks; zero access leaks and nonexistent accepted governing edges. Report misses, denominators and p95 latency (goal<=60s, hard120s).

## Review Focus

1. Same policy label in Finance/People, ambiguous entity or authorized Legal relationship: route by business intent, preserve explicit filter, never invent governance. Tasks1–4.
2. A row/entity/section has a new URI namespace or a hidden path intermediate: enforce graph ACLs and source ACLs without revealing IDs/counts. Tasks2/3/6.
3. Valid evidence ID with unsupported text, superseded/conflicting policy or wrong unit/period: fail support validation, retrieve better evidence or return partial. Tasks3/5.
4. Model/tool times out, scope changes, cancellation/reload occurs during parallel reads or source freshness changes: stop safely, publish atomically and do not replay paid requests. Tasks4/6/8.
5. User opens a product/table/document/citation on mobile or with keyboard/reduced motion: see actual content promptly and retain context/relationship access without duplicate generation. Tasks6–8.

## Shared interfaces and file responsibilities

Create `backend/app/knowledge/{contracts,graph,tools,content}.py` for semantic/content services; `backend/app/agent/{actions,coverage,prompts,verification}.py` for agent decisions and support checks; `backend/evals/{cases,runner,metrics}.py` and JSONL manifests for evaluation. Keep provider/run ownership in existing modules. Reuse existing storage/catalog functions but split full ingestion from UI preview. Create frontend `components/content/{ContentViewer,DocumentView,DatasetView,ProductView,ContextPanel,RelationshipPath}.tsx`; existing detail components become wrappers for that shared viewer. Interface types below live in knowledge/contracts.py and are generated into frontend clients when exposed.

## Task 1: Evidence-rich corpus, semantic assertions and gold evaluation

**Files:** Create `backend/app/knowledge/contracts.py`; modify `backend/app/{fixtures,seed}.py`, `backend/app/ontology/{service.py,shapes.ttl}`; create `backend/fixtures/semantic/manifest.json`, richer managed document fixtures, `backend/evals/{cases,metrics}.py`, `backend/evals/cases/{development,heldout}.jsonl`; tests `backend/tests/integration/test_semantic_corpus.py`, `backend/tests/test_eval_metrics.py`.
**Interfaces:** Produce `SourceRef(asset_id,version,locator,domain_id)` and `GraphAssertion(subject,predicate,object,source_ref,valid_from,valid_to,origin)` in knowledge/contracts.py; `load_semantic_manifest() -> list[GraphAssertion]`; `score_run(run:dict,gold:GoldCase) -> CaseMetrics` with retrieval recall, facet coverage, support precision and outcome validity. GoldCase specifies query/persona/filter, required facts, acceptable source refs/paths and outcome; human-reviewed textual labels are explicit.

- [ ] Write RED tests for named treasury policy instances with real clause spans, active/superseded dates, SQL/document two-hop mappings, unrelated People distractors, no false `Asset governedBy PolicyClass`, and seed reruns preserving edited metadata.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_semantic_corpus.py backend/tests/test_eval_metrics.py -q`; expect missing semantic manifest/contracts and failing source/path assertions.
- [ ] Implement the manifest, fixtures and SHACL mapping/version requirements; populate real managed objects/rows and stable business entities. Add two answerable scenarios per domain; do not use fictional metadata descriptions as factual gold evidence.
- [ ] Write all60cases and fixed40/20split; test metrics reject correct IDs with unsupported facts and do not grade by one mandatory tool sequence. Keep held-out labels out of prompts.
- [ ] Run the above command; expect all cases of fixture/metric validation PASS. Record original enriched-corpus baseline without model calls in the default test command; live evaluation is an explicit task8 action.
- [ ] Commit `feat: add source-backed semantic corpus and search gold cases`.

## Task 2: Scoped graph resolution and typed source-tool kernel

**Files:** Create knowledge/graph.py, tools.py; modify ontology/service.py and knowledge/contracts.py, storage/structured.py; tests `backend/tests/integration/test_graph_routing.py`, `test_knowledge_tools.py`.
**Interfaces:** `resolve_entities(ctx:ToolContext, query:str) -> EntityResolution`; `traverse_graph(ctx, roots:list[str], predicates:list[str], target_kinds:list[str], depth:int=3) -> ToolResult`; `execute_read(ctx, call:ReadAction) -> ToolResult`. ToolContext contains ScopeContext, deadline and remaining limits. ReadAction is a discriminated union for the six named spec tools; ToolResult includes outcome/items/cursor/has_more/truncated/source_refs/paths. DatasetQuery contains registered asset_id, approved select fields, typed filters and optional aggregate, never raw SQL.

- [ ] RED tests: Treasury aliases resolve Finance ahead of People; return multiple ambiguous candidates; Finance→authorized Legal works without an explicit filter; explicit Finance excludes Legal; hidden intermediate/new-namespace node leaks no label/count/path; malformed predicate/field/raw query rejected; aggregate units/date predicates exact.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_graph_routing.py backend/tests/integration/test_knowledge_tools.py -q`; expect missing kernel and failing resolution/ACL assertions.
- [ ] Implement parameterized graph templates, source handle registry, bounded typed dataset operations and distinct tool outcomes. Register resolve_entities/traverse_graph/read_document/query_dataset now; task3 adds search_evidence and task6 adds read_content. Advertise only implemented tools; schemas alone never stand in for a working reader. Guard before/after every read, parameterize values and map approved fields in application code; do not interpolate model-selected SQL identifiers.
- [ ] Run the same tests; expect PASS including bounds and all authorization cases. Commit `feat: route scoped knowledge tools through RDF paths`.

## Task 3: Versioned content ingestion and query-focused retrieval

**Files:** Modify retrieval/{extract,service,index}.py, storage/objects.py; create agent/coverage.py; extend knowledge/contracts.py; tests `test_content_retrieval.py`, `test_answer_coverage.py`.
**Interfaces:** `EvidenceFragment` carries source ref, content kind/text or typed values, units/period, path and matched facet IDs. `search_evidence(ctx, query:str, asset_ids:list[str]|None, kinds:list[str], strategy:Literal['keyword','vector','hybrid']) -> ToolResult`; `assess_coverage(intent:SearchIntentV2,evidence:list[EvidenceFragment]) -> CoverageReport`. CoverageReport has supported/uncovered facets, irrelevant handles, conflicts and suggested source needs, not mere source-type counts.

- [ ] RED tests: original treasury query retains applicable Finance policy clauses and excludes People distractors; pure SQL query doesn't require a document; policy query doesn't require rows; overlapping spans deduplicate; a relevant late section beyond UI preview is indexed; changed object version invalidates old mappings; lexical/vector/graph-assisted variants produce distinguishable execution.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_content_retrieval.py backend/tests/test_answer_coverage.py -q`; expect wrong-source/coverage behavior and missing version fields.
- [ ] Implement versioned section/row evidence, full managed object ingestion, scoped graph candidates, hybrid fusion with applicability/path weighting and relevance decisions. Use deterministic applicability constraints plus model relevance at task4's boundary; remove forced irrelevant source-type quotas. Keep no-match/unavailable/stale outcomes distinct.
- [ ] Same tests PASS; compare original retrieval on the enriched corpus to graph-assisted fixed retrieval, recording gold-fragment metrics. Commit `feat: retrieve relevant versioned source content`.

## Task 4: Dynamic decisions, prompts and bounded run lifecycle

**Files:** Create agent/{actions,prompts}.py; modify agent/{graph,state,service,provider}.py, config.py, contracts.py; tests `test_adaptive_agent.py`, `test_agent_lifecycle_v2.py`, provider boundary tests.
**Interfaces:** `decide_next(state:ResearchState, deadline:float) -> ActionDecision`; ActionDecision contains read_calls, required_facet_ids, stop_action and brief operational summary; `ResearchState` contains spec ledger/versions/counters; `choose_adapter(capabilities:ProviderCapabilities) -> Literal['native_tools','json_actions']`. Lifecycle status remains compatible; add answer_outcome and stored engine_version/deadline/usage/stop_reason. Both adapters invoke execute_read from task2.

- [ ] RED scripted-provider tests: irrelevant document leaves policy facet uncovered and selects a governing path/document read; unrelated first variant triggers an observed-gap action; SQL→document join uses returned entity handles; multiple concept roots explored; repeated actions stop; material ambiguity returns needs_clarification. Assert correct facts/limits, not one universal sequence.
- [ ] RED lifecycle/provider tests: unknown tool and argument injection never execute; exact adapter preserves tool IDs/results; model timeout creates no hidden paid replay; six-call/sixteen-tool/depth/node/deadline limits enforced; parallel scope change/cancel cannot publish; old90srun deadline is unchanged; same browser intent still starts once.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/test_adaptive_agent.py backend/tests/integration/test_agent_lifecycle_v2.py -q`, then `env PYTHONPATH=backend uv run --project backend pytest backend/tests -k provider -q`; expect missing action loop/contracts and lifecycle failures.
- [ ] Implement versioned phase prompts, structured action validation, native-tools and strict JSON-actions adapters, dynamic coverage loop, run-local scoped/versioned read cache and small parallel read batch. Keep no private reasoning in events. Reserve finalization budget; calculate deadline once and reuse in guards/transitions/resume.
- [ ] Run each named suite unfiltered; expect PASS. Provider compatibility live probe is task8, not implicit in CI. Commit `feat: adapt graph search actions to evidence gaps`.

## Task 5: Claim support, contradictions and honest answer outcomes

**Files:** Create agent/verification.py; modify provider.py/graph.py/contracts.py; tests `test_claim_support.py`, integration/test_adaptive_agent_quality.py; eval runner.py.
**Interfaces:** `verify_claims(ctx, claims:list[SupportedClaim], evidence:list[EvidenceFragment]) -> VerificationReport`; SupportedClaim has text, cited SourceRefs and exact supporting locators/fields; report distinguishes supported/unsupported/conflicting/stale and uncovered facets. `evaluate_engine(engine:Literal['legacy','graph_fixed','adaptive'], cases:list[GoldCase], provider_mode:Literal['offline','live']) -> EvaluationReport` records denominators/call usage/errors/latency.

- [ ] RED tests: correct ID/wrong clause rejected; PolicyClass path cannot prove applicability; superseded source/date/unit mismatch rejected; deterministic aggregation exact; conflicting current policies cited as conflict; removed-access evidence rejected at publication; insufficient remaining budget returns partial/source-only without fabricated conclusion.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/test_claim_support.py backend/tests/integration/test_adaptive_agent_quality.py -q`; expect current ID-only validation failures.
- [ ] Implement deterministic source/span/numeric checks plus fallible structured textual support verification. Remove unsupported claims or use a remaining-budget corrective action; revision never exceeds six model calls. Return answered/partial/no_evidence/needs_clarification with clear gaps and contradictions.
- [ ] Same tests PASS; run40development cases offline and inspect individual failures. Commit `feat: verify factual support and question coverage`.

## Task 6: Unified actual-content API and FastMCP tools

**Files:** Create knowledge/content.py; modify main.py/mcp/server.py/contracts.py/catalog/service.py/storage readers; regenerate frontend/src/api/generated.ts; tests integration/test_content_api.py/test_mcp.py.
**Interfaces:** `open_content(ctx, handle:ContentHandle, cursor:str|None=None) -> ContentPage`; ContentHandle discriminates asset/record/document-section/definition/product and version/locator. ContentPage has actual content, source refs, graph paths, separate context, cursor/has_more/truncated/freshness. Add GET `/content/{kind}/{id}` and GET `/products/{id}/content`; API validates kind/query bounds. ProductContentManifest lists real linked content handles with configured primary handle; query-matched evidence can choose a permitted handle, never arbitrary source location.

- [ ] RED tests for direct document/row/definition/product content, matching locator, real pagination/truncation, stale cited snapshot/current-source labeling, reauthorized snapshots, inaccessible nested source, unsupported content type, changed persona and canceled fetch. Opening content must not create a search run.
- [ ] RED actual HTTP/stdio clients call the six task2 tools against the shared kernel; legacy names still work; identity cannot be passed as model arguments; malformed dataset/graph operations denied.
- [ ] Run `env PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_content_api.py backend/tests/integration/test_mcp.py -q`; expect missing content-first API/tool schemas.
- [ ] Implement ContentPage/manifests and truthful limited readers, register FastMCP wrappers with read-only annotations, preserve existing search/poll tools. Regenerate OpenAPI client types. Same tests PASS. Commit `feat: expose actual knowledge content through API and MCP`.

## Task 7: Content-first result and citation experience

**Files:** Create components/content/{ContentViewer,DocumentView,DatasetView,ProductView,ContextPanel,RelationshipPath}.tsx; modify AssetDetail.tsx, discovery/{DiscoveryDetail,ResultList,AnswerPanel}.tsx, search/page.tsx, discovery.css and API hooks; tests e2e/content-viewer.spec.ts and existing browser suites.
**Interfaces:** `ContentViewer({handle:ContentHandle, onClose, queryContext?})` uses task6 generated ContentPage; ResultList uses actual snippets and source handles; citations use the same locator-aware viewer. Context/Relationships remain available at390px; one dialog surface owns focus/scroll/close behavior.

- [ ] RED browser assertions: clicking document immediately shows its actual matching passage; clicking table shows actual relevant rows; definition shows RDF facts; product chooses real primary/query-relevant content; no Preview second action; citations highlight exact source; no modal nesting; context/relationships remain reachable on mobile; loading/source failure distinguish unavailable from absent; rapid query/persona changes discard stale content; zero extra generation POSTs.
- [ ] Run `npm --prefix frontend run test:e2e -- content-viewer.spec.ts`; expect old metadata-first details to fail.
- [ ] Use mandatory12ui design workflow on the content-first search/viewer states at implementation time. Preserve light red/subtle tint and current search shell, readable source formatting, field units/time and visible truncation. Keep generated factual copy non-authoritative. Reuse Motion/GSAP ownership and reduced-motion preferences; read bundled Next docs per AGENTS before code.
- [ ] Implement viewer/source switching/context/path components and progressively adapt wrappers; prevent unsafe HTML rendering. Run named browser suite/typecheck; expect PASS. Inspect1440/768/390screens, focus/Escape and source overflow. Commit `feat: open knowledge results directly to source content`.

## Task 8: Provider certification, held-out quality and rollout

**Files:** backend/evals/runner.py, scripts/evaluate_search.py, tests/integration lifecycle/ACL suites, e2e current search/catalog tests; README, docs/verification.md, docs/mcp.md; versioned evaluation artifacts under docs/evaluations/.
**Interfaces:** CLI `uv run --project backend python scripts/evaluate_search.py --engine adaptive --split heldout --provider live --max-runs 20`; default provider offline; compatibility mode `--probe-provider` is a separately bounded explicit action. Store actual model/provider/framework/prompt/graph versions, calls/tokens/errors; never credentials/private reasoning.

- [ ] Add remaining RED regressions for final behavior discovered during implementation: replay/cancel during tool reads, unsupported parameters, malformed tool args, source edits after citations, strict persona filter and withheld-source absence. Run each failure before its fix.
- [ ] Pin/probe the exact configured DeepSeek/OpenRouter route and SDK with one-tool/multi-turn/final-schema/error/cancel cases; record adapter and whether thinking is disabled. Stop and expose incompatibility rather than changing providers silently. Native-tool failure may select tested JSON-actions adapter explicitly; no automatic ambiguous paid retry.
- [ ] Run40development offline cases, then explicit20held-out live batch on the same enriched corpus used for legacy/graph-fixed comparison. Report failures, gold recall/facet support, deterministic accuracy, ACLs, p50/p95, requests/usage and hard-budget adherence. Tune only development cases; any additional held-out iteration is a new disclosed evaluation run, not hidden retesting until success.
- [ ] Execute backend suite then actual frontend browser suite sequentially to avoid shared indexing collisions; typecheck/build/audit and actual FastMCP HTTP/stdio included. Commands: `env PYTHONPATH=backend uv run --project backend pytest backend/tests -q`; `npm --prefix frontend run typecheck`; `npm --prefix frontend run build`; `npm --prefix frontend run test:e2e`; `npm --prefix frontend audit`. Expect all PASS/zero applicable audit vulnerabilities and no credential exposure.
- [ ] Review with one fresh reviewer for native execution. Fix material findings with RED→GREEN and appropriate full-suite checks; do not claim model judges prove correctness. Switch `graph_search_v2` default only when stated gates pass; otherwise preserve proposed config and report unmet gates rather than calling delivery complete.
- [ ] Document concrete treasury example (named active policies, sections and two-hop paths), real content opening, missing evidence/ambiguity behavior and measured limitations. Commit `feat: verify graph-centered search quality and content delivery`; keep local preview/worktree.

## Self-review

Coverage: source graph/corpus→1/2; retrieval→3; dynamic prompting/provider/lifecycle→4; factual support/outcomes→5; actual content/API/MCP→6; user inspection→7; held-out quality/rollout→8. All five Review Focus cases have named task tests. New interfaces have explicit producers/consumers; generated frontend types come from task6. The plan permits multiple valid tool sequences and preserves source access, deadlines and no-paid-replay rules. Full Deep Agents adoption, global community summaries and public deployment are explicitly excluded from this initial fix; research is retained for a later measured decision.

## Scale additions approved through user steering

These requirements apply to the current eight tasks, not a later optional hardening phase:

- **Task2:** server-side bounded Fuseki SELECT/frontier templates and batch SQL ACL checks; no full CONSTRUCT/all_records in resolution/traversal. Add tests that assert bounded candidate/frontier/response shapes with unrelated nodes and hidden intermediates. Use indexed entity lookup and row predicates/aggregation in SQL, cursor paging by `(asset_id,id)`; add Alembic migration under `backend/alembic/versions/` for necessary indexes after inspecting existing convention. ToolContext carries configurable response-byte limits; reject oversized tool output explicitly.
- **Task3:** streamed/full-source ingestion in fixed batches, incremental graph/index projection jobs and versioned OpenSearch aliases; cache keys contain scope/domain/graph/source versions. Add bounded batch/freshness/cache isolation tests. Full rebuild remains an explicit maintenance operation.
- **Task4:** add `backend/app/agent/worker.py` and persisted claim/lease fields with atomic SQL ownership/heartbeat. Replace process-local search ownership with durable queued execution while retaining a convenient local worker. Add optional SearchRequest intent_id and unique server-owned persona/intent idempotency key; legacy requests still work. Default per-persona active-search cap2 and global queued-search cap100 are configurable/shared in SQL; test overload and multi-worker dispatch. Uncertain paid-call checkpoints never automatically replay after lease recovery.
- **Task6/7:** use cursor/byte-limited content reads and abortable UI fetches; never materialize all rows/full blobs merely to open a result. Distinguish queue/loading/truncation/source errors and keep available content responsive.
- **Task8:** create opt-in `scripts/benchmark_search_scale.py` with an isolated benchmark graph/database namespace, 10,000 entities/100,000 rows and documented cleanup for only resources it created. Record environment, indexed query plans, bounded counts/bytes, latency and two-worker recovery/cancellation behavior. Do not infer production throughput. Document API/worker/source-service deployment boundaries and tunable pools/budgets. Local demo remains the deliverable.

## Approved UI steering (result rendering / ontology)

Use React Flow with elkjs for ontology interactions and asynchronous layout. Include search/focus, domain/type/relation filters, fit/zoom/minimap, neighborhood/evidence-path highlighting, source-content opening, keyboard access and list fallback; test empty/cyclic/disconnected graphs and stale/failing layout responses. Evaluate Blume across official docs/subpages for Markdown compatibility; keep permission-scoped runtime content and native citations. Integration findings: `docs/research/2026-10-08-result-rendering-and-graph.md`. Apply during Task7 and include in final UI/backend verification; do not replace Next.js solely for Blume Astro site generation.

## Approved answer presentation steering

AI results must directly answer the question as coherent, well-formed content. Use a concise leading answer and neutral sections when helpful, with readable source titles/locators attached to the specific verified claims. Do not render an arbitrary reference list as the answer. For treasury, show named current governing policies, requirements and source-backed applicability. Remove unsupported/unrelated claims before rendering; section structure may reference only accepted statement indices. Clicking a source opens the exact supporting passage/row, with metadata separate. Preserve ordinary results and honest missing/conflicting evidence states.
