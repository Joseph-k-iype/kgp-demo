from evals.cases import load_cases, GoldCase
from evals.metrics import score_run


def test_gold_split_is_fixed_and_covers_domains_and_edge_cases():
    dev, held = load_cases("development"), load_cases("heldout")
    assert len(dev) == 40 and len(held) == 20
    assert not ({c.id for c in dev} & {c.id for c in held})
    assert len({c.domain_id for c in dev + held if c.category == "domain"}) == 11
    assert sum(c.outcome == "answered" for c in held) == 14
    assert sum(c.category == "unanswerable" for c in held) == 3
    assert sum(c.outcome == "needs_clarification" for c in held) == 2
    assert sum(c.category == "injection" for c in held) == 1


def test_valid_citation_id_does_not_prove_a_wrong_amount():
    gold = GoldCase(
        id="amount",
        query="What is FIN-100 liquidity?",
        category="finance",
        domain_id="finance",
        facts=[
            {
                "id": "amount",
                "answer_pattern": r"12[,.]?500[,.]?000",
                "asset_ids": ["finance-asset-0"],
            }
        ],
    )
    bad = {
        "answer_outcome": "answered",
        "evidence": [{"id": "e1", "asset_id": "finance-asset-0"}],
        "statements": [
            {
                "text": "USD 99,000,000",
                "evidence_ids": ["e1"],
                "support_status": "supported",
            }
        ],
    }
    score = score_run(bad, gold)
    assert score.support_precision == 0 and score.facet_coverage == 0
    bad["statements"][0]["text"] = "USD 12,500,000"
    score = score_run(bad, gold)
    assert score.support_precision == 1 and score.facet_coverage == 1


def test_metrics_do_not_require_a_specific_tool_sequence():
    gold = GoldCase(
        id="policy",
        query="Which policy?",
        category="finance",
        facts=[
            {
                "id": "policy",
                "answer_pattern": "TL-POL-001",
                "asset_ids": ["finance-asset-1"],
            }
        ],
    )
    run = {
        "answer_outcome": "answered",
        "evidence": [{"id": "e1", "asset_id": "finance-asset-1"}],
        "statements": [
            {
                "text": "TL-POL-001 governs liquidity",
                "evidence_ids": ["e1"],
                "support_status": "supported",
            }
        ],
    }
    a = score_run({**run, "events": [{"stage": "graph"}]}, gold)
    b = score_run({**run, "events": [{"stage": "document"}]}, gold)
    assert a == b and a.retrieval_recall == 1


def test_fixture_gold_facts_are_in_actual_source_content():
    import re, json
    from app.fixtures import make_fixtures, business_data, document_text

    records = {r["id"]: r for r in make_fixtures()}
    for case in load_cases("development") + load_cases("heldout"):
        for fact in case.facts:
            texts = []
            for asset_id in fact.asset_ids:
                asset = records[asset_id]
                texts.append(
                    document_text(asset)
                    if asset["payload"]["type"] == "Document"
                    else json.dumps(business_data(asset))
                )
            assert any(re.search(fact.answer_pattern, text, re.I) for text in texts), (
                case.id,
                fact.id,
            )


def test_policy_fact_requires_gold_relationship_path():
    gold = GoldCase(
        id="path",
        query="Which policy governs liquidity?",
        category="finance",
        facts=[
            {
                "id": "policy",
                "answer_pattern": "TL-POL-001",
                "asset_ids": ["finance-asset-1"],
            }
        ],
        paths=[["treasury-liquidity", "governedBy", "TL-POL-001"]],
    )
    run = {
        "answer_outcome": "answered",
        "evidence": [{"id": "e1", "asset_id": "finance-asset-1"}],
        "statements": [
            {
                "text": "TL-POL-001 governs liquidity",
                "evidence_ids": ["e1"],
                "support_status": "supported",
            }
        ],
    }
    assert score_run(run, gold).support_precision == 0
    run["graph_paths"] = [["treasury-liquidity", "governedBy", "TL-POL-001"]]
    assert score_run(run, gold).support_precision == 1


def test_correct_dataset_but_wrong_row_does_not_cover_a_fact():
    gold = GoldCase(
        id="row",
        query="FIN-100 liquidity",
        category="finance",
        facts=[
            {
                "id": "amount",
                "answer_pattern": r"12500000",
                "asset_ids": ["finance-asset-0"],
                "locator": "finance-asset-0-row-0",
            }
        ],
    )
    run = {
        "answer_outcome": "answered",
        "evidence": [
            {
                "id": "e1",
                "asset_id": "finance-asset-0",
                "provenance": {"row_id": "finance-asset-0-row-1"},
            }
        ],
        "statements": [
            {"text": "12500000", "evidence_ids": ["e1"], "support_status": "supported"}
        ],
    }
    assert score_run(run, gold).support_precision == 0
