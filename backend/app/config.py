from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://atlas:atlas_local_demo@127.0.0.1:56432/atlas"
    )
    minio_endpoint: str = "127.0.0.1:59010"
    minio_access_key: str = "atlasdemo"
    minio_secret_key: str = "atlas_local_demo"
    bucket: str = "atlas-knowledge"
    fuseki_url: str = "http://127.0.0.1:53030/catalog"
    opensearch_url: str = "http://127.0.0.1:59200"
    llm_provider: Literal["openrouter", "openai"] = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-v3.2"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    mcp_token: str = "atlas-local-analyst-token"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    index_name: str = "atlas-evidence-v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def llm_key(self):
        return (
            self.openrouter_api_key
            if self.llm_provider == "openrouter"
            else self.openai_api_key
        )

    @property
    def llm_model(self):
        return (
            self.openrouter_model
            if self.llm_provider == "openrouter"
            else self.openai_model
        )


@lru_cache
def settings():
    return Settings()
