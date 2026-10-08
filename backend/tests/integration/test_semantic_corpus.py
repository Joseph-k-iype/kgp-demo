from datetime import date
from rdflib import URIRef
from app.auth import resolve_scope
from app.seed import seed_demo
from app.db import query
from app.storage.objects import preview_object
from app.ontology.service import rdf_graph, K, I, sync_ontology
from app.knowledge.corpus import load_semantic_manifest


def test_real_named_policies_and_versioned_graph_paths():
    seed_demo()
    sync_ontology()
    scope = resolve_scope("admin")
    graph = rdf_graph(scope)
    clauses = preview_object(scope, "finance-asset-1")["text"]
    assert "TL-POL-001" in clauses and "daily" in clauses
    assert "TF-POL-002" in preview_object(scope, "finance-asset-5")["text"]
    assert "Superseded" in preview_object(scope, "finance-asset-9")["text"]
    assert "Treasury" not in preview_object(scope, "people-asset-1")["text"]
    assert (I["treasury-liquidity"], K.governedBy, I["TL-POL-001"]) in graph
    assert (
        I["TL-POL-001"],
        K.supportedBy,
        I["finance-asset-1-section-controls"],
    ) in graph
    assert (I["treasury-liquidity"], K.recordedIn, I["finance-asset-0"]) in graph
    assert not list(graph.triples((None, K.governedBy, K.Policy)))
    assertions = load_semantic_manifest()
    current = [
        a
        for a in assertions
        if a.subject == "treasury-liquidity"
        and a.predicate == "governedBy"
        and a.valid_on(date(2026, 9, 30))
    ]
    assert {a.object for a in current} == {"TL-POL-001", "TF-POL-002"}
    assert all(a.source_ref.version and a.source_ref.locator for a in assertions)


def test_semantic_seed_preserves_human_metadata_edits():
    original = query("SELECT payload FROM records WHERE id='finance-project'")[0][
        "payload"
    ]["budget"]
    try:
        query(
            "UPDATE records SET payload=jsonb_set(payload,'{budget}','432100') WHERE id='finance-project' RETURNING id"
        )
        seed_demo()
        assert (
            query("SELECT payload FROM records WHERE id='finance-project'")[0][
                "payload"
            ]["budget"]
            == 432100
        )
        assert (
            "finance-product-0"
            in query("SELECT payload FROM records WHERE id='finance-asset-5'")[0][
                "payload"
            ]["product_ids"]
        )
    finally:
        query(
            "UPDATE records SET payload=jsonb_set(payload,'{budget}',CAST(:v AS jsonb)) WHERE id='finance-project' RETURNING id",
            {"v": str(original)},
        )
