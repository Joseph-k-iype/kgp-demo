import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import resolve_scope
from app.db import query

client = TestClient(app)
HEADERS = {"Authorization": "Bearer atlas-session-admin"}


def test_document_opens_to_actual_passage_and_separate_context_without_search_run():
    before = query("SELECT count(*) AS n FROM search_runs")[0]["n"]
    response = client.get(
        "/content/document-section/finance-asset-1",
        params={"locator": "controls"},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["content_type"] == "document"
    assert "reconcile liquidity positions daily" in page["text"]
    assert "Treasury Liquidity Monitoring Policy" in page["title"]
    assert page["source_refs"][0]["locator"] == "controls"
    assert page["context"]["record"]["id"] == "finance-asset-1"
    assert query("SELECT count(*) AS n FROM search_runs")[0]["n"] == before


def test_dataset_content_returns_actual_filtered_row_and_cursor_pagination():
    first = client.get(
        "/content/asset/finance-asset-0", params={"limit": 3}, headers=HEADERS
    )
    assert first.status_code == 200, first.text
    a = first.json()
    assert a["content_type"] == "dataset" and len(a["rows"]) == 3 and a["has_more"]
    assert a["rows"][0]["values"]["liquidity_usd"] == 12500000
    b = client.get(
        "/content/asset/finance-asset-0",
        params={"limit": 3, "cursor": a["cursor"]},
        headers=HEADERS,
    ).json()
    assert not {r["locator"] for r in a["rows"]} & {r["locator"] for r in b["rows"]}
    exact = client.get(
        "/content/record/finance-asset-0",
        params={"locator": "finance-asset-0-row-0"},
        headers=HEADERS,
    ).json()
    assert (
        len(exact["rows"]) == 1
        and exact["rows"][0]["values"]["position_id"] == "FIN-100"
    )


def test_product_primary_content_and_definition_are_real_sources():
    response = client.get("/products/finance-product-0/content", headers=HEADERS)
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["manifest"]["sources"] and page["manifest"]["primary"]
    assert page["content_type"] in ["document", "dataset"]
    assert page["text"] or page["rows"]
    definition = client.get("/content/definition/Policy", headers=HEADERS)
    assert definition.status_code == 200, definition.text
    assert definition.json()["content_type"] == "definition"
    assert definition.json()["facts"] and "Policy" in str(definition.json()["facts"])


def test_stale_citation_is_labeled_current_source_not_silently_same_snapshot():
    page = client.get(
        "/content/document-section/finance-asset-1",
        params={"locator": "controls", "version": "old-version"},
        headers=HEADERS,
    )
    assert page.status_code == 200, page.text
    assert (
        page.json()["freshness"] == "changed"
        and page.json()["requested_version"] == "old-version"
    )
    assert page.json()["source_refs"][0]["version"] != "old-version"


def test_content_access_and_handles_are_validated_without_nested_leaks():
    legal = {"Authorization": "Bearer atlas-session-legal"}
    denied = client.get("/content/asset/finance-asset-1", headers=legal)
    assert denied.status_code == 404
    assert "reconcile liquidity positions daily" not in denied.text
    assert (
        client.get("/content/shell/finance-asset-1", headers=HEADERS).status_code == 422
    )
    assert (
        client.get(
            "/content/asset/finance-asset-0", params={"limit": 101}, headers=HEADERS
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/content/asset/finance-asset-0",
            params={"cursor": "foreign-invalid-cursor"},
            headers=HEADERS,
        ).status_code
        == 422
    )


def test_read_content_tool_returns_real_fragments_and_separate_context():
    from app.knowledge.contracts import ToolContext, ReadContentAction
    from app.knowledge.tools import execute_read
    from app.agent.verification import verify_claims, SupportedClaim, ClaimCitation
    from app.knowledge.contracts import EvidenceFragment

    ctx = ToolContext(scope=resolve_scope("admin"), deadline=time.time() + 30)
    document = execute_read(ctx, ReadContentAction(kind="asset", id="finance-asset-1"))
    assert document.content["context"]["record"]["id"] == "finance-asset-1"
    assert any(
        "reconcile liquidity positions daily" in e["text"] for e in document.items
    )
    definition = execute_read(ctx, ReadContentAction(kind="definition", id="Policy"))
    item = definition.items[0]
    e = EvidenceFragment(
        **{k: v for k, v in item.items() if k in EvidenceFragment.model_fields},
        domain_id=item["source_ref"]["domain_id"],
    )
    assert definition.content["facts"] and e.content_kind == "definition"
    report = verify_claims(
        ctx,
        [
            SupportedClaim(
                text=e.text, citations=[ClaimCitation(evidence_id=e.id, quote=e.text)]
            )
        ],
        [e],
    )
    assert report.supported
    row = execute_read(
        ctx, ReadContentAction(kind="record", id="finance-asset-0-row-0")
    )
    assert len(row.items) == 1 and row.items[0]["values"]["position_id"] == "FIN-100"


def test_cursor_cannot_cross_asset_or_persona():
    a = client.get(
        "/content/asset/finance-asset-0", params={"limit": 1}, headers=HEADERS
    ).json()
    cross = client.get(
        "/content/asset/finance-asset-4",
        params={"cursor": a["cursor"]},
        headers=HEADERS,
    )
    assert cross.status_code == 422
    other = client.get(
        "/content/asset/finance-asset-0",
        params={"cursor": a["cursor"]},
        headers={"Authorization": "Bearer atlas-session-analyst"},
    )
    assert other.status_code == 422


def test_entity_opens_its_source_and_explicit_definition_keeps_rdf_facts():
    source = client.get("/content/record/TL-POL-001", headers=HEADERS)
    assert source.status_code == 200, source.text
    assert (
        source.json()["content_type"] == "document"
        and "reconcile liquidity positions daily" in source.json()["text"]
    )
    rdf = client.get("/content/definition/TL-POL-001", headers=HEADERS)
    assert rdf.status_code == 200, rdf.text
    assert rdf.json()["content_type"] == "definition" and rdf.json()["facts"]


def test_product_does_not_accept_an_unrelated_preferred_source():
    result = client.get(
        "/products/finance-product-0/content",
        params={"preferred_asset_id": "legal-asset-1"},
        headers=HEADERS,
    )
    assert result.status_code == 404


def test_document_version_race_closes_object_without_serving_mislabeled_text(
    monkeypatch,
):
    from app.knowledge.sources import iter_document_sections
    from app.knowledge.contracts import SourceRef
    from fastapi import HTTPException
    import app.knowledge.sources as sources

    class Response:
        headers = {"x-amz-meta-sha256": "new-version", "content-type": "text/plain"}
        closed = False

        def stream(self, amt):
            yield b"# Changed source\n"

        def close(self):
            self.closed = True

        def release_conn(self):
            pass

    response = Response()

    class Store:
        def get_object(self, *a):
            return response

    monkeypatch.setattr(
        sources,
        "source_info",
        lambda *a: SourceRef(
            asset_id="finance-asset-1",
            domain_id="finance",
            version="old-version",
            locator="document",
        ),
    )
    monkeypatch.setattr(sources, "client", lambda: Store())
    with pytest.raises(HTTPException) as e:
        list(iter_document_sections(resolve_scope("admin"), "finance-asset-1"))
    assert e.value.status_code == 409 and response.closed


def test_unsupported_document_format_is_a_truthful_unavailable_content_page(
    monkeypatch,
):
    from fastapi import HTTPException
    import app.knowledge.content as content

    monkeypatch.setattr(
        content,
        "iter_document_sections",
        lambda *a: (_ for _ in ()).throw(
            HTTPException(
                415, "A text reader is not available for this document format"
            )
        ),
    )
    result = client.get("/content/asset/finance-asset-1", headers=HEADERS)
    assert result.status_code == 200, result.text
    assert result.json()["content_type"] == "unavailable" and not result.json()["text"]
    assert "format" in result.json()["detail"]


def test_catalog_pagination_and_product_context_do_not_materialize_the_estate(
    monkeypatch,
):
    import app.catalog.service as catalog

    monkeypatch.setattr(
        catalog,
        "all_records",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("No full estate scan for catalog/details")
        ),
    )
    listed = client.get(
        "/catalog",
        params={"kind": "asset", "domain_id": "finance", "page_size": 2},
        headers=HEADERS,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 2 and listed.json()["total"] > 2
    detail = client.get("/products/finance-product-0", headers=HEADERS)
    assert detail.status_code == 200, detail.text
    assert detail.json()["assets"]


def test_direct_source_content_has_current_source_backed_relationship_paths():
    page = client.get("/content/asset/finance-asset-1", headers=HEADERS)
    assert page.status_code == 200, page.text
    assert any(
        e["predicate"] == "governedBy" and e["target"] == "TL-POL-001"
        for p in page.json()["paths"]
        for e in p["edges"]
    )


def test_cited_snapshot_is_reauthorized_and_labeled_when_source_version_changed():
    import json, uuid

    id = uuid.uuid4().hex
    source = {
        "asset_id": "finance-asset-1",
        "domain_id": "finance",
        "version": "old-version",
        "locator": "controls",
    }
    run = {
        "run_id": id,
        "person_id": "admin",
        "scope_version": resolve_scope("admin").scope_version,
        "status": "completed",
        "query": "Treasury controls",
        "mode": "extractive",
        "created_at": time.time(),
        "events": [],
        "statements": [],
        "gaps": [],
        "graph": {},
        "evidence": [
            {
                "id": "previous-clause",
                "asset_id": "finance-asset-1",
                "text": "Former clause snapshot",
                "source_ref": source,
            }
        ],
    }
    query(
        "INSERT INTO search_runs(id,person_id,payload) VALUES(:id,'admin',CAST(:p AS jsonb)) RETURNING id",
        {"id": id, "p": json.dumps(run)},
    )
    try:
        params = {
            "locator": "controls",
            "version": "old-version",
            "run_id": id,
            "evidence_id": "previous-clause",
        }
        page = client.get(
            "/content/document-section/finance-asset-1", params=params, headers=HEADERS
        )
        assert page.status_code == 200, page.text
        assert page.json()["freshness"] == "changed"
        assert page.json()["cited_snapshot"]["text"] == "Former clause snapshot"
        assert "reconcile liquidity positions daily" in page.json()["text"]
        denied = client.get(
            "/content/document-section/finance-asset-1",
            params=params,
            headers={"Authorization": "Bearer atlas-session-analyst"},
        )
        assert denied.status_code == 404
        assert "Former clause snapshot" not in denied.text
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_run_evidence_endpoint_supports_nonindex_citations_with_authorization():
    import json, uuid

    id = uuid.uuid4().hex
    item = {
        "id": "finance-asset-1:controls",
        "asset_id": "finance-asset-1",
        "domain_id": "finance",
        "text": "Recorded exact clause",
        "source_ref": {
            "asset_id": "finance-asset-1",
            "domain_id": "finance",
            "version": "recorded-version",
            "locator": "controls",
        },
    }
    run = {
        "run_id": id,
        "person_id": "admin",
        "scope_version": resolve_scope("admin").scope_version,
        "status": "completed",
        "query": "Treasury",
        "mode": "extractive",
        "created_at": time.time(),
        "events": [],
        "evidence": [item],
    }
    query(
        "INSERT INTO search_runs(id,person_id,payload) VALUES(:id,'admin',CAST(:p AS jsonb)) RETURNING id",
        {"id": id, "p": json.dumps(run)},
    )
    try:
        response = client.get(
            "/evidence/finance-asset-1:controls", params={"run_id": id}, headers=HEADERS
        )
        assert response.status_code == 200, response.text
        assert response.json()["text"] == "Recorded exact clause"
        denied = client.get(
            "/evidence/finance-asset-1:controls",
            params={"run_id": id},
            headers={"Authorization": "Bearer atlas-session-analyst"},
        )
        assert denied.status_code == 404
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_product_query_match_preserves_the_selected_source_passage():
    from app.knowledge.content import open_content
    from app.knowledge.contracts import ToolContext, ContentHandle

    page = open_content(
        ToolContext(scope=resolve_scope("admin"), deadline=time.time() + 30),
        ContentHandle(kind="product", id="finance-product-0", locator="controls"),
        preferred_asset_id="finance-asset-1",
    )
    assert page.manifest.primary.id == "finance-asset-1"
    assert page.source_refs and page.source_refs[0].locator == "controls"
    assert page.sections[0]["locator"] == "controls"
    assert "reconcile liquidity positions daily" in page.text
