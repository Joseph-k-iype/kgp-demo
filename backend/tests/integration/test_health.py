from app.health import service_health

def test_real_services_ready_and_no_secrets():
    result = service_health()
    assert all(result['services'][name]['status'] == 'ready' for name in ['postgres', 'minio', 'fuseki', 'opensearch'])
    assert 'password' not in str(result).lower()
