from types import SimpleNamespace
from rdflib import Graph, URIRef, Literal, RDF, RDFS
from app.ontology.service import K, I
from app.knowledge.contracts import ContentHandle


def test_definition_does_not_expose_unmapped_foreign_namespace_objects(monkeypatch):
    import app.knowledge.content as content

    private = "urn:private:finance:acquisition"
    scope = SimpleNamespace(domain_ids=["legal"])
    monkeypatch.setattr(content, "guard", lambda *a: scope)
    monkeypatch.setattr(content, "query", lambda *a, **kw: [])
    monkeypatch.setattr(
        content,
        "select",
        lambda *a, **kw: [
            {
                "predicate": {"value": str(K.relatedTo)},
                "object": {"type": "uri", "value": private},
            },
            {
                "predicate": {"value": str(RDF.type)},
                "object": {"type": "uri", "value": str(K.Policy)},
            },
        ],
    )
    page = content._definition(
        None,
        ContentHandle(kind="definition", id="legal-asset-0"),
        {"id": "legal-asset-0", "name": "Permitted asset", "domain_id": "legal"},
    )
    assert private not in page.model_dump_json()
    assert str(K.Policy) in page.model_dump_json()


def test_rdf_export_and_mcp_resource_deny_foreign_subjects_and_assertions(monkeypatch):
    import app.ontology.service as ontology
    import app.mcp.server as mcp

    scope = SimpleNamespace(domain_ids=["legal"])
    private = URIRef("urn:private:finance:acquisition")
    assertion = URIRef("urn:private:proof:1")
    full = Graph()
    full.add((private, RDFS.label, Literal("Confidential acquisition")))
    full.add((K.Policy, RDFS.label, Literal("Policy")))
    full.add((assertion, RDF.type, K.GraphAssertion))
    full.add((assertion, RDF.subject, private))
    full.add((assertion, RDF.object, I["legal-asset-0"]))
    full.add((assertion, K.sourceAsset, I["legal-asset-0"]))
    full.add((assertion, K.belongsToDomain, I["legal"]))
    monkeypatch.setattr(
        ontology.httpx,
        "get",
        lambda *a, **kw: SimpleNamespace(
            text=full.serialize(format="turtle"), raise_for_status=lambda: None
        ),
    )
    monkeypatch.setattr(ontology, "all_records", lambda *a, **kw: [])
    monkeypatch.setattr(mcp, "scope", lambda: scope)
    assert "Confidential acquisition" not in ontology.rdf_graph(scope).serialize(
        format="turtle"
    )
    resource = mcp.ontology_resource()
    assert "urn:private:" not in resource
    assert "Policy" in resource


def test_registered_foreign_iri_is_visible_only_through_authorized_record_mapping(
    monkeypatch,
):
    import app.ontology.service as ontology

    known = URIRef("urn:legal:contract:permitted")
    private = URIRef("urn:finance:contract:denied")
    full = Graph()
    full.add((known, RDFS.label, Literal("Permitted contract")))
    full.add((private, RDFS.label, Literal("Denied contract")))
    monkeypatch.setattr(
        ontology.httpx,
        "get",
        lambda *a, **kw: SimpleNamespace(
            text=full.serialize(format="turtle"), raise_for_status=lambda: None
        ),
    )
    monkeypatch.setattr(
        ontology,
        "all_records",
        lambda *a, **kw: [
            {"id": "legal-contract", "kind": "entity", "iri": str(known)}
        ],
    )
    exported = ontology.rdf_graph(SimpleNamespace(domain_ids=["legal"])).serialize(
        format="turtle"
    )
    assert "Permitted contract" in exported and "Denied contract" not in exported


def test_definition_truncation_does_not_count_withheld_resource_objects(monkeypatch):
    import app.knowledge.content as content

    scope = SimpleNamespace(domain_ids=["legal"])
    monkeypatch.setattr(content, "guard", lambda *a: scope)
    monkeypatch.setattr(content, "query", lambda *a, **kw: [])
    rows = [
        {
            "predicate": {"value": str(K.relatedTo)},
            "object": {"type": "uri", "value": "urn:private:" + str(i)},
        }
        for i in range(50)
    ]
    rows.append(
        {
            "predicate": {"value": str(RDF.type)},
            "object": {"type": "uri", "value": str(K.Policy)},
        }
    )
    monkeypatch.setattr(content, "select", lambda *a, **kw: rows)
    page = content._definition(
        None,
        ContentHandle(kind="definition", id="legal-asset-0"),
        {"id": "legal-asset-0", "name": "Permitted asset", "domain_id": "legal"},
    )
    assert not page.truncated
    assert len(page.facts) == 1
