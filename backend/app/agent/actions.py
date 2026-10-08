"""Validated action decisions; runtime identity and executable SQL are never model fields."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from app.knowledge.contracts import SearchIntentV2, EvidenceFragment, CoverageReport


class PlannedCall(BaseModel):
    call_id: str | None = None
    model_config = ConfigDict(extra="forbid")
    tool: Literal[
        "resolve_entities",
        "traverse_graph",
        "search_evidence",
        "read_document",
        "query_dataset",
        "read_content",
    ]
    arguments_json: str = Field(max_length=8000)


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    facet_ids: list[str] = Field(default_factory=list, max_length=8)
    relevant: bool


class ActionDecision(BaseModel):
    _native_message: dict | None = PrivateAttr(default=None)
    _native_controls: list[dict] = PrivateAttr(default_factory=list)
    model_config = ConfigDict(extra="forbid")
    intent: SearchIntentV2 | None = None
    read_calls: list[PlannedCall] = Field(default_factory=list, max_length=4)
    assessments: list[EvidenceAssessment] = Field(default_factory=list, max_length=40)
    stop_action: Literal["continue", "finish", "clarify"] = "continue"
    summary: str = Field(default="", max_length=300)


class ResearchState(BaseModel):
    graph_nodes: list[str] = Field(default_factory=list)
    graph_edges: list[str] = Field(default_factory=list)
    native_history: list[dict] = Field(default_factory=list)
    query: str
    intent: SearchIntentV2 | None = None
    observations: list[dict] = Field(default_factory=list)
    evidence: list[EvidenceFragment] = Field(default_factory=list)
    paths: list[dict] = Field(default_factory=list)
    coverage: CoverageReport = Field(default_factory=CoverageReport)
    model_calls: int = 0
    tool_calls: int = 0
    no_progress_rounds: int = 0
    action_keys: list[str] = Field(default_factory=list)
    invalid_actions: int = 0
    last_decision: ActionDecision | None = None
    stop_reason: str = ""
    answer_outcome: str = "partial"
    clarification: str = ""
    entities: list[dict] = Field(default_factory=list)
