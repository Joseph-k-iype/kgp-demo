import time
from app.agent.service import start_search, get_search, cancel_search
from app.auth import resolve_scope
from app.contracts import SearchRequest
from fastapi import HTTPException
import pytest


def await_run(scope, id):
    for _ in range(90):
        r = get_search(scope, id)
        if r["status"] not in ["pending", "running"]:
            return r
        time.sleep(0.5)
    raise AssertionError("search did not finish")


def test_extractive_run_has_real_citations_and_owner_scope():
    scope = resolve_scope("admin")
    run = start_search(
        scope,
        SearchRequest(query="counterparty exposure due diligence", mode="extractive"),
    )
    result = await_run(scope, run["run_id"])
    assert result["status"] == "completed", result
    assert result["statements"] and result["evidence"]
    assert all(s["evidence_ids"] for s in result["statements"])
    assert {"plan", "retrieve", "synthesize", "validate"} <= {
        e["stage"] for e in result["events"]
    }
    assert get_search(scope, run["run_id"])["statements"] == result["statements"]
    with pytest.raises(HTTPException):
        get_search(resolve_scope("legal"), run["run_id"])


def test_no_key_is_explicit(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings(), "openrouter_api_key", "")
    monkeypatch.setattr(settings(), "openai_api_key", "")
    scope = resolve_scope("admin")
    run = start_search(
        scope, SearchRequest(query="counterparty exposure", mode="openai")
    )
    r = await_run(scope, run["run_id"])
    assert r["status"] == "configuration_required"
    assert not r["statements"]


def test_scope_change_blocks_previous_run_evidence():
    from app.catalog.service import update_metadata, get_record

    admin = resolve_scope("admin")
    legal = resolve_scope("legal")
    run = start_search(
        legal, SearchRequest(query="contract obligations", mode="extractive")
    )
    await_run(legal, run["run_id"])
    role = get_record(admin, "role-legal")
    try:
        update_metadata(admin, "role", "role-legal", {"domain_ids": ["risk"]})
        with pytest.raises(HTTPException) as exc:
            get_search(resolve_scope("legal"), run["run_id"])
        assert exc.value.status_code == 409
    finally:
        update_metadata(admin, "role", "role-legal", {"domain_ids": role["domain_ids"]})


def test_cancellation_is_terminal():
    scope = resolve_scope("admin")
    run = start_search(
        scope, SearchRequest(query="counterparty exposure", mode="extractive")
    )
    cancel_search(scope, run["run_id"])
    assert get_search(scope, run["run_id"])["status"] == "cancelled"
    time.sleep(1)
    assert get_search(scope, run["run_id"])["status"] == "cancelled"


def test_completed_resume_does_not_repeat_generation():
    from app.agent.service import resume_search

    scope = resolve_scope("admin")
    run = start_search(
        scope, SearchRequest(query="counterparty exposure", mode="extractive")
    )
    complete = await_run(scope, run["run_id"])
    resumed = resume_search(scope, run["run_id"])
    assert resumed["statements"] == complete["statements"]
    assert resumed["events"] == complete["events"]
