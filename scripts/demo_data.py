"""Export/validate/restore the synthetic catalog across its three source stores.

Runtime jobs, search runs, model receipts, credentials and derived indexes are
never exported. Restore is deliberately restricted to an empty catalog database.
"""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
import httpx
from rdflib import Graph
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from app.config import settings
from app.db import engine, query
from app.catalog.models import records, rows
from app.storage.objects import client

GRAPH_NAMES = ("vocabulary", "instances")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def export(directory):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "objects").mkdir()
    (directory / "rdf").mkdir()
    # One PostgreSQL snapshot keeps the catalog/rows mutually consistent.
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        with conn.begin():
            catalog = [
                dict(r)
                for r in conn.execute(
                    text(
                        "SELECT id,kind,domain_id,payload FROM records ORDER BY kind,id"
                    )
                ).mappings()
            ]
            source_rows = [
                dict(r)
                for r in conn.execute(
                    text(
                        "SELECT id,asset_id,payload FROM business_rows ORDER BY asset_id,id"
                    )
                ).mappings()
            ]
    write_json(directory / "catalog.json", catalog)
    write_json(directory / "business-rows.json", source_rows)
    objects = []
    store = client()
    for asset in catalog:
        if asset["kind"] != "asset" or asset["payload"]["type"] != "Document":
            continue
        key = asset["payload"]["object_key"]
        info = store.stat_object(settings().bucket, key)
        response = store.get_object(settings().bucket, key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
        sha = digest(data)
        if info.metadata.get("x-amz-meta-sha256") != sha:
            raise ValueError("Document changed or its managed digest is invalid")
        file = "objects/" + asset["id"] + ".txt"
        (directory / file).write_bytes(data)
        objects.append(
            {
                "asset_id": asset["id"],
                "key": key,
                "file": file,
                "sha256": sha,
                "bytes": len(data),
                "content_type": info.content_type,
            }
        )
    graphs = []
    for name in GRAPH_NAMES:
        response = httpx.get(
            settings().fuseki_url + "/data",
            params={"graph": "https://atlas.example/graphs/" + name},
            headers={"Accept": "text/turtle"},
            timeout=30,
        )
        response.raise_for_status()
        file = "rdf/" + name + ".ttl"
        (directory / file).write_bytes(response.content)
        graphs.append({"name": name, "file": file, "sha256": digest(response.content)})
    write_json(
        directory / "manifest.json",
        {
            "format_version": 1,
            "synthetic": True,
            "catalog_records": len(catalog),
            "business_rows": len(source_rows),
            "objects": objects,
            "graphs": graphs,
            "files": [
                {"file": f, "sha256": digest((directory / f).read_bytes())}
                for f in ["catalog.json", "business-rows.json"]
            ],
        },
    )
    return validate(directory)


def validate(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["format_version"] != 1 or manifest["synthetic"] is not True:
        raise ValueError("Unsupported or non-synthetic snapshot")
    for entry in manifest["files"] + manifest["objects"] + manifest["graphs"]:
        file = (directory / entry["file"]).resolve()
        if (
            not file.is_relative_to(directory.resolve())
            or digest(file.read_bytes()) != entry["sha256"]
        ):
            raise ValueError("Snapshot file escaped its directory or failed its digest")
    catalog = json.loads((directory / "catalog.json").read_text())
    data = json.loads((directory / "business-rows.json").read_text())
    ids = {r["id"] for r in catalog}
    if (
        len(ids) != len(catalog)
        or len(catalog) != manifest["catalog_records"]
        or len(data) != manifest["business_rows"]
    ):
        raise ValueError("Snapshot counts or IDs are invalid")
    if any(r["domain_id"] and r["domain_id"] not in ids for r in catalog) or any(
        r["asset_id"] not in ids for r in data
    ):
        raise ValueError("Snapshot references are invalid")
    for obj in manifest["objects"]:
        asset = next(r for r in catalog if r["id"] == obj["asset_id"])
        if (
            asset["kind"] != "asset"
            or obj["key"] != asset["payload"]["object_key"]
            or not obj["key"].startswith(asset["domain_id"] + "/")
            or ".." in obj["key"]
        ):
            raise ValueError("Invalid scoped object key")
    triple_counts = {
        g["name"]: len(Graph().parse(directory / g["file"], format="turtle"))
        for g in manifest["graphs"]
    }
    return {
        "catalog_records": len(catalog),
        "business_rows": len(data),
        "objects": len(manifest["objects"]),
        "rdf_triples": triple_counts,
    }


def restore(directory):
    counts = validate(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    catalog = json.loads((directory / "catalog.json").read_text())
    data = json.loads((directory / "business-rows.json").read_text())
    with engine.begin() as conn:
        conn.execute(text("LOCK TABLE records, business_rows IN EXCLUSIVE MODE"))
        if conn.execute(text("SELECT count(*) FROM records")).scalar_one():
            raise ValueError(
                "Restore requires an empty catalog; it never replaces existing records"
            )
        for r in sorted(catalog, key=lambda r: r["kind"] != "domain"):
            conn.execute(insert(records).values(**r))
        for offset in range(0, len(data), 200):
            conn.execute(insert(rows), data[offset : offset + 200])
    store = client()
    if not store.bucket_exists(settings().bucket):
        store.make_bucket(settings().bucket)
    for obj in manifest["objects"]:
        content = (directory / obj["file"]).read_bytes()
        store.put_object(
            settings().bucket,
            obj["key"],
            BytesIO(content),
            len(content),
            content_type=obj["content_type"],
            metadata={"sha256": obj["sha256"]},
        )
    for graph in manifest["graphs"]:
        httpx.put(
            settings().fuseki_url + "/data",
            params={"graph": "https://atlas.example/graphs/" + graph["name"]},
            content=(directory / graph["file"]).read_bytes(),
            headers={"Content-Type": "text/turtle"},
            timeout=30,
        ).raise_for_status()
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["export", "validate", "restore"])
    parser.add_argument("--directory", type=Path, default=Path("data/demo"))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required for restore; target catalog must be empty",
    )
    args = parser.parse_args()
    if args.operation == "restore" and not args.execute:
        parser.error("Use --execute for an explicitly selected empty restore target")
    print(json.dumps(globals()[args.operation](args.directory), indent=2))
