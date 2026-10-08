"""Durable bounded search admission and atomic worker leases across API replicas."""

import json, time, uuid, threading
import logging
from fastapi import HTTPException
from sqlalchemy import text
from app.db import engine, query
from app.config import settings
from app.auth import narrow_scope


def enqueue(scope, request):
    narrow_scope(scope, request.domain_id)
    cfg = settings()
    now = time.time()
    id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('knowledge-search-admission'))")
        )
        if request.intent_id:
            previous = (
                conn.execute(
                    text(
                        "SELECT id,payload FROM search_runs WHERE person_id=:person AND intent_id=:intent"
                    ),
                    {"person": scope.person_id, "intent": request.intent_id},
                )
                .mappings()
                .first()
            )
            if previous:
                p = previous["payload"]
                if (p["query"], p["mode"], p.get("domain_id")) != (
                    request.query,
                    request.mode,
                    request.domain_id,
                ):
                    raise HTTPException(
                        409, "Search intent already used for different parameters"
                    )
                return previous["id"]
        active = (
            conn.execute(
                text(
                    "SELECT count(*) AS total,count(*) FILTER (WHERE person_id=:person) AS mine FROM search_runs WHERE payload->>'status' IN ('pending','running') AND COALESCE((payload->>'deadline')::double precision,(payload->>'created_at')::double precision+90)>:now"
                ),
                {"person": scope.person_id, "now": now},
            )
            .mappings()
            .one()
        )
        if (
            active["mine"] >= cfg.search_persona_limit
            or active["total"] >= cfg.search_queue_limit
        ):
            raise HTTPException(
                429,
                "Search capacity is busy. Stop an active answer or try again shortly.",
                headers={"Retry-After": "2"},
            )
        run = {
            "run_id": id,
            "person_id": scope.person_id,
            "scope_version": scope.scope_version,
            "domain_id": request.domain_id,
            "query": request.query,
            "mode": request.mode,
            "status": "pending",
            "engine_version": "graph_v2",
            "created_at": now,
            "deadline": now + cfg.search_deadline_seconds,
            "model_inflight": False,
            "statements": [],
            "evidence": [],
            "gaps": [],
            "graph": {"nodes": [], "edges": []},
            "events": [
                {
                    "stage": "queue",
                    "status": "pending",
                    "summary": "Waiting for an available search worker",
                    "at": now,
                }
            ],
        }
        conn.execute(
            text(
                "INSERT INTO search_runs(id,person_id,intent_id,payload) VALUES(:id,:person,:intent,CAST(:payload AS jsonb))"
            ),
            {
                "id": id,
                "person": scope.person_id,
                "intent": request.intent_id,
                "payload": json.dumps(run),
            },
        )
    return id


def claim_next(worker_id, run_id=None):
    now = time.time()
    rows = query(
        """WITH candidate AS (SELECT id FROM search_runs WHERE payload->>'status'='pending' AND payload->>'engine_version'='graph_v2' AND (CAST(:id AS text) IS NULL OR id=:id) AND (payload->>'deadline')::double precision>:now ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1)
      UPDATE search_runs SET lease_owner=:owner,lease_until=:lease,payload=payload || '{"status":"running"}'::jsonb FROM candidate WHERE search_runs.id=candidate.id RETURNING search_runs.payload""",
        {
            "id": run_id,
            "now": now,
            "owner": worker_id,
            "lease": now + settings().search_lease_seconds,
        },
    )
    return rows[0]["payload"] if rows else None


def recover_expired():
    now = time.time()
    failed = query(
        """UPDATE search_runs SET lease_owner=NULL,lease_until=NULL,payload=payload || CAST(:patch AS jsonb) WHERE payload->>'engine_version'='graph_v2' AND payload->>'status'='running' AND lease_until<:now AND COALESCE((payload->>'model_inflight')::boolean,false) RETURNING id""",
        {
            "now": now,
            "patch": json.dumps(
                {
                    "status": "failed",
                    "error": "A provider call has an uncertain outcome after worker interruption. Generate an answer explicitly; it will not be replayed.",
                    "answer_outcome": "partial",
                }
            ),
        },
    )
    query(
        """UPDATE search_runs SET lease_owner=NULL,lease_until=NULL,payload=payload || '{"status":"pending"}'::jsonb WHERE payload->>'engine_version'='graph_v2' AND payload->>'status'='running' AND lease_until<:now AND NOT COALESCE((payload->>'model_inflight')::boolean,false) AND (payload->>'deadline')::double precision>:now RETURNING id""",
        {"now": now},
    )
    query(
        """UPDATE search_runs SET lease_owner=NULL,lease_until=NULL,payload=payload || '{"status":"failed","error":"Search deadline expired before execution finished."}'::jsonb WHERE payload->>'engine_version'='graph_v2' AND payload->>'status' IN ('pending','running') AND (payload->>'deadline')::double precision<=:now RETURNING id""",
        {"now": now},
    )
    return len(failed)


def heartbeat(worker_id, run_id):
    return bool(
        query(
            "UPDATE search_runs SET lease_until=:until WHERE id=:id AND lease_owner=:owner AND payload->>'status'='running' RETURNING id",
            {
                "until": time.time() + settings().search_lease_seconds,
                "id": run_id,
                "owner": worker_id,
            },
        )
    )


class LeaseLost(Exception):
    pass


def assert_owned(run_id, worker_id):
    rows = query(
        "SELECT payload FROM search_runs WHERE id=:id AND lease_owner=:owner AND lease_until>:now AND payload->>'status'='running' AND (payload->>'deadline')::double precision>:now",
        {"id": run_id, "owner": worker_id, "now": time.time()},
    )
    if not rows:
        raise LeaseLost("Search cancelled, deadline expired, or worker lease lost")
    return rows[0]["payload"]


def publish_owned(run_id, worker_id, patch, final_event=None):
    return bool(
        query(
            "UPDATE search_runs SET payload=jsonb_set(payload || CAST(:patch AS jsonb),'{events}',(payload->'events') || CAST(:events AS jsonb)) WHERE id=:id AND lease_owner=:owner AND lease_until>:now AND payload->>'status'='running' AND (payload->>'deadline')::double precision>:now AND (:failure OR (payload->>'scope_version')::integer=COALESCE((SELECT (r.payload->>'scope_version')::integer FROM records r WHERE r.id='role-' || search_runs.person_id AND r.kind='role'),1)) RETURNING id",
            {
                "id": run_id,
                "owner": worker_id,
                "now": time.time(),
                "patch": json.dumps(patch),
                "failure": patch.get("status") in ["failed", "configuration_required"],
                "events": json.dumps([final_event] if final_event else []),
            },
        )
    )


def begin_model(run_id, worker_id, fingerprint):
    """Durably mark a paid attempt before dispatch; known responses are reusable."""
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    "SELECT payload,lease_owner,lease_until FROM search_runs WHERE id=:id FOR UPDATE"
                ),
                {"id": run_id},
            )
            .mappings()
            .first()
        )
        now = time.time()
        if (
            not row
            or row["lease_owner"] != worker_id
            or row["lease_until"] <= now
            or row["payload"]["status"] != "running"
            or row["payload"]["deadline"] <= now
        ):
            raise LeaseLost("Worker no longer owns this search")
        run = row["payload"]
        receipt = run.get("model_receipts", {}).get(fingerprint)
        if receipt is not None:
            return receipt
        if run.get("model_inflight"):
            raise LeaseLost(
                "Previous provider attempt has an uncertain outcome; it will not be replayed"
            )
        if run.get("paid_calls", 0) >= 6:
            raise TimeoutError("Model call budget exhausted")
        patch = {
            "model_inflight": True,
            "model_fingerprint": fingerprint,
            "paid_calls": run.get("paid_calls", 0) + 1,
        }
        conn.execute(
            text(
                "UPDATE search_runs SET payload=payload || CAST(:patch AS jsonb) WHERE id=:id"
            ),
            {"id": run_id, "patch": json.dumps(patch)},
        )
    return None


def complete_model(run_id, worker_id, fingerprint, receipt):
    # Receipt and inflight reset are one transaction; a process crash cannot expose
    # a cleared marker without the parsed provider response needed for resumption.
    rows = query(
        "UPDATE search_runs SET payload=payload || jsonb_build_object('model_receipts',COALESCE(payload->'model_receipts','{}'::jsonb) || jsonb_build_object(CAST(:fingerprint AS text),CAST(:receipt AS jsonb)),'model_inflight',false) WHERE id=:id AND lease_owner=:owner AND lease_until>:now AND payload->>'status'='running' AND payload->>'model_fingerprint'=:fingerprint RETURNING id",
        {
            "id": run_id,
            "owner": worker_id,
            "now": time.time(),
            "fingerprint": fingerprint,
            "receipt": json.dumps(receipt),
        },
    )
    if not rows:
        raise LeaseLost(
            "Worker cannot record a provider response after losing its lease"
        )


def worker_loop(stop):
    worker = uuid.uuid4().hex
    while not stop.is_set():
        try:
            recover_expired()
            run = claim_next(worker)
            if not run:
                stop.wait(0.3)
                continue
            from app.agent.service import execute_graph_run

            execute_graph_run(run["run_id"], worker)
        except Exception:
            logging.getLogger(__name__).exception("Search worker iteration failed")
            stop.wait(1)


_started = False
_local_stop = threading.Event()
_start_lock = threading.Lock()


def ensure_local_worker():
    global _started
    with _start_lock:
        if _started:
            return
        _started = True
        for _ in range(settings().search_worker_concurrency):
            threading.Thread(
                target=worker_loop, args=(_local_stop,), daemon=True
            ).start()


if __name__ == "__main__":
    try:
        worker_loop(_local_stop)
    except KeyboardInterrupt:
        _local_stop.set()
