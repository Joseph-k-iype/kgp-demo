import json, hashlib
import httpx
from urllib.parse import quote
from collections import defaultdict
from fastapi import HTTPException
from app.config import settings
from app.db import query
from app.auth import resolve_scope
from app.catalog.service import all_records, get_record
from app.retrieval.extract import extract_evidence
from app.retrieval.embed import embed
from app.retrieval.index import request, ensure_index
from app.deadline import remaining_timeout


def index_assets(asset_ids):
    ensure_index()
    c = settings()
    scope = resolve_scope("admin")
    assets = all_records(scope, "asset")
    docs = []
    selected = []
    try:
        for a in assets:
            if asset_ids and a["id"] not in asset_ids:
                continue
            selected.append(a["id"])
            query(
                "UPDATE records SET payload=jsonb_set(payload,'{indexing_state}','\"pending\"') WHERE id=:id RETURNING id",
                {"id": a["id"]},
            )
            docs.extend(extract_evidence(scope, a))
        vectors = embed([d["text"] for d in docs])
        import httpx

        body = ""
        for d, v in zip(docs, vectors):
            d["vector"] = v
            d["content_hash"] = hashlib.sha256(d["text"].encode()).hexdigest()
            d["model"] = c.embedding_model
            body += (
                json.dumps({"index": {"_index": c.index_name, "_id": d["id"]}})
                + "\n"
                + json.dumps(d)
                + "\n"
            )
        for a in selected:
            request(
                "POST",
                "/" + c.index_name + "/_delete_by_query",
                {"query": {"term": {"asset_id": a}}},
            )
        r = httpx.post(
            c.opensearch_url + "/_bulk",
            content=body,
            headers={"Content-Type": "application/x-ndjson"},
            timeout=90,
        )
        r.raise_for_status()
        if r.json().get("errors"):
            raise RuntimeError("Bulk indexing failed")
        request("POST", "/" + c.index_name + "/_refresh")
        for a in selected:
            query(
                "UPDATE records SET payload=jsonb_set(payload,'{indexing_state}','\"ready\"') WHERE id=:id RETURNING id",
                {"id": a},
            )
        # Removed assets cannot remain searchable.
        request(
            "POST",
            "/" + c.index_name + "/_delete_by_query",
            {
                "query": {
                    "bool": {
                        "must_not": {"terms": {"asset_id": [a["id"] for a in assets]}}
                    }
                }
            },
        )
        return {
            "indexed_assets": len(selected),
            "evidence_chunks": len(docs),
            "model": c.embedding_model,
            "dimensions": 384,
        }
    except Exception:
        for a in selected:
            query(
                "UPDATE records SET payload=jsonb_set(payload,'{indexing_state}','\"failed\"') WHERE id=:id RETURNING id",
                {"id": a},
            )
        raise


def retrieve(scope, query_text, concept_ids, limit=10, deadline=None):
    if not 1 <= limit <= 30 or not query_text.strip():
        raise HTTPException(422, "Invalid retrieval request")
    ensure_index(timeout=remaining_timeout(deadline, 10))

    def search_request(method, path, body=None):
        return request(method, path, body, timeout=remaining_timeout(deadline))

    c = settings()
    allowed = [
        a["id"]
        for a in all_records(scope, "asset")
        if a.get("indexing_state") == "ready"
    ]
    if not allowed:
        return []
    filters = [
        {"terms": {"domain_id": scope.domain_ids}},
        {"terms": {"asset_id": allowed}},
    ]
    lexical = search_request(
        "POST",
        "/" + c.index_name + "/_search",
        {
            "size": 100,
            "query": {
                "bool": {
                    "filter": filters,
                    "must": [
                        {"match": {"text": {"query": query_text, "operator": "or"}}}
                    ],
                    "should": [{"terms": {"concept_iris": concept_ids}}],
                }
            },
        },
    )["hits"]["hits"]
    vector = embed([query_text])[0]
    semantic = search_request(
        "POST",
        "/" + c.index_name + "/_search",
        {
            "size": 100,
            "query": {
                "script_score": {
                    "query": {"bool": {"filter": filters}},
                    "script": {
                        "source": "knn_score",
                        "lang": "knn",
                        "params": {
                            "field": "vector",
                            "query_value": vector,
                            "space_type": "cosinesimil",
                        },
                    },
                }
            },
        },
    )["hits"]["hits"]
    # Exclude very weak matches instead of returning irrelevant answers.
    semantic = [h for h in semantic if h["_score"] >= 1.35]
    scores = defaultdict(float)
    sources = {}
    for hits in [lexical, semantic]:
        for rank, h in enumerate(hits):
            sources[h["_id"]] = h["_source"]
            scores[h["_id"]] += 1 / (60 + rank)
    ordered = sorted(scores, key=lambda id: scores[id], reverse=True)
    # Diversify sources so one table's near-identical rows do not consume all results.
    results = []
    per_asset = defaultdict(int)
    # Reserve the highest-ranked evidence of each source type, then fill by fused rank.
    seen_types = set()
    diversified = []
    for id in ordered:
        kind = sources[id]["provenance"]["type"]
        if kind not in seen_types:
            diversified.append(id)
            seen_types.add(kind)
    diversified += [id for id in ordered if id not in diversified]
    for id in diversified:
        d = sources[id]
        if per_asset[d["asset_id"]] >= 2:
            continue
        per_asset[d["asset_id"]] += 1
        d.pop("vector", None)
        d["score"] = round(scores[id], 5)
        results.append(d)
        if len(results) >= limit:
            break
    return results


def get_evidence(scope, evidence_id, deadline=None):
    asset_id = evidence_id.split(":")[0]
    a = get_record(scope, asset_id, "asset")
    if a.get("indexing_state") != "ready":
        raise HTTPException(409, "Evidence index is not current")
    try:
        d = request(
            "GET",
            "/" + settings().index_name + "/_doc/" + quote(evidence_id, safe=""),
            timeout=remaining_timeout(deadline),
        )["_source"]
    except TimeoutError:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, "Evidence not found")
        raise
    d.pop("vector", None)
    return d


def expand_evidence(scope, evidence, deadline=None):
    # Recheck the current asset scope/readiness once, then fetch bounded evidence
    # together. Serial per-item calls consume the agent's deadline unnecessarily.
    if not evidence:
        return []
    if len(evidence) > 30:
        raise HTTPException(422, "Too many evidence items")
    assets = {a["id"]: a for a in all_records(scope, "asset")}
    ids = [e["id"] for e in evidence]
    for id in ids:
        asset = assets.get(id.split(":")[0])
        if not asset:
            raise HTTPException(404, "Evidence not found")
        if asset.get("indexing_state") != "ready":
            raise HTTPException(409, "Evidence index is not current")
    response = request(
        "POST", "/" + settings().index_name + "/_mget", {"ids": ids},
        timeout=remaining_timeout(deadline),
    )
    docs = {d["_id"]: d for d in response["docs"]}
    result = []
    for id in ids:
        item = docs.get(id, {})
        doc = item.get("_source", {})
        if (not item.get("found") or doc.get("id") != id
            or doc.get("asset_id") != id.split(":")[0]
            or doc.get("domain_id") not in scope.domain_ids):
            raise HTTPException(404, "Evidence not found")
        doc.pop("vector", None)
        result.append(doc)
    return result
