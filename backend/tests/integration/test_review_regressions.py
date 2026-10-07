import time
from types import SimpleNamespace
import pytest
from app.auth import resolve_scope
from app.catalog.service import get_record
from app.db import query
from app.contracts import SearchRequest


def test_extraction_failure_marks_asset_failed(monkeypatch):
    from app.retrieval import service

    scope = resolve_scope("admin")
    id = "risk-asset-1"
    before = get_record(scope, id)["indexing_state"]
    monkeypatch.setattr(
        service,
        "extract_evidence",
        lambda *a: (_ for _ in ()).throw(RuntimeError("Storage unavailable")),
    )
    try:
        with pytest.raises(RuntimeError):
            service.index_assets([id])
        assert get_record(scope, id)["indexing_state"] == "failed"
    finally:
        query(
            "UPDATE records SET payload=jsonb_set(payload,'{indexing_state}',CAST(:state AS jsonb)) WHERE id=:id RETURNING id",
            {"id": id, "state": '"' + before + '"'},
        )


def test_cancellation_between_initial_read_and_start_is_terminal(monkeypatch):
    from app.agent import service

    scope = resolve_scope("admin")
    monkeypatch.setattr(service, "executor", SimpleNamespace(submit=lambda *a: None))
    run = service.start_search(
        scope, SearchRequest(query="counterparty", mode="extractive")
    )
    original = service.raw_run
    cancelled = False

    def read(id):
        nonlocal cancelled
        r = original(id)
        if not cancelled:
            cancelled = True
            service.cancel_search(scope, id)
        return r

    class FakeGraph:
        def invoke(self, *a, **k):
            return {
                "statements": [],
                "evidence": [],
                "retrieval_passes": 1,
                "tool_calls": 1,
            }

    monkeypatch.setattr(service, "raw_run", read)
    monkeypatch.setattr(service, "build_graph", lambda *a: FakeGraph())
    service.execute_run(run["run_id"])
    assert original(run["run_id"])["status"] == "cancelled"


def test_expiration_during_validation_cannot_complete(monkeypatch):
    from app.agent import graph

    clock = [time.time()]
    monkeypatch.setattr(graph, "time", SimpleNamespace(time=lambda: clock[0]))
    evidence = {
        "id": "risk-asset-0:rows-0",
        "asset_id": "risk-asset-0",
        "text": "Synthetic exposure evidence",
        "provenance": {"type": "structured"},
    }
    monkeypatch.setattr(graph, "retrieve", lambda *a, **k: [evidence])
    expansions = [0]

    def expand(*a, **k):
        expansions[0] += 1
        if expansions[0] == 2:
            clock[0] += 91
        return [evidence]

    monkeypatch.setattr(graph, "expand_evidence", expand)
    scope = resolve_scope("admin")
    with pytest.raises(TimeoutError):
        graph.build_graph().invoke(
            {
                "run_id": "deadline-test",
                "person_id": "admin",
                "scope_version": scope.scope_version,
                "query": "exposure",
                "mode": "extractive",
                "started": clock[0],
                "evidence": [],
            }
        )
