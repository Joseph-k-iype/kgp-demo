"""Persisted, claim-once ingestion jobs. Can run inside the API executor or standalone."""

import json, time, uuid, logging
from fastapi import HTTPException
from app.auth import resolve_scope
from app.db import query
from app.catalog.service import get_record, all_records
from app.retrieval.service import index_assets


def submit_index(scope, asset_ids):
    if scope.role != "Administrator":
        raise HTTPException(403, "Only administrators can rebuild the index")
    ids = asset_ids or [a["id"] for a in all_records(scope, "asset")]
    for id in ids:
        get_record(scope, id, "asset")
    id = str(uuid.uuid4())
    payload = {
        "asset_ids": ids,
        "person_id": scope.person_id,
        "scope_version": scope.scope_version,
        "created_at": time.time(),
    }
    query(
        "INSERT INTO jobs(id,state,payload) VALUES(:id,'pending',CAST(:p AS jsonb)) RETURNING id",
        {"id": id, "p": json.dumps(payload)},
    )
    return {"id": id, "state": "pending", **payload}


def get_job(scope, id):
    rows = query("SELECT * FROM jobs WHERE id=:id", {"id": id})
    if not rows or rows[0]["payload"]["person_id"] != scope.person_id:
        raise HTTPException(404, "Index job not found")
    return {"id": id, "state": rows[0]["state"], **rows[0]["payload"]}


def run_index_job(id):
    rows = query(
        "UPDATE jobs SET state='running' WHERE id=:id AND state='pending' RETURNING payload",
        {"id": id},
    )
    if not rows:
        return
    p = rows[0]["payload"]
    try:
        scope = resolve_scope(p["person_id"])
        if scope.scope_version != p["scope_version"] or scope.role != "Administrator":
            raise ValueError("Index job access scope changed")
        for asset_id in p["asset_ids"]:
            get_record(scope, asset_id, "asset")
        result = index_assets(p["asset_ids"])
        query(
            "UPDATE jobs SET state='completed',payload=payload || CAST(:p AS jsonb) WHERE id=:id RETURNING id",
            {"id": id, "p": json.dumps({"result": result, "finished_at": time.time()})},
        )
    except Exception:
        logging.exception("Index job %s failed", id)
        query(
            "UPDATE jobs SET state='failed',payload=payload || CAST(:p AS jsonb) WHERE id=:id RETURNING id",
            {
                "id": id,
                "p": json.dumps(
                    {
                        "error": "Indexing failed. Check storage, model and OpenSearch readiness."
                    }
                ),
            },
        )


if __name__ == "__main__":
    while True:
        for row in query(
            "SELECT id FROM jobs WHERE state='pending' ORDER BY id LIMIT 1"
        ):
            run_index_job(row["id"])
        time.sleep(2)
