# Agentic search architecture

The graph unifies business meaning, governance and source handles. The agent cannot issue arbitrary SQL/SPARQL or select an identity. It chooses typed read operations inside the current server-owned scope.

## Adaptive workflow

1. **Authorize and admit.** Intersect requested domain with current persona scope. Persist an idempotent run and the original deadline in PostgreSQL. Enforce shared admission limits.
2. **Resolve and route.** Resolve candidate business entities using indexed labels/aliases. Follow a bounded RDF neighborhood with source-backed `governedBy`, `supportedBy`, `recordedIn` and `partOf` relationships. Read an initial bounded source page, including its identifying header, when the graph supplies a source handle.
3. **Decide.** A LangGraph decision node supplies a versioned dynamic prompt: original question, required facets, resolved entities, current evidence, graph proofs, coverage, observations and remaining budgets. It is not a fixed sequence of searches. A simple policy-name question should not acquire unrelated budget/amount facets.
4. **Execute tools.** Validate every action against a discriminated Pydantic union. Independent reads can run in parallel (maximum two); dependent graph-to-source reads occur in later decisions. Preserve typed observations and native tool-call receipts. Correct invalid arguments or unsupported handles within a two-invalid-action budget; stop repeated no-progress attempts.
5. **Assess coverage.** Decide whether to retrieve missing facets, clarify genuinely ambiguous entities, finish, or return honest missing evidence. Search candidates from BM25/HNSW and RDF are read against authoritative sources before they can support claims.
6. **Draft.** Generate atomic claims with supplied evidence IDs and exact passage quotes or actual structured field/value, unit and period. Neutral sections reference zero-based claim indices. A leading answer addresses the question; sections are not a reference inventory.
7. **Verify.** Recheck current source access/version, exact live spans, numeric/currency/date/entity boundaries and independently executed aggregation. Governing claims require a current source-backed policy-instance path attached to the cited document. A semantic judgment checks entailment, relevance and omitted question requirements after deterministic gates.
8. **Publish.** Only accepted claims survive. Remap sections to accepted indices and attach named sources/locators. Outcomes are `answered`, `partial`, `no_evidence` or `needs_clarification`. Explicit source-only mode is labeled and never masquerades as verified model synthesis.

## Provider adapters and prompts

The OpenAI SDK accesses OpenRouter's Chat Completions endpoint. The configured DeepSeek model and upstream route are explicit. Native tools require certification of the exact gateway/model/upstream for plan control, a source read and a multi-turn receipt answer. JSON-actions is a separately configured adapter sharing the same tool contracts; there is no automatic ambiguous paid replay or silent provider change.

Final answers use either provider JSON schema or explicitly configured JSON-object mode. Both include the complete schema in instructions and undergo strict Pydantic validation with extra fields forbidden. JSON-object mode does not remove source or claim validation. Reasoning is disabled for the selected OpenRouter route; private reasoning and raw model receipts are not returned to users or exported in the demo snapshot.

Retrieved text is untrusted evidence. Prompts explicitly reject instructions inside sources. Dynamic context carries only bounded relevant observations and source handles. Native receipts are compacted as valid JSON with truncation indicated, rather than slicing serialized JSON into malformed tool messages. Actual full source fragments remain in the checkpoint.

## Durable execution

`app.agent.worker` claims a queued row with PostgreSQL `FOR UPDATE SKIP LOCKED`, assigns an owner and renews a lease. Only the current owner can publish. Persona/intent idempotency prevents duplicate generations from repeated submission; reload and filters reconnect to the stored run instead of starting another paid request.

Before each paid call, persist the fingerprint, in-flight marker and attempt count. Persist its known receipt before clearing the marker. Recovery can reuse a known receipt, but an interrupted call with an uncertain outcome fails explicitly rather than paying again. Cancellation and scope-version changes remain authoritative across worker handoff. Budgets reserve finalization time so tool exploration does not consume the entire deadline.

## Treasury walkthrough

For “Which policies govern treasury liquidity?”, resolve `treasury-liquidity`, traverse its current `governedBy` assertions, and read the actual policies:

- `TL-POL-001`, Treasury Liquidity Monitoring Policy: daily reconciliation and same-day escalation below USD 10,000,000. Source: `finance-asset-1`, controls/escalation.
- `TF-POL-002`, Treasury Funding Evidence Policy: monthly funding evidence review. Source: `finance-asset-5`, controls.

The supporting route can be `treasury-liquidity → TL-POL-001 → finance-asset-1-section-controls`. Every edge carries a source version and locator. The superseded `TL-POL-000` does not provide current authority. Daily liquidity reconciliation and monthly funding evidence review are separate obligations, not contradictory frequencies. Opening a citation shows its actual passage before its surrounding metadata.

## Evaluation boundaries

Development cases are separate from a 20-case held-out split. Offline comparisons exercise retrieval and deterministic verification without paid generation; they do not measure LLM answer quality. Live reports record errors, accepted statements, source IDs/locators, paths, usage, attempts, versions and latency. Empty-gold conventional metrics are reported separately from answerable-case metrics. Provider probes establish protocol compatibility, not answer correctness. Deep Agents, community summarization, arbitrary agent writes and external connectors are outside this demo; see the primary-source research for considered strategies.

## Tested experimental configuration

Protocol compatibility passed for `deepseek/deepseek-v4.1-flash` via OpenRouter upstream `Fireworks`, native tools and explicit JSON-object output. The schema is still strictly validated on the server. The supplied example pins this route and its compatibility flags; changing the gateway/model/upstream invalidates native certification. The graph-centered engine remains **disabled by default** because the repeated live answer-quality gates have not passed. Enable `GRAPH_SEARCH_V2=true` only for an explicit experimental local preview; this does not certify provider reliability or factual precision.

Known completed model usage is retained even when a later source/provider call fails. Unknown failed response usage cannot be reconstructed. Failed runs record a safe error class without exporting SDK bodies, keys or private reasoning. Checkpoint decoding explicitly permits application state types and disables pickle fallback.
