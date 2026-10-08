from alembic import op

revision = "002_source_read_indexes"
down_revision = "001_catalog"


def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_business_rows_asset_id_id ON business_rows(asset_id,id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_records_entities_domain ON records(domain_id,id) WHERE kind IN ('entity','section')"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_records_entities_domain")
    op.execute("DROP INDEX IF EXISTS ix_business_rows_asset_id_id")
