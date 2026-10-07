import pytest
from fastapi import HTTPException
from app.catalog.service import list_catalog, get_product, get_asset, update_metadata, list_domains
from app.auth import resolve_scope

def test_filters_scope_and_persisted_edits():
    admin = resolve_scope('admin')
    analyst = resolve_scope('risk')
    domains = list_domains(admin)
    assert len(domains) == 11
    result = list_catalog(admin, {'domain_id': 'risk', 'kind': 'product', 'page_size': 20})
    assert result['total'] == 4
    product = result['items'][0]
    assert get_product(admin, product['id'])['assets']
    update_metadata(admin, 'project', 'risk-project', {'budget': 950000})
    assert list_catalog(admin, {'kind':'project', 'text': 'Counterparty'})['items'][0]['budget'] == 950000
    with pytest.raises(HTTPException) as exc:
        get_asset(analyst, 'legal-asset-0')
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        update_metadata(resolve_scope('analyst'), 'project', 'risk-project', {'budget': 1})
