import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field


class GoldFact(BaseModel):
    id: str
    answer_pattern: str
    asset_ids: list[str]
    locator: str | None = None


class GoldCase(BaseModel):
    id: str
    query: str
    category: str
    persona: str = "admin"
    domain_id: str | None = None
    outcome: Literal["answered", "partial", "no_evidence", "needs_clarification"] = (
        "answered"
    )
    facts: list[GoldFact] = Field(default_factory=list)
    paths: list[list[str]] = Field(default_factory=list)
    note: str = ""


def load_cases(split: Literal["development", "heldout"]) -> list[GoldCase]:
    if split not in ("development", "heldout"):
        raise ValueError("Unknown split")
    return [
        GoldCase.model_validate(json.loads(line))
        for line in (Path(__file__).parent / "cases" / (split + ".jsonl"))
        .read_text()
        .splitlines()
        if line.strip()
    ]
