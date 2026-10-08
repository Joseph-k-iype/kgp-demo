import time, uuid
import pytest
from fastapi import HTTPException
from app.config import settings
from app.auth import resolve_scope
from app.contracts import SearchRequest
from app.agent import service
from app.agent.worker import claim_next, recover_expired
from app.db import query


def test_shared_intent_idempotency_and_single_worker_claim(monkeypatch):
    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    identity = uuid.uuid4().hex
    scope = resolve_scope("admin")
    request = SearchRequest(query="Which treasury policies apply?", intent_id=identity)
    first = service.start_search(scope, request)
    try:
        second = service.start_search(scope, request)
        assert first["run_id"] == second["run_id"]
        assert first["deadline"] - first["created_at"] == 120
        assert (
            claim_next("worker-one", run_id=first["run_id"])["run_id"]
            == first["run_id"]
        )
        assert claim_next("worker-two", run_id=first["run_id"]) is None
        with pytest.raises(HTTPException):
            service.start_search(
                scope, SearchRequest(query="Different query", intent_id=identity)
            )
    finally:
        service.cancel_search(scope, first["run_id"])


def test_uncertain_paid_call_is_not_replayed_after_lease_expiry(monkeypatch):
    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find policies", intent_id=uuid.uuid4().hex)
    )
    try:
        claim_next("dead-worker", run_id=run["run_id"])
        query(
            "UPDATE search_runs SET lease_until=:expiry,payload=jsonb_set(payload,'{model_inflight}','true') WHERE id=:id RETURNING id",
            {"expiry": time.time() - 1, "id": run["run_id"]},
        )
        recover_expired()
        current = service.get_search(scope, run["run_id"])
        assert current["status"] == "failed" and "uncertain" in current["error"].lower()
        assert claim_next("new-worker", run_id=run["run_id"]) is None
    finally:
        service.cancel_search(scope, run["run_id"])


def test_legacy_run_deadline_is_not_extended_by_new_engine():
    id = "legacy-" + uuid.uuid4().hex
    now = time.time() - 91
    payload = {
        "run_id": id,
        "person_id": "admin",
        "scope_version": resolve_scope("admin").scope_version,
        "query": "legacy",
        "mode": "extractive",
        "status": "pending",
        "created_at": now,
        "events": [],
        "statements": [],
        "evidence": [],
        "gaps": [],
        "graph": {"nodes": [], "edges": []},
    }
    import json

    query(
        "INSERT INTO search_runs(id,person_id,payload) VALUES(:id,'admin',CAST(:payload AS jsonb)) RETURNING id",
        {"id": id, "payload": json.dumps(payload)},
    )
    try:
        assert service.get_search(resolve_scope("admin"), id)["status"] == "failed"
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_lease_owner_controls_publication_and_model_receipts(monkeypatch):
    from app.agent.worker import (
        begin_model,
        complete_model,
        publish_owned,
        assert_owned,
    )

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    id = run["run_id"]
    try:
        claim_next("owner", run_id=id)
        with pytest.raises(Exception):
            begin_model(id, "intruder", "decision-one")
        assert begin_model(id, "owner", "decision-one") is None
        complete_model(
            id, "owner", "decision-one", {"decision": {"stop_action": "finish"}}
        )
        assert (
            begin_model(id, "owner", "decision-one")["decision"]["stop_action"]
            == "finish"
        )
        assert service.raw_run(id)["paid_calls"] == 1
        query(
            "UPDATE search_runs SET lease_until=:expiry WHERE id=:id RETURNING id",
            {"id": id, "expiry": time.time() - 1},
        )
        recover_expired()
        assert claim_next("successor", run_id=id)
        assert not publish_owned(id, "owner", {"status": "completed"})
        assert publish_owned(id, "successor", {"status": "completed"})
        public = service.get_search(scope, id)
        assert "model_receipts" not in public and "paid_calls" in public
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_cancel_revokes_reads_and_terminal_publication(monkeypatch):
    from app.agent.worker import assert_owned, publish_owned

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    id = run["run_id"]
    try:
        claim_next("owner", run_id=id)
        service.cancel_search(scope, id)
        with pytest.raises(Exception):
            assert_owned(id, "owner")
        assert not publish_owned(id, "owner", {"status": "completed"})
        assert service.get_search(scope, id)["status"] == "cancelled"
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_shared_admission_rejects_capacity_without_creating_run(monkeypatch):
    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    monkeypatch.setattr(settings(), "search_persona_limit", 1)
    scope = resolve_scope("admin")
    first = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    try:
        with pytest.raises(HTTPException) as e:
            service.start_search(
                scope,
                SearchRequest(query="Find legal controls", intent_id=uuid.uuid4().hex),
            )
        assert e.value.status_code == 429 and e.value.headers["Retry-After"] == "2"
    finally:
        service.cancel_search(scope, first["run_id"])


def test_durable_worker_finishes_without_exposing_checkpoint_or_private_history(
    monkeypatch,
):
    from app.agent.actions import ActionDecision
    from app.agent.worker import claim_next
    from app.agent import provider

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    monkeypatch.setattr(
        provider,
        "make_decider",
        lambda *a, **k: (
            lambda *args: ActionDecision(
                intent={
                    "query": "Missing obligation",
                    "facets": [
                        {
                            "id": "obligation",
                            "description": "Actual obligation",
                            "kinds": ["document"],
                        }
                    ],
                },
                stop_action="finish",
            )
        ),
    )
    from app.agent import finalization
    from app.agent.verification import DraftAnswer

    # The provider boundary is offline even when the developer has a real key.
    monkeypatch.setattr(finalization, "parse_response", lambda *a, **kw: DraftAnswer())
    scope = resolve_scope("admin")
    run = service.start_search(
        scope,
        SearchRequest(query="A nonexistent obligation", intent_id=uuid.uuid4().hex),
    )
    id = run["run_id"]
    try:
        claim_next("owner", run_id=id)
        service.execute_graph_run(id, "owner")
        result = service.get_search(scope, id)
        assert result["status"] == "completed", result
        assert result["answer_outcome"] == "no_evidence" and not result["statements"]
        assert 1 <= result["tool_calls"] <= 3
        assert (
            result["paid_calls"] == 1
        )  # One persisted mocked synthesis attempt; no SDK call.
        assert len([e for e in result["events"] if e["stage"] == "finish"]) == 1
        assert "native_history" not in result and "checkpoint" not in result
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_paid_model_budget_is_enforced_across_worker_recovery(monkeypatch):
    from app.agent.worker import begin_model, complete_model

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    id = run["run_id"]
    try:
        claim_next("owner", run_id=id)
        for n in range(6):
            assert begin_model(id, "owner", str(n)) is None
            complete_model(id, "owner", str(n), {"decision": {"stop_action": "finish"}})
        with pytest.raises(TimeoutError):
            begin_model(id, "owner", "seventh")
        assert service.raw_run(id)["paid_calls"] == 6
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_cancellation_during_decision_cannot_publish_a_completed_answer(monkeypatch):
    from app.agent.actions import ActionDecision
    from app.agent import provider

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    id = run["run_id"]

    def decide(*a):
        service.cancel_search(scope, id)
        return ActionDecision(stop_action="finish")

    monkeypatch.setattr(provider, "make_decider", lambda *a, **k: decide)
    try:
        claim_next("owner", run_id=id)
        service.execute_graph_run(id, "owner")
        result = service.get_search(scope, id)
        assert result["status"] == "cancelled" and not result["statements"]
        assert len([e for e in result["events"] if e["stage"] == "finish"]) == 1
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_explicit_extractive_mode_never_calls_an_llm_provider(monkeypatch):
    from app.agent import provider

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    monkeypatch.setattr(
        provider,
        "make_decider",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("Extractive demo cannot dispatch a model")
        ),
    )
    scope = resolve_scope("admin")
    run = service.start_search(
        scope,
        SearchRequest(
            query="Which policies govern treasury liquidity?",
            mode="extractive",
            intent_id=uuid.uuid4().hex,
        ),
    )
    id = run["run_id"]
    try:
        claim_next("owner", run_id=id)
        service.execute_graph_run(id, "owner")
        result = service.get_search(scope, id)
        assert result["status"] == "completed", result
        assert result["semantic_verification"] == "source_only"
        assert not result.get("paid_calls")
        assert result["evidence"] and result["answer_outcome"] == "partial"
    finally:
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_scope_revocation_between_guard_and_publication_is_atomic(monkeypatch):
    import json
    from app.agent.worker import publish_owned

    monkeypatch.setattr(settings(), "graph_search_v2", True)
    monkeypatch.setattr(settings(), "local_search_worker", False)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope, SearchRequest(query="Find treasury controls", intent_id=uuid.uuid4().hex)
    )
    id = run["run_id"]
    original = query("SELECT payload FROM records WHERE id='role-admin'")[0]["payload"]
    try:
        claim_next("owner", run_id=id)
        changed = {
            **original,
            "scope_version": scope.scope_version + 1,
            "domain_ids": ["legal"],
        }
        query(
            "UPDATE records SET payload=CAST(:p AS jsonb) WHERE id='role-admin' RETURNING id",
            {"p": json.dumps(changed)},
        )
        assert not publish_owned(
            id,
            "owner",
            {
                "status": "completed",
                "statements": [{"text": "Private amount", "evidence_ids": []}],
            },
        )
        assert service.raw_run(id)["status"] != "completed"
    finally:
        query(
            "UPDATE records SET payload=CAST(:p AS jsonb) WHERE id='role-admin' RETURNING id",
            {"p": json.dumps(original)},
        )
        query("DELETE FROM search_runs WHERE id=:id RETURNING id", {"id": id})


def test_failure_retains_known_usage_and_reports_safe_error_category(monkeypatch):
    from app.agent.worker import begin_model, complete_model
    from app.agent import provider

    monkeypatch.setattr(settings(), "local_search_worker", False)
    monkeypatch.setattr(settings(), "graph_search_v2", True)
    scope = resolve_scope("admin")
    run = service.start_search(
        scope,
        SearchRequest(
            query="A diagnostic failure", mode="llm", intent_id=uuid.uuid4().hex
        ),
    )
    id = run["run_id"]
    assert claim_next("owner", run_id=id)
    try:
        begin_model(id, "owner", "known")
        complete_model(
            id,
            "owner",
            "known",
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 3,
                    "total_tokens": 13,
                }
            },
        )

        def unavailable(*a, **kw):
            raise RuntimeError("Private diagnostic details must not escape")

        monkeypatch.setattr(provider, "make_decider", unavailable)
        service.execute_graph_run(id, "owner")
        result = service.get_search(scope, id)
        assert result["status"] == "failed"
        assert result["usage"]["total_tokens"] == 13
        assert result["error_category"] == "RuntimeError"
        assert "Private diagnostic" not in str(result)
    finally:
        service.cancel_search(scope, id)
