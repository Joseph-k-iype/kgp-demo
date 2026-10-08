# Graph-centered agentic search: research and recommendations

Researched 2026-10-08 against primary sources. This is an architectural recommendation, not a provider compatibility certification. No paid model calls, dependency changes, or credential reads were performed.

## Recommendation

Start with a bounded LangGraph evidence-gathering loop and a small set of scoped FastMCP tools. Make RDF the semantic source router: resolve concepts/entities, follow meaningful relations, identify relevant source handles, then retrieve actual PostgreSQL rows and MinIO document passages. Use OpenSearch for candidate discovery and ranking. Adopt Deep Agents only if measured workloads need its long-running context harness; adding a harness does not fix entity resolution, stale mappings, edge semantics, provenance, or authorization.

This recommendation combines established patterns rather than claiming a single paper validates the complete architecture. Anthropic describes just-in-time context using lightweight identifiers and on-demand loading, with a hybrid initial retrieval plus autonomous exploration approach; exploration can increase latency and requires suitable tools and heuristics. [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

## What the evidence supports

**Dynamic discovery and context are supported without adopting the full harness.** LangChain documents filtering tools using state and runtime permissions, and middleware that changes messages, prompts, tools, or model calls. Its tool runtime separates mutable state from invocation context, and injected runtime arguments are hidden from model tool schemas. These facilities support server-owned identity and budget context plus an agent-selected next action. They do not themselves enforce data-layer ACLs. [Context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering), [Tools](https://docs.langchain.com/oss/python/langchain/tools).

**Deep Agents supplies useful infrastructure.** It bundles filesystem context management, summarization/offloading, isolated subagents, memory, MCP tools, and optional planning/skills. That makes it attractive for extensive research sessions with large intermediate results. It also introduces capabilities and policies unnecessary for a short read-only search: file access, memory lifecycle, delegation, and potentially execution. The current docs contain version-qualified capabilities; pin and inspect the actual package before copying examples. [Overview](https://docs.langchain.com/oss/python/deepagents/overview), [Profiles](https://docs.langchain.com/oss/python/deepagents/profiles).

| Approach | Benefit | Tradeoff and decision |
|---|---|---|
| Custom LangGraph loop | Explicit scope, evidence state, budgets, stopping rules, and final validation | Build context compaction and retries deliberately; recommended first |
| Full Deep Agents | Context offloading and isolated delegation already available | More harness configuration and capability surface; evaluate later on long research tasks |
| Microsoft GraphRAG package | Established local/global/DRIFT search over its indexed artifacts | Different indexing/data model from an enterprise RDF source router; borrow patterns before replacing the existing stack |

**GraphRAG modes answer different questions.** Local search joins entity/relationship context with document text units and is intended for entity-specific questions. Global search uses precomputed community reports and map-reduce for dataset-wide themes. DRIFT begins with relevant community reports, generates follow-up questions, and uses local search to refine them. These are not synonymous with arbitrary RDF traversal or exact SQL aggregation. [Local](https://microsoft.github.io/graphrag/query/local_search/), [Global](https://microsoft.github.io/graphrag/query/global_search/), [DRIFT](https://microsoft.github.io/graphrag/query/drift_search/).

**Adaptive retrieval has research precedent, with important limits.** ReAct interleaves reasoning and actions so observations can update plans. Self-RAG trains reflection tokens for deciding whether to retrieve and evaluating passages/generation; a prompt-only critique loop on hosted DeepSeek is an adaptation, not the paper's trained method. CRAG evaluates retrieval quality to select corrective actions, including web retrieval in its experiments. For private enterprise questions, correction should stay inside authorized sources unless external search is explicitly appropriate. These papers motivate feedback loops; they do not guarantee correctness on this catalog. [ReAct](https://arxiv.org/abs/2210.03629), [Self-RAG](https://arxiv.org/abs/2310.11511), [CRAG](https://arxiv.org/abs/2401.15884).

## Proposed semantic routing loop

The following are project recommendations:

1. Resolve the question into candidate entities, concepts, time constraints, required comparisons, and answer requirements. Keep ambiguous matches explicit.
2. Retrieve a small authorized semantic neighborhood: labels, typed edges, mapping confidence, provenance, source handles, and freshness. Expand multiple relevant concepts instead of only the first match.
3. Let the model choose the next useful read action: refine lexical/semantic search, traverse an allowed edge, inspect source metadata, fetch passages, execute an approved structured read, or finish. A fixed graph can host a dynamic decision node; dynamic does not require unrestricted tools.
4. Track a coverage ledger tied to the question: which entity, period, comparison, or claim remains unsupported. Judge relevance before retaining material; presence of both document and structured evidence is not a coverage test.
5. Synthesize claims only from retained evidence. Validate authorized evidence IDs, source locations, source versions, factual entailment, numerical calculations, and contradictions. Stop with a partial answer and specific gaps when evidence or budget runs out.

For example, “Which counterparties exceed the threshold, and what do their contracts say?” needs SQL aggregation for amounts and dated contract passages for terms. An RDF path can discover the joins and contracts; the path alone does not prove either amount or clause.

Prefer a few tools with distinct purposes: `resolve_entities`, `explore_relations`, `search_evidence`, `fetch_evidence`, and `query_structured_source`. Return concise previews and stable handles, pagination, and explicit status (`no_match`, `truncated`, `forbidden`, `stale`, `unavailable`). Define when each tool is useful, allowed predicates/filters, units/time semantics, and output provenance. Anthropic recommends task-oriented tools, meaningful responses, non-overlapping purposes, token efficiency, and realistic held-out evaluations. [Tool design](https://www.anthropic.com/engineering/writing-tools-for-agents).

Identity, scope version, deadlines, and connector credentials must come from server context, never model arguments. Reauthorize all graph discovery, index hits, row reads, document fetches, final citations, and persisted result reads. Use application-owned source handles instead of arbitrary URLs/object keys. Use restricted database roles, query allowlists or validated read plans, timeout/row limits, tenant filters, and no write/shell tools. Tool visibility is a usability optimization; backend authorization is the security boundary. Keep checkpoints, caches, summaries, and telemetry scoped because they can retain sensitive evidence.

## OpenRouter / DeepSeek compatibility gate

OpenRouter documents OpenAI SDK integration and standardized client tool calls. Tools must accompany subsequent requests; execution remains application-owned. Structured output requires a compatible model/provider and `response_format: json_schema`; tool support does not imply schema support. `provider.require_parameters: true` prevents routing to providers lacking requested parameters, whereas default routing can ignore unsupported parameters. [SDK](https://openrouter.ai/docs/guides/community/openai-sdk), [Tools](https://openrouter.ai/docs/guides/features/tool-calling), [Schemas](https://openrouter.ai/docs/guides/features/structured-outputs), [Routing](https://openrouter.ai/docs/guides/routing/provider-selection).

DeepSeek's current direct API documents thinking-mode tool calls and mandatory preservation of `reasoning_content` across requests containing tools. This is a direct-API requirement, not proof that every OpenRouter provider uses the same representation. Preserve OpenRouter's documented reasoning metadata in the adapter and test the exact route. [DeepSeek thinking](https://api-docs.deepseek.com/guides/thinking_mode/).

Before rollout, pin SDK/framework versions and probe the configured model ID/provider with synthetic fixtures: one tool call, multiple turns, malformed arguments, errors, streamed argument assembly, cancellation, thinking metadata, tools plus final schema, and unsupported parameters. Verify structured output locally; reject unknown tool names and invalid arguments; cap repair attempts. Record actual provider, parameters, usage, and failures. No route has been certified by this research.

## Evaluation and acceptance

Compare current retrieval, graph-assisted fixed retrieval, and dynamic loop on the same held-out questions. Include entity ambiguity, multi-hop routing, SQL/document joins, theme queries, missing mappings, stale documents, contradictions, unauthorized sources, and genuine no-answer cases.

Measure separately: retrieval precision/recall; required-facet coverage; mapping/path correctness; claim entailment and citation accuracy; exact aggregate accuracy; unsupported-claim rate and appropriate abstention; ACL leakage; latency, calls, and token/cost budgets. Human-label a subset of claims and facets; a second LLM judge is advisory, not proof. Correct evidence IDs alone do not establish support. Do not require a particular tool sequence when several paths are valid. Track failures by retrieval, graph mapping, selection, synthesis, and validation so framework changes cannot conceal data defects.

Initial code inspection found `backend/app/agent/graph.py` expands only the first concept at depth one, allows at most two preset query variants, and assesses source-type presence. Those mechanisms should evolve into question-specific evidence selection and coverage, while preserving its scope-change checks and bounded execution. This observation is based on local source, not a live system test.
