from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class ScopeContext(BaseModel):
    person_id: str
    role: str
    domain_ids: list[str]
    scope_version: int = 1

class CatalogQuery(BaseModel):
    text: str = Field('', max_length=500)
    domain_id: str | None = None
    subdomain_id: str | None = None
    kind: str = 'product'
    source_id: str | None = None
    owner_id: str | None = None
    status: str | None = None
    classification: str | None = None
    quality: str | None = None
    sort: Literal['name', 'updated', 'quality'] = 'name'
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(20, ge=1, le=100)

class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    mode: Literal['openai', 'extractive'] = 'openai'
    model_config = ConfigDict(extra='forbid')

class PlanOutput(BaseModel):
    concept_labels: list[str]
    query_variants: list[str]
    strategies: list[Literal['keyword', 'vector', 'graph']]

class Statement(BaseModel):
    text: str
    evidence_ids: list[str]

class AnswerOutput(BaseModel):
    statements: list[Statement]
    gaps: list[str]
    uncertainty: str
