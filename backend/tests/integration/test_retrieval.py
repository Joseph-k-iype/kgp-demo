from app.retrieval.service import index_assets, retrieve, get_evidence
from app.auth import resolve_scope
from app.config import settings
import httpx
import pytest
from fastapi import HTTPException

def test_real_vectors_cross_source_and_scope():
    report=index_assets([])
    assert report['indexed_assets']==150
    result=retrieve(resolve_scope('admin'),'counterparty exposure due diligence',['Counterparty'],limit=10)
    assert result
    assert {'structured','document'} <= {r['provenance']['type'] for r in result}
    assert all(r['id'] and r['asset_id'] for r in result)
    vector=httpx.get(settings().opensearch_url+'/'+settings().index_name+'/_search',params={'size':1}).json()['hits']['hits'][0]['_source']['vector']
    assert len(vector)==384
    scoped=retrieve(resolve_scope('legal'),'counterparty exposure due diligence',['Counterparty'])
    assert all(r['domain_id']=='legal' for r in scoped)
    with pytest.raises(HTTPException):get_evidence(resolve_scope('legal'),'risk-asset-0:rows-0')
