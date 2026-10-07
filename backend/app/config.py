from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://atlas:atlas_local_demo@127.0.0.1:56432/atlas'
    minio_endpoint: str = '127.0.0.1:59010'
    minio_access_key: str = 'atlasdemo'
    minio_secret_key: str = 'atlas_local_demo'
    bucket: str = 'atlas-knowledge'
    fuseki_url: str = 'http://127.0.0.1:53030/catalog'
    opensearch_url: str = 'http://127.0.0.1:59200'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    mcp_token: str = 'atlas-local-analyst-token'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    embedding_revision: str = 'c9745ed1d9f207416be6d2e6f8de32d1f16199bf'
    index_name: str = 'atlas-evidence-v1'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

@lru_cache
def settings():
    return Settings()
