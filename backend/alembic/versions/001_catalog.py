from alembic import op
from app.catalog.models import metadata
revision = '001_catalog'
down_revision = None

def upgrade():
    metadata.create_all(op.get_bind())

def downgrade():
    metadata.drop_all(op.get_bind())
