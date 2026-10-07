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
