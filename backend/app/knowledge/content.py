"""Actual source content with separate catalog context and bounded readers."""

import base64, json
from fastapi import HTTPException
from app.db import query
from app.catalog.service import get_record, unpack
from app.knowledge.contracts import (
    ContentHandle,
    ContentPage,
    ProductContentManifest,
    ContentSource,
    SourceRef,
    QueryDatasetAction,
    ToolContext,
)
from app.knowledge.runtime import guard, version
from app.knowledge.sources import source_info, iter_document_sections
from app.knowledge.tools import query_dataset
from app.knowledge.graph import traverse_graph, select, iri
from app.ontology.service import K, I, CLASSES, RELATIONS


def _encode(ctx, handle, source_version, position):
    return base64.urlsafe_b64encode(
        json.dumps(
            {
                "id": handle.id,
                "kind": handle.kind,
                "version": source_version,
                "person": ctx.scope.person_id,
                "scope": ctx.scope.scope_version,
                "position": position,
            },
            separators=(",", ":"),
        ).encode()
    ).decode()


def _decode(ctx, handle, cursor, source_version=None):
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if (
            value["id"] != handle.id
            or value["kind"] != handle.kind
            or value["person"] != ctx.scope.person_id
            or value["scope"] != ctx.scope.scope_version
        ):
            raise ValueError()
        if source_version and value["version"] != source_version:
            raise HTTPException(
                409, "The source changed while paging. Open its current content."
            )
        return value["position"]
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise HTTPException(422, "Invalid content cursor") from None


def _context(scope, record):
    context = {"record": record}
    for name, key, kind in [
        ("domain", "domain_id", "domain"),
        ("source", "source_id", "source"),
    ]:
        if record.get(key):
            try:
                context[name] = get_record(scope, record[key], kind)
            except HTTPException as error:
                if error.status_code != 404:
                    raise
    return context


def product_manifest(ctx, id, preferred_asset_id=None):
    scope = guard(ctx)
    product = get_record(scope, id, "product")
    found = query(
        "SELECT * FROM records WHERE kind='asset' AND domain_id=ANY(:domains) AND payload->'product_ids' @> CAST(:product AS jsonb) ORDER BY id LIMIT 51",
        {"domains": scope.domain_ids, "product": json.dumps([id])},
    )
    assets = [unpack(row) for row in found[:50]]
    sources = [
        ContentSource(
            title=a["name"],
            source_type=a["type"],
            handle=ContentHandle(kind="asset", id=a["id"]),
        )
        for a in assets
    ]
    primary_id = preferred_asset_id or product.get("primary_asset_id")
    if preferred_asset_id and preferred_asset_id not in {a["id"] for a in assets}:
        raise HTTPException(
            404, "This source is not an accessible member of the product"
        )
    primary = next((s.handle for s in sources if s.handle.id == primary_id), None)
    if primary is None:
        primary = next(
            (
                s.handle
                for s in sources
                if s.source_type in ["Table", "Data product", "Document"]
            ),
            sources[0].handle if sources else None,
        )
    guard(ctx)
    return product, ProductContentManifest(
        product_id=id,
        title=product["name"],
        primary=primary,
        sources=sources,
        truncated=len(found) > 50,
    )


def _definition(ctx, handle, record=None):
    scope = guard(ctx)
    schema = handle.id in CLASSES or handle.id in RELATIONS
    subject = "<" + str(K[handle.id]) + ">" if schema else iri(handle.id)
    if not schema and record is None:
        record = get_record(scope, handle.id)
    statements = select(
        ctx,
        f"SELECT DISTINCT ?predicate ?object WHERE {{ GRAPH <https://atlas.example/graphs/{'vocabulary' if schema else 'instances'}> {{ {subject} ?predicate ?object . }} }} ORDER BY ?predicate ?object LIMIT 51",
    )
    ids = [
        row["object"]["value"].removeprefix(str(I))
        for row in statements
        if row["object"].get("type") == "uri"
        and row["object"]["value"].startswith(str(I))
    ]
    allowed = (
        {
            r["id"]
            for r in query(
                "SELECT id FROM records WHERE id=ANY(:ids) AND (domain_id IS NULL OR domain_id=ANY(:domains))",
                {"ids": ids, "domains": scope.domain_ids},
            )
        }
        if ids
        else set()
    )
    facts = []
    for row in statements[:50]:
        obj = row["object"]
        if (
            obj.get("type") == "uri"
            and obj["value"].startswith(str(I))
            and obj["value"].removeprefix(str(I)) not in allowed
        ):
            continue
        predicate = row["predicate"]["value"]
        facts.append(
            {
                "subject": subject[1:-1],
                "predicate": predicate,
                "label": predicate.rsplit("#", 1)[-1].rsplit("/", 1)[-1],
                "object": obj["value"],
                "object_type": obj["type"],
            }
        )
    title = handle.id if schema else record["name"]
    context = (
        {"definition_iri": subject[1:-1], "schema_definition": schema}
        if schema
        else _context(scope, record)
    )
    guard(ctx)
    ref = SourceRef(
        asset_id=handle.id,
        domain_id=record.get("domain_id") or "ontology" if record else "ontology",
        version=version(facts),
        locator="rdf",
    )
    return ContentPage(
        handle=handle,
        title=title,
        content_type="definition",
        facts=facts,
        text="\n".join(f["label"] + ": " + f["object"] for f in facts),
        source_refs=[ref],
        context=context,
        truncated=len(statements) > 50,
        requested_version=handle.version,
        freshness="changed"
        if handle.version and handle.version != version(facts)
        else "current",
    )


def _document(ctx, handle, asset, cursor, limit):
    scope = guard(ctx)
    current = source_info(scope, asset["id"])
    position = _decode(ctx, handle, cursor, current.version) if cursor else None
    if position is not None and (
        not isinstance(position, int) or not 0 <= position <= 1000000
    ):
        raise HTTPException(422, "Invalid document cursor position")
    iterator = iter_document_sections(scope, asset["id"])
    sections = []
    title = asset["name"]
    started = position is not None or handle.locator is None
    has_more = False
    next_position = None
    refs = []
    try:
        for n, section in enumerate(iterator):
            guard(ctx)
            if section["source_ref"]["version"] != current.version:
                raise HTTPException(
                    409, "The source changed during reading. Open its current content."
                )
            title = section["title"] or title
            if position is not None and n < position:
                continue
            if not started:
                if (
                    section["locator"] != handle.locator
                    and section["section_id"] != handle.locator
                ):
                    continue
                started = True
            if len(sections) == min(limit, 8):
                has_more = True
                next_position = n
                break
            sections.append(
                {
                    k: section[k]
                    for k in ["text", "locator", "section_id", "start", "end"]
                }
            )
            refs.append(SourceRef.model_validate(section["source_ref"]))
    finally:
        iterator.close()
    if handle.locator and not sections:
        raise HTTPException(404, "This passage is not present in the current source")
    guard(ctx)
    return ContentPage(
        handle=handle,
        title=title,
        content_type="document",
        text="\n\n".join(s["text"] for s in sections),
        sections=sections,
        source_refs=refs,
        context=_context(scope, asset),
        has_more=has_more,
        truncated=has_more,
        cursor=_encode(ctx, handle, current.version, next_position)
        if has_more
        else None,
        requested_version=handle.version,
        freshness="changed"
        if handle.version and handle.version != current.version
        else "current",
    )


def _dataset(ctx, handle, asset, cursor, limit):
    position = _decode(ctx, handle, cursor) if cursor else None
    if position is not None and (not isinstance(position, str) or len(position) > 181):
        raise HTTPException(422, "Invalid dataset cursor position")
    filters = (
        [{"field": "record_id", "op": "eq", "value": handle.locator}]
        if handle.locator
        else []
    )
    result = query_dataset(
        ctx,
        QueryDatasetAction(
            query={
                "asset_id": asset["id"],
                "filters": filters,
                "cursor": position,
                "limit": limit,
            }
        ),
    )
    rows = [
        {
            "locator": item["locator"],
            "values": item["values"],
            "source_ref": ref.model_dump(),
        }
        for item, ref in zip(result.items, result.source_refs)
    ]
    sample = rows[0]["values"] if rows else {}
    columns = [
        {
            "name": name,
            "type": type(value).__name__,
            "unit": "USD"
            if name.endswith("_usd")
            else "percent"
            if name.endswith("_percent")
            else None,
        }
        for name, value in sample.items()
    ]
    fingerprint = version([ref.model_dump() for ref in result.source_refs])
    guard(ctx)
    return ContentPage(
        handle=handle,
        title=asset["name"],
        content_type="dataset",
        rows=rows,
        columns=columns,
        source_refs=result.source_refs,
        context=_context(guard(ctx), asset),
        has_more=result.has_more,
        cursor=_encode(ctx, handle, fingerprint, result.cursor)
        if result.has_more
        else None,
        requested_version=handle.version,
        freshness="changed"
        if handle.version
        and not any(ref.version == handle.version for ref in result.source_refs)
        else "current",
    )


def _source_paths(ctx, asset_id):
    statements = select(
        ctx,
        f"SELECT DISTINCT ?subject WHERE {{ GRAPH <https://atlas.example/graphs/instances> {{ ?a <http://www.w3.org/1999/02/22-rdf-syntax-ns#subject> ?subject ; <{K.sourceAsset}> {iri(asset_id)} . }} }} LIMIT 9",
    )
    ids = [
        r["subject"]["value"].removeprefix(str(I))
        for r in statements
        if r["subject"]["value"].startswith(str(I))
    ]
    allowed = (
        [
            r["id"]
            for r in query(
                "SELECT id FROM records WHERE kind='entity' AND id=ANY(:ids) AND domain_id=ANY(:domains) ORDER BY id LIMIT 6",
                {"ids": ids, "domains": guard(ctx).domain_ids},
            )
        ]
        if ids
        else []
    )
    paths = []
    for offset in range(0, len(allowed), 3):
        result = traverse_graph(
            ctx,
            allowed[offset : offset + 3],
            [
                "governedBy",
                "supportedBy",
                "recordedIn",
                "partOf",
                "partyTo",
                "requiresContract",
            ],
            [],
            depth=2,
        )
        for path in result.paths:
            if (
                any(e["source_ref"]["asset_id"] == asset_id for e in path["edges"])
                and path not in paths
            ):
                paths.append(path)
    return paths[:20]


def open_content(ctx, handle, cursor=None, limit=20, preferred_asset_id=None):
    handle = ContentHandle.model_validate(handle)
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid content page size")
    scope = guard(ctx)
    if handle.kind == "product":
        product, manifest = product_manifest(ctx, handle.id, preferred_asset_id)
        if manifest.primary:
            page = open_content(ctx, manifest.primary, cursor, limit)
            page.manifest = manifest
            page.context = {**page.context, "product": product}
            page.handle = handle
        else:
            page = ContentPage(
                handle=handle,
                title=product["name"],
                content_type="unavailable",
                manifest=manifest,
                context={"product": product},
                detail="This product has no accessible source content",
            )
        return page
    if handle.kind == "definition" and (handle.id in CLASSES or handle.id in RELATIONS):
        return _definition(ctx, handle)
    if handle.kind == "record":
        rows = query(
            "SELECT asset_id FROM business_rows WHERE id=:id LIMIT 1", {"id": handle.id}
        )
        if rows:
            return open_content(
                ctx,
                handle.model_copy(
                    update={"id": rows[0]["asset_id"], "locator": handle.id}
                ),
                cursor,
                limit,
            )
    record = get_record(scope, handle.id)
    if handle.kind == "definition":
        return _definition(ctx, handle, record)
    if record["kind"] == "product":
        return open_content(
            ctx,
            handle.model_copy(update={"kind": "product"}),
            cursor,
            limit,
            preferred_asset_id,
        )
    if record["kind"] == "entity":
        routed = traverse_graph(
            ctx, [record["id"]], ["supportedBy", "recordedIn", "partOf"], [], depth=2
        )
        if routed.source_refs:
            ref = routed.source_refs[0]
            page = open_content(
                ctx,
                ContentHandle(
                    kind="asset",
                    id=ref.asset_id,
                    locator=ref.locator,
                    version=handle.version or ref.version,
                ),
                cursor,
                limit,
            )
            page.context = {**page.context, "entity": record}
            page.paths = routed.paths
            return page
        return _definition(ctx, handle, record)
    if record["kind"] != "asset":
        return _definition(ctx, handle, record)
    if handle.kind == "definition" or record["type"] == "Metadata":
        page = _definition(ctx, handle, record)
    elif record["type"] == "Document":
        try:
            page = _document(ctx, handle, record, cursor, limit)
        except HTTPException as error:
            if error.status_code != 415:
                raise
            page = ContentPage(
                handle=handle,
                title=record["name"],
                content_type="unavailable",
                context=_context(scope, record),
                detail=str(error.detail),
                requested_version=handle.version,
            )
    elif record["type"] in ["Table", "Data product"]:
        page = _dataset(ctx, handle, record, cursor, limit)
    else:
        page = ContentPage(
            handle=handle,
            title=record["name"],
            content_type="unavailable",
            context=_context(scope, record),
            detail="A content reader is not available for this source type",
        )
    if record["kind"] == "asset" and page.content_type != "unavailable":
        page.paths = _source_paths(ctx, record["id"])
    if handle.run_id and handle.evidence_id:
        from app.agent.service import get_search

        run = get_search(scope, handle.run_id)
        e = next((e for e in run["evidence"] if e["id"] == handle.evidence_id), None)
        if (
            e
            and e.get("source_ref", {}).get("asset_id") == handle.id
            and e["source_ref"].get("version") == handle.version
            and (not handle.locator or e["source_ref"].get("locator") == handle.locator)
        ):
            page.cited_snapshot = {
                "text": e["text"],
                "values": e.get("values"),
                "source_ref": e["source_ref"],
            }
    guard(ctx)
    return page


def run_evidence(scope, run_id, evidence_id):
    from app.agent.service import get_search
    import time

    run = get_search(scope, run_id)
    item = next((e for e in run["evidence"] if e["id"] == evidence_id), None)
    if not item:
        raise HTTPException(404, "Evidence not found in this run")
    ctx = ToolContext(scope=scope, deadline=time.time() + 30)
    ref = item.get("source_ref")
    if item.get("content_kind") == "definition":
        open_content(ctx, {"kind": "definition", "id": item["asset_id"]})
    else:
        asset = get_record(guard(ctx), item["asset_id"], "asset")
        if not item.get("content_kind"):
            item = {
                **item,
                "content_kind": "document"
                if asset["type"] == "Document"
                else "metadata"
                if asset["type"] == "Metadata"
                else "structured",
            }
    result = dict(item)
    result["recorded_snapshot"] = True
    result["freshness"] = "recorded"
    if ref:
        from app.agent.verification import fresh
        from app.knowledge.contracts import EvidenceFragment

        result["freshness"] = (
            "current"
            if fresh(ctx, EvidenceFragment.model_validate(item))
            else "changed"
        )
    guard(ctx)
    return result
