"""Same-corpus comparisons with explicit offline/source-only and live modes."""

import time
from pydantic import BaseModel, Field
from app.auth import resolve_scope
from app.config import settings
from app.knowledge.contracts import ToolContext
from app.agent.adaptive import run_research
from app.agent.offline import make_offline_decider
from app.agent.actions import ResearchState
from app.agent.finalization import finalize_research
from app.retrieval.service import retrieve
from evals.metrics import score_run


class EvaluationReport(BaseModel):
    engine: str
    provider_mode: str
    cases: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def evaluate_engine(engine, cases, provider_mode="offline", max_runs=None):
    if engine not in ["legacy", "graph_fixed", "adaptive"] or provider_mode not in [
        "offline",
        "live",
    ]:
        raise ValueError("Unknown evaluation mode")
    selected = cases[:max_runs] if max_runs is not None else cases
    if provider_mode == "live" and (engine != "adaptive" or len(selected) > 20):
        raise ValueError("Live evaluation is limited to twenty adaptive runs")
    report = EvaluationReport(engine=engine, provider_mode=provider_mode)
    if provider_mode == "offline":
        report.limitations = [
            "Offline mode evaluates current source exploration and deterministic verification; it makes no provider calls and does not measure model answer quality.",
            "Source excerpts do not receive semantic-supported answer labels. Answerable-case claim precision/coverage do not measure a model in this mode; aggregate metrics also include conventional empty-gold-case defaults.",
        ]
    for case in selected:
        started = time.time()
        scope = resolve_scope(case.persona)
        result = {"statements": [], "evidence": [], "answer_outcome": "no_evidence"}
        error = None
        try:
            if provider_mode == "live":
                from app.agent.worker import enqueue, claim_next
                from app.agent.service import execute_graph_run, get_search
                from app.contracts import SearchRequest
                import uuid

                worker = "eval-" + uuid.uuid4().hex
                id = enqueue(
                    scope,
                    SearchRequest(
                        query=case.query,
                        domain_id=case.domain_id,
                        intent_id=uuid.uuid4().hex,
                    ),
                )
                if not claim_next(worker, run_id=id):
                    raise RuntimeError("Evaluation worker could not claim its run")
                execute_graph_run(id, worker)
                result = get_search(scope, id)
                if result["status"] != "completed":
                    error = result.get("error", result["status"])
            else:
                ctx = ToolContext(
                    scope=scope, domain_id=case.domain_id, deadline=started + 120
                )
                if engine == "legacy":
                    from app.auth import narrow_scope

                    evidence = retrieve(
                        narrow_scope(scope, case.domain_id),
                        case.query,
                        [],
                        limit=10,
                        deadline=ctx.deadline,
                    )
                    from app.knowledge.contracts import EvidenceFragment

                    fragments = [
                        EvidenceFragment(
                            id=e["id"],
                            asset_id=e["asset_id"],
                            domain_id=e["domain_id"],
                            content_kind=e.get(
                                "content_kind",
                                e.get("provenance", {}).get("type", "metadata"),
                            ),
                            text=e["text"],
                            source_ref=e["source_ref"],
                            values=e.get("values"),
                            provenance=e.get("provenance", {}),
                        )
                        for e in evidence
                        if e.get("source_ref")
                    ]
                    state = ResearchState(query=case.query, evidence=fragments)
                else:
                    state = run_research(
                        ctx,
                        case.query,
                        make_offline_decider(ctx, adaptive=engine == "adaptive"),
                    )
                result = finalize_research(
                    ctx,
                    state,
                    "extractive",
                    lambda *a: (_ for _ in ()).throw(
                        AssertionError("No model calls in offline evaluation")
                    ),
                    lambda *a: None,
                )
            metrics = score_run(result, case).model_dump()
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
            metrics = score_run(result, case).model_dump()
        report.cases.append(
            {
                "case_id": case.id,
                "category": case.category,
                "persona": case.persona,
                "domain_id": case.domain_id,
                "query": case.query,
                "elapsed_seconds": round(time.time() - started, 3),
                "error": error,
                "metrics": metrics,
                "answer_outcome": result.get("answer_outcome"),
                "run_id": result.get("run_id"),
                "tool_calls": result.get("tool_calls", 0),
                "model_attempts": result.get("paid_calls", 0),
                "usage": result.get("usage", {}),
                "versions": result.get("versions", {}),
                "statements": result.get("statements", []),
                "retrieved_sources": [
                    {
                        "asset_id": e["asset_id"],
                        "locator": e.get("locator")
                        or e.get("source_ref", {}).get("locator"),
                    }
                    for e in result.get("evidence", [])
                ],
                "graph_paths": result.get("graph_paths", []),
            }
        )
    count = len(report.cases)
    latencies = sorted(c["elapsed_seconds"] for c in report.cases)
    report.summary = {
        "case_count": count,
        "errors": sum(c["error"] is not None for c in report.cases),
        "model_attempts": sum(c["model_attempts"] for c in report.cases),
        "retrieval_recall": sum(c["metrics"]["retrieval_recall"] for c in report.cases)
        / count
        if count
        else None,
        "facet_coverage": sum(c["metrics"]["facet_coverage"] for c in report.cases)
        / count
        if count
        else None,
        "support_precision": sum(
            c["metrics"]["support_precision"] for c in report.cases
        )
        / count
        if count
        else None,
        "outcome_accuracy": sum(c["metrics"]["outcome_valid"] for c in report.cases)
        / count
        if count
        else None,
        "p50_seconds": latencies[int((count - 1) * 0.5)] if count else None,
        "p95_seconds": latencies[int((count - 1) * 0.95)] if count else None,
    }
    return report
