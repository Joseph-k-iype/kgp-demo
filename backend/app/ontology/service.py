from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, URIRef
from pyshacl import validate
import httpx
from fastapi import HTTPException
from app.config import settings
from app.db import query
from app.catalog.service import all_records

K = Namespace("https://atlas.example/ontology/")
I = Namespace("https://atlas.example/id/")
CONCEPTS = [
    "Counterparty",
    "Contract",
    "Obligation",
    "Service",
    "Exposure",
    "Policy",
    "Person",
    "Project",
    "Product",
    "DataElement",
]
CLASSES = [
    "Domain",
    "Subdomain",
    "KnowledgeProduct",
    "Asset",
    "StructuredAsset",
    "Document",
    "Source",
    "Gap",
    "Role",
    "BusinessEntity",
    "EvidenceSection",
    "LiquidityPosition",
    "GraphAssertion",
] + CONCEPTS
RELATIONS = {
    "belongsToDomain": ("Asset", "Domain"),
    "belongsToSubdomain": ("KnowledgeProduct", "Subdomain"),
    "usesAsset": ("KnowledgeProduct", "Asset"),
    "sourcedFrom": ("Asset", "Source"),
    "representsConcept": ("Asset", "DataElement"),
    "stewardedBy": ("Asset", "Person"),
    "deliversProduct": ("Project", "KnowledgeProduct"),
    "hasGap": ("KnowledgeProduct", "Gap"),
    "relatedTo": ("DataElement", "DataElement"),
    "governedBy": ("BusinessEntity", "Policy"),
    "hasPolicyClassification": ("Asset", "Policy"),
    "supportedBy": ("BusinessEntity", "EvidenceSection"),
    "recordedIn": ("BusinessEntity", "Asset"),
    "partOf": ("EvidenceSection", "Asset"),
    "representsEntity": ("KnowledgeProduct", "BusinessEntity"),
    "measures": ("BusinessEntity", "LiquidityPosition"),
    "partyTo": ("Counterparty", "Contract"),
    "requiresContract": ("Policy", "Contract"),
    "storedIn": ("Asset", "Source"),
    "delegatedTo": ("Domain", "Person"),
}


def sync_ontology():
    vocab = Graph()
    vocab.bind("atlas", K)
    for c in CLASSES:
        vocab.add((K[c], RDF.type, OWL.Class))
        vocab.add((K[c], RDFS.label, Literal(c)))
    for p, (d, r) in RELATIONS.items():
        vocab.add((K[p], RDF.type, OWL.ObjectProperty))
        vocab.add((K[p], RDFS.label, Literal(p)))
        vocab.add((K[p], RDFS.domain, K[d]))
        vocab.add((K[p], RDFS.range, K[r]))
    instances = Graph()
    instances.bind("atlas", K)
    instances.bind("id", I)
    for row in query("SELECT * FROM records ORDER BY id"):
        if row["kind"] == "role":
            continue
        p = row["payload"]
        node = I[row["id"]]
        kind = {"product": "KnowledgeProduct", "subdomain": "Subdomain"}.get(
            row["kind"], row["kind"].title()
        )
        instances.add((node, RDF.type, K[kind]))
        instances.add((node, RDFS.label, Literal(p.get("name", row["id"]))))
        if row["domain_id"]:
            instances.add((node, K.belongsToDomain, I[row["domain_id"]]))
        if p.get("steward") and row["id"] != "risk-asset-0":
            instances.add(
                (
                    node,
                    K.stewardedBy,
                    I["person-" + p["steward"].lower().replace(" ", "-")],
                )
            )
        for delegate in p.get("delegates", []):
            instances.add(
                (node, K.delegatedTo, I["person-" + delegate.lower().replace(" ", "-")])
            )
        if p.get("subdomain_id"):
            instances.add((node, K.belongsToSubdomain, I[p["subdomain_id"]]))
        if row["kind"] == "asset":
            instances.add(
                (
                    node,
                    RDF.type,
                    K.Document if p["type"] == "Document" else K.StructuredAsset,
                )
            )
            instances.add((node, K.sourcedFrom, I[p["source_id"]]))
            instances.add((node, K.storedIn, I[p["source_id"]]))
            instances.add((node, K.hasPolicyClassification, K.Policy))
            for product in p["product_ids"]:
                instances.add((I[product], K.usesAsset, node))
            for c in p["concepts"]:
                instances.add((node, K.representsConcept, K[c]))
        if row["kind"] == "project":
            instances.add((node, K.deliversProduct, I[p["product_id"]]))
        if row["kind"] == "gap":
            instances.add((I[p["product_id"]], K.hasGap, node))
    for a, b in [
        ("Counterparty", "Exposure"),
        ("Counterparty", "Contract"),
        ("Contract", "Obligation"),
        ("Exposure", "Policy"),
        ("Service", "Policy"),
    ]:
        instances.add((K[a], K.relatedTo, K[b]))
    from app.knowledge.corpus import semantic_manifest, load_semantic_manifest
    from rdflib.namespace import XSD

    for n in semantic_manifest()["nodes"]:
        node = I[n["id"]]
        instances.add((node, RDF.type, K[n["entity_type"]]))
        for alias in n.get("aliases", []):
            instances.add((node, K.alias, Literal(alias)))
        for key in ["asset_id", "section_id", "valid_from", "valid_to", "status"]:
            if n.get(key):
                instances.add((node, K[key], Literal(n[key])))
    for index, assertion in enumerate(load_semantic_manifest()):
        subject, predicate, target = (
            I[assertion.subject],
            K[assertion.predicate],
            I[assertion.object],
        )
        instances.add((subject, predicate, target))
        a = I["assertion-" + str(index)]
        instances.add((a, RDF.type, K.GraphAssertion))
        instances.add((a, RDF.subject, subject))
        instances.add((a, RDF.predicate, predicate))
        instances.add((a, RDF.object, target))
        instances.add((a, K.sourceAsset, I[assertion.source_ref.asset_id]))
        instances.add((a, K.sourceVersion, Literal(assertion.source_ref.version)))
        instances.add((a, K.sourceLocator, Literal(assertion.source_ref.locator)))
        instances.add((a, K.origin, Literal(assertion.origin)))
        instances.add((a, K.belongsToDomain, I[assertion.source_ref.domain_id]))
        for key in ["valid_from", "valid_to"]:
            value = getattr(assertion, key)
            if value:
                instances.add((a, K[key], Literal(value, datatype=XSD.date)))
    for name, graph in [("vocabulary", vocab), ("instances", instances)]:
        httpx.put(
            settings().fuseki_url + "/data",
            params={"graph": f"https://atlas.example/graphs/{name}"},
            content=graph.serialize(format="turtle"),
            headers={"Content-Type": "text/turtle"},
            timeout=30,
        ).raise_for_status()
    Path(__file__).with_name("vocabulary.ttl").write_text(
        vocab.serialize(format="turtle")
    )
    return {"triples": len(vocab) + len(instances)}


def rdf_graph(scope):
    r = httpx.get(
        settings().fuseki_url + "/query",
        params={"query": "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"},
        headers={"Accept": "text/turtle"},
        timeout=10,
    )
    r.raise_for_status()
    full = Graph().parse(data=r.text, format="turtle")
    from app.ontology.access import record_iris, permitted as resource_permitted
    from rdflib import BNode

    allowed = record_iris(all_records(scope))
    g = Graph()
    g.bind("atlas", K)
    g.bind("id", I)

    def permitted(term):
        return resource_permitted(term, allowed)

    # Reified assertions are visible only when every participating business/source node is visible.
    for assertion in full.subjects(RDF.type, K.GraphAssertion):
        participants = [
            full.value(assertion, RDF.subject),
            full.value(assertion, RDF.object),
            full.value(assertion, K.sourceAsset),
            full.value(assertion, K.belongsToDomain),
        ]
        if all(
            isinstance(term, (URIRef, BNode)) and permitted(term)
            for term in participants
        ):
            allowed.add(str(assertion))
    for s, p, o in full:
        if permitted(s) and permitted(p) and permitted(o):
            g.add((s, p, o))
    return g


def resolve_concepts(scope, labels):
    return [c for c in CONCEPTS if any(c.lower() in label.lower() for label in labels)]


def explore_ontology(scope, concept_id="Counterparty", depth=1, limit=50):
    from app.knowledge.explorer import neighborhood

    return neighborhood(scope, concept_id, depth, limit)


def validate_ontology(scope=None):
    if scope is None:
        from app.auth import resolve_scope

        scope = resolve_scope("admin")
    g = rdf_graph(scope)
    shape = Graph().parse(Path(__file__).with_name("shapes.ttl"), format="turtle")
    conforms, report, _ = validate(g, shacl_graph=shape)
    SH = Namespace("http://www.w3.org/ns/shacl#")
    findings = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        node = report.value(result, SH.focusNode)
        message = report.value(result, SH.resultMessage)
        findings.append(
            {
                "asset_id": str(node).replace(str(I), ""),
                "rule": "Required stewardship",
                "message": str(message),
                "severity": "Warning",
            }
        )
    return findings
