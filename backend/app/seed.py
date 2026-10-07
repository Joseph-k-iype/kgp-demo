import json
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert
from app.catalog.models import records, rows
from app.db import engine, query
from app.fixtures import make_fixtures, business_data, document_text
from app.storage.objects import put_object


def seed_demo():
    fixtures = make_fixtures()
    with engine.begin() as conn:
        for r in fixtures:
            conn.execute(
                insert(records)
                .values(**r)
                .on_conflict_do_nothing(index_elements=["id"])
            )
        for a in fixtures:
            if a["kind"] == "asset" and a["payload"]["type"] != "Document":
                for row in business_data(a):
                    conn.execute(
                        insert(rows)
                        .values(id=row["record_id"], asset_id=a["id"], payload=row)
                        .on_conflict_do_update(
                            index_elements=["id"], set_={"payload": row}
                        )
                    )
    for a in fixtures:
        if a["kind"] == "asset" and a["payload"]["type"] == "Document":
            original = document_text(a)
            put_object(a["payload"]["object_key"], original)
            directory = Path(__file__).resolve().parents[1] / "fixtures" / "documents"
            directory.mkdir(exist_ok=True)
            (directory / (a["id"] + ".txt")).write_text(original)
    counts = {
        k: query("SELECT count(*) AS n FROM records WHERE kind=:k", {"k": k})[0]["n"]
        for k in ["domain", "subdomain", "product", "asset"]
    }
    Path(__file__).resolve().parents[1].joinpath("fixtures/catalog.json").write_text(
        json.dumps(fixtures, indent=2)
    )
    return {"counts": counts, "stages": {"catalog": "ready", "objects": "ready"}}


if __name__ == "__main__":
    print(json.dumps(seed_demo()))
