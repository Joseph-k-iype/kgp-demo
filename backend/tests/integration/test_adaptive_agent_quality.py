import json, time
import pytest
from fastapi import HTTPException
from app.auth import resolve_scope
from app.knowledge.contracts import (
    ToolContext,
    EvidenceFragment,
    ReadDocumentAction,
    QueryDatasetAction,
)
from app.knowledge.tools import execute_read
from app.knowledge.graph import traverse_graph
from app.agent.verification import (
    SupportedClaim,
    ClaimCitation,
    TextJudgment,
    verify_claims,
)


def context(persona="admin"):
    return ToolContext(scope=resolve_scope(persona), deadline=time.time() + 40)


def document(ctx, asset):
    result = execute_read(
        ctx, ReadDocumentAction(asset_id=asset, section_id="controls")
    )
    return EvidenceFragment(
        id=asset,
        asset_id=asset,
        domain_id=result.source_refs[0].domain_id,
        content_kind="document",
        text=result.items[0]["text"],
        source_ref=result.source_refs[0],
    )


def supported(*args):
    return [TextJudgment(claim_index=0, status="supported", facet_ids=["policies"])]


def test_current_governing_path_and_real_clause_are_both_required():
    ctx = context()
    source = document(ctx, "finance-asset-1")
    graph = traverse_graph(
        ctx, ["treasury-liquidity"], ["governedBy"], ["Policy"], depth=1
    )
    claim = SupportedClaim(
        text="TL-POL-001 governs treasury liquidity.",
        citations=[ClaimCitation(evidence_id=source.id, quote=source.text)],
        governance_paths=[["treasury-liquidity", "TL-POL-001"]],
    )
    report = verify_claims(ctx, [claim], [source], judge=supported, paths=graph.paths)
    assert len(report.supported) == 1, report
    invalid = claim.model_copy(
        update={"governance_paths": [["treasury-liquidity", "Policy"]]}
    )
    report = verify_claims(ctx, [invalid], [source], judge=supported, paths=graph.paths)
    assert not report.supported
    superseded = claim.model_copy(
        update={"governance_paths": [["treasury-liquidity", "TL-POL-000"]]}
    )
    assert not verify_claims(
        ctx, [superseded], [source], judge=supported, paths=graph.paths
    ).supported


def test_governing_path_cannot_lend_authority_to_a_different_document():
    ctx = context()
    source = document(ctx, "legal-asset-1")
    graph = traverse_graph(
        ctx, ["treasury-liquidity"], ["governedBy"], ["Policy"], depth=1
    )
    claim = SupportedClaim(
        text="TL-POL-001 governs treasury liquidity.",
        citations=[ClaimCitation(evidence_id=source.id, quote=source.text)],
        governance_paths=[["treasury-liquidity", "TL-POL-001"]],
    )
    report = verify_claims(ctx, [claim], [source], judge=supported, paths=graph.paths)
    assert not report.supported


def test_aggregate_support_reexecutes_the_approved_parameterized_query():
    ctx = context()
    call = QueryDatasetAction(
        query={
            "asset_id": "finance-asset-0",
            "aggregate": {"operation": "sum", "field": "liquidity_usd"},
            "filters": [{"field": "liquidity_usd", "op": "gt", "value": 20000000}],
        }
    )
    result = execute_read(ctx, call)
    values = result.items[0]["values"]
    e = EvidenceFragment(
        id="sum",
        asset_id="finance-asset-0",
        domain_id="finance",
        content_kind="structured",
        text=json.dumps(values),
        values=values,
        source_ref=result.source_refs[0],
        provenance={"operation": call.query.model_dump(mode="json")},
    )
    claim = SupportedClaim(
        text="Total liquidity is USD " + str(values["sum"]) + ".",
        citations=[
            ClaimCitation(
                evidence_id=e.id, field="sum", value=str(values["sum"]), unit="USD"
            )
        ],
    )
    assert verify_claims(ctx, [claim], [e], judge=supported).supported
    corrupt = e.model_copy(update={"values": {**values, "sum": values["sum"] + 1}})
    assert not verify_claims(ctx, [claim], [corrupt], judge=supported).supported


def test_out_of_scope_source_cannot_be_published_even_with_a_valid_id():
    ctx = context()
    e = document(ctx, "finance-asset-1")
    claim = SupportedClaim(
        text=e.text, citations=[ClaimCitation(evidence_id=e.id, quote=e.text)]
    )
    with pytest.raises(HTTPException):
        verify_claims(context("legal"), [claim], [e], judge=supported)


def test_finalization_with_no_model_budget_returns_source_excerpts_and_a_gap():
    from app.agent.actions import ResearchState
    from app.agent.finalization import finalize_research

    ctx = context()
    e = document(ctx, "finance-asset-1")
    state = ResearchState(
        query="Which policies govern treasury?",
        intent={
            "query": "Which policies govern treasury?",
            "facets": [
                {
                    "id": "policies",
                    "description": "Current governing policies",
                    "kinds": ["document"],
                }
            ],
        },
        evidence=[e],
    )
    calls = []
    ctx.deadline = time.time() + 4
    result = finalize_research(
        ctx, state, "llm", lambda *a: calls.append(1), lambda *a: None
    )
    assert not calls and result["answer_outcome"] == "partial"
    assert result["statements"][0]["text"] == e.text
    assert result["semantic_verification"] == "source_only" and result["gaps"]


def test_conflicting_supported_passages_cannot_be_reported_as_answered(monkeypatch):
    from app.agent.actions import ResearchState
    from app.agent.finalization import finalize_research
    from app.agent.verification import DraftAnswer

    ctx = context()
    e = document(ctx, "finance-asset-1")
    state = ResearchState(
        query="What reconciliation frequency is required?",
        intent={
            "query": "What reconciliation frequency is required?",
            "facets": [
                {"id": "frequency", "description": "Frequency", "kinds": ["document"]}
            ],
        },
        evidence=[e],
    )
    draft = DraftAnswer(
        claims=[
            SupportedClaim(
                text="Daily reconciliation is required.",
                citations=[ClaimCitation(evidence_id=e.id, quote=e.text)],
                facet_ids=["frequency"],
            )
        ]
    )
    result = finalize_research(
        ctx,
        state,
        "llm",
        lambda *a: None,
        lambda *a: None,
        draft_provider=lambda *a: draft,
        judge_provider=lambda *a: [
            TextJudgment(
                claim_index=0,
                status="conflicting",
                facet_ids=["frequency"],
                reason="Current source passages disagree",
            )
        ],
    )
    assert result["answer_outcome"] == "partial" and result["conflicts"]
    assert not result["statements"]


def test_exact_aggregate_preserves_large_decimal_precision():
    from app.db import query
    from app.knowledge.tools import query_dataset
    from app.knowledge.contracts import QueryDatasetAction

    row = "finance-asset-0-row-0"
    original = query("SELECT payload FROM business_rows WHERE id=:id", {"id": row})[0][
        "payload"
    ]
    try:
        changed = {**original, "liquidity_usd": 9007199254740993}
        query(
            "UPDATE business_rows SET payload=CAST(:p AS jsonb) WHERE id=:id RETURNING id",
            {"id": row, "p": json.dumps(changed)},
        )
        result = query_dataset(
            context(),
            QueryDatasetAction(
                query={
                    "asset_id": "finance-asset-0",
                    "filters": [{"field": "record_id", "op": "eq", "value": row}],
                    "aggregate": {"operation": "sum", "field": "liquidity_usd"},
                }
            ),
        )
        assert result.items[0]["values"]["sum"] == 9007199254740993
    finally:
        query(
            "UPDATE business_rows SET payload=CAST(:p AS jsonb) WHERE id=:id RETURNING id",
            {"id": row, "p": json.dumps(original)},
        )


def test_answer_sections_include_only_verified_claims_and_named_sources():
    from app.agent.actions import ResearchState
    from app.agent.finalization import finalize_research
    from app.agent.verification import DraftAnswer

    ctx = context()
    e = document(ctx, "finance-asset-1").model_copy(
        update={"source_title": "TL-POL-001 — Treasury Liquidity Monitoring Policy"}
    )
    state = ResearchState(
        query="What reconciliation frequency is required?",
        intent={
            "query": "What reconciliation frequency is required?",
            "facets": [
                {"id": "frequency", "description": "Frequency", "kinds": ["document"]}
            ],
        },
        evidence=[e],
    )
    draft = DraftAnswer(
        claims=[
            SupportedClaim(
                text="Treasury must reconcile liquidity positions daily.",
                citations=[ClaimCitation(evidence_id=e.id, quote=e.text)],
                facet_ids=["frequency"],
            ),
            SupportedClaim(
                text="Weekly reconciliation is required.",
                citations=[
                    ClaimCitation(
                        evidence_id=e.id, quote="Weekly reconciliation is required."
                    )
                ],
            ),
        ],
        sections=[
            {"title": "Answer", "claim_indices": [0, 1]},
            {"title": "Key requirements", "claim_indices": [1]},
        ],
    )
    result = finalize_research(
        ctx,
        state,
        "llm",
        lambda *a: None,
        lambda *a: None,
        draft_provider=lambda *a: draft,
        judge_provider=lambda *a: [
            TextJudgment(claim_index=0, status="supported", facet_ids=["frequency"])
        ],
    )
    assert len(result["statements"]) == 1
    assert result["answer_sections"] == [{"title": "Answer", "statement_indices": [0]}]
    assert result["evidence"][0]["source_title"].startswith("TL-POL-001")
    assert result["statements"][0]["supporting_locators"][0]["source_title"].startswith(
        "TL-POL-001"
    )


def test_source_only_dataset_values_are_verified_without_json_key_order_assumptions():
    from app.agent.actions import ResearchState
    from app.agent.finalization import finalize_research

    ctx = context()
    result = execute_read(
        ctx,
        QueryDatasetAction(
            query={
                "asset_id": "finance-asset-0",
                "select": ["position_id", "liquidity_usd", "as_of"],
                "limit": 1,
            }
        ),
    )
    item = result.items[0]
    e = EvidenceFragment(
        id=item["id"],
        asset_id="finance-asset-0",
        domain_id="finance",
        content_kind="structured",
        text=json.dumps(item["values"]),
        values=item["values"],
        source_ref=result.source_refs[0],
    )
    output = finalize_research(
        ctx,
        ResearchState(query="FIN-100 liquidity", evidence=[e]),
        "extractive",
        lambda *a: None,
        lambda *a: None,
    )
    assert output["statements"] and "12500000" in output["statements"][0]["text"]
    assert output["statements"][0]["support_status"] == "source_only"
