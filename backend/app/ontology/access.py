"""Fail-closed RDF resource authorization shared by content and explicit export."""

from functools import lru_cache
from pathlib import Path
from rdflib import Graph, URIRef, BNode, Namespace

K = Namespace("https://atlas.example/ontology/")
I = Namespace("https://atlas.example/id/")


@lru_cache(maxsize=1)
def public_terms():
    terms = set()
    for file in ["vocabulary.ttl", "shapes.ttl"]:
        graph = Graph().parse(Path(__file__).with_name(file), format="turtle")
        for triple in graph:
            terms.update(
                str(term)
                for term in triple
                if isinstance(term, URIRef) and not str(term).startswith(str(I))
            )
    terms.update(
        str(K[name])
        for name in [
            "Entity",
            "alias",
            "asset_id",
            "section_id",
            "valid_from",
            "valid_to",
            "status",
            "sourceAsset",
            "sourceVersion",
            "sourceLocator",
            "origin",
            "delegatedTo",
            "storedIn",
            "hasPolicyClassification",
        ]
    )
    return frozenset(terms)


def record_iris(records):
    allowed = set()
    for record in records:
        if record.get("kind") == "role":
            continue
        allowed.add(str(I[record["id"]]))
        payload = record.get("payload", record)
        if isinstance(payload.get("iri"), str):
            allowed.add(payload["iri"])
    return allowed


def permitted(term, allowed):
    if isinstance(term, (URIRef, BNode)):
        return (
            str(term) in allowed
            or isinstance(term, URIRef)
            and str(term) in public_terms()
        )
    return True
