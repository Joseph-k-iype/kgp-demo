from alembic import context
from app.db import engine
from app.catalog.models import metadata
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
