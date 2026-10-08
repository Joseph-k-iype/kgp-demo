from app.agent.coverage import assess_coverage
from app.knowledge.contracts import SearchIntentV2, EvidenceFragment, SourceRef


def evidence(id, kind, facets):
    return EvidenceFragment(
        id=id,
        asset_id="finance-asset-0",
        domain_id="finance",
        content_kind=kind,
        text="Synthetic evidence",
        source_ref=SourceRef(
            asset_id="finance-asset-0", domain_id="finance", version="v1", locator="row"
        ),
        matched_facet_ids=facets,
    )


def test_policy_coverage_rejects_irrelevant_document_and_does_not_require_rows():
    intent = SearchIntentV2(
        query="Which policies govern treasury liquidity?",
        facets=[
            {
                "id": "policies",
                "description": "Applicable governing policy clauses",
                "kinds": ["document"],
            }
        ],
    )
    bad = assess_coverage(intent, [evidence("people", "document", [])])
    assert bad.uncovered_facet_ids == ["policies"] and bad.irrelevant_ids == ["people"]
    good = assess_coverage(intent, [evidence("policy", "document", ["policies"])])
    assert not good.uncovered_facet_ids


def test_numeric_question_does_not_require_an_unrelated_document():
    intent = SearchIntentV2(
        query="FIN-100 liquidity",
        facets=[
            {"id": "amount", "description": "USD liquidity", "kinds": ["structured"]}
        ],
    )
    assert not assess_coverage(
        intent, [evidence("row", "structured", ["amount"])]
    ).uncovered_facet_ids
