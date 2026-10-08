import time, hashlib, json
from fastapi import HTTPException
from app.auth import resolve_scope, narrow_scope
from app.knowledge.contracts import ToolContext


def guard(ctx: ToolContext):
    if time.time() >= ctx.deadline:
        raise TimeoutError("Search deadline exceeded")
    current = resolve_scope(ctx.scope.person_id)
    if current.scope_version != ctx.scope.scope_version:
        raise HTTPException(409, "Access scope changed; start a new search")
    return narrow_scope(current, ctx.domain_id)


def version(value) -> str:
    content = (
        value
        if isinstance(value, str)
        else json.dumps(value, sort_keys=True, separators=(",", ":"))
    )
    return hashlib.sha256(content.encode()).hexdigest()
