from app.ontology.service import (
    sync_ontology,
    explore_ontology,
    validate_ontology,
    resolve_concepts,
)
from app.auth import resolve_scope


def test_rdf_paths_scope_and_validation():
    sync_ontology()
    scope = resolve_scope("admin")
    graph = explore_ontology(scope, "Counterparty", depth=2, limit=50)
    assert any(n["id"] == "risk-asset-0" for n in graph["nodes"])
    assert graph["edges"]
    assert len(explore_ontology(scope, "Counterparty", depth=2, limit=5)["nodes"]) <= 5
    assert validate_ontology()
    scoped = explore_ontology(
        resolve_scope("legal"), "Counterparty", depth=2, limit=100
    )
    assert not any(n["id"].startswith("risk-asset") for n in scoped["nodes"])
    assert resolve_concepts(scope, ["counterparty"]) == ["Counterparty"]


def test_small_neighborhood_preserves_business_concept_paths():
    g = explore_ontology(resolve_scope("admin"), "Counterparty", depth=1, limit=13)
    ids = {n["id"] for n in g["nodes"]}
    assert {"Counterparty", "Exposure", "Contract"} <= ids


def test_explorer_is_server_bounded_and_never_constructs_entire_estate(monkeypatch):
    import app.ontology.service as ontology

    monkeypatch.setattr(
        ontology,
        "rdf_graph",
        lambda *a: (_ for _ in ()).throw(
            AssertionError("Ontology explorer cannot load full estate")
        ),
    )
    result = ontology.explore_ontology(
        resolve_scope("admin"), "treasury-liquidity", depth=2, limit=30
    )
    assert result["nodes"] and len(result["nodes"]) <= 30
    assert any(e["label"] == "governedBy" for e in result["edges"])


def test_bounded_explorer_every_returned_node_is_connected_to_requested_root():
    g = explore_ontology(
        resolve_scope("admin"), "treasury-liquidity", depth=1, limit=30
    )
    reached = {"treasury-liquidity"}
    while True:
        extra = {
            node
            for edge in g["edges"]
            if edge["source"] in reached or edge["target"] in reached
            for node in [edge["source"], edge["target"]]
        }
        if extra <= reached:
            break
        reached.update(extra)
    assert {n["id"] for n in g["nodes"]} <= reached
    assert {"TL-POL-001", "TF-POL-002"} <= {n["id"] for n in g["nodes"]}
    assert "CP-1000" not in {n["id"] for n in g["nodes"]}
