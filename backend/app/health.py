import httpx
from concurrent.futures import ThreadPoolExecutor
from app.config import settings
from app.db import query


def service_health():
    cfg = settings()

    def check(name):
        try:
            if name == "postgres":
                query("SELECT 1")
            else:
                url = {
                    "minio": f"http://{cfg.minio_endpoint}/minio/health/live",
                    "fuseki": f"{cfg.fuseki_url}/query?query=ASK%7B%7D",
                    "opensearch": f"{cfg.opensearch_url}/_cluster/health",
                }[name]
                httpx.get(url, timeout=3).raise_for_status()
            return name, {"status": "ready"}
        except Exception:
            return name, {"status": "unavailable"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        services = dict(pool.map(check, ["postgres", "minio", "fuseki", "opensearch"]))
    return {
        "services": services,
        "llm": {
            "configured": bool(cfg.llm_key),
            "provider": cfg.llm_provider,
            "model": cfg.llm_model,
        },
        "embedding_model": cfg.embedding_model,
        "mcp": "/mcp",
    }
