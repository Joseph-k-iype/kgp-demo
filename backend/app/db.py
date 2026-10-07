from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(
    settings().database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
)


def query(sql, params=None):
    with engine.begin() as conn:
        return list(conn.execute(text(sql), params or {}).mappings())
