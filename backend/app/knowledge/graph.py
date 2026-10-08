"""Bounded graph source routing. Fuseki filters before any graph is materialized."""

import json, re
from collections import deque
from datetime import date
import httpx
from rdflib import Literal
from fastapi import HTTPException
from app.config import settings
from app.db import query
from app.ontology.service import I, K
from app.knowledge.runtime import guard
from app.knowledge.contracts import (
    ToolContext,
    EntityCandidate,
    EntityResolution,
    ToolResult,
    SourceRef,
)

PREDICATES = {
    "governedBy",
    "supportedBy",
    "recordedIn",
    "partOf",
    "representsEntity",
    "measures",
    "partyTo",
    "requiresContract",
    "usesAsset",
    "sourcedFrom",
    "hasGap",
}


def iri(id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}", id):
        raise HTTPException(422, "Invalid graph identifier")
    return I[id].n3()


def domain_values(ctx):
    return " ".join(iri(id) for id in guard(ctx).domain_ids)


def select(ctx, body):
    guard(ctx)
    with httpx.stream(
        "POST",
        settings().fuseki_url + "/query",
        data={"query": body},
        headers={"Accept": "application/sparql-results+json"},
        timeout=min(10, max(0.1, ctx.deadline - __import__("time").time())),
    ) as response:
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > ctx.max_response_bytes:
                raise HTTPException(413, "Graph response exceeded the configured limit")
            chunks.append(chunk)
    guard(ctx)
    return json.loads(b"".join(chunks))["results"]["bindings"]


def scoped_ids(ctx, ids):
    if not ids:
        return set()
    scope = guard(ctx)
    return {
        r["id"]
        for r in query(
            "SELECT id FROM records WHERE id=ANY(:ids) AND domain_id=ANY(:domains)",
            {"ids": list(ids), "domains": scope.domain_ids},
        )
    }


def resolve_entities(ctx: ToolContext, query_text: str) -> EntityResolution:
    words = re.findall(r"[\w-]+", query_text.lower())
    stop = {
        "which",
        "what",
        "does",
        "govern",
        "governs",
        "the",
        "a",
        "an",
        "of",
        "is",
        "are",
        "applies",
        "apply",
        "to",
        "and",
        "show",
        "current",
        "policies",
        "policy",
    }
    anchors = [w for w in words if w not in stop][:8]
    parameters = {"domains": guard(ctx).domain_ids}
    conditions = []
    for index, word in enumerate(anchors):
        parameters["word" + str(index)] = "%" + word + "%"
        conditions.append(
            f"(lower(payload->>'name') LIKE :word{index} OR lower(payload->>'aliases') LIKE :word{index})"
        )
    condition = (
        " OR ".join(conditions) if conditions else "payload->>'entity_type'='Policy'"
    )
    candidates_sql = query(
        "SELECT id FROM records WHERE kind='entity' AND domain_id=ANY(:domains) AND ("
        + condition
        + ") ORDER BY id LIMIT 80",
        parameters,
    )
    if not candidates_sql:
        return EntityResolution(outcome="no_match", candidates=[])
    values = " ".join(iri(r["id"]) for r in candidates_sql)
    rows = select(
        ctx,
        f"""SELECT DISTINCT ?node ?label ?type ?domain ?alias WHERE {{ GRAPH <https://atlas.example/graphs/instances> {{
      VALUES ?domain {{ {domain_values(ctx)} }} VALUES ?node {{ {values} }}
      ?node <{K.belongsToDomain}> ?domain; <http://www.w3.org/2000/01/rdf-schema#label> ?label; a ?type.
      OPTIONAL {{ ?node <{K.alias}> ?alias }}
      FILTER(?type IN (<{K.BusinessEntity}>,<{K.Policy}>,<{K.Contract}>,<{K.Counterparty}>,<{K.LiquidityPosition}>))
      }} }} ORDER BY STR(?node) LIMIT 240""",
    )
    ids = {r["node"]["value"].removeprefix(str(I)) for r in rows}
    allowed = scoped_ids(ctx, ids)
    candidates = {}
    for r in rows:
        id = r["node"]["value"].removeprefix(str(I))
        if id not in allowed:
            continue
        alias = r.get("alias", {}).get("value", "")
        name = r["label"]["value"]
        normalized = query_text.lower()
        score = sum(len(w) + 2 for w in anchors if w in (name + " " + alias).lower())
        if alias and alias.lower() in normalized:
            score += len(alias) * 3
        if id.lower() in normalized:
            score += len(id) * 4
        entry = candidates.setdefault(
            id,
            EntityCandidate(
                id=id,
                name=name,
                domain_id=r["domain"]["value"].removeprefix(str(I)),
                entity_type=r["type"]["value"].removeprefix(str(K)),
                score=0,
                aliases=[],
            ),
        )
        entry.score = max(entry.score, float(score))
        if alias and alias not in entry.aliases:
            entry.aliases.append(alias)
    ranked = sorted(candidates.values(), key=lambda n: (-n.score, n.id))
    ambiguous = bool(ranked) and (
        not anchors or len(ranked) > 1 and ranked[0].score - ranked[1].score < 3
    )
    return EntityResolution(
        outcome="ambiguous" if ambiguous else "ok" if ranked else "no_match",
        candidates=ranked[:3],
        truncated=len(ranked) > 3,
    )


def traverse_graph(
    ctx: ToolContext,
    roots: list[str],
    predicates: list[str],
    target_kinds: list[str],
    depth: int = 3,
) -> ToolResult:
    guard(ctx)
    if (
        not 1 <= depth <= 3
        or len(roots) > 3
        or any(p not in PREDICATES for p in predicates)
    ):
        raise HTTPException(422, "Invalid graph bounds or predicates")
    if not set(roots) <= scoped_ids(ctx, roots):
        raise HTTPException(404, "Graph root not found in your scope")
    queue = deque((r, []) for r in roots)
    seen = set(roots)
    items = {}
    paths = []
    refs = []
    truncated = False
    stale = False
    freshness = {}
    selected = predicates or sorted(PREDICATES)
    while queue:
        root, path = queue.popleft()
        if len(path) >= depth:
            continue
        rows = select(
            ctx,
            f"""SELECT DISTINCT ?target ?label ?type ?domain ?predicate ?source ?version ?locator ?from ?until WHERE {{ GRAPH <https://atlas.example/graphs/instances> {{
          VALUES ?domain {{ {domain_values(ctx)} }} VALUES ?predicate {{ {" ".join(K[p].n3() for p in selected)} }}
          {iri(root)} ?predicate ?target . ?target <{K.belongsToDomain}> ?domain; <http://www.w3.org/2000/01/rdf-schema#label> ?label; a ?type.
          ?assertion a <{K.GraphAssertion}>; <http://www.w3.org/1999/02/22-rdf-syntax-ns#subject> {iri(root)}; <http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate> ?predicate; <http://www.w3.org/1999/02/22-rdf-syntax-ns#object> ?target;
          <{K.sourceAsset}> ?source; <{K.sourceVersion}> ?version; <{K.sourceLocator}> ?locator.
          OPTIONAL {{ ?assertion <{K.valid_from}> ?from }} OPTIONAL {{ ?assertion <{K.valid_to}> ?until }}
          }} }} ORDER BY STR(?target) LIMIT 51""",
        )
        allids = {r["target"]["value"].removeprefix(str(I)) for r in rows} | {
            r["source"]["value"].removeprefix(str(I)) for r in rows
        }
        allowed = scoped_ids(ctx, allids)
        source_domains = {
            r["id"]: r["domain_id"]
            for r in query(
                "SELECT id,domain_id FROM records WHERE id=ANY(:ids) AND domain_id=ANY(:domains)",
                {"ids": list(allowed), "domains": guard(ctx).domain_ids},
            )
        }
        for r in rows:
            target = r["target"]["value"].removeprefix(str(I))
            asset = r["source"]["value"].removeprefix(str(I))
            predicate = r["predicate"]["value"].removeprefix(str(K))
            if target not in allowed or asset not in allowed:
                continue
            if r.get("from") and date.fromisoformat(r["from"]["value"]) > ctx.as_of:
                continue
            if r.get("until") and date.fromisoformat(r["until"]["value"]) < ctx.as_of:
                continue
            edgekey = root + "|" + predicate + "|" + target
            if (
                len(ctx.graph_nodes | {root, target}) > 50
                or len(ctx.graph_edges | {edgekey}) > 100
            ):
                truncated = True
                continue
            ctx.graph_nodes.update([root, target])
            ctx.graph_edges.add(edgekey)
            ref = SourceRef(
                asset_id=asset,
                version=r["version"]["value"],
                locator=r["locator"]["value"],
                domain_id=source_domains[asset],
            )
            from app.knowledge.sources import source_ref_is_current

            key = (ref.asset_id, ref.version, ref.locator)
            if key not in freshness:
                freshness[key] = source_ref_is_current(guard(ctx), ref)
            if not freshness[key]:
                stale = True
                continue
            edge = {
                "source": root,
                "predicate": predicate,
                "target": target,
                "source_ref": ref.model_dump(mode="json"),
            }
            nextpath = path + [edge]
            typ = r["type"]["value"].removeprefix(str(K))
            if not target_kinds or typ in target_kinds:
                items[target] = {
                    "id": target,
                    "name": r["label"]["value"],
                    "entity_type": typ,
                    "domain_id": r["domain"]["value"].removeprefix(str(I)),
                }
                if len(paths) < 20:
                    paths.append({"edges": nextpath})
                else:
                    truncated = True
                if ref not in refs:
                    refs.append(ref)
            if target not in seen:
                seen.add(target)
                queue.append((target, nextpath))
    guard(ctx)
    return ToolResult(
        outcome="ok" if items else "stale" if stale else "no_match",
        items=list(items.values()),
        source_refs=refs,
        paths=paths,
        truncated=truncated,
        detail="Some graph assertions are stale" if stale else None,
    )
