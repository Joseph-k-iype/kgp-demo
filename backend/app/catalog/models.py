from sqlalchemy import MetaData, Table, Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
records = Table(
    "records",
    metadata,
    Column("id", String, primary_key=True),
    Column("kind", String, nullable=False, index=True),
    Column("domain_id", String, ForeignKey("records.id"), index=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), server_default=text("now()")),
)
rows = Table(
    "business_rows",
    metadata,
    Column("id", String, primary_key=True),
    Column("asset_id", String, ForeignKey("records.id")),
    Column("payload", JSONB, nullable=False),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("state", String),
    Column("payload", JSONB),
)
runs = Table(
    "search_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("person_id", String, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
)
