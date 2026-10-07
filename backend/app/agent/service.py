import json, time, uuid, threading
from concurrent.futures import ThreadPoolExecutor
from langgraph.checkpoint.postgres import PostgresSaver
from fastapi import HTTPException
from app.db import query
from app.config import settings
from app.agent.graph import build_graph, RunCancelled, ScopeChanged
from app.agent.provider import ConfigurationRequired, ModelRefusal
from app.auth import resolve_scope
from app.contracts import SearchRequest

executor = ThreadPoolExecutor(max_workers=2)
_setup_lock = threading.Lock()
_active = set()
_active_lock = threading.Lock()


def raw_run(id):
    rows = query("SELECT payload FROM search_runs WHERE id=:id", {"id": id})
    if not rows:
        raise HTTPException(404, "Search run not found")
    return rows[0]["payload"]


def transition_run(id, patch, allowed, deadline=None):
    rows = query(
        "UPDATE search_runs SET payload=payload || CAST(:patch AS jsonb) WHERE id=:id AND payload->>'status'=ANY(:allowed) AND (CAST(:deadline AS double precision) IS NULL OR EXTRACT(EPOCH FROM clock_timestamp()) < :deadline) RETURNING id",
        {
            "id": id,
            "patch": json.dumps(patch),
            "allowed": allowed,
            "deadline": deadline,
        },
    )
    return bool(rows)


def event(id, stage, status, summary):
    e = {"stage": stage, "status": status, "summary": summary, "at": time.time()}
    # One runner per run; PostgreSQL append avoids losing cancellation updates.
    query(
        "UPDATE search_runs SET payload=jsonb_set(payload,'{events}', (payload->'events') || CAST(:e AS jsonb)) WHERE id=:id RETURNING id",
        {"id": id, "e": json.dumps([e])},
    )


def get_search(scope, run_id):
    run = raw_run(run_id)
    if run["person_id"] != scope.person_id:
        raise HTTPException(404, "Search run not found")
    current = resolve_scope(scope.person_id)
    if current.scope_version != run["scope_version"]:
        raise HTTPException(
            409, "Access scope changed; run evidence is no longer available"
        )
    if (
        run["status"] in ["pending", "running"]
        and time.time() - run["created_at"] >= 90
    ):
        transition_run(
            run_id,
            {
                "status": "failed",
                "error": "Search deadline expired or the worker was interrupted. Start a new search.",
            },
            ["pending", "running"],
        )
        run = raw_run(run_id)
    run = dict(run)
    for i, e in enumerate(run["events"]):
        e["sequence"] = i + 1
    run.pop("scope_version", None)
    run.pop("person_id", None)
    return run


def start_search(scope, request):
    request = SearchRequest.model_validate(request)
    id = str(uuid.uuid4())
    run = {
        "run_id": id,
        "person_id": scope.person_id,
        "scope_version": scope.scope_version,
        "query": request.query,
        "mode": request.mode,
        "status": "pending",
        "statements": [],
        "evidence": [],
        "gaps": [],
        "events": [],
        "graph": {"nodes": [], "edges": []},
        "created_at": time.time(),
    }
    query(
        "INSERT INTO search_runs(id,person_id,payload) VALUES(:id,:person,CAST(:payload AS jsonb)) RETURNING id",
        {"id": id, "person": scope.person_id, "payload": json.dumps(run)},
    )
    with _active_lock:
        _active.add(id)
    executor.submit(execute_run, id)
    return get_search(scope, id)


def execute_run(id, resume=False):
    run = raw_run(id)
    if run["status"] == "cancelled":
        with _active_lock:
            _active.discard(id)
        return
    if not transition_run(
        id,
        {"status": "running"},
        ["pending", "running", "failed", "configuration_required"],
    ):
        with _active_lock:
            _active.discard(id)
        return
    conn = settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        with PostgresSaver.from_conn_string(conn) as saver:
            with _setup_lock:
                saver.setup()
            graph = build_graph(saver, event, raw_run)
            state = {
                "run_id": id,
                "person_id": run["person_id"],
                "scope_version": run["scope_version"],
                "query": run["query"],
                "mode": run["mode"],
                "started": run["created_at"],
                "evidence": [],
            }
            config = {"configurable": {"thread_id": id}, "recursion_limit": 24}
            snapshot = graph.get_state(config) if resume else None
            if snapshot and not snapshot.next and snapshot.values.get("statements"):
                output = snapshot.values
            else:
                if (
                    resume
                    and snapshot
                    and snapshot.next
                    and snapshot.next[0] in ["plan", "synthesize"]
                    and any(e["stage"] == snapshot.next[0] for e in run["events"])
                ):
                    raise ValueError(
                        "A previous provider call has an uncertain outcome. Start a new search; it will not be replayed automatically."
                    )
                output = graph.invoke(
                    None if resume and snapshot and snapshot.values else state,
                    config=config,
                )
        completed = transition_run(
            id,
            {
                "status": "completed",
                "statements": output.get("statements", []),
                "evidence": output.get("evidence", []),
                "gaps": output.get("gaps", []),
                "uncertainty": output.get("uncertainty", ""),
                "graph": output.get("graph", {}),
                "retrieval_passes": output["retrieval_passes"],
                "tool_calls": output["tool_calls"],
            },
            ["running"],
            deadline=run["created_at"] + 90,
        )
        if completed:
            event(
                id, "finish", "completed", "Search completed with validated citations"
            )
        elif time.time() >= run["created_at"] + 90:
            raise TimeoutError("Search exceeded its 90 second limit")
    except RunCancelled:
        transition_run(id, {"status": "cancelled"}, ["pending", "running"])
    except Exception as e:
        status = (
            "configuration_required"
            if isinstance(e, ConfigurationRequired)
            else "refused"
            if isinstance(e, ModelRefusal)
            else "scope_changed"
            if isinstance(e, ScopeChanged)
            else "failed"
        )
        message = (
            str(e)
            if isinstance(
                e,
                (
                    ConfigurationRequired,
                    ModelRefusal,
                    ScopeChanged,
                    TimeoutError,
                    ValueError,
                ),
            )
            else "A search dependency failed. Check service readiness and server logs."
        )
        import logging

        logging.getLogger(__name__).exception("Search run %s failed", id)
        if transition_run(
            id,
            {"status": status, "error": message, "statements": [], "evidence": []},
            ["pending", "running"],
        ):
            event(id, "finish", status, message)
    finally:
        with _active_lock:
            _active.discard(id)


def resume_search(scope, run_id):
    run = get_search(scope, run_id)
    if run["status"] in ["completed", "cancelled"]:
        return run
    with _active_lock:
        if run_id in _active:
            return run
        if time.time() - run["created_at"] > 90:
            transition_run(
                run_id,
                {
                    "status": "failed",
                    "error": "Original search deadline expired. Start a new search.",
                },
                ["pending", "running", "failed", "configuration_required"],
            )
            return get_search(scope, run_id)
        _active.add(run_id)
    executor.submit(execute_run, run_id, True)
    return get_search(scope, run_id)


def cancel_search(scope, run_id):
    run = get_search(scope, run_id)
    if run["status"] in ["pending", "running"]:
        if transition_run(run_id, {"status": "cancelled"}, ["pending", "running"]):
            event(run_id, "finish", "cancelled", "Search cancelled")
    return get_search(scope, run_id)
