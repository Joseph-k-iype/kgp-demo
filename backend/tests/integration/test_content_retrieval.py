import time
from app.auth import resolve_scope
from app.knowledge.contracts import ToolContext
from app.knowledge.retrieval import search_evidence
from app.knowledge.sources import iter_document_sections, source_info
from app.storage.objects import put_object, preview_object
from app.catalog.service import get_record


def ctx(domain="finance"):
    return ToolContext(
        scope=resolve_scope("admin"), domain_id=domain, deadline=time.time() + 60
    )


def test_treasury_document_retrieval_is_relevant_versioned_and_not_forced_people():
    from app.seed import seed_demo
    from app.retrieval.service import index_assets

    seed_demo()
    index_assets(["finance-asset-1", "finance-asset-5"])
    result = search_evidence(
        ctx(),
        "treasury liquidity policies",
        ["finance-asset-1", "finance-asset-5"],
        ["document"],
        "keyword",
    )
    assert result.items and all(item["domain_id"] == "finance" for item in result.items)
    assert any("TL-POL-001" in item["text"] for item in result.items)
    assert all(
        item["source_ref"]["version"] and item["source_ref"]["locator"]
        for item in result.items
    )
    assert len(
        {(item["asset_id"], item["source_ref"]["locator"]) for item in result.items}
    ) == len(result.items)


def test_full_document_sections_survive_preview_limit_and_versions_change():
    scope = resolve_scope("admin")
    asset = get_record(scope, "finance-asset-13", "asset")
    original = preview_object(scope, asset["id"])["text"]
    try:
        put_object(
            asset["object_key"],
            "# Long evidence\n"
            + ("ordinary content\n" * 18000)
            + "\n## Late requirement\nFunding approval requires sponsor SIGN-900.\n",
        )
        info = source_info(scope, asset["id"])
        sections = list(iter_document_sections(scope, asset["id"]))
        assert any("SIGN-900" in section["text"] for section in sections)
        assert preview_object(scope, asset["id"])["truncated"]
        old = info.version
        put_object(asset["object_key"], original)
        assert source_info(scope, asset["id"]).version != old
    finally:
        put_object(asset["object_key"], original)


def test_changed_document_invalidates_index_and_asserted_graph_proof():
    from app.knowledge.graph import traverse_graph

    scope = resolve_scope("admin")
    asset = get_record(scope, "finance-asset-5", "asset")
    original = preview_object(scope, asset["id"])["text"]
    try:
        put_object(
            asset["object_key"], original + "\nThis is a newly revised source.\n"
        )
        indexed = search_evidence(
            ctx(),
            "Treasury Funding Evidence Policy",
            ["finance-asset-5"],
            ["document"],
            "keyword",
        )
        assert indexed.outcome == "stale" and not indexed.items
        graph = traverse_graph(
            ctx(), ["treasury-liquidity"], ["governedBy"], ["Policy"]
        )
        assert "TF-POL-002" not in {item["id"] for item in graph.items}
        assert graph.detail and "stale" in graph.detail.lower()
    finally:
        put_object(asset["object_key"], original)


def test_keyword_strategy_does_not_run_vector_embedding(monkeypatch):
    import app.knowledge.retrieval as module

    monkeypatch.setattr(
        module,
        "embed",
        lambda *args: (_ for _ in ()).throw(AssertionError("Unexpected embedding")),
    )
    assert search_evidence(
        ctx(), "Treasury Liquidity", ["finance-asset-1"], ["document"], "keyword"
    ).items


def test_unicode_document_preview_does_not_split_a_codepoint():
    scope = resolve_scope("admin")
    asset = get_record(scope, "finance-asset-13", "asset")
    original = preview_object(scope, asset["id"])["text"]
    try:
        put_object(asset["object_key"], "a" + ("π" * 150000))
        preview = preview_object(scope, asset["id"])
        assert preview["truncated"] and preview["text"].startswith("aπ")
        assert "\ufffd" not in preview["text"]
    finally:
        put_object(asset["object_key"], original)


def test_incremental_projection_records_only_the_source_revision():
    from app.knowledge.graph import select

    result = select(
        ctx(),
        "SELECT ?revision WHERE { GRAPH <https://atlas.example/graphs/source/finance-asset-1> { <https://atlas.example/id/finance-asset-1> <https://atlas.example/ontology/sourceRevision> ?revision } } LIMIT 1",
    )
    assert (
        result[0]["revision"]["value"]
        == source_info(resolve_scope("admin"), "finance-asset-1").version
    )


def test_extraction_failure_preserves_previously_indexed_content(monkeypatch):
    import pytest
    from app.retrieval import service
    from app.retrieval.index import request
    from app.config import settings

    scope = resolve_scope("admin")
    asset = "finance-asset-1"
    original = service.extract_evidence
    service.index_assets([asset])
    before = request(
        "GET", "/" + settings().index_name + "/_doc/" + asset + ":chunk-0"
    )["_source"]["text"]
    monkeypatch.setattr(
        service,
        "extract_evidence",
        lambda *args: (_ for _ in ()).throw(RuntimeError("Transient read failure")),
    )
    try:
        with pytest.raises(RuntimeError):
            service.index_assets([asset])
        after = request(
            "GET", "/" + settings().index_name + "/_doc/" + asset + ":chunk-0"
        )["_source"]["text"]
        assert after == before
    finally:
        monkeypatch.setattr(service, "extract_evidence", original)
        service.index_assets([asset])
