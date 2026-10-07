from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class DiscoveryQuery(BaseModel):
    q: str = Field(min_length=3, max_length=2000)
    domain_id: str | None = None
    type: Literal['all', 'product', 'data', 'document'] = 'all'
    sort: Literal['relevance', 'name'] = 'relevance'
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=30)
    model_config = ConfigDict(str_strip_whitespace=True)


class DiscoveryItem(BaseModel):
    id: str
    kind: Literal['product', 'data', 'document']
    title: str
    excerpt: str
    domain_id: str
    source_type: str
    asset_id: str | None = None
    product_id: str | None = None
    evidence_id: str | None = None
    steward: str | None = None
    quality: float | None = None
    score: float


class DiscoveryPage(BaseModel):
    items: list[DiscoveryItem]
    returned_count: int
    has_more: bool
    page: int
    page_size: int
    query: str
    domain_id: str | None = None
