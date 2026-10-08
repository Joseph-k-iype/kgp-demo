from datetime import date
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    version: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    domain_id: str


class GraphAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str
    predicate: str
    object: str
    source_ref: SourceRef
    valid_from: date | None = None
    valid_to: date | None = None
    origin: str = "managed_fixture"

    def valid_on(self, at: date) -> bool:
        return (self.valid_from is None or at >= self.valid_from) and (
            self.valid_to is None or at <= self.valid_to
        )


from typing import Literal, Annotated, Any
from app.contracts import ScopeContext


class ToolContext(BaseModel):
    _lifecycle_guard: Any = PrivateAttr(default=None)
    scope: ScopeContext
    deadline: float
    domain_id: str | None = None
    max_tool_calls: int = 16
    tool_calls: int = 0
    max_response_bytes: int = 256000
    graph_nodes: set[str] = Field(default_factory=set)
    graph_edges: set[str] = Field(default_factory=set)
    as_of: date = Field(default_factory=date.today)


class EntityCandidate(BaseModel):
    id: str
    name: str
    domain_id: str
    entity_type: str
    score: float
    aliases: list[str] = Field(default_factory=list)


class EntityResolution(BaseModel):
    outcome: Literal["ok", "no_match", "ambiguous"]
    candidates: list[EntityCandidate]
    truncated: bool = False


class ToolResult(BaseModel):
    content: dict | None = None
    outcome: Literal["ok", "no_match", "ambiguous", "stale", "unavailable"] = "ok"
    items: list[dict] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    paths: list[dict] = Field(default_factory=list)
    cursor: str | None = None
    has_more: bool = False
    truncated: bool = False
    detail: str | None = None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetFilter(StrictModel):
    field: str
    op: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in"] = "eq"
    value: Any


class DatasetAggregate(StrictModel):
    operation: Literal["sum", "avg", "min", "max", "count"]
    field: str | None = None


class DatasetQuery(StrictModel):
    asset_id: str
    select: list[str] = Field(default_factory=list, max_length=20)
    filters: list[DatasetFilter] = Field(default_factory=list, max_length=10)
    aggregate: DatasetAggregate | None = None
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=100)


class ResolveEntitiesAction(StrictModel):
    tool: Literal["resolve_entities"] = "resolve_entities"
    query: str = Field(min_length=1, max_length=2000)


class TraverseGraphAction(StrictModel):
    tool: Literal["traverse_graph"] = "traverse_graph"
    roots: list[str] = Field(min_length=1, max_length=3)
    predicates: list[str] = Field(default_factory=list, max_length=10)
    target_kinds: list[str] = Field(default_factory=list, max_length=10)
    depth: int = Field(default=3, ge=1, le=3)


class ReadDocumentAction(StrictModel):
    tool: Literal["read_document"] = "read_document"
    asset_id: str
    section_id: str | None = None


class QueryDatasetAction(StrictModel):
    tool: Literal["query_dataset"] = "query_dataset"
    query: DatasetQuery


class SearchEvidenceAction(StrictModel):
    tool: Literal["search_evidence"] = "search_evidence"
    query: str
    asset_ids: list[str] | None = None
    kinds: list[str] = Field(default_factory=list)
    strategy: Literal["keyword", "vector", "hybrid"] = "hybrid"


class ReadContentAction(StrictModel):
    tool: Literal["read_content"] = "read_content"
    kind: Literal["asset", "record", "document-section", "definition", "product"]
    id: str
    cursor: str | None = None


ReadAction = Annotated[
    ResolveEntitiesAction
    | TraverseGraphAction
    | ReadDocumentAction
    | QueryDatasetAction
    | SearchEvidenceAction
    | ReadContentAction,
    Field(discriminator="tool"),
]


class AnswerFacet(BaseModel):
    id: str
    description: str
    kinds: list[Literal["document", "structured", "definition", "metadata"]] = Field(
        default_factory=list
    )


class SearchIntentV2(BaseModel):
    query: str
    facets: list[AnswerFacet]
    entity_ids: list[str] = Field(default_factory=list)
    ambiguous: bool = False


class EvidenceFragment(BaseModel):
    source_title: str | None = None
    id: str
    asset_id: str
    domain_id: str
    content_kind: Literal["document", "structured", "definition", "metadata"]
    text: str
    source_ref: SourceRef
    values: dict | None = None
    units: str | None = None
    period: str | None = None
    paths: list[dict] = Field(default_factory=list)
    matched_facet_ids: list[str] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)


class CoverageReport(BaseModel):
    supported_facet_ids: list[str] = Field(default_factory=list)
    uncovered_facet_ids: list[str] = Field(default_factory=list)
    irrelevant_ids: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    suggested_source_needs: list[str] = Field(default_factory=list)


class ContentHandle(StrictModel):
    kind: Literal["asset", "record", "document-section", "definition", "product"]
    id: str = Field(min_length=1, max_length=181)
    locator: str | None = Field(default=None, max_length=200)
    version: str | None = Field(default=None, max_length=200)
    run_id: str | None = Field(default=None, max_length=80)
    evidence_id: str | None = Field(default=None, max_length=240)


class ContentSource(StrictModel):
    title: str
    source_type: str
    handle: ContentHandle


class ProductContentManifest(StrictModel):
    product_id: str
    title: str
    primary: ContentHandle | None = None
    sources: list[ContentSource] = Field(default_factory=list)
    truncated: bool = False


class ContentPage(StrictModel):
    handle: ContentHandle
    title: str
    content_type: Literal["document", "dataset", "definition", "unavailable"]
    text: str = ""
    sections: list[dict] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    columns: list[dict] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    paths: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    manifest: ProductContentManifest | None = None
    cursor: str | None = None
    has_more: bool = False
    truncated: bool = False
    freshness: Literal["current", "changed"] = "current"
    requested_version: str | None = None
    cited_snapshot: dict | None = None
    detail: str | None = None


class GraphNode(StrictModel):
    aliases: list[str] = Field(default_factory=list, max_length=30)
    id: str
    iri: str
    name: str
    kind: str
    domain_id: str | None = None
    content_handle: ContentHandle
    source_type: str | None = None
    status: str | None = None


class GraphEdge(StrictModel):
    source: str
    target: str
    label: str
    asserted: bool = True
    source_ref: SourceRef | None = None


class GraphPage(StrictModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    root: str
    truncated: bool
    limits: dict
