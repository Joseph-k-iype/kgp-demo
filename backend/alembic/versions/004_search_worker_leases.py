from alembic import op

revision = "004_search_worker_leases"
down_revision = "003_entity_alias_indexes"


def upgrade():
    op.execute("ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS lease_owner text")
    op.execute(
        "ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS lease_until double precision"
    )
    op.execute("ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS intent_id text")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_search_intent ON search_runs(person_id,intent_id) WHERE intent_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_search_pending ON search_runs(created_at,id) WHERE payload->>'status'='pending'"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_search_pending")
    op.execute("DROP INDEX IF EXISTS ix_search_intent")
    op.execute("ALTER TABLE search_runs DROP COLUMN IF EXISTS intent_id")
    op.execute("ALTER TABLE search_runs DROP COLUMN IF EXISTS lease_until")
    op.execute("ALTER TABLE search_runs DROP COLUMN IF EXISTS lease_owner")
