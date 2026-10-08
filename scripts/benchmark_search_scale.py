"""Opt-in isolated 10k RDF/100k SQL benchmark. Creates and removes only its own DB/container."""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path


def child(prefix, output):
    import httpx
    from sqlalchemy import insert, text
    from rdflib import Literal, RDF, RDFS
    from app.db import engine, query
    from app.catalog.models import records
    from app.config import settings
    from app.auth import resolve_scope
    from app.ontology.service import I, K
    from app.knowledge.runtime import version
    from app.knowledge.contracts import ToolContext, QueryDatasetAction, DatasetQuery
    from app.knowledge.graph import resolve_entities, traverse_graph
    from app.knowledge.tools import execute_read
    from app.contracts import SearchRequest
    from app.agent.worker import (
        enqueue,
        claim_next,
        recover_expired,
        assert_owned,
        LeaseLost,
    )
    from app.agent.service import cancel_search

    asset = prefix + "-asset"
    with engine.begin() as conn:
        conn.execute(
            insert(records),
            {
                "id": asset,
                "kind": "asset",
                "domain_id": "risk",
                "payload": {
                    "name": "Scale source records",
                    "type": "Table",
                    "source_id": "risk-source-0",
                },
            },
        )
        for start in range(0, 10000, 1000):
            conn.execute(
                insert(records),
                [
                    {
                        "id": prefix + "-entity-" + str(i),
                        "kind": "entity",
                        "domain_id": "risk",
                        "payload": {
                            "name": prefix + " root"
                            if i == 0
                            else "Scale entity " + str(i),
                            "aliases": [],
                            "entity_type": "BusinessEntity",
                        },
                    }
                    for i in range(start, start + 1000)
                ],
            )
        for batch_start in range(0, 100000, 1000):
            conn.execute(
                text("""
              INSERT INTO business_rows(id,asset_id,payload)
              SELECT :prefix || '-row-' || lpad(i::text,6,'0'), :asset,
              jsonb_build_object('record_id',:prefix || '-row-' || lpad(i::text,6,'0'),
              'as_of','2026-09-30','domain','risk','counterparty_id','SCALE-' || i::text,
              'counterparty_name','Scale counterparty ' || i::text,'exposure_usd',i*10,
              'risk_level','Low','due_diligence_status','Complete','country','GB')
              FROM generate_series(CAST(:first_row AS integer),CAST(:last_row AS integer)) i
            """),
                {
                    "prefix": prefix,
                    "asset": asset,
                    "first_row": batch_start,
                    "last_row": batch_start + 999,
                },
            )

    row = query(
        "SELECT id,payload FROM business_rows WHERE asset_id=:asset ORDER BY id LIMIT 1",
        {"asset": asset},
    )[0]
    digest = version(row["payload"])
    graph = "<https://atlas.example/graphs/instances>"
    root = prefix + "-entity-0"
    for start in range(0, 10000, 500):
        triples = []
        for i in range(start, min(start + 500, 10000)):
            node = I[prefix + "-entity-" + str(i)].n3()
            label = prefix + " root" if i == 0 else "Scale entity " + str(i)
            triples.append(
                f"{node} {RDF.type.n3()} {K.BusinessEntity.n3()}; {RDFS.label.n3()} {Literal(label).n3()}; {K.belongsToDomain.n3()} {I.risk.n3()}."
            )
            # A broad root plus a chain tests bounded branching and traversal depth.
            for target in ([i + 1] if i < 9999 else []) + (
                [i] if i > 0 and i < 101 else []
            ):
                source = I[root].n3() if target == i else node
                dest = I[prefix + "-entity-" + str(target)].n3()
                assertion = I[prefix + "-assertion-" + str(i) + "-" + str(target)].n3()
                triples.append(
                    f"{source} {K.partOf.n3()} {dest}. {assertion} {RDF.type.n3()} {K.GraphAssertion.n3()}; {RDF.subject.n3()} {source}; {RDF.predicate.n3()} {K.partOf.n3()}; {RDF.object.n3()} {dest}; {K.sourceAsset.n3()} {I[asset].n3()}; {K.sourceVersion.n3()} {Literal(digest).n3()}; {K.sourceLocator.n3()} {Literal(row['id']).n3()}."
                )
        response = httpx.post(
            settings().fuseki_url + "/update",
            data={
                "update": "INSERT DATA { GRAPH "
                + graph
                + " { "
                + " ".join(triples)
                + " } }"
            },
            timeout=30,
        )
        response.raise_for_status()
    with engine.begin() as conn:
        conn.execute(text("ANALYZE records"))
        conn.execute(text("ANALYZE business_rows"))
    scope = resolve_scope("admin")
    results = {}

    def measure(name, operation):
        values = []
        result = None
        for _ in range(5):
            started = time.perf_counter()
            result = operation()
            values.append(time.perf_counter() - started)
        results[name] = {
            "p50_seconds": round(sorted(values)[2], 4),
            "p95_seconds": round(max(values), 4),
            "samples": 5,
        }
        return result

    resolved = measure(
        "entity_resolution",
        lambda: resolve_entities(
            ToolContext(scope=scope, deadline=time.time() + 30), prefix + " root"
        ),
    )
    routed = measure(
        "rdf_frontier",
        lambda: traverse_graph(
            ToolContext(scope=scope, deadline=time.time() + 30),
            [root],
            ["partOf"],
            [],
            depth=3,
        ),
    )
    dataset = measure(
        "sql_page",
        lambda: execute_read(
            ToolContext(scope=scope, deadline=time.time() + 30),
            QueryDatasetAction(
                query=DatasetQuery(
                    asset_id=asset,
                    select=["record_id", "counterparty_name", "exposure_usd"],
                    limit=20,
                )
            ),
        ),
    )
    assert len(resolved.candidates) <= 3 and resolved.candidates[0].id == root
    assert len(routed.paths) <= 20 and len(routed.items) <= 50
    assert len(dataset.items) == 20 and dataset.has_more
    assert len(routed.model_dump_json().encode()) < 256000
    assert len(dataset.model_dump_json().encode()) < 256000
    results["bounded_results"] = {
        "entity_candidates": len(resolved.candidates),
        "graph_items": len(routed.items),
        "graph_paths": len(routed.paths),
        "graph_truncated": routed.truncated,
        "graph_bytes": len(routed.model_dump_json().encode()),
        "sql_rows": len(dataset.items),
        "sql_bytes": len(dataset.model_dump_json().encode()),
    }
    results["sql_query_plan"] = [
        dict(r)
        for r in query(
            "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT id,payload FROM business_rows WHERE asset_id=:asset AND id>:after ORDER BY id LIMIT 20",
            {"asset": asset, "after": prefix + "-row-050000"},
        )
    ]
    run = enqueue(
        scope,
        SearchRequest(
            query="Scale recovery",
            mode="extractive",
            intent_id=prefix.replace("_", "-") + "-intent",
        ),
    )
    assert claim_next(prefix + "-worker-a", run_id=run)
    assert claim_next(prefix + "-worker-b", run_id=run) is None
    query(
        "UPDATE search_runs SET lease_until=:past WHERE id=:id RETURNING id",
        {"past": time.time() - 1, "id": run},
    )
    recover_expired()
    assert claim_next(prefix + "-worker-b", run_id=run)
    try:
        assert_owned(run, prefix + "-worker-a")
    except LeaseLost:
        pass
    else:
        raise AssertionError("Old owner retained its lease")
    cancel_search(scope, run)
    try:
        assert_owned(run, prefix + "-worker-b")
    except LeaseLost:
        pass
    else:
        raise AssertionError("Cancellation did not revoke ownership")
    results["two_worker_recovery"] = {
        "exclusive_claim": True,
        "expired_lease_reclaimed": True,
        "old_owner_rejected": True,
        "cancelled_owner_rejected": True,
        "provider_requests": 0,
    }
    report = {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "postgres": "17.4",
            "fuseki": "5.4.0",
            "isolated_database": prefix,
            "isolated_container": prefix,
        },
        "fixture": {"rdf_entities": 10000, "sql_rows": 100000},
        "results": results,
        "limitations": [
            "Local bounded-operation measurements, not a production throughput or multi-tenant load claim.",
            "Worker checks use two independent ownership identities against real Postgres; no paid calls or process-kill replay are simulated.",
        ],
    }
    Path(output).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(results["bounded_results"]))


def parent(output, image):
    if Path(output).exists():
        raise ValueError("Refusing to overwrite an existing benchmark report")
    import httpx
    import psycopg
    from psycopg import sql
    from app.config import settings
    from app.db import query
    from sqlalchemy import create_engine, insert
    from app.catalog.models import metadata, records

    prefix = "kpm_bench_" + uuid.uuid4().hex[:12]
    original = settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    connection = psycopg.connect(original, autocommit=True)
    created_db = created_container = False
    try:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(prefix)))
        created_db = True
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                prefix,
                "--publish",
                "127.0.0.1::3030",
                image,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        created_container = True
        ports = json.loads(
            subprocess.check_output(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{json .NetworkSettings.Ports}}",
                    prefix,
                ],
                text=True,
            )
        )
        port = int(ports["3030/tcp"][0]["HostPort"])
        address = f"http://127.0.0.1:{port}/catalog"
        ready = False
        for _ in range(60):
            try:
                response = httpx.post(
                    address + "/query", data={"query": "ASK {}"}, timeout=2
                )
                if response.status_code == 200:
                    ready = True
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        if not ready:
            raise RuntimeError("Isolated Fuseki did not start")
        from sqlalchemy.engine import make_url

        cloned_url = make_url(settings().database_url).set(database=prefix)
        cloned = create_engine(cloned_url)
        metadata.create_all(cloned)
        snapshot = [
            dict(r) for r in query("SELECT id,kind,domain_id,payload FROM records")
        ]
        with cloned.begin() as conn:
            conn.execute(
                insert(records), [r for r in snapshot if r["kind"] == "domain"]
            )
            conn.execute(
                insert(records), [r for r in snapshot if r["kind"] != "domain"]
            )
        cloned.dispose()
        environment = {
            **os.environ,
            "DATABASE_URL": cloned_url.render_as_string(hide_password=False),
            "FUSEKI_URL": address,
            "LOCAL_SEARCH_WORKER": "false",
        }
        # Apply the real registered indexes and lease schema to the isolated database.
        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                "backend",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "head",
            ],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [sys.executable, __file__, "--child", prefix, "--output", output],
            env=environment,
            check=True,
        )
    finally:
        if created_container:
            subprocess.run(
                ["docker", "stop", prefix], check=True, capture_output=True, text=True
            )
        if created_db:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(prefix))
            )
        connection.close()
        if Path(output).exists():
            report = json.loads(Path(output).read_text())
            report["cleanup"] = {
                "isolated_database_removed": created_db,
                "isolated_container_removed": created_container,
            }
            Path(output).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Create isolated local benchmark resources and clean them up.",
    )
    parser.add_argument("--child", help=argparse.SUPPRESS)
    parser.add_argument("--output", default="docs/evaluations/2026-10-08-scale.json")
    parser.add_argument("--fuseki-image", default="atlas-knowledge-catalog-fuseki")
    args = parser.parse_args()
    if args.child:
        child(args.child, args.output)
    elif args.execute:
        parent(args.output, args.fuseki_image)
    else:
        parser.error("Use --execute to run this opt-in isolated benchmark")
