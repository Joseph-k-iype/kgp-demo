import time
from app.agent.service import start_search,get_search,cancel_search
from app.auth import resolve_scope
from app.contracts import SearchRequest
from fastapi import HTTPException
import pytest

def await_run(scope,id):
    for _ in range(90):
        r=get_search(scope,id)
        if r['status'] not in ['pending','running']:return r
        time.sleep(0.5)
    raise AssertionError('search did not finish')

def test_extractive_run_has_real_citations_and_owner_scope():
    scope=resolve_scope('admin')
    run=start_search(scope,SearchRequest(query='counterparty exposure due diligence',mode='extractive'))
    result=await_run(scope,run['run_id'])
    assert result['status']=='completed',result
    assert result['statements'] and result['evidence']
    assert all(s['evidence_ids'] for s in result['statements'])
    assert {'plan','retrieve','synthesize','validate'} <= {e['stage'] for e in result['events']}
    assert get_search(scope,run['run_id'])['statements']==result['statements']
    with pytest.raises(HTTPException):get_search(resolve_scope('legal'),run['run_id'])

def test_no_key_is_explicit():
    from app.config import settings
    if settings().openai_api_key:pytest.skip('Live key configured')
    scope=resolve_scope('admin')
    run=start_search(scope,SearchRequest(query='counterparty exposure',mode='openai'))
    r=await_run(scope,run['run_id'])
    assert r['status']=='configuration_required'
    assert not r['statements']
