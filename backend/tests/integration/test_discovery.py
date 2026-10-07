import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import resolve_scope
from app.agent.service import start_search, get_search
from app.contracts import SearchRequest
from app.retrieval.service import get_evidence

client = TestClient(app)
headers = {'Authorization': 'Bearer atlas-session-admin'}


def test_discovery_returns_real_products_data_and_documents():
    response = client.get('/discovery/search', params={'q': 'counterparty', 'domain_id': 'risk', 'page_size': 30}, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert {'product', 'data', 'document'} <= {item['kind'] for item in result['items']}
    assert 'risk-product-0' in {item['id'] for item in result['items']}
    assert all(item['domain_id'] == 'risk' for item in result['items'])
    assert len({item['id'] for item in result['items']}) == len(result['items'])
    for item in result['items']:
        if item.get('evidence_id'):
            evidence = get_evidence(resolve_scope('admin'), item['evidence_id'])
            assert evidence['asset_id'] == item['asset_id']
            assert evidence['provenance']['location']


def test_discovery_pages_are_stable_and_filtered():
    params = {'q': 'counterparty', 'type': 'data', 'sort': 'name', 'page_size': 1}
    first = client.get('/discovery/search', params=params, headers=headers).json()
    repeat = client.get('/discovery/search', params=params, headers=headers).json()
    second = client.get('/discovery/search', params={**params, 'page': 2}, headers=headers).json()
    assert first['items'] == repeat['items']
    assert first['items'][0]['kind'] == 'data'
    assert second['items'][0]['id'] != first['items'][0]['id']
    assert first['has_more'] is True
    assert first['returned_count'] == 1


def test_discovery_rejects_denied_domain_and_scopes_results():
    legal = {'Authorization': 'Bearer atlas-session-legal'}
    response = client.get('/discovery/search', params={'q': 'counterparty', 'domain_id': 'risk'}, headers=legal)
    assert response.status_code == 404
    allowed = client.get('/discovery/search', params={'q': 'contract'}, headers=legal)
    assert allowed.status_code == 200
    assert allowed.json()['items']
    assert all(item['domain_id'] == 'legal' for item in allowed.json()['items'])


@pytest.mark.parametrize('params', [{'q':'  '}, {'q':'x'*2001}, {'q':'risk','page':0}, {'q':'risk','page_size':31}, {'q':'risk','type':'invalid'}])
def test_discovery_validates_input(params):
    assert client.get('/discovery/search', params=params, headers=headers).status_code == 422


def test_ai_rejects_denied_domain_before_creating_run():
    response = client.post('/search/runs', json={'query':'counterparty exposure','mode':'extractive','domain_id':'risk'}, headers={'Authorization':'Bearer atlas-session-legal'})
    assert response.status_code == 404


def test_ai_uses_selected_domain_for_every_retrieval():
    scope = resolve_scope('admin')
    run = start_search(scope, SearchRequest(query='counterparty exposure due diligence', mode='extractive', domain_id='risk'))
    for _ in range(160):
        result = get_search(scope, run['run_id'])
        if result['status'] not in ['pending','running']:
            break
        time.sleep(.5)
    assert result['status'] == 'completed', result
    assert result['domain_id'] == 'risk'
    assert result['evidence']
    assert all(item['domain_id'] == 'risk' for item in result['evidence'])
