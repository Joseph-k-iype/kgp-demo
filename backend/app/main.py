import asyncio, json, time, secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Body, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.auth import scope_dependency, resolve_scope, PERSONAS
from app.contracts import (
    CatalogQuery,
    SearchRequest,
    CatalogPage,
    ProductDetail,
    AssetDetail,
    SearchResult,
)
from app.catalog import service as catalog
from app.health import service_health
from app.storage.objects import preview_object
from app.storage.structured import preview_rows
from app.ontology.service import (
    explore_ontology,
    CONCEPTS,
    validate_ontology,
    rdf_graph,
)
from app.retrieval.service import get_evidence
from app.agent.service import start_search, get_search, cancel_search, resume_search
from app.mcp.server import mcp_http_app, identity
from app.config import settings
from app.discovery.contracts import DiscoveryQuery, DiscoveryPage
from app.discovery.service import search_discovery
from app.knowledge.contracts import ContentHandle, ContentPage, ToolContext, GraphPage
from app.knowledge.content import open_content
from typing import Literal


@asynccontextmanager
async def lifespan(app):
    from app.retrieval.embed import embed

    # Load the pinned local model before accepting time-bounded searches.
    await asyncio.to_thread(embed, ["Knowledge Product Manager readiness"])
    async with mcp_http_app.lifespan(app):
        yield


app = FastAPI(title="Knowledge Product Manager", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:53000", "http://127.0.0.1:53000"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def mcp_identity(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        if request.url.hostname not in ["127.0.0.1", "localhost", "testserver"]:
            return JSONResponse({"error": "Invalid host"}, 400)
        origin = request.headers.get("origin")
        if origin and origin not in [
            "http://localhost:53000",
            "http://127.0.0.1:53000",
        ]:
            return JSONResponse({"error": "Invalid origin"}, 403)
        if not secrets.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + settings().mcp_token
        ):
            return JSONResponse({"error": "MCP bearer token required"}, 401)
        token = identity.set("analyst")
        try:
            return await call_next(request)
        finally:
            identity.reset(token)
    return await call_next(request)


@app.exception_handler(Exception)
async def dependency_error(request, exc):
    import logging

    logging.getLogger(__name__).exception("API dependency error")
    return JSONResponse(
        {
            "detail": "A required service is unavailable. Check the service readiness panel."
        },
        503,
    )


@app.get("/health")
def health():
    return service_health()


@app.get("/personas")
def personas():
    return [
        {"id": id, "name": name, "role": role, "domains": domains}
        for id, (name, role, domains) in PERSONAS.items()
    ]


@app.post("/session")
def session(persona: str = Body(embed=True)):
    scope = resolve_scope(persona)
    return {"token": "atlas-session-" + persona, "scope": scope.model_dump()}


@app.get("/catalog", response_model=CatalogPage)
def list_catalog(filters: CatalogQuery = Depends(), scope=Depends(scope_dependency)):
    return catalog.list_catalog(scope, filters.model_dump())


@app.get("/discovery/search", response_model=DiscoveryPage)
def discovery(request: DiscoveryQuery = Depends(), scope=Depends(scope_dependency)):
    return search_discovery(scope, request)


@app.get("/domains")
def domains(scope=Depends(scope_dependency)):
    return catalog.list_domains(scope)


@app.get("/overview")
def overview(scope=Depends(scope_dependency)):
    return catalog.overview(scope)


@app.get("/products/{id}", response_model=ProductDetail)
def product(id: str, scope=Depends(scope_dependency)):
    return catalog.get_product(scope, id)


@app.get("/assets/{id}", response_model=AssetDetail)
def asset(id: str, scope=Depends(scope_dependency)):
    return catalog.get_asset(scope, id)


@app.get("/assets/{id}/rows")
def rows(
    id: str, limit: int = Query(20, ge=1, le=100), scope=Depends(scope_dependency)
):
    return preview_rows(scope, id, limit)


@app.get("/content/{kind}/{id}", response_model=ContentPage)
def content(
    kind: Literal["asset", "record", "document-section", "definition", "product"],
    id: str,
    locator: str | None = Query(None, max_length=200),
    version: str | None = Query(None, max_length=200),
    cursor: str | None = Query(None, max_length=2000),
    limit: int = Query(20, ge=1, le=100),
    run_id: str | None = Query(None, max_length=80),
    evidence_id: str | None = Query(None, max_length=240),
    scope=Depends(scope_dependency),
):
    ctx = ToolContext(scope=scope, deadline=time.time() + 30)
    return open_content(
        ctx,
        ContentHandle(
            kind=kind,
            id=id,
            locator=locator,
            version=version,
            run_id=run_id,
            evidence_id=evidence_id,
        ),
        cursor,
        limit,
    )


@app.get("/products/{id}/content", response_model=ContentPage)
def product_content(
    id: str,
    preferred_asset_id: str | None = Query(None, max_length=181),
    cursor: str | None = Query(None, max_length=2000),
    limit: int = Query(20, ge=1, le=100),
    scope=Depends(scope_dependency),
):
    return open_content(
        ToolContext(scope=scope, deadline=time.time() + 30),
        ContentHandle(kind="product", id=id),
        cursor,
        limit,
        preferred_asset_id,
    )


@app.get("/assets/{id}/preview")
def preview(id: str, scope=Depends(scope_dependency)):
    return preview_object(scope, id)


@app.get("/evidence/{id}")
def evidence(
    id: str,
    run_id: str | None = Query(None, max_length=80),
    scope=Depends(scope_dependency),
):
    if run_id:
        from app.knowledge.content import run_evidence

        return run_evidence(scope, run_id, id)
    return get_evidence(scope, id)


@app.get("/ontology/concepts")
def concepts(scope=Depends(scope_dependency)):
    return [
        {"id": c, "name": c, "iri": "https://atlas.example/ontology/" + c}
        for c in CONCEPTS
    ]


@app.get("/ontology/neighborhood", response_model=GraphPage)
def neighborhood(
    concept_id: str = "Counterparty",
    depth: int = Query(1, ge=1, le=3),
    limit: int = Query(30, ge=1, le=100),
    scope=Depends(scope_dependency),
):
    return explore_ontology(scope, concept_id, depth, limit)


@app.get("/ontology/findings")
def findings(scope=Depends(scope_dependency)):
    return validate_ontology(scope)


@app.get("/ontology/rdf")
def turtle(scope=Depends(scope_dependency)):
    return {"turtle": rdf_graph(scope).serialize(format="turtle")}


@app.patch("/records/{kind}/{id}")
def edit(kind: str, id: str, patch: dict = Body(), scope=Depends(scope_dependency)):
    return catalog.update_metadata(scope, kind, id, patch)


@app.post("/search/runs", response_model=SearchResult)
def search(request: SearchRequest, scope=Depends(scope_dependency)):
    return start_search(scope, request)


@app.get("/search/runs/{id}", response_model=SearchResult)
def search_run(id: str, scope=Depends(scope_dependency)):
    return get_search(scope, id)


@app.post("/search/runs/{id}/resume")
def resume(id: str, scope=Depends(scope_dependency)):
    return resume_search(scope, id)


@app.get("/session/scope")
def session_scope(scope=Depends(scope_dependency)):
    return scope.model_dump()


@app.post("/search/runs/{id}/cancel")
def cancel(id: str, scope=Depends(scope_dependency)):
    return cancel_search(scope, id)


@app.get("/search/runs/{id}/events")
def search_events(
    id: str, after_sequence: int = Query(0, ge=0), scope=Depends(scope_dependency)
):
    get_search(scope, id)

    async def events():
        last = after_sequence
        for _ in range(240):
            run = await asyncio.to_thread(get_search, scope, id)
            for event in run["events"]:
                if event["sequence"] > last:
                    yield f"id: {event['sequence']}\ndata: {json.dumps(event)}\n\n"
                    last = event["sequence"]
            if run["status"] not in ["pending", "running"]:
                yield "event: result\ndata: " + json.dumps(run) + "\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@app.post("/index/jobs")
def submit_job(
    asset_ids: list[str] = Body(default=[]), scope=Depends(scope_dependency)
):
    from app.worker import submit_index, run_index_job
    from app.agent.service import executor

    job = submit_index(scope, asset_ids)
    executor.submit(run_index_job, job["id"])
    return job


@app.get("/index/jobs/{id}")
def job(id: str, scope=Depends(scope_dependency)):
    from app.worker import get_job

    return get_job(scope, id)


app.mount("/", mcp_http_app)
