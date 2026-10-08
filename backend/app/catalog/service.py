import json
from fastapi import HTTPException
from pydantic import ValidationError
from app.db import query
from app.contracts import CatalogQuery
from app.auth import can_view, require_edit


def unpack(row):
    return {
        **row["payload"],
        "id": row["id"],
        "kind": row["kind"],
        "domain_id": row["domain_id"],
        "updated_at": str(row["updated_at"]),
    }


def all_records(scope, kind=None):
    rows = query(
        "SELECT * FROM records WHERE (CAST(:kind AS text) IS NULL OR kind=CAST(:kind AS text)) AND (domain_id IS NULL OR domain_id=ANY(:domains))",
        {"kind": kind, "domains": scope.domain_ids},
    )
    return [unpack(row) for row in rows]


def get_record(scope, record_id, kind=None):
    rows = query("SELECT * FROM records WHERE id=:id", {"id": record_id})
    if not rows or not can_view(scope, rows[0]) or (kind and rows[0]["kind"] != kind):
        raise HTTPException(404, "Record not found in your scope")
    return unpack(rows[0])


def list_catalog(scope, filters):
    f = CatalogQuery.model_validate(filters)
    predicates = ["r.kind=:kind", "(r.domain_id IS NULL OR r.domain_id=ANY(:domains))"]
    params = {
        "kind": f.kind,
        "domains": scope.domain_ids,
        "limit": f.page_size,
        "offset": (f.page - 1) * f.page_size,
    }
    for field in [
        "domain_id",
        "subdomain_id",
        "source_id",
        "owner_id",
        "status",
        "classification",
    ]:
        value = getattr(f, field)
        if not value:
            continue
        params[field] = value
        if field == "source_id" and f.kind == "product":
            predicates.append(
                "EXISTS (SELECT 1 FROM records a WHERE a.kind='asset' AND a.domain_id=ANY(:domains) AND a.payload->>'source_id'=:source_id AND a.payload->'product_ids' @> jsonb_build_array(r.id))"
            )
        elif field == "domain_id":
            predicates.append("r.domain_id=:domain_id")
        else:
            predicates.append("r.payload->>'" + field + "'= :" + field)
    if f.asset_type:
        predicates.append("r.payload->>'type'=:asset_type")
        params["asset_type"] = f.asset_type
    if f.quality:
        predicates.append(
            "COALESCE((r.payload->>'quality')::numeric,100) "
            + ("<90" if f.quality == "attention" else ">=90")
        )
    for n, term in enumerate(f.text.lower().split()):
        key = "term" + str(n)
        params[key] = term
        predicates.append(
            "strpos(lower(COALESCE(r.payload->>'name','') || ' ' || COALESCE(r.payload->>'description','') || ' ' || COALESCE((SELECT string_agg(t,' ') FROM jsonb_array_elements_text(COALESCE(r.payload->'tags','[]'::jsonb)) t),'')),:"
            + key
            + ")>0"
        )
    where = " AND ".join(predicates)
    total = query("SELECT count(*) AS n FROM records r WHERE " + where, params)[0]["n"]
    order = {
        "name": "r.payload->>'name',r.id",
        "quality": "COALESCE((r.payload->>'quality')::numeric,100),r.id",
        "updated": "r.updated_at DESC,r.id",
    }[f.sort]
    items = [
        unpack(r)
        for r in query(
            "SELECT r.* FROM records r WHERE "
            + where
            + " ORDER BY "
            + order
            + " LIMIT :limit OFFSET :offset",
            params,
        )
    ]
    if f.kind == "gap":
        for gap in items:
            gap["quality_issues"] = query(
                "SELECT count(*) AS n FROM records WHERE kind='issue' AND domain_id=ANY(:domains) AND payload->>'status'='Open' AND payload->>'asset_id'=ANY(:ids)",
                {"domains": scope.domain_ids, "ids": gap.get("asset_ids", [])},
            )[0]["n"]
            gap["coverage"] = (
                round(gap["covered"] / gap["required"] * 100)
                if gap.get("required")
                else 0
            )
    return {"items": items, "total": total, "page": f.page, "page_size": f.page_size}


def get_product(scope, product_id):
    p = get_record(scope, product_id, "product")
    for key, kind in [("assets", "asset"), ("projects", "project"), ("gaps", "gap")]:
        predicate = (
            "payload->'product_ids' @> CAST(:products AS jsonb)"
            if kind == "asset"
            else "payload->>'product_id'=:id"
        )
        found = query(
            "SELECT * FROM records WHERE kind=:kind AND domain_id=ANY(:domains) AND "
            + predicate
            + " ORDER BY id LIMIT 101",
            {
                "kind": kind,
                "domains": scope.domain_ids,
                "products": json.dumps([product_id]),
                "id": product_id,
            },
        )
        p[key] = [unpack(row) for row in found[:100]]
        if len(found) > 100:
            p[key + "_truncated"] = True
    return p


def get_asset(scope, asset_id):
    a = get_record(scope, asset_id, "asset")
    a["source"] = get_record(scope, a["source_id"], "source")
    a["issues"] = [
        unpack(r)
        for r in query(
            "SELECT * FROM records WHERE kind='issue' AND domain_id=ANY(:domains) AND payload->>'asset_id'=:asset ORDER BY id LIMIT 100",
            {"domains": scope.domain_ids, "asset": asset_id},
        )
    ]
    a["products"] = [
        unpack(r)
        for r in query(
            "SELECT * FROM records WHERE kind='product' AND id=ANY(:ids) AND domain_id=ANY(:domains) ORDER BY id LIMIT 100",
            {"domains": scope.domain_ids, "ids": a.get("product_ids", [])},
        )
    ]
    return a


def list_domains(scope):
    domains = [
        unpack(r)
        for r in query(
            "SELECT * FROM records WHERE kind='domain' AND (domain_id IS NULL OR domain_id=ANY(:domains)) ORDER BY id LIMIT 100",
            {"domains": scope.domain_ids},
        )
    ]
    counts = {
        (r["domain_id"], r["kind"]): r["n"]
        for r in query(
            "SELECT domain_id,kind,count(*) AS n FROM records WHERE kind IN ('asset','product') AND domain_id=ANY(:domains) GROUP BY domain_id,kind",
            {"domains": scope.domain_ids},
        )
    }
    subdomains = [
        unpack(r)
        for r in query(
            "SELECT * FROM records WHERE kind='subdomain' AND domain_id=ANY(:domains) ORDER BY id LIMIT 1000",
            {"domains": scope.domain_ids},
        )
    ]
    for d in domains:
        d["product_count"] = counts.get((d["id"], "product"), 0)
        d["asset_count"] = counts.get((d["id"], "asset"), 0)
        d["subdomains"] = [s for s in subdomains if s["domain_id"] == d["id"]]
    return domains


def update_metadata(scope, kind, record_id, patch):
    record = get_record(scope, record_id, kind)
    require_edit(scope, record, kind)
    allowed = {
        "project": {
            "name",
            "description",
            "status",
            "budget",
            "currency",
            "sponsor",
            "subdomain_id",
        },
        "gap": {"description", "status", "owner", "tags"},
        "role": {"role", "domain_ids"},
        "product": {"description", "status", "tags", "steward"},
    }
    if kind not in allowed or not patch or set(patch) - allowed[kind]:
        raise HTTPException(422, "Unsupported edit")
    for field in [
        "name",
        "description",
        "status",
        "sponsor",
        "owner",
        "steward",
        "role",
        "subdomain_id",
    ]:
        if field in patch and (
            not isinstance(patch[field], str) or len(patch[field]) > 20000
        ):
            raise HTTPException(422, "Invalid text field")
    if "tags" in patch and (
        not isinstance(patch["tags"], list)
        or len(patch["tags"]) > 30
        or any(not isinstance(t, str) or len(t) > 200 for t in patch["tags"])
    ):
        raise HTTPException(422, "Invalid tags")
    if "budget" in patch and (
        not isinstance(patch["budget"], (int, float))
        or isinstance(patch["budget"], bool)
        or not 0 <= patch["budget"] <= 1e12
    ):
        raise HTTPException(422, "Invalid budget")
    if (
        "subdomain_id" in patch
        and get_record(scope, patch["subdomain_id"], "subdomain")["domain_id"]
        != record["domain_id"]
    ):
        raise HTTPException(422, "Subdomain must belong to product domain")
    if "status" in patch and patch["status"] not in [
        "Active",
        "Draft",
        "In development",
        "Planned",
        "In progress",
        "Completed",
        "Open",
        "Resolved",
    ]:
        raise HTTPException(422, "Invalid status")
    if "role" in patch and patch["role"] not in [
        "Administrator",
        "Analyst",
        "Domain steward",
        "Delegate",
        "Product owner",
        "Reviewer",
    ]:
        raise HTTPException(422, "Invalid role")
    if "domain_ids" in patch:
        from app.auth import DOMAINS

        if not isinstance(patch["domain_ids"], list) or any(
            d not in DOMAINS for d in patch["domain_ids"]
        ):
            raise HTTPException(422, "Invalid domain scope")
    if kind == "role":
        patch["scope_version"] = record.get("scope_version", 1) + 1
    query(
        "UPDATE records SET payload=payload || CAST(:patch AS jsonb), updated_at=now() WHERE id=:id RETURNING id",
        {"id": record_id, "patch": json.dumps(patch)},
    )
    if kind == "product":
        query(
            "UPDATE records SET payload=jsonb_set(payload,'{indexing_state}','\"stale\"') WHERE kind='asset' AND payload->'product_ids' @> CAST(:p AS jsonb) RETURNING id",
            {"p": json.dumps([record_id])},
        )
    return get_record(scope, record_id)


def overview(scope):
    kinds = ["domain", "product", "asset", "source", "gap", "project", "issue"]
    grouped = {
        r["kind"]: r["n"]
        for r in query(
            "SELECT kind,count(*) AS n FROM records WHERE (domain_id IS NULL OR domain_id=ANY(:domains)) GROUP BY kind",
            {"domains": scope.domain_ids},
        )
    }
    return {
        "counts": {k: grouped.get(k, 0) for k in kinds},
        "domains": list_domains(scope),
        "attention": [
            unpack(r)
            for r in query(
                "SELECT * FROM records WHERE kind='gap' AND domain_id=ANY(:domains) AND payload->>'status'='Open' ORDER BY id LIMIT 6",
                {"domains": scope.domain_ids},
            )
        ],
        "recent": [
            unpack(r)
            for r in query(
                "SELECT * FROM records WHERE kind='product' AND domain_id=ANY(:domains) ORDER BY updated_at DESC,id LIMIT 5",
                {"domains": scope.domain_ids},
            )
        ],
        "indexed": query(
            "SELECT count(*) AS n FROM records WHERE kind='asset' AND domain_id=ANY(:domains) AND payload->>'indexing_state'='ready'",
            {"domains": scope.domain_ids},
        )[0]["n"],
    }
