"""Read-only source tools shared by agent/API/MCP; no model-owned SQL or identity."""

import json, re
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from sqlalchemy import select, cast, Numeric, Date, func, String
from app.db import engine
from app.catalog.models import rows
from app.catalog.service import get_record
from app.storage.objects import preview_object
from app.fixtures import business_data
from app.knowledge.runtime import guard, version
from app.knowledge.contracts import (
    ToolContext,
    ToolResult,
    SourceRef,
    QueryDatasetAction,
    ReadDocumentAction,
    TraverseGraphAction,
    ResolveEntitiesAction,
    SearchEvidenceAction,
    ReadContentAction,
)
from app.knowledge.graph import resolve_entities, traverse_graph


def available_tools():
    return [
        "resolve_entities",
        "traverse_graph",
        "read_document",
        "query_dataset",
        "search_evidence",
        "read_content",
    ]


def read_document(ctx, call):
    scope = guard(ctx)
    asset = get_record(scope, call.asset_id, "asset")
    if asset["type"] != "Document":
        raise HTTPException(422, "This asset is not a document")
    from app.knowledge.sources import iter_document_sections

    iterator = iter_document_sections(scope, call.asset_id)
    selected = []
    more = False
    try:
        for section in iterator:
            guard(ctx)
            if (
                call.section_id
                and section["locator"] != call.section_id
                and section["section_id"] != call.section_id
            ):
                continue
            if selected:
                more = True
                break
            selected.append(section)
    finally:
        iterator.close()
    if not selected:
        return ToolResult(outcome="no_match", detail="Document section not found")
    section = selected[0]
    ref = SourceRef.model_validate(section["source_ref"])
    headers = []
    if call.section_id and section["locator"] != "overview":
        header_iterator = iter_document_sections(scope, call.asset_id)
        try:
            header = next(header_iterator, None)
            if (
                header
                and header["locator"] == "overview"
                and header["source_ref"]["version"] == ref.version
            ):
                headers.append(header)
        finally:
            header_iterator.close()
    return ToolResult(
        items=[
            {
                "id": call.asset_id + ":" + ref.locator,
                "asset_id": call.asset_id,
                "title": section["title"],
                "source_ref": ref.model_dump(mode="json"),
                "text": section["text"],
                "locator": ref.locator,
                "start": section["start"],
                "end": section["end"],
            }
        ]
        + [
            {
                "id": call.asset_id + ":" + h["locator"],
                "asset_id": call.asset_id,
                "title": h["title"],
                "text": h["text"],
                "locator": h["locator"],
                "source_ref": h["source_ref"],
                "start": h["start"],
                "end": h["end"],
            }
            for h in headers
        ],
        source_refs=[ref]
        + [SourceRef.model_validate(h["source_ref"]) for h in headers],
        truncated=more,
    )


def query_dataset(ctx, call):
    scope = guard(ctx)
    q = call.query
    asset = get_record(scope, q.asset_id, "asset")
    if asset["type"] not in ["Table", "Data product"]:
        raise HTTPException(422, "This asset is not a dataset")
    # Managed schema, never inferred from arbitrary model input; source migrations update this registration.
    sample = business_data({"id": q.asset_id, "domain_id": asset["domain_id"]})[0]
    schema = {name: type(value) for name, value in sample.items()}
    fields = q.select or list(schema)
    requested = (
        fields
        + [f.field for f in q.filters]
        + ([q.aggregate.field] if q.aggregate and q.aggregate.field else [])
    )
    if any(field not in schema for field in requested):
        raise HTTPException(422, "Unknown dataset field")

    def column(field):
        value = rows.c.payload[field].astext
        return (
            cast(value, Numeric)
            if schema[field] in [int, float]
            else cast(value, Date)
            if field.endswith("_date") or field == "as_of"
            else value
        )

    predicates = [rows.c.asset_id == q.asset_id]
    for f in q.filters:
        col = column(f.field)

        def typed(value):
            if value is None:
                return None
            try:
                if schema[f.field] in [int, float]:
                    numeric = Decimal(str(value))
                    if not numeric.is_finite():
                        raise ValueError("Non-finite number")
                    return numeric
                if f.field.endswith("_date") or f.field == "as_of":
                    return date.fromisoformat(value)
                if not isinstance(value, str):
                    raise ValueError("Expected text")
                return value
            except (ValueError, TypeError, InvalidOperation):
                raise HTTPException(422, "Invalid typed dataset filter") from None

        value = (
            [typed(v) for v in f.value]
            if f.op == "in" and isinstance(f.value, list)
            else typed(f.value)
        )
        if f.op == "in":
            if not isinstance(value, list) or not 1 <= len(value) <= 50:
                raise HTTPException(422, "Invalid membership filter")
            predicates.append(col.in_(value))
        else:
            if isinstance(value, (dict, list)):
                raise HTTPException(422, "Invalid filter value")
            predicates.append(
                {
                    "eq": lambda: col == value,
                    "ne": lambda: col != value,
                    "gt": lambda: col > value,
                    "gte": lambda: col >= value,
                    "lt": lambda: col < value,
                    "lte": lambda: col <= value,
                }[f.op]()
            )
    if q.aggregate:
        a = q.aggregate
        if a.operation != "count" and (
            not a.field or schema[a.field] not in [int, float]
        ):
            raise HTTPException(422, "Aggregate requires a numeric field")
        unit = (
            "USD"
            if a.field and a.field.endswith("_usd")
            else "percent"
            if a.field and a.field.endswith("_percent")
            else "count"
            if a.operation == "count"
            else "units"
        )
        aggregate = (
            func.count()
            if a.operation == "count"
            else getattr(func, a.operation)(column(a.field))
        )
        statement = select(
            aggregate.label("value"), func.count().label("row_count")
        ).where(*predicates)
        with engine.begin() as conn:
            result = dict(conn.execute(statement).mappings().one())
        value = result["value"]
        if isinstance(value, Decimal):
            value = (
                int(value) if value == value.to_integral_value() else format(value, "f")
            )
        values = {a.operation: value, "unit": unit, "row_count": result["row_count"]}
        ref = SourceRef(
            asset_id=q.asset_id,
            version=version({"query": q.model_dump(mode="json"), "values": values}),
            domain_id=asset["domain_id"],
            locator="aggregate:" + version(q.model_dump(mode="json")),
        )
        return ToolResult(
            outcome="ok" if result["row_count"] else "no_match",
            items=[
                {
                    "asset_id": q.asset_id,
                    "title": asset["name"],
                    "values": values,
                    "operation": q.model_dump(mode="json"),
                }
            ],
            source_refs=[ref],
        )
    if q.cursor:
        predicates.append(rows.c.id > q.cursor)
    statement = (
        select(rows.c.id, rows.c.payload)
        .where(*predicates)
        .order_by(rows.c.id)
        .limit(q.limit + 1)
    )
    with engine.begin() as conn:
        results = list(conn.execute(statement).mappings())
    has_more = len(results) > q.limit
    selected = results[: q.limit]
    refs = []
    items = []
    for r in selected:
        ref = SourceRef(
            asset_id=q.asset_id,
            version=version(r["payload"]),
            domain_id=asset["domain_id"],
            locator=r["id"],
        )
        refs.append(ref)
        items.append(
            {
                "id": r["id"],
                "asset_id": q.asset_id,
                "title": asset["name"],
                "values": {f: r["payload"].get(f) for f in fields},
                "locator": r["id"],
            }
        )
    return ToolResult(
        outcome="ok" if items else "no_match",
        items=items,
        source_refs=refs,
        cursor=selected[-1]["id"] if has_more else None,
        has_more=has_more,
    )


def execute_read(ctx: ToolContext, call) -> ToolResult:
    guard(ctx)
    if ctx.tool_calls >= ctx.max_tool_calls:
        raise TimeoutError("Search tool limit exceeded")
    ctx.tool_calls += 1
    if isinstance(call, ResolveEntitiesAction):
        resolution = resolve_entities(ctx, call.query)
        result = ToolResult(
            outcome=resolution.outcome,
            items=[c.model_dump() for c in resolution.candidates],
            truncated=resolution.truncated,
        )
    elif isinstance(call, TraverseGraphAction):
        result = traverse_graph(
            ctx, call.roots, call.predicates, call.target_kinds, call.depth
        )
    elif isinstance(call, ReadDocumentAction):
        result = read_document(ctx, call)
    elif isinstance(call, QueryDatasetAction):
        result = query_dataset(ctx, call)
    elif isinstance(call, SearchEvidenceAction):
        from app.knowledge.retrieval import search_evidence

        result = search_evidence(
            ctx, call.query, call.asset_ids, call.kinds, call.strategy
        )
    elif isinstance(call, ReadContentAction):
        from app.knowledge.content import open_content

        page = open_content(ctx, {"kind": call.kind, "id": call.id}, cursor=call.cursor)
        fragments = []
        if page.content_type == "document":
            for section, ref in zip(page.sections, page.source_refs):
                fragments.append(
                    {
                        "id": ref.asset_id + ":" + ref.locator,
                        "asset_id": ref.asset_id,
                        "text": section["text"],
                        "content_kind": "document",
                        "source_ref": ref.model_dump(mode="json"),
                        "title": page.title,
                    }
                )
        elif page.content_type == "dataset":
            for row in page.rows:
                ref = row["source_ref"]
                fragments.append(
                    {
                        "id": ref["asset_id"] + ":" + row["locator"],
                        "asset_id": ref["asset_id"],
                        "text": json.dumps(row["values"]),
                        "values": row["values"],
                        "title": page.title,
                        "content_kind": "structured",
                        "source_ref": ref,
                    }
                )
        elif page.content_type == "definition" and page.text:
            ref = page.source_refs[0]
            fragments.append(
                {
                    "id": ref.asset_id + ":rdf",
                    "asset_id": ref.asset_id,
                    "text": page.text[:1600],
                    "content_kind": "definition",
                    "title": page.title,
                    "source_ref": ref.model_dump(mode="json"),
                }
            )
        result = ToolResult(
            content=page.model_dump(mode="json"),
            items=fragments,
            source_refs=page.source_refs,
            paths=page.paths,
            cursor=page.cursor,
            has_more=page.has_more,
            truncated=page.truncated,
        )
    else:
        raise HTTPException(422, "Tool is not available")
    guard(ctx)
    if (
        len(json.dumps(result.model_dump(mode="json")).encode())
        > ctx.max_response_bytes
    ):
        raise HTTPException(413, "Source response exceeded the configured limit")
    return result
