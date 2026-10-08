from datetime import date
from pydantic import BaseModel, ConfigDict, Field


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
