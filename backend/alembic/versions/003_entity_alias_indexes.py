from alembic import op

revision = "003_entity_alias_indexes"
down_revision = "002_source_read_indexes"


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entity_names_trgm ON records USING gin (lower(payload->>'name') gin_trgm_ops) WHERE kind='entity'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entity_aliases_trgm ON records USING gin (lower(payload->>'aliases') gin_trgm_ops) WHERE kind='entity'"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_entity_aliases_trgm")
    op.execute("DROP INDEX IF EXISTS ix_entity_names_trgm")
