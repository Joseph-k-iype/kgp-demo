# Graph-centered agentic search and content-first results

Status: proposed for user review, 8 October 2026. Research: `docs/research/2026-10-08-graph-centered-agentic-search.md`. Existing implementation: `d8463c4`, worktree branch `codex/knowledge-catalog`.

## User outcome and constraints

The user wants effective dynamic agentic search across structured and unstructured sources, with RDF as the unifying layer. Opening a result must show its actual content first; metadata remains available for context. Success means a useful, source-supported answer, understandable paths between the answer and its sources, and immediate inspection of those sources.

Keep Knowledge Product Manager, the exact existing eleven domains, PostgreSQL, MinIO, RDF/Fuseki, OpenSearch, LangGraph, standalone FastMCP, OpenRouter/DeepSeek through the OpenAI-compatible SDK, and the light-only red/tinted UI. Keep simultaneous AI and ordinary search results, current personas/access checks, explicit paid-generation intent, cancellation, saved-run reconnection and project/gap/role editing.

The proposed budgets, evaluation thresholds and default interactions below are design choices for review, not measurements or previously approved requirements. This planning turn changes documents only.

## Diagnosis and approaches

The recorded treasury-policy query completed in approximately fourteen seconds, retrieved ten entries including People policy briefs, and produced no answer statements. The finance document inspected is a generic evidence brief, not a set of named governing policies. Current coverage tests ask whether any document and any structured evidence exist, concepts resolve by substring, only the first concept is explored one hop, planner strategies are unused, and citations are checked only for valid IDs. The graph currently confuses a Policy class label with an actual governing policy. Asset dialogs require a second Preview action to reach source content.

Three approaches were considered:

1. Improve the fixed RAG prompt/ranker: quick, but leaves graph source routing and adaptive tool choice absent.
2. Graph-centered bounded LangGraph agent: recommended. Curated semantic paths connect business entities to actual source reads; the agent selects tools against explicit answer requirements.
3. Replace the runtime with full Deep Agents/Microsoft GraphRAG: useful harnesses/patterns, but migration cannot repair missing source content, mappings or relevance. Deep Agents adds workspace/context/delegation capabilities; Microsoft global/DRIFT introduces community indexing with a different data model.

Use approach 2 for the initial delivery. Adopt Deep Agents' task planning, concise evidence handles, on-demand context and compaction patterns. Do not install a full filesystem/subagent harness in the initial search path. Evaluate that harness later if long research sessions need delegation; the same scoped tool registry must serve either runtime. Local GraphRAG/entity-text routing and DRIFT-style follow-up discovery inform this design; it does not claim to implement either paper/package unchanged. Dataset-wide qualitative community summaries and unrestricted autonomous source writes are outside this delivery.

## RDF as the unifying evidence layer

Separate vocabulary/classes from real instances. Add stable business entity IDs, aliases, dataset/column mappings, document/section IDs, record mappings, policy/control instances, versions and applicable periods. Use the existing RDF stack; no new graph database.

Authoritative paths must connect sources, for example: Treasury Liquidity product → measures Liquidity Position → governedBy policy TL-POL-001 → supportedBy versioned document section → storedIn MinIO; Liquidity Position → recordedIn dataset → approved PostgreSQL fields/row keys. Cross-domain relationships are allowed only when all participating content is authorized. Generic Policy taxonomy membership must never imply a real governing policy.

Add actual synthetic treasury policies with policy IDs, titles, applicability, effective dates, requirements, source sections and controlled exceptions. Include at least two governing policies and one superseded policy, two-hop SQL/document joins, relevant legal links, distractor People policies, and deliberately missing mappings. Give every domain two meaningful user-answerable scenarios. Preserve stable catalog IDs and edited metadata; fixture upserts update only managed semantic/content fields. Counts may change when new supporting assets are needed; do not preserve a count by fabricating associations.

Store asserted edges with provenance (source asset/version/section or row, assertion origin, validity period). Application-approved fixtures are authoritative; future LLM-extracted candidate edges are separately labeled and cannot be promoted to authoritative facts automatically. SHACL validates domain, target type and provenance. Source/version mismatch makes a mapping stale; inspect/update the source before using it.

Entity resolution combines exact IDs/aliases, lexical matches and semantic candidates. Return up to three candidates per ambiguous mention with reasons grounded in labels/relationships. Route by specific business anchors; generic words such as Policy must not route to People. Inferred domains are soft ranking hints. Explicit domain filters remain hard constraints. Without an explicit filter, a Finance entity may lead to an authorized Legal policy. Material ambiguity requests clarification rather than guessing; unauthorized candidates do not disclose their labels, paths or counts.

Scoped graph queries use server-owned, parameterized RDF templates and whitelisted predicates. Apply authorization at every node, edge and source mapping, including new URI namespaces; a non-catalog URI is not automatically public. Only vocabulary terms are public by explicit allowlist. No unrestricted model-generated SQL/SPARQL.

## Tool and evidence contract

A shared kernel serves the agent, API and FastMCP without the server making loopback HTTP calls to its own MCP endpoint. Identity, scope version, credentials and budgets are injected server context, not model arguments.

Six distinct read tools:

- `resolve_entities`: resolve mentions and scoped business anchors.
- `traverse_graph`: follow typed relations to entities, policies and source handles; return source-backed paths.
- `search_evidence`: lexical/vector/hybrid discovery constrained by graph candidate handles or scoped fallback.
- `read_document`: read relevant sections/neighboring passages of a versioned document.
- `query_dataset`: select/filter/aggregate approved fields using typed operations; parameters compile to application-owned SQL.
- `read_content`: open a document, record, definition or product content manifest with a stable content handle.

Each response has outcome (`ok`, `no_match`, `ambiguous`, `stale`, `unavailable`), items, cursor/has_more, truncation, source/version references and graph paths. Unauthorized IDs produce the existing non-disclosing denial behavior. A tool description states when to use it, when another tool is preferable, parameter bounds and examples. Missing content, failed source and absent graph mapping remain distinct outcomes.

Evidence is a source fragment, not a metadata description. Each fragment has ID, content kind, source asset, content version/hash, domain, text/typed values, locator (section/span/row), units/period, graph path and relevance to named answer requirements. Metadata can establish stewardship or location, but cannot prove a liquidity amount or a policy clause. Store full material outside model context; pass concise snippets and handles, fetching details as needed. Index actual full managed documents independently of the bounded UI preview; expose truncation instead of silently treating a prefix as the whole source.

OpenSearch remains the candidate engine. Fuse keyword/vector ranks with graph-path specificity, explicit applicability/time constraints and query-focused relevance assessment. No forced source-type quota may insert an irrelevant document. Deduplicate overlapping passages and distinguish authoritative source content from descriptions. A graph miss permits authorized content discovery, but the answer explicitly distinguishes textual support from a missing governance path.

## Adaptive agent and prompts

Persist a versioned research state: interpreted question, candidate entities, required answer facets, task plan, selected tools, evidence handles, coverage, contradictory evidence, graph paths, counters and stop reason. LangGraph executes authorize → interpret/resolve → decide → validated tool batch → relevance/coverage → decide, then synthesize → verify → finish. Several valid tool sequences are possible.

Initial intent identifies required facets such as policy names, applicability, effective dates and governing relationship. Each decision chooses read actions for uncovered facets using current observations. A structured result explains the missing requirement and next action in short public operational terms; do not request or display private chain-of-thought. A second query is generated from an observed gap, not a second preset string used only when a document type is missing. Cache normalized read actions by scope/version/source version within the run; repeated actions with no new evidence force a different action or stop.

Dynamic prompts have a stable role/source-trust block plus only the current intent, authorized semantic neighborhood, available tool schemas, coverage ledger, concise observations and remaining budget. Few-shot examples cover treasury policy routing, cross-source joins, unrelated-policy rejection, ambiguity and justified abstention. Phase-specific prompts separate interpretation, tool decision, relevance, synthesis and claim verification. Documents/rows are untrusted data, never instructions. Preserve structured schema validation; unknown tools/invalid args are not executed.

Provider gate: probe the exact configured OpenRouter model/provider/SDK for native tools, multi-turn tool IDs, errors, structured outputs and cancellation. Disable thinking initially as today; do not switch reasoning modes silently. If native tools are incompatible, use a strict JSON action-decision envelope executed by the same registry, expose the selected adapter and test it equivalently. This is still dynamic tool selection, not returning to preset retrieval. No automatic paid retry after an ambiguous request outcome. One validated argument-repair decision is permitted within the normal model-call budget when the server knows no tool ran.

Initial intent/task planning shares the first decision call. Coverage and relevance judgments are included in decision responses, not additional uncounted model calls. Deterministic source checks do not consume a model call.

Default proposed bounds: 120 seconds per new run, sixteen source-tool invocations, four model decision calls plus one synthesis and one verification call; maximum two concurrent independent read tools; graph depth three with fifty nodes/one hundred edges per run, twenty paths; forty candidates per retrieval; twenty selected fragments; ten-thousand-token estimated evidence packing target with actual provider usage recorded. These are search bounds, not guaranteed monetary billing caps. Reserve twenty seconds for synthesis/verification; if insufficient, return supported partial content or explicitly labeled source excerpts. Old runs preserve their stored original deadline; do not extend them on resume. Cancellation/scope-change guards run before/after every model/tool call, and final publication remains atomic.

Stop when all necessary facets have supported evidence, ambiguity prevents useful progress, no new evidence is obtained after two consecutive decision/tool rounds, sources are unavailable, or budget expires. Return an explicit answer outcome (`answered`, `partial`, `no_evidence`, `needs_clarification`) independently of run lifecycle. Incomplete coverage must not be called a successful complete answer simply because transport finished.

## Claim support and quality

Require versioned evidence IDs plus exact supporting spans/row fields for each claim. Verify permissions and freshness again at publication and source opening. Check numeric/date/unit comparisons with deterministic operations; aggregations cite the operation, source selection and returned row-set provenance. Check textual support/contradictions using a separate verifier with constrained outputs, but treat its judgment as fallible. Unsupported claims are removed or trigger a targeted remaining-budget retrieval; at most one synthesis revision, charged against the existing synthesis/verification budget allocation (replace a remaining decision call if needed, never exceed six model calls). A policy applicability statement needs both the clause and an asserted, applicable path; a taxonomy label is insufficient.

No-answer/partial answers state exactly which facts or governing links are absent. Do not expose unauthorized source identities. Conflicting current sources are shown with citations rather than silently selecting one. Model-generated confidence is not a calibrated truth score.

## Content-first user experience

Keep the existing search-first home and AI/results together. Improve result rows with an actual excerpt/row sample, a specific title, content type and a compact relationship hint (e.g. Governs Treasury Liquidity); steward/location/index information remains secondary. Show operational progress and concrete uncovered requirements, not an indistinct spinner.

On opening:

- Document: display the original readable document/section immediately, highlight the matching or cited passage, offer full document/neighboring sections, with version and source location in context.
- Data/table: display actual rows or the matched record immediately, with visible fields, units, period, filtering and truthful pagination. Approved aggregates show result values and underlying selection; do not display metadata as the result.
- Definition/metadata asset: display its real RDF assertions/business definition as content, labeled Definition, rather than pretending it is a SQL dataset.
- Knowledge product: default to Content containing a manifest of actual linked datasets/documents/definitions, select the query-relevant source when known or the deterministic configured primary source. Choose among sources without stacking modal dialogs. Do not invent a blended dataset or generate a new paid answer on opening.
- Citation: open the same content viewer at the exact supported passage/row, not a separate metadata-first view. If a source changed, label the cited snapshot and current version explicitly; recheck access before displaying either.

Use a single accessible detail surface: content primary, collapsible Context (domain, steward, delegates, source, quality, projects, tags), and Relationships showing the small answer/source path with clickable nodes. Desktop can use a resizable contextual column; mobile defaults to Content and retains Context/Relationships disclosures. No new dashboard or graph wall. Preserve focus, Escape, reduced-motion behavior and light red/subtle tint. Invoke the required UI design workflow during implementation for search/result-viewer states; keep actual source rendering authoritative if generated references invent data.

## Evaluation and delivery gate

Create sixty labeled tasks: twenty-two (two per domain), ten treasury, eight risk, eight cross-source/domain, six unanswerable, four ambiguous, two source-injection. Split forty development and twenty held-out tasks before prompt tuning; held-out contains fourteen answerable, three unanswerable, two ambiguous, one injection. Gold facts reference real row fields, document spans and RDF edges, not just expected prose.

Compare the original fixed retrieval, graph-assisted fixed retrieval and adaptive agent on the same enriched corpus; report data-only improvements separately. Proposed held-out targets: >=90% gold-fragment recall, >=95% supported factual-claim precision and >=85% required-facet coverage across answerable tasks; all deterministic amounts/units/dates exact; all unanswerable/ambiguous/injection cases handled appropriately; zero access leaks and zero nonexistent governing edges accepted. Document denominators and individual failures, not only aggregate scores. A small demo benchmark is not production-quality certification. Human-review textual entailment labels and disputed model judgments.

Run offline provider-boundary tests in CI; execute the twenty-case live provider evaluation explicitly as a bounded batch, log calls/usage/latency/errors and do not replay failed requests automatically. Latency goal p95 <=60 seconds for held-out answerable tasks, with the hard120s budget honored; report misses honestly. Regression gates include reload/cancel/deadline, domain/persona changes, stale content, missing mappings, tool injection, bounded aggregation, content-first source opening, mobile relationship access and no duplicate paid runs.

Roll out behind server-owned `graph_search_v2` configuration; record run engine/prompt/graph/content versions. Keep the previous retrieval for measured comparison/rollback, not a hidden answer fallback. Switch the default only after the new quality and lifecycle gates pass. Regenerate OpenAPI/client types; add FastMCP tools using the shared kernel and preserve existing tool names. Finish with backend suite, actual HTTP/stdio clients, provider compatibility/evaluation, frontend build/typecheck, browser tests and visual verification.
