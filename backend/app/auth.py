from fastapi import HTTPException, Header
from app.contracts import ScopeContext
from app.db import query
from app.config import settings
import secrets

DOMAINS = [
    "risk",
    "legal",
    "technology",
    "product",
    "operations",
    "data",
    "finance",
    "people",
    "third-party",
    "strategy",
    "customer",
]
PERSONAS = {
    "admin": ("Elena Vasquez", "Administrator", DOMAINS),
    "analyst": ("James Morgan", "Analyst", DOMAINS),
    "risk": ("Priya Shah", "Domain steward", ["risk", "customer", "third-party"]),
    "legal": ("Marcus Chen", "Delegate", ["legal"]),
}


def resolve_scope(token: str) -> ScopeContext:
    if token not in PERSONAS:
        raise HTTPException(401, "Unknown demo identity")
    _, role, domains = PERSONAS[token]
    stored = query(
        "SELECT payload FROM records WHERE id = :id AND kind='role'",
        {"id": f"role-{token}"},
    )
    if stored:
        p = stored[0]["payload"]
        role = p["role"]
        domains = p["domain_ids"]
        version = p.get("scope_version", 1)
    else:
        version = 1
    return ScopeContext(
        person_id=token, role=role, domain_ids=domains, scope_version=version
    )


def can_view(scope, record):
    return record.get("domain_id") is None or record["domain_id"] in scope.domain_ids


def require_edit(scope, record, kind):
    if scope.role == "Administrator":
        return
    if (
        scope.role not in ["Domain steward", "Delegate", "Product owner"]
        or not can_view(scope, record)
        or kind == "role"
    ):
        raise HTTPException(403, "This demo role cannot edit this record")


def scope_dependency(authorization: str = Header("")):
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(401, "A demo session is required")
    token = authorization[len(prefix) :]
    if secrets.compare_digest(token, settings().mcp_token):
        return resolve_scope("analyst")
    if token.startswith("atlas-session-"):
        return resolve_scope(token.removeprefix("atlas-session-"))
    raise HTTPException(401, "Invalid demo session")


def narrow_scope(scope: ScopeContext, domain_id: str | None) -> ScopeContext:
    if domain_id is None:
        return scope
    if domain_id not in scope.domain_ids:
        raise HTTPException(404, "Domain not found in your scope")
    return scope.model_copy(update={"domain_ids": [domain_id]})
