from alembic import op

revision = "006_rdf_resource_iri_index"
down_revision = "005_catalog_reference_indexes"


def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_resource_iri ON records((payload->>'iri'))"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_record_resource_iri")
