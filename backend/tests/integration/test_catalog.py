import pytest
from fastapi import HTTPException
from app.catalog.service import (
    list_catalog,
    get_product,
    get_asset,
    update_metadata,
    list_domains,
)
from app.auth import resolve_scope


def test_filters_scope_and_persisted_edits():
    admin = resolve_scope("admin")
    analyst = resolve_scope("risk")
    domains = list_domains(admin)
    assert len(domains) == 11
    result = list_catalog(
        admin, {"domain_id": "risk", "kind": "product", "page_size": 20}
    )
    assert result["total"] == 4
    product = result["items"][0]
    assert get_product(admin, product["id"])["assets"]
    update_metadata(admin, "project", "risk-project", {"budget": 950000})
    assert (
        list_catalog(admin, {"kind": "project", "text": "Counterparty"})["items"][0][
            "budget"
        ]
        == 950000
    )
    with pytest.raises(HTTPException) as exc:
        get_asset(analyst, "legal-asset-0")
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        update_metadata(
            resolve_scope("analyst"), "project", "risk-project", {"budget": 1}
        )


def test_project_scope_and_malformed_filters():
    from pydantic import ValidationError

    admin = resolve_scope("admin")
    with pytest.raises(HTTPException) as exc:
        update_metadata(
            admin, "project", "risk-project", {"subdomain_id": "legal-sub-0"}
        )
    assert exc.value.status_code == 422
    with pytest.raises(ValidationError):
        list_catalog(admin, {"page_size": 1001})
    with pytest.raises(HTTPException):
        update_metadata(admin, "project", "risk-project", {"budget": -1})


def test_source_path_cannot_escape_asset_scope():
    from app.storage.objects import preview_object

    with pytest.raises(HTTPException):
        preview_object(resolve_scope("legal"), "risk-asset-1")


def test_product_source_filter_matches_constituent_assets():
    page = list_catalog(
        resolve_scope("admin"),
        {"kind": "product", "source_id": "risk-minio", "page_size": 20},
    )
    assert page["total"] == 4
    assert all(p["domain_id"] == "risk" for p in page["items"])


def test_metadata_patch_rejects_wrong_field_types():
    scope = resolve_scope("admin")
    with pytest.raises(HTTPException):
        update_metadata(scope, "project", "risk-project", {"description": 123})
    with pytest.raises(HTTPException):
        update_metadata(scope, "gap", "risk-gap", {"tags": "not-a-list"})
