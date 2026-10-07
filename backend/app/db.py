from sqlalchemy import create_engine, text
from app.config import settings
engine = create_engine(settings().database_url, pool_pre_ping=True)

def query(sql, params=None):
    with engine.begin() as conn:
        return list(conn.execute(text(sql), params or {}).mappings())
