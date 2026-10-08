import time
from app.auth import resolve_scope
from app.knowledge.contracts import ToolContext
from app.knowledge.graph import resolve_entities, traverse_graph


def context(domain=None, persona="admin"):
    return ToolContext(
        scope=resolve_scope(persona), domain_id=domain, deadline=time.time() + 30
    )


def test_treasury_entity_routing_and_ambiguity():
    result = resolve_entities(context(), "Which policies govern treasury liquidity?")
    assert result.candidates[0].id == "treasury-liquidity"
    assert result.candidates[0].domain_id == "finance"
    ambiguous = resolve_entities(context(), "Which policy applies?")
    assert ambiguous.outcome == "ambiguous"
    assert len(ambiguous.candidates) >= 2


def test_graph_routes_to_real_policy_sources_and_authorized_legal():
    result = traverse_graph(
        context(),
        ["treasury-liquidity"],
        ["governedBy", "supportedBy", "requiresContract"],
        ["Policy", "EvidenceSection", "Contract"],
        depth=3,
    )
    ids = {item["id"] for item in result.items}
    assert {"TL-POL-001", "TF-POL-002", "CT-2000"} <= ids
    assert "TL-POL-000" not in ids
    assert result.paths and result.source_refs
    scoped = traverse_graph(
        context("finance"),
        ["treasury-liquidity"],
        ["governedBy", "supportedBy", "requiresContract"],
        ["Policy", "EvidenceSection", "Contract"],
    )
    assert "CT-2000" not in {item["id"] for item in scoped.items}
    assert "CT-2000" not in str(scoped.model_dump())


def test_hidden_intermediate_never_leaks_to_risk_persona():
    result = traverse_graph(
        context(persona="risk"),
        ["CP-1000"],
        ["partyTo", "supportedBy"],
        ["Contract", "EvidenceSection"],
    )
    assert "CT-2000" not in str(result.model_dump())


def test_unknown_namespace_target_is_denied_without_label_leak(monkeypatch):
    import app.knowledge.graph as module

    def external(ctx, body):
        return [
            {
                "target": {"value": "https://private.example/secret-policy"},
                "label": {"value": "Secret Policy"},
                "type": {"value": str(module.K.Policy)},
                "domain": {"value": str(module.I["finance"])},
                "predicate": {"value": str(module.K.governedBy)},
                "source": {"value": str(module.I["finance-asset-1"])},
                "version": {"value": "v1"},
                "locator": {"value": "controls"},
            }
        ]

    monkeypatch.setattr(module, "select", external)
    result = traverse_graph(
        context(), ["treasury-liquidity"], ["governedBy"], ["Policy"]
    )
    assert result.outcome == "no_match"
    assert "secret-policy" not in str(
        result.model_dump()
    ) and "Secret Policy" not in str(result.model_dump())


def test_queries_are_server_bounded_and_do_not_construct_the_estate(monkeypatch):
    import app.knowledge.graph as module

    original = module.select
    queries = []

    def observe(ctx, body):
        queries.append(body)
        return original(ctx, body)

    monkeypatch.setattr(module, "select", observe)
    ctx = context()
    traverse_graph(
        ctx,
        ["treasury-liquidity"],
        ["governedBy", "supportedBy"],
        ["Policy", "EvidenceSection"],
    )
    assert all(
        "SELECT" in q and "LIMIT 51" in q and "CONSTRUCT" not in q for q in queries
    )
    assert len(ctx.graph_nodes) <= 50 and len(ctx.graph_edges) <= 100
