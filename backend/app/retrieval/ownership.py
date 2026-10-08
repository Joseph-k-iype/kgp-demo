"""PostgreSQL session ownership serializes each asset's index generations.

Different assets remain independent. Worker/process death releases the session
lock; no indexer may prune another live generation for the same asset.
"""

from contextlib import contextmanager
from sqlalchemy import text
from fastapi import HTTPException
from app.db import engine


@contextmanager
def asset_index_ownership(asset_id):
    with engine.connect() as conn:
        acquired = conn.execute(
            text("SELECT pg_try_advisory_lock(hashtextextended(:id,0))"),
            {"id": "asset-index:" + asset_id},
        ).scalar_one()
        conn.commit()
        if not acquired:
            raise HTTPException(409, "This source is already being indexed")
        pid = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
        conn.commit()

        def check():
            if conn.invalidated or conn.closed:
                raise RuntimeError("Source indexing ownership was lost")
            current = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            conn.commit()
            if current != pid:
                raise RuntimeError("Source indexing session changed")

        try:
            yield check
        finally:
            if not conn.closed and not conn.invalidated:
                conn.rollback()
                conn.execute(
                    text("SELECT pg_advisory_unlock(hashtextextended(:id,0))"),
                    {"id": "asset-index:" + asset_id},
                )
                conn.commit()
