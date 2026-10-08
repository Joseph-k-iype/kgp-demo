"""Bounded content candidate search with live provenance/version checks."""

import json
from collections import defaultdict
from fastapi import HTTPException
from app.db import query
from app.config import settings
from app.retrieval.index import ensure_content_index, request
from app.retrieval.embed import embed
from app.knowledge.runtime import guard, version
from app.knowledge.sources import source_info
from app.knowledge.contracts import ToolResult, EvidenceFragment, SourceRef


def search_evidence(ctx, query_text, asset_ids=None, kinds=None, strategy="hybrid"):
    scope = guard(ctx)
    if strategy not in ["keyword", "vector", "hybrid"] or not query_text.strip():
        raise HTTPException(422, "Invalid retrieval strategy")
    if asset_ids and len(asset_ids) > 50:
        raise HTTPException(422, "Too many source handles")
    if kinds and any(
        k not in ["document", "structured", "metadata", "definition"] for k in kinds
    ):
        raise HTTPException(422, "Invalid content kind")
    ensure_content_index()
    c = settings()
    filters = [{"terms": {"domain_id": scope.domain_ids}}]
    if asset_ids:
        filters.append({"terms": {"asset_id": asset_ids}})
    if kinds:
        filters.append({"terms": {"content_kind": kinds}})
    scores = defaultdict(float)
    documents = {}
    if strategy in ["keyword", "hybrid"]:
        hits = request(
            "POST",
            "/" + c.content_index_name + "/_search",
            {
                "size": 40,
                "query": {
                    "bool": {
                        "filter": filters,
                        "must": [
                            {"match": {"text": {"query": query_text, "operator": "or"}}}
                        ],
                    }
                },
            },
            timeout=max(0.1, min(15, ctx.deadline - __import__("time").time())),
        )["hits"]["hits"]
        for rank, h in enumerate(hits):
            documents[h["_id"]] = h["_source"]
            scores[h["_id"]] += 1 / (60 + rank)
    if strategy in ["vector", "hybrid"]:
        hits = request(
            "POST",
            "/" + c.content_index_name + "/_search",
            {
                "size": 40,
                "query": {
                    "script_score": {
                        "query": {"bool": {"filter": filters}},
                        "script": {
                            "source": "knn_score",
                            "lang": "knn",
                            "params": {
                                "field": "vector",
                                "query_value": embed([query_text])[0],
                                "space_type": "cosinesimil",
                            },
                        },
                    }
                },
            },
            timeout=max(0.1, min(15, ctx.deadline - __import__("time").time())),
        )["hits"]["hits"]
        for rank, h in enumerate(hits):
            if h["_score"] < 1.35:
                continue
            documents[h["_id"]] = h["_source"]
            scores[h["_id"]] += 1 / (60 + rank)
    guard(ctx)
    ids = list({d["asset_id"] for d in documents.values()})
    allowed = (
        {
            r["id"]: r["payload"]
            for r in query(
                "SELECT id,payload FROM records WHERE kind='asset' AND id=ANY(:ids) AND domain_id=ANY(:domains)",
                {"ids": ids, "domains": scope.domain_ids},
            )
        }
        if ids
        else {}
    )
    items = []
    refs = []
    seen = set()
    stale = False
    doc_versions = {}
    rowids = [
        d.get("provenance", {}).get("row_id")
        for d in documents.values()
        if d.get("content_kind") == "structured"
    ]
    rows = (
        {
            r["id"]: (r["asset_id"], r["payload"])
            for r in query(
                "SELECT id,asset_id,payload FROM business_rows WHERE id=ANY(:ids)",
                {"ids": [id for id in rowids if id]},
            )
        }
        if rowids
        else {}
    )
    for id in sorted(scores, key=lambda id: (-scores[id], id)):
        d = documents[id]
        asset = allowed.get(d["asset_id"])
        if not asset or asset.get("indexing_state") != "ready":
            continue
        if not d.get("source_ref"):
            stale = True
            continue
        ref = SourceRef.model_validate(d["source_ref"])
        if ref.domain_id not in scope.domain_ids or ref.asset_id != d["asset_id"]:
            continue
        key = (ref.asset_id, ref.locator)
        if key in seen:
            continue
        if d["content_kind"] == "document":
            if ref.asset_id not in doc_versions:
                doc_versions[ref.asset_id] = source_info(scope, ref.asset_id).version
            if doc_versions[ref.asset_id] != ref.version:
                stale = True
                continue
        elif d["content_kind"] == "structured":
            current = rows.get(ref.locator)
            if (
                not current
                or current[0] != ref.asset_id
                or version(current[1]) != ref.version
            ):
                stale = True
                continue
        seen.add(key)
        fragment = EvidenceFragment(
            id=id,
            asset_id=ref.asset_id,
            domain_id=ref.domain_id,
            content_kind=d["content_kind"],
            text=d["text"],
            source_title=d["text"].splitlines()[0].lstrip("# ")
            if d["content_kind"] == "document"
            else asset.get("name"),
            source_ref=ref,
            values=d.get("values"),
            provenance=d["provenance"],
        )
        items.append(fragment.model_dump(mode="json"))
        refs.append(ref)
        if len(items) == 20:
            break
    guard(ctx)
    return ToolResult(
        outcome="ok" if items else "stale" if stale else "no_match",
        items=items,
        source_refs=refs,
        truncated=len(scores) > len(items),
        detail="Some indexed content is stale" if stale else None,
    )
