import json, time, uuid, threading
from concurrent.futures import ThreadPoolExecutor
from langgraph.checkpoint.postgres import PostgresSaver
from fastapi import HTTPException
from app.db import query
from app.config import settings
from app.agent.graph import build_graph, RunCancelled, ScopeChanged
from app.agent.provider import ConfigurationRequired, ModelRefusal
from app.auth import resolve_scope, narrow_scope
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


def transition_run(id, patch, allowed, deadline=None, final_event=None):
    rows = query(
        "UPDATE search_runs SET payload=jsonb_set(payload || CAST(:patch AS jsonb),'{events}', (payload->'events') || CAST(:final_events AS jsonb)) WHERE id=:id AND payload->>'status'=ANY(:allowed) AND (CAST(:deadline AS double precision) IS NULL OR EXTRACT(EPOCH FROM clock_timestamp()) < :deadline) RETURNING id",
        {
            "id": id,
            "patch": json.dumps(patch),
            "allowed": allowed,
            "deadline": deadline,
            "final_events": json.dumps([final_event] if final_event else []),
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
    if run["status"] in ["pending", "running"] and time.time() >= run.get(
        "deadline", run["created_at"] + 90
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
    for private in [
        "model_receipts",
        "model_fingerprint",
        "model_inflight",
        "checkpoint",
    ]:
        run.pop(private, None)
    return run


def start_search(scope, request):
    request = SearchRequest.model_validate(request)
    if settings().graph_search_v2:
        from app.agent.worker import enqueue, ensure_local_worker

        id = enqueue(scope, request)
        if settings().local_search_worker:
            ensure_local_worker()
        return get_search(scope, id)
    narrow_scope(scope, request.domain_id)
    id = str(uuid.uuid4())
    run = {
        "run_id": id,
        "person_id": scope.person_id,
        "scope_version": scope.scope_version,
        "domain_id": request.domain_id,
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
            saver.serde = checkpoint_serializer()
            with _setup_lock:
                saver.setup()
            graph = build_graph(saver, event, raw_run)
            state = {
                "run_id": id,
                "person_id": run["person_id"],
                "scope_version": run["scope_version"],
                "domain_id": run.get("domain_id"),
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
            final_event={
                "stage": "finish",
                "status": "completed",
                "summary": "Search completed with validated citations",
                "at": time.time(),
            },
        )
        if not completed and time.time() >= run["created_at"] + 90:
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
    if run.get("engine_version") == "graph_v2":
        # Recovery is owned by leases. A failed/uncertain paid run must be started
        # again explicitly with a new browser intent, never submitted to v1.
        if run["status"] in ["pending", "running"] and settings().local_search_worker:
            from app.agent.worker import ensure_local_worker

            ensure_local_worker()
        return run
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


def checkpoint_serializer():
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    allowed = [
        ("app.agent.actions", name)
        for name in [
            "ResearchState",
            "ActionDecision",
            "PlannedCall",
            "EvidenceAssessment",
        ]
    ]
    allowed += [
        ("app.knowledge.contracts", name)
        for name in [
            "SearchIntentV2",
            "AnswerFacet",
            "CoverageReport",
            "EvidenceFragment",
            "SourceRef",
        ]
    ]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed, pickle_fallback=False)


def finalize_research(ctx, state, mode, before_model, after_model):
    from app.agent.finalization import finalize_research as finalize

    return finalize(ctx, state, mode, before_model, after_model)


def execute_graph_run(id, worker):
    from app.agent.worker import (
        assert_owned,
        heartbeat,
        begin_model,
        complete_model,
        publish_owned,
        LeaseLost,
    )
    from app.agent.provider import make_decider
    from app.agent.adaptive import build_research_graph
    from app.agent.actions import ResearchState
    from app.agent.prompts import PROMPT_VERSION
    from app.knowledge.contracts import ToolContext

    stop = threading.Event()

    def renew():
        while not stop.wait(max(1, settings().search_lease_seconds / 3)):
            try:
                if not heartbeat(worker, id):
                    return
            except Exception:
                return

    renewer = threading.Thread(target=renew, daemon=True)
    renewer.start()
    try:
        run = assert_owned(id, worker)
        scope = resolve_scope(run["person_id"])
        if scope.scope_version != run["scope_version"]:
            raise ScopeChanged("Access scope changed; start a new search")
        ctx = ToolContext(
            scope=scope,
            deadline=run["deadline"],
            domain_id=run.get("domain_id"),
            finalization_reserve_seconds=settings().search_finalization_reserve_seconds
            if run["mode"] != "extractive"
            else 8,
        )
        ctx._lifecycle_guard = lambda: assert_owned(id, worker)
        before = lambda fingerprint: begin_model(id, worker, fingerprint)
        after = lambda fingerprint, receipt: complete_model(
            id, worker, fingerprint, receipt
        )

        def notice(stage, summary):
            if not publish_owned(
                id,
                worker,
                {},
                {
                    "stage": stage,
                    "status": "running",
                    "summary": summary,
                    "at": time.time(),
                },
            ):
                raise LeaseLost("Search no longer belongs to this worker")

        conn = settings().database_url.replace("postgresql+psycopg://", "postgresql://")
        with PostgresSaver.from_conn_string(conn) as saver:
            saver.serde = checkpoint_serializer()
            with _setup_lock:
                saver.setup()
            if run["mode"] == "extractive":
                from app.agent.offline import make_offline_decider

                decider = make_offline_decider(ctx)
            else:
                decider = make_decider(ctx, before_model=before, after_model=after)
            graph = build_research_graph(
                ctx,
                decider,
                checkpointer=saver,
                on_event=notice,
            )
            config = {"configurable": {"thread_id": id}, "recursion_limit": 24}
            snapshot = graph.get_state(config)
            if snapshot.values:
                state = ResearchState.model_validate(snapshot.values)
                ctx.tool_calls = state.tool_calls
                ctx.graph_nodes = set(state.graph_nodes)
                ctx.graph_edges = set(state.graph_edges)
            if snapshot.values and not snapshot.next:
                result = snapshot.values
            else:
                result = graph.invoke(
                    None if snapshot.values else ResearchState(query=run["query"]),
                    config,
                )
        state = ResearchState.model_validate(result)
        from app.knowledge.runtime import guard

        guard(ctx)
        output = finalize_research(ctx, state, run["mode"], before, after)
        guard(ctx)
        receipts = list(raw_run(id).get("model_receipts", {}).values())
        output["usage"] = {
            key: sum(int(r.get("usage", {}).get(key) or 0) for r in receipts)
            for key in ["prompt_tokens", "completion_tokens", "total_tokens"]
        }
        from importlib.metadata import version as package_version
        from app.knowledge.runtime import version as content_version

        output["versions"] = {
            "engine": "graph_v2",
            "prompt": PROMPT_VERSION,
            "model": settings().llm_model if run["mode"] != "extractive" else None,
            "provider": settings().llm_provider
            if run["mode"] != "extractive"
            else None,
            "upstream": settings().openrouter_upstream
            if run["mode"] != "extractive" and settings().llm_provider == "openrouter"
            else None,
            "adapter": next(
                (r["adapter"] for r in receipts if r.get("adapter")),
                settings().agent_adapter,
            )
            if run["mode"] != "extractive"
            else "offline",
            "structured_mode": settings().openrouter_structured_mode
            if run["mode"] != "extractive"
            else None,
            "langgraph": package_version("langgraph"),
            "retrieved_graph_digest": content_version(state.paths),
            "source_versions": {e.id: e.source_ref.version for e in state.evidence},
        }
        publish_owned(
            id,
            worker,
            {**output, "status": "completed", "prompt_version": PROMPT_VERSION},
            {
                "stage": "finish",
                "status": "completed",
                "summary": "Search finished",
                "at": time.time(),
            },
        )
    except LeaseLost:
        # Cancellation or another owner's recovery must remain authoritative.
        pass
    except Exception as exc:
        status = (
            "configuration_required"
            if isinstance(exc, ConfigurationRequired)
            else "failed"
        )
        message = (
            str(exc)
            if isinstance(
                exc,
                (
                    ConfigurationRequired,
                    ModelRefusal,
                    ScopeChanged,
                    HTTPException,
                    ValueError,
                    TimeoutError,
                ),
            )
            else "Search could not finish because a source or provider was unavailable. Generate an answer explicitly to try again."
        )
        known_receipts = raw_run(id).get("model_receipts", {}).values()
        known_usage = {
            key: sum(int(r.get("usage", {}).get(key) or 0) for r in known_receipts)
            for key in ["prompt_tokens", "completion_tokens", "total_tokens"]
        }
        publish_owned(
            id,
            worker,
            {
                "status": status,
                "error": message,
                "error_category": type(exc).__name__,
                "usage": known_usage,
            },
            {
                "stage": "finish",
                "status": status,
                "summary": message,
                "at": time.time(),
            },
        )
    finally:
        stop.set()
        renewer.join(timeout=1)
