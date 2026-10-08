# Evaluation artifacts

Reports are synthetic source evaluations, not production or universal correctness certificates.

- `2026-10-08-adaptive-development-offline.json`: 40 fixed development cases, no provider calls, actual source exploration and deterministic checks.
- `2026-10-08-legacy-heldout-offline.json` and `graph-fixed-heldout-offline.json`: same enriched corpus, twenty offline comparison cases. Source-only mode cannot receive model-supported claim labels.
- `2026-10-08-adaptive-heldout-live-01.json`: first twenty-case paid evaluation on DeepSeek V4.1 Flash / Fireworks, prompt v2.5. Failed quality gates; retained.
- `2026-10-08-adaptive-heldout-live-02.json`: disclosed second iteration after generic development regressions and fixes, prompt v2.6. This is a repeated held-out evaluation, not untouched hold-out certification.
- Development/provider reports retain failed compatibility and end-to-end attempts. One successful native probe is not a quality gate: native plan control, source read, multi-turn receipts, final strict server schema and actual answers are tested separately.
- `2026-10-08-scale.json`: isolated 10,000 RDF entities / 100,000 PostgreSQL rows, five samples per operation, bounded output, indexed query plans, lease recovery and cancellation. Temporary resources were removed.
- `2026-10-08-data-restore.json`: isolated PostgreSQL/MinIO/Fuseki round trip, exact catalog/row/object equality, named-graph triple counts, resource cleanup.

## Metric interpretation

Retrieval recall counts expected source/locator matches. Facet coverage requires the expected fact pattern in an accepted supported claim with its gold source and required graph paths. The `support_precision` field is **gold-pattern claim relevance**, not an independent measurement of all factual entailment: a true additional source fact can miss a narrow gold pattern. Keep that limitation visible; do not call a model's own support labels ground truth. Current-source gates and a fallible semantic judge run before accepted statements appear. Independent human review is still needed for factual precision certification.

Empty-gold cases conventionally score one for some retrieval/coverage fields. Reports therefore separate the fourteen answerable held-out cases (or thirty-four answerable development cases) and their denominators. Outcomes and errors must also be examined individually. Provider failure is retained, not silently retried. Live requests/attempts and token usage are reported, including invalid decisions when known receipts exist; ambiguous failed responses may have unreported upstream token usage.

The first implementation evaluations ran during uncommitted Task8 work on the recorded base commit. Prompt/model/framework/source versions are included, but the base SHA alone does not reconstruct every interim patch. Final reproducibility is the published source/lockfiles/snapshot and final verification record; historical failures are diagnostic evidence, not exact source-tree release attestations.

The `final-request-diagnostic` artifact records one explicitly isolated additional schema request on synthetic recorded context. It does not resume the original failed run or contribute to held-out scores. Its response failed strict validation. Subsequent development cross-source diagnostics succeeded, demonstrating that protocol probes do not establish universal provider reliability.
