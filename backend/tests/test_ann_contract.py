from app.retrieval.index import content_mapping
from app.knowledge.retrieval import vector_query


def test_content_vector_is_a_filtered_lucene_hnsw_index():
    mapping = content_mapping()
    assert mapping["settings"]["index.knn"] is True
    vector = mapping["mappings"]["properties"]["vector"]
    assert vector["dimension"] == 384
    assert vector["method"]["engine"] == "lucene"
    assert vector["method"]["name"] == "hnsw"
    filters = [{"terms": {"domain_id": ["finance"]}}]
    query = vector_query([0.0] * 384, filters)
    assert query["knn"]["vector"]["filter"]["bool"]["filter"] == filters
    assert query["knn"]["vector"]["k"] == 40
    assert "script_score" not in query
