"""Incremental per-asset RDF source projections; never promote a changed policy clause."""

import httpx
from rdflib import Graph, Literal, RDF
from app.config import settings
from app.db import query
from app.ontology.service import I, K
from app.knowledge.sources import source_info
from app.knowledge.runtime import version


def project_source(scope, asset, index_generation):
    if asset["type"] == "Document":
        revision = source_info(scope, asset["id"]).version
    else:
        # Generation hashes the indexed row versions; it does not claim a global SQL snapshot.
        revision = index_generation
    graph = Graph()
    node = I[asset["id"]]
    graph.add((node, RDF.type, K.Asset))
    graph.add((node, K.belongsToDomain, I[asset["domain_id"]]))
    graph.add((node, K.sourceRevision, Literal(revision)))
    response = httpx.put(
        settings().fuseki_url + "/data",
        params={"graph": "https://atlas.example/graphs/source/" + asset["id"]},
        content=graph.serialize(format="turtle"),
        headers={"Content-Type": "text/turtle"},
        timeout=10,
    )
    response.raise_for_status()
    query(
        "UPDATE records SET payload=jsonb_set(payload,'{source_revision}',to_jsonb(CAST(:revision AS text))) WHERE id=:id RETURNING id",
        {"id": asset["id"], "revision": revision},
    )
    return revision
