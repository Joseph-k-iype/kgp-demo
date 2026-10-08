from alembic import op

revision = "005_catalog_reference_indexes"
down_revision = "004_search_worker_leases"


def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asset_product_refs ON records USING gin ((payload->'product_ids')) WHERE kind='asset'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_domain_kind_name ON records(domain_id,kind,(payload->>'name'),id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_domain_kind_updated ON records(domain_id,kind,updated_at DESC,id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_product_id ON records((payload->>'product_id')) WHERE kind IN ('project','gap')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_issue_asset ON records((payload->>'asset_id')) WHERE kind='issue'"
    )


def downgrade():
    for name in [
        "ix_record_issue_asset",
        "ix_record_product_id",
        "ix_record_domain_kind_updated",
        "ix_record_domain_kind_name",
        "ix_asset_product_refs",
    ]:
        op.execute("DROP INDEX IF EXISTS " + name)
