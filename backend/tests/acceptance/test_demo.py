import httpx
from app.auth import resolve_scope
from app.catalog.service import list_domains, get_product, get_asset, overview
from app.storage.objects import preview_object
from app.storage.structured import preview_rows
from app.ontology.service import explore_ontology
from app.retrieval.service import retrieve


def test_every_domain_connects_real_sources_to_knowledge():
    scope = resolve_scope("admin")
    domains = list_domains(scope)
    assert len(domains) == 11
    for domain in domains:
        d = domain["id"]
        product = get_product(scope, f"{d}-product-0")
        assert {a["type"] for a in product["assets"]} >= {"Table", "Document"}
        assert preview_rows(scope, f"{d}-asset-0")
        assert "Synthetic" in preview_object(scope, f"{d}-asset-1")["text"]
        assert explore_ontology(scope, f"{d}-asset-0")["edges"]
    summary = overview(scope)
    assert summary["counts"]["asset"] == 150
    assert summary["indexed"] == 150


def test_unknown_question_returns_no_evidence():
    assert retrieve(resolve_scope("admin"), "zzzxqvplk nnnn", []) == []
