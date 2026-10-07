from app.catalog.service import get_record
from app.db import query
from fastapi import HTTPException


def preview_rows(scope, asset_id, limit=20):
    a = get_record(scope, asset_id, "asset")
    if a["type"] == "Document" or not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid structured preview")
    return [
        r["payload"]
        for r in query(
            "SELECT payload FROM business_rows WHERE asset_id=:id ORDER BY id LIMIT :limit",
            {"id": asset_id, "limit": limit},
        )
    ]
