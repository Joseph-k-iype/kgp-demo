"""Gold-fact scoring; textual verifier labels remain subject to human review."""

import re
from pydantic import BaseModel
from evals.cases import GoldCase, GoldFact


class CaseMetrics(BaseModel):
    retrieval_recall: float
    facet_coverage: float
    support_precision: float
    path_coverage: float
    outcome_valid: bool


def matches_source(evidence: dict, fact: GoldFact) -> bool:
    if evidence.get("asset_id") not in fact.asset_ids:
        return False
    p = evidence.get("provenance", {})
    return not fact.locator or fact.locator in [
        evidence.get("locator"),
        p.get("section_id"),
        p.get("row_id"),
    ]


def score_run(run: dict, gold: GoldCase) -> CaseMetrics:
    evidence = {e["id"]: e for e in run.get("evidence", [])}
    claims = run.get("statements", [])
    present_paths = run.get("graph_paths", [])
    path_coverage = (
        sum(path in present_paths for path in gold.paths) / len(gold.paths)
        if gold.paths
        else 1.0
    )
    paths_supported = path_coverage == 1
    retrieved = covered = supported = 0

    def supported_fact(claim, fact):
        return (
            paths_supported
            and claim.get("support_status") == "supported"
            and bool(re.search(fact.answer_pattern, claim["text"], re.I))
            and any(
                matches_source(evidence.get(id, {}), fact)
                for id in claim.get("evidence_ids", [])
            )
        )

    for fact in gold.facts:
        retrieved += any(matches_source(e, fact) for e in evidence.values())
        covered += any(supported_fact(c, fact) for c in claims)
    for claim in claims:
        supported += any(supported_fact(claim, f) for f in gold.facts)
    return CaseMetrics(
        retrieval_recall=retrieved / len(gold.facts) if gold.facts else 1,
        facet_coverage=covered / len(gold.facts) if gold.facts else 1,
        support_precision=supported / len(claims)
        if claims
        else (1 if not gold.facts else 0),
        path_coverage=path_coverage,
        outcome_valid=run.get("answer_outcome") == gold.outcome,
    )
