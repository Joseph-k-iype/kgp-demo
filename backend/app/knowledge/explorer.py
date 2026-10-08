"""Scoped RDF display neighborhoods queried at the server, with bounded frontiers."""

import time
from datetime import date
from fastapi import HTTPException
from app.db import query
from app.ontology.service import I, K, CLASSES, RELATIONS
from app.knowledge.graph import select, iri
from app.knowledge.contracts import ToolContext, SourceRef
from app.knowledge.runtime import guard
from app.knowledge.sources import source_ref_is_current

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PROOF_RELATIONS = {
    "governedBy",
    "supportedBy",
    "recordedIn",
    "partyTo",
    "requiresContract",
    "measures",
    "representsEntity",
    "partOf",
}


def neighborhood(scope, root="Counterparty", depth=1, limit=50):
    if not 1 <= depth <= 3 or not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid graph bounds")
    ctx = ToolContext(scope=scope, deadline=time.time() + 30)
    limit = min(limit, 50)
    schema = set(CLASSES) | set(RELATIONS)
    root_uri = str(K[root]) if root in schema else iri(root)[1:-1]
    stored = {}

    def load(ids):
        if not ids:
            return
        for r in query(
            "SELECT id,kind,domain_id,payload FROM records WHERE id=ANY(:ids) AND (domain_id IS NULL OR domain_id=ANY(:domains))",
            {"ids": list(ids), "domains": guard(ctx).domain_ids},
        ):
            stored[r["id"]] = r

    if root not in schema:
        load({root})
        if root not in stored:
            raise HTTPException(404, "Graph root not found in your scope")

    def permitted(uri):
        if uri.startswith(str(K)):
            return uri.removeprefix(str(K)) in schema
        return uri.startswith(str(I)) and uri.removeprefix(str(I)) in stored

    def node(uri):
        id = uri.removeprefix(str(K)).removeprefix(str(I))
        record = stored.get(id)
        return {
            "id": id,
            "iri": uri,
            "name": record["payload"].get("name", id) if record else id,
            "kind": record["payload"].get("entity_type", record["kind"].title())
            if record
            else "Concept",
            "domain_id": record["domain_id"] if record else None,
            "source_type": record["payload"].get("type") if record else None,
            "status": record["payload"].get("status") if record else None,
            "content_handle": {
                "kind": "definition" if not record else "record",
                "id": id,
            },
        }

    nodes = {root_uri: node(root_uri)}
    frontier = {root_uri}
    edges = {}
    truncated = False
    freshness = {}
    predicates = " ".join(K[p].n3() for p in RELATIONS) + " <" + RDF + "type>"
    domains = " ".join(iri(id) for id in guard(ctx).domain_ids)
    for level in range(depth):
        if not frontier:
            break
        values = " ".join("<" + uri + ">" for uri in sorted(frontier))
        rows = select(
            ctx,
            f'''SELECT DISTINCT ?s ?p ?o ?source ?version ?locator ?from ?until WHERE {{ GRAPH <https://atlas.example/graphs/instances> {{
        VALUES ?p {{ {predicates} }}
        {{ VALUES ?s {{ {values} }} ?s ?p ?o }} UNION {{ VALUES ?o {{ {values} }} ?s ?p ?o }}
        FILTER(isIRI(?o) && ?s != ?o)
        FILTER(STRSTARTS(STR(?s),"{K}") || EXISTS {{ ?s <{K.belongsToDomain}> ?sd . VALUES ?sd {{ {domains} }} }})
        FILTER(STRSTARTS(STR(?o),"{K}") || EXISTS {{ ?o <{K.belongsToDomain}> ?od . VALUES ?od {{ {domains} }} }})
        OPTIONAL {{ ?a a <{K.GraphAssertion}>; <{RDF}subject> ?s; <{RDF}predicate> ?p; <{RDF}object> ?o; <{K.sourceAsset}> ?source; <{K.sourceVersion}> ?version; <{K.sourceLocator}> ?locator.
        OPTIONAL {{ ?a <{K.valid_from}> ?from }} OPTIONAL {{ ?a <{K.valid_to}> ?until }} }}
        }} }} ORDER BY (?p != <{K.relatedTo}>) STR(?s) STR(?o) LIMIT 101''',
        )
        if len(rows) > 100:
            truncated = True
        ids = {
            term["value"].removeprefix(str(I))
            for r in rows
            for key, term in r.items()
            if key in ["s", "o", "source"] and term["value"].startswith(str(I))
        }
        load(ids)
        next_front = set()
        for r in rows[:100]:
            s, o = r["s"]["value"], r["o"]["value"]
            if not permitted(s) or not permitted(o):
                continue
            predicate = r["p"]["value"]
            label = (
                predicate.removeprefix(str(K))
                if predicate.startswith(str(K))
                else "type"
            )
            ref = None
            if label in PROOF_RELATIONS:
                if "source" not in r:
                    continue
                source = r["source"]["value"].removeprefix(str(I))
                asset = stored.get(source)
                if not asset or asset["kind"] != "asset":
                    continue
                start = date.fromisoformat(r["from"]["value"]) if "from" in r else None
                end = date.fromisoformat(r["until"]["value"]) if "until" in r else None
                if start and ctx.as_of < start or end and ctx.as_of > end:
                    continue
                ref = SourceRef(
                    asset_id=source,
                    domain_id=asset["domain_id"],
                    version=r["version"]["value"],
                    locator=r["locator"]["value"],
                )
                key = (source, ref.version, ref.locator)
                if key not in freshness:
                    freshness[key] = source_ref_is_current(guard(ctx), ref)
                if not freshness[key]:
                    continue
            needed = {s, o} - nodes.keys()
            if len(nodes) + len(needed) > limit or len(edges) >= 100:
                truncated = True
                continue
            for uri in needed:
                nodes[uri] = node(uri)
            next_front.update(needed)
            key = (s, predicate, o)
            edges[key] = {
                "source": nodes[s]["id"],
                "target": nodes[o]["id"],
                "label": label,
                "asserted": True,
                "source_ref": ref.model_dump(mode="json") if ref else None,
            }
        frontier = next_front
    guard(ctx)
    return {
        "nodes": sorted(nodes.values(), key=lambda n: (n["id"] != root, n["name"])),
        "edges": list(edges.values()),
        "root": root,
        "truncated": truncated,
        "limits": {"nodes": 50, "edges": 100, "depth": 3},
    }
