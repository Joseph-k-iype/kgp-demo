"""Bounded SQL metadata shortlist merged with versioned content candidates."""

import time
from collections import defaultdict
from app.auth import narrow_scope
from app.catalog.service import all_records, unpack
from app.db import query as sql
from app.knowledge.contracts import ToolContext
from app.knowledge.retrieval import search_evidence
from app.discovery.contracts import DiscoveryQuery, DiscoveryItem, DiscoveryPage


def search_discovery(scope, request):
    request = DiscoveryQuery.model_validate(request)
    scope = narrow_scope(scope, request.domain_id)
    predicates = ["kind IN ('asset','product')", "domain_id=ANY(:domains)"]
    params = {"domains": scope.domain_ids}
    for n, term in enumerate(request.q.lower().split()):
        key = "term" + str(n)
        params[key] = term
        predicates.append(
            "strpos(lower(COALESCE(payload->>'name','') || ' ' || COALESCE(payload->>'description','') || ' ' || COALESCE((SELECT string_agg(t,' ') FROM jsonb_array_elements_text(COALESCE(payload->'tags','[]'::jsonb)) t),'')),:"
            + key
            + ")>0"
        )
    metadata = [
        unpack(row)
        for row in sql(
            "SELECT * FROM records WHERE "
            + " AND ".join(predicates)
            + " ORDER BY lower(payload->>'name'),id LIMIT 100",
            params,
        )
    ]
    ctx = ToolContext(
        scope=scope, domain_id=request.domain_id, deadline=time.time() + 30
    )
    hits = search_evidence(
        ctx, request.q, kinds=["document", "structured", "metadata"], strategy="hybrid"
    ).items
    ids = list(dict.fromkeys(e["asset_id"] for e in hits))[:40]
    assets = (
        {
            r["id"]: unpack(r)
            for r in sql(
                "SELECT * FROM records WHERE kind='asset' AND id=ANY(:ids) AND domain_id=ANY(:domains)",
                {"ids": ids, "domains": scope.domain_ids},
            )
        }
        if ids
        else {}
    )
    product_ids = list(
        {id for a in assets.values() for id in a.get("product_ids", [])}
    )[:100]
    products = (
        {
            r["id"]: unpack(r)
            for r in sql(
                "SELECT * FROM records WHERE kind='product' AND id=ANY(:ids) AND domain_id=ANY(:domains)",
                {"ids": product_ids, "domains": scope.domain_ids},
            )
        }
        if product_ids
        else {}
    )
    records = {r["id"]: r for r in metadata}
    records.update(assets)
    records.update(products)
    source_ids = list(
        {a.get("source_id") for a in records.values() if a.get("source_id")}
    )
    sources = (
        {
            r["id"]: unpack(r)
            for r in sql(
                "SELECT * FROM records WHERE kind='source' AND id=ANY(:ids) AND domain_id=ANY(:domains)",
                {"ids": source_ids, "domains": scope.domain_ids},
            )
        }
        if source_ids
        else {}
    )
    metadata_rank = [r["id"] for r in metadata]
    evidence_rank = []
    excerpts = {}
    for hit in hits:
        asset = assets.get(hit["asset_id"])
        if not asset:
            continue
        if asset["id"] not in excerpts:
            excerpts[asset["id"]] = hit
            evidence_rank.append(asset["id"])
        for id in asset.get("product_ids", []):
            if id in products and id not in evidence_rank:
                evidence_rank.append(id)
            if id in products:
                excerpts.setdefault(id, hit)

    def kind(item):
        return (
            "product"
            if item["kind"] == "product"
            else "document"
            if item.get("type") == "Document"
            else "data"
        )

    scores = defaultdict(float)
    for ranking in [metadata_rank, evidence_rank]:
        ranking = [
            id
            for id in ranking
            if request.type == "all" or kind(records[id]) == request.type
        ]
        for rank, id in enumerate(ranking):
            scores[id] += 1 / (60 + rank)
    results = []
    for id in sorted(scores, key=lambda id: (-scores[id], id))[:100]:
        item = records[id]
        product = item["kind"] == "product"
        evidence = excerpts.get(id)
        source = sources.get(item.get("source_id"), {})
        title = item["name"]
        if evidence and not product and evidence["content_kind"] == "document":
            title = evidence["text"].splitlines()[0].lstrip("# ")
        results.append(
            DiscoveryItem(
                id=id,
                kind=kind(item),
                title=title,
                excerpt=evidence["text"][:420]
                if evidence
                else item.get("description", ""),
                domain_id=item["domain_id"],
                source_type="Knowledge product"
                if product
                else source.get("type", item.get("type", "Metadata")),
                asset_id=None if product else id,
                product_id=id if product else None,
                evidence_id=evidence["id"] if evidence else None,
                steward=item.get("steward") or item.get("owner"),
                quality=item.get("quality"),
                source_ref=evidence["source_ref"] if evidence else None,
                content_handle={
                    "kind": "product" if product else "asset",
                    "id": id,
                    "locator": evidence["source_ref"]["locator"] if evidence else None,
                    "version": evidence["source_ref"]["version"] if evidence else None,
                },
                content_kind=evidence["content_kind"] if evidence else None,
                score=round(scores[id], 6),
            )
        )
    if request.sort == "name":
        results.sort(key=lambda item: (item.title.casefold(), item.id))
    start = (request.page - 1) * request.page_size
    page = results[start : start + request.page_size]
    return DiscoveryPage(
        items=page,
        returned_count=len(page),
        has_more=start + len(page) < len(results),
        page=request.page,
        page_size=request.page_size,
        query=request.q,
        domain_id=request.domain_id,
    )
