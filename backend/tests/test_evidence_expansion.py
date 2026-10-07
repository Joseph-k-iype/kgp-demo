from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.retrieval import service


def test_provenance_expansion_batches_reads_and_preserves_scope(monkeypatch):
    scope = SimpleNamespace(domain_ids=['risk'])
    monkeypatch.setattr(service, 'all_records', lambda *a: [
        {'id': 'risk-asset-0', 'indexing_state': 'ready'}
    ])
    calls = []
    def request(method, path, body=None, **kwargs):
        calls.append((method, path, body))
        return {'docs': [{'_id': id, 'found': True, '_source': {
            'id': id, 'asset_id': 'risk-asset-0', 'domain_id': 'risk', 'vector': [1]
        }} for id in body['ids']]}
    monkeypatch.setattr(service, 'request', request)
    ids = ['risk-asset-0:rows-0', 'risk-asset-0:rows-1']
    result = service.expand_evidence(scope, [{'id': id} for id in ids])
    assert [item['id'] for item in result] == ids
    assert all('vector' not in item for item in result)
    assert len(calls) == 1 and calls[0][1].endswith('/_mget')
    with pytest.raises(HTTPException):
        service.expand_evidence(scope, [{'id': 'legal-asset-0:rows-0'}])
    assert len(calls) == 1
