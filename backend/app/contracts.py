from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class ScopeContext(BaseModel):
    person_id: str
    role: str
    domain_ids: list[str]
    scope_version: int = 1


class CatalogQuery(BaseModel):
    text: str = Field("", max_length=500)
    domain_id: str | None = None
    subdomain_id: str | None = None
    kind: str = "product"
    asset_type: Literal["Table", "Document", "Metadata", "Data product"] | None = None
    source_id: str | None = None
    owner_id: str | None = None
    status: str | None = None
    classification: str | None = None
    quality: str | None = None
    sort: Literal["name", "updated", "quality"] = "name"
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(20, ge=1, le=100)


class SearchRequest(BaseModel):
    intent_id: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9-]+$"
    )
    domain_id: str | None = None
    query: str = Field(min_length=3, max_length=2000)
    mode: Literal["llm", "openai", "extractive"] = "llm"
    model_config = ConfigDict(extra="forbid")


class PlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_labels: list[str]
    query_variants: list[str]
    strategies: list[Literal["keyword", "vector", "graph"]]


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    evidence_ids: list[str]


class VerifiedStatement(Statement):
    support_status: Literal["supported", "source_only"] | None = None
    facet_ids: list[str] = Field(default_factory=list)
    supporting_locators: list[dict] = Field(default_factory=list)


class AnswerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statements: list[Statement]
    gaps: list[str]
    uncertainty: str


class CatalogRecord(BaseModel):
    id: str
    kind: str
    name: str
    description: str = ""
    domain_id: str | None = None
    model_config = ConfigDict(extra="allow")


class CatalogPage(BaseModel):
    items: list[CatalogRecord]
    total: int
    page: int
    page_size: int


class ProductDetail(CatalogRecord):
    assets: list[CatalogRecord]
    projects: list[CatalogRecord]
    gaps: list[CatalogRecord]


class AssetDetail(CatalogRecord):
    source: CatalogRecord
    issues: list[CatalogRecord]
    products: list[CatalogRecord]


class SearchEvent(BaseModel):
    sequence: int
    stage: str
    status: str
    summary: str
    at: float


class AnswerSection(BaseModel):
    title: str
    statement_indices: list[int]


class SearchResult(BaseModel):
    domain_id: str | None = None
    run_id: str
    status: str
    query: str
    mode: str
    statements: list[VerifiedStatement]
    answer_sections: list[AnswerSection] = Field(default_factory=list)
    evidence: list[dict]
    gaps: list[str]
    events: list[SearchEvent]
    graph: dict
    created_at: float
    model_config = ConfigDict(extra="allow")
