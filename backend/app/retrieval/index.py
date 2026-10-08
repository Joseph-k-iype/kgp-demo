import httpx
from app.config import settings


def request(method, path, body=None, timeout=45):
    r = httpx.request(
        method, settings().opensearch_url + path, json=body, timeout=timeout
    )
    r.raise_for_status()
    return r.json()


def ensure_index(timeout=10):
    c = settings()
    r = httpx.get(c.opensearch_url + "/" + c.index_name, timeout=timeout)
    if r.status_code == 404:
        request(
            "PUT",
            "/" + c.index_name,
            {
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "_meta": {
                        "model": c.embedding_model,
                        "revision": c.embedding_revision,
                    },
                    "properties": {
                        "id": {"type": "keyword"},
                        "asset_id": {"type": "keyword"},
                        "domain_id": {"type": "keyword"},
                        "concept_iris": {"type": "keyword"},
                        "product_ids": {"type": "keyword"},
                        "text": {"type": "text"},
                        "content_hash": {"type": "keyword"},
                        "vector": {"type": "knn_vector", "dimension": 384},
                    },
                },
            },
        )
    else:
        r.raise_for_status()
        mapping = r.json()[c.index_name]["mappings"]
        if (
            mapping.get("_meta")
            != {"model": c.embedding_model, "revision": c.embedding_revision}
            or mapping["properties"]["vector"]["dimension"] != 384
        ):
            raise ValueError(
                "Embedding model or index dimension mismatch; rebuild with a new index name"
            )


def ensure_content_index(timeout=10):
    c = settings()
    alias = c.content_index_name
    response = httpx.get(c.opensearch_url + "/_alias/" + alias, timeout=timeout)
    if response.status_code == 404:
        physical = alias + "-v2-000001"
        exists = httpx.head(c.opensearch_url + "/" + physical, timeout=timeout)
        if exists.status_code == 404:
            request(
                "PUT",
                "/" + physical,
                {
                    "settings": {
                        "number_of_shards": c.content_index_shards,
                        "number_of_replicas": c.content_index_replicas,
                    },
                    "mappings": {
                        "_meta": {
                            "schema_version": 2,
                            "model": c.embedding_model,
                            "revision": c.embedding_revision,
                        },
                        "properties": {
                            "id": {"type": "keyword"},
                            "asset_id": {"type": "keyword"},
                            "domain_id": {"type": "keyword"},
                            "content_kind": {"type": "keyword"},
                            "text": {"type": "text"},
                            "source_ref": {
                                "properties": {
                                    "asset_id": {"type": "keyword"},
                                    "domain_id": {"type": "keyword"},
                                    "version": {"type": "keyword"},
                                    "locator": {"type": "keyword"},
                                }
                            },
                            "vector": {"type": "knn_vector", "dimension": 384},
                        },
                    },
                },
            )
        else:
            exists.raise_for_status()
        request(
            "POST",
            "/_aliases",
            {"actions": [{"add": {"index": physical, "alias": alias}}]},
        )
    else:
        response.raise_for_status()
    mapping = httpx.get(c.opensearch_url + "/" + alias + "/_mapping", timeout=timeout)
    mapping.raise_for_status()
    indexes = mapping.json()
    for value in indexes.values():
        meta = value["mappings"].get("_meta", {})
        if meta != {
            "schema_version": 2,
            "model": c.embedding_model,
            "revision": c.embedding_revision,
        }:
            raise ValueError("Content index schema/model mismatch")
    return alias
