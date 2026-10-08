import time
from app.agent.verification import (
    SupportedClaim,
    ClaimCitation,
    verify_claims,
    TextJudgment,
)
from app.knowledge.contracts import EvidenceFragment, ToolContext
from app.auth import resolve_scope


def context():
    return ToolContext(scope=resolve_scope("admin"), deadline=time.time() + 30)


def evidence(text="Daily reconciliation is required."):
    return EvidenceFragment(
        id="clause",
        asset_id="finance-asset-1",
        domain_id="finance",
        content_kind="document",
        text=text,
        source_ref={
            "asset_id": "finance-asset-1",
            "domain_id": "finance",
            "version": "v1",
            "locator": "controls",
        },
    )


def test_correct_id_wrong_clause_is_rejected_before_text_judge(monkeypatch):
    import app.agent.verification as module

    monkeypatch.setattr(module, "fresh", lambda *a: True)
    monkeypatch.setattr(
        module, "live_content", lambda *a: "Daily reconciliation is required."
    )
    called = []
    claim = SupportedClaim(
        text="Weekly reconciliation is required.",
        facet_ids=["controls"],
        citations=[
            ClaimCitation(
                evidence_id="clause", quote="Weekly reconciliation is required."
            )
        ],
    )
    result = verify_claims(
        context(), [claim], [evidence()], judge=lambda *a: called.append(1)
    )
    assert (
        not result.supported
        and result.rejected[0].status == "unsupported"
        and not called
    )


def test_exact_quote_does_not_prove_a_contradictory_paraphrase(monkeypatch):
    import app.agent.verification as module

    monkeypatch.setattr(module, "fresh", lambda *a: True)
    monkeypatch.setattr(
        module, "live_content", lambda *a: "Daily reconciliation is required."
    )
    claim = SupportedClaim(
        text="No reconciliation is required.",
        citations=[
            ClaimCitation(
                evidence_id="clause", quote="Daily reconciliation is required."
            )
        ],
    )
    result = verify_claims(
        context(),
        [claim],
        [evidence()],
        judge=lambda claims, evidence: [
            TextJudgment(
                claim_index=0,
                status="unsupported",
                facet_ids=[],
                reason="Contradiction",
            )
        ],
    )
    assert not result.supported and result.rejected[0].status == "unsupported"


def test_stale_source_never_reaches_semantic_judge(monkeypatch):
    import app.agent.verification as module

    monkeypatch.setattr(module, "fresh", lambda *a: False)
    claim = SupportedClaim(
        text="Daily reconciliation is required.",
        citations=[
            ClaimCitation(
                evidence_id="clause", quote="Daily reconciliation is required."
            )
        ],
    )
    result = verify_claims(
        context(),
        [claim],
        [evidence()],
        judge=lambda *a: (_ for _ in ()).throw(
            AssertionError("must not judge stale source")
        ),
    )
    assert result.rejected[0].status == "stale"


def test_wrong_unit_or_period_is_rejected(monkeypatch):
    import app.agent.verification as module

    e = evidence().model_copy(
        update={
            "content_kind": "structured",
            "values": {"liquidity_usd": 12500000, "as_of": "2026-09-30"},
            "text": "12500000 USD on 2026-09-30",
        }
    )
    monkeypatch.setattr(module, "fresh", lambda *a: True)
    monkeypatch.setattr(module, "live_content", lambda *a: e.text)
    for citation in [
        ClaimCitation(
            evidence_id="clause", field="liquidity_usd", value="12500000", unit="EUR"
        ),
        ClaimCitation(
            evidence_id="clause",
            field="liquidity_usd",
            value="12500000",
            unit="USD",
            period="2025-09-30",
        ),
    ]:
        report = verify_claims(
            context(),
            [SupportedClaim(text="Amount", citations=[citation])],
            [e],
            judge=lambda *a: [],
        )
        assert report.rejected[0].status == "unsupported"


def test_no_judge_means_only_exact_source_quotes_can_be_supported(monkeypatch):
    import app.agent.verification as module

    monkeypatch.setattr(module, "fresh", lambda *a: True)
    monkeypatch.setattr(
        module, "live_content", lambda *a: "Daily reconciliation is required."
    )
    claims = [
        SupportedClaim(
            text="Daily reconciliation is required.",
            citations=[
                ClaimCitation(
                    evidence_id="clause", quote="Daily reconciliation is required."
                )
            ],
        ),
        SupportedClaim(
            text="A daily review ensures everything is safe.",
            citations=[
                ClaimCitation(
                    evidence_id="clause", quote="Daily reconciliation is required."
                )
            ],
        ),
    ]
    result = verify_claims(context(), claims, [evidence()])
    assert len(result.supported) == 1 and len(result.rejected) == 1


def test_a_cross_source_claim_can_cite_amount_and_obligation_separately(monkeypatch):
    import app.agent.verification as module

    a = evidence("Exposure is USD 1.25 million.")
    b = evidence("The contract requires annual disclosure.").model_copy(
        update={
            "id": "contract",
            "asset_id": "legal-asset-1",
            "domain_id": "legal",
            "source_ref": a.source_ref.model_copy(
                update={"asset_id": "legal-asset-1", "domain_id": "legal"}
            ),
        }
    )
    monkeypatch.setattr(module, "fresh", lambda *a: True)
    monkeypatch.setattr(module, "live_content", lambda ctx, e: e.text)
    claim = SupportedClaim(
        text="Exposure is USD 1.25 million and the contract requires annual disclosure.",
        citations=[
            ClaimCitation(evidence_id="clause", quote=a.text),
            ClaimCitation(evidence_id="contract", quote=b.text),
        ],
    )
    report = verify_claims(
        context(),
        [claim],
        [a, b],
        judge=lambda *a: [
            TextJudgment(
                claim_index=0, status="supported", facet_ids=["exposure", "obligation"]
            )
        ],
    )
    assert len(report.supported) == 1 and not report.rejected


def test_explicit_predicate_path_matches_only_the_exact_current_proof(monkeypatch):
    import app.agent.verification as module
    import app.knowledge.graph as graph
    from app.knowledge.contracts import ToolResult

    e = evidence()
    paths = [
        {
            "edges": [
                {
                    "source": "treasury-liquidity",
                    "predicate": "governedBy",
                    "target": "TL-POL-001",
                    "source_ref": e.source_ref.model_dump(),
                }
            ]
        }
    ]
    monkeypatch.setattr(module, "get_record", lambda *a: {"entity_type": "Policy"})
    monkeypatch.setattr(
        graph, "traverse_graph", lambda *a, **kw: ToolResult(outcome="ok", paths=paths)
    )
    claim = SupportedClaim(
        text="TL-POL-001 governs liquidity.",
        citations=[ClaimCitation(evidence_id=e.id, quote=e.text)],
        governance_paths=[["treasury-liquidity", "governedBy", "TL-POL-001"]],
    )
    assert module.governance_current(context(), claim, paths, {e.id: e})
    claim.governance_paths = [["treasury-liquidity", "relatedTo", "TL-POL-001"]]
    assert not module.governance_current(context(), claim, paths, {e.id: e})


def test_structured_period_and_percent_representation_are_normalized_without_changing_facts():
    import json
    from app.agent.verification import citation_error

    e = evidence().model_copy(
        update={
            "content_kind": "structured",
            "values": {"sla_percent": 96.0, "as_of": "2026-09-30"},
        }
    )
    claim = SupportedClaim(
        text="SLA is 96% on 2026-09-30.",
        citations=[
            ClaimCitation(
                evidence_id=e.id,
                field="sla_percent",
                value="96.0",
                unit="%",
                period="as_of 2026-09-30",
            )
        ],
    )
    assert citation_error(claim, claim.citations[0], e, json.dumps(e.values)) is None
    claim.citations[0].period = "as_of 2025-09-30"
    assert (
        citation_error(claim, claim.citations[0], e, json.dumps(e.values)) is not None
    )


def test_governance_claim_can_include_its_separate_current_supporting_path(monkeypatch):
    import app.agent.verification as module
    import app.knowledge.graph as graph
    from app.knowledge.contracts import ToolResult

    e = evidence()
    edge = lambda s, p, t: {
        "source": s,
        "predicate": p,
        "target": t,
        "source_ref": e.source_ref.model_dump(),
    }
    paths = [
        {"edges": [edge("liquidity", "governedBy", "policy")]},
        {"edges": [edge("policy", "supportedBy", "section")]},
    ]
    monkeypatch.setattr(module, "get_record", lambda *a: {"entity_type": "Policy"})
    monkeypatch.setattr(
        graph, "traverse_graph", lambda *a, **kw: ToolResult(paths=paths)
    )
    claim = SupportedClaim(
        text="Policy governs liquidity.",
        citations=[ClaimCitation(evidence_id=e.id, quote=e.text)],
        governance_paths=[["liquidity", "policy"], ["policy", "section"]],
    )
    assert module.governance_current(context(), claim, paths, {e.id: e})
    claim.governance_paths = [["policy", "section"]]
    assert not module.governance_current(context(), claim, paths, {e.id: e})
