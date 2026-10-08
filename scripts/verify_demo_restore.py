"""Restore the committed snapshot into isolated stores, verify, then clean up."""

import json, os, subprocess, sys, time, uuid
from pathlib import Path
import httpx, psycopg
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.catalog.models import metadata
from app.config import settings
from app.storage.objects import client

if __name__ == "__main__":
    prefix = "kpm-restore-" + uuid.uuid4().hex[:12]
    url = make_url(settings().database_url)
    connection = psycopg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False),
        autocommit=True,
    )
    db = container = bucket = False
    store = client()
    report = {}
    try:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(prefix)))
        db = True
        cloned = create_engine(url.set(database=prefix))
        metadata.create_all(cloned)
        cloned.dispose()
        store.make_bucket(prefix)
        bucket = True
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
                "atlas-knowledge-catalog-fuseki",
            ],
            check=True,
            capture_output=True,
        )
        container = True
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
        address = "http://127.0.0.1:" + ports["3030/tcp"][0]["HostPort"] + "/catalog"
        for _ in range(60):
            try:
                if (
                    httpx.post(
                        address + "/query", data={"query": "ASK {}"}, timeout=2
                    ).status_code
                    == 200
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        env = {
            **os.environ,
            "DATABASE_URL": url.set(database=prefix).render_as_string(
                hide_password=False
            ),
            "BUCKET": prefix,
            "FUSEKI_URL": address,
        }
        restored = subprocess.run(
            [sys.executable, "scripts/demo_data.py", "restore", "--execute"],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(restored.stdout)
        clone = create_engine(url.set(database=prefix))
        with clone.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM records")).scalar_one()
                == report["catalog_records"]
            )
            assert (
                conn.execute(text("SELECT count(*) FROM business_rows")).scalar_one()
                == report["business_rows"]
            )
        clone.dispose()
        checked = subprocess.run(
            [
                sys.executable,
                "scripts/demo_data.py",
                "export",
                "--directory",
                "/tmp/" + prefix,
            ],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(checked.stdout) == report
        original = json.loads(Path("data/demo/manifest.json").read_text())
        roundtrip = json.loads(Path("/tmp/" + prefix + "/manifest.json").read_text())
        assert original["objects"] == roundtrip["objects"]
        assert json.loads(Path("data/demo/catalog.json").read_text()) == json.loads(
            Path("/tmp/" + prefix + "/catalog.json").read_text()
        )
        assert json.loads(
            Path("data/demo/business-rows.json").read_text()
        ) == json.loads(Path("/tmp/" + prefix + "/business-rows.json").read_text())
        report["catalog_rows_objects_roundtrip_equal"] = True
    finally:
        if container:
            subprocess.run(["docker", "stop", prefix], check=True, capture_output=True)
        if bucket:
            for obj in store.list_objects(prefix, recursive=True):
                store.remove_object(prefix, obj.object_name)
            store.remove_bucket(prefix)
        if db:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(prefix))
            )
        connection.close()
    report["isolated_resources_removed"] = True
    Path("docs/evaluations/2026-10-08-data-restore.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
