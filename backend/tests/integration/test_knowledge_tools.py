import time
import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from app.auth import resolve_scope
from app.knowledge.contracts import (
    ToolContext,
    DatasetQuery,
    QueryDatasetAction,
    ReadDocumentAction,
    TraverseGraphAction,
)
from app.knowledge.tools import execute_read, available_tools


def context(persona="admin", domain=None):
    return ToolContext(
        scope=resolve_scope(persona), deadline=time.time() + 30, domain_id=domain
    )


def test_approved_structured_filter_and_aggregation():
    call = QueryDatasetAction(
        query=DatasetQuery(
            asset_id="finance-asset-0",
            select=["position_id", "liquidity_usd", "currency", "as_of"],
            filters=[{"field": "position_id", "op": "eq", "value": "FIN-100"}],
        )
    )
    result = execute_read(context(), call)
    assert result.items[0]["values"]["liquidity_usd"] == 12500000
    assert result.items[0]["values"]["currency"] == "USD"
    assert result.source_refs[0].locator == "finance-asset-0-row-0"
    aggregate = execute_read(
        context(),
        QueryDatasetAction(
            query=DatasetQuery(
                asset_id="finance-asset-0",
                aggregate={"operation": "sum", "field": "liquidity_usd"},
                filters=[
                    {"field": "currency", "op": "eq", "value": "USD"},
                    {"field": "as_of", "op": "eq", "value": "2026-09-30"},
                ],
            )
        ),
    )
    assert aggregate.items[0]["values"]["sum"] == 32000000
    assert aggregate.items[0]["values"]["unit"] == "USD"


def test_invalid_fields_queries_and_predicates_are_not_executed():
    with pytest.raises(ValidationError):
        DatasetQuery(asset_id="finance-asset-0", sql="DROP TABLE records")
    with pytest.raises(HTTPException):
        execute_read(
            context(),
            QueryDatasetAction(
                query=DatasetQuery(asset_id="finance-asset-0", select=["password"])
            ),
        )
    with pytest.raises(HTTPException):
        execute_read(
            context(),
            TraverseGraphAction(
                roots=["treasury-liquidity"],
                predicates=["sameAs; DROP"],
                target_kinds=[],
            ),
        )
    with pytest.raises(HTTPException):
        execute_read(
            context("risk"),
            QueryDatasetAction(query=DatasetQuery(asset_id="finance-asset-0")),
        )


def test_actual_document_read_and_budget_scope_guards():
    ctx = context()
    result = execute_read(
        ctx, ReadDocumentAction(asset_id="finance-asset-1", section_id="controls")
    )
    assert "TL-POL-001" in str(result.items)
    assert "daily" in result.items[0]["text"]
    assert ctx.tool_calls == 1
    assert {
        "resolve_entities",
        "traverse_graph",
        "read_document",
        "query_dataset",
        "search_evidence",
        "read_content",
    } == set(available_tools())
    with pytest.raises(TimeoutError):
        execute_read(
            ToolContext(scope=resolve_scope("admin"), deadline=time.time() - 1),
            ReadDocumentAction(asset_id="finance-asset-1"),
        )


def test_source_pages_are_bounded_and_cursors_advance():
    first = execute_read(
        context(),
        QueryDatasetAction(query=DatasetQuery(asset_id="finance-asset-0", limit=1)),
    )
    assert first.has_more and len(first.items) == 1
    second = execute_read(
        context(),
        QueryDatasetAction(
            query=DatasetQuery(asset_id="finance-asset-0", limit=1, cursor=first.cursor)
        ),
    )
    assert second.items[0]["id"] != first.items[0]["id"]
    with pytest.raises(HTTPException):
        execute_read(
            context(),
            QueryDatasetAction(
                query=DatasetQuery(
                    asset_id="finance-asset-0",
                    filters=[{"field": "as_of", "value": "not-a-date"}],
                )
            ),
        )


def test_named_document_clause_also_returns_its_identifying_header_with_separate_locator():
    result = execute_read(
        context(), ReadDocumentAction(asset_id="finance-asset-5", section_id="controls")
    )
    assert result.items[0]["locator"] == "controls"
    header = next(item for item in result.items if item["locator"] == "overview")
    assert "TF-POL-002" in header["text"]
    assert header["source_ref"]["locator"] == "overview"
    assert result.items[0]["source_ref"]["locator"] == "controls"
