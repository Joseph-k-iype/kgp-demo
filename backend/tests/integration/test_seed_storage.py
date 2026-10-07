from app.seed import seed_demo
from app.storage.structured import preview_rows
from app.storage.objects import preview_object
from app.auth import resolve_scope
from app.catalog.service import list_catalog


def test_real_objects_rows_and_idempotent_seed():
    result = seed_demo()
    assert result["counts"] == {
        "domain": 11,
        "subdomain": 33,
        "product": 44,
        "asset": 150,
    }
    scope = resolve_scope("admin")
    assets = list_catalog(scope, {"kind": "asset", "page_size": 100})["items"]
    for domain in [
        "risk",
        "legal",
        "technology",
        "product",
        "operations",
        "data",
        "finance",
        "people",
        "third-party",
        "strategy",
        "customer",
    ]:
        assert preview_rows(scope, f"{domain}-asset-0")
        assert "Synthetic" in preview_object(scope, f"{domain}-asset-1")["text"]
    assert seed_demo()["counts"] == result["counts"]
