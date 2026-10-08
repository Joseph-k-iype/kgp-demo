# Knowledge Product Manager MCP

The standalone FastMCP 4 server exposes governed application capabilities through Streamable HTTP and stdio. Both use the same catalog permissions and evidence retrieval as the web app.

## HTTP

Endpoint: `http://127.0.0.1:58123/mcp`

Send `Authorization: Bearer atlas-local-analyst-token` (or the configured `MCP_TOKEN`). The token maps to the Analyst demo persona. The server is bound to loopback. This is a local demonstration identity, not production OAuth.

Tools: `list_domains`, `search_catalog`, `get_knowledge_product`, `get_asset`, `explore_ontology`, `get_evidence`, `agentic_search`, `search_knowledge`.

Resources: `knowledge://domains`, `knowledge://products/{id}`, `knowledge://ontology`.

Prompt: `search_knowledge(query)`.

`search_knowledge(query, domain_id=None, type="all", page=1, page_size=20)` shares ranked product/data/document discovery with the web app. Domain filters intersect current access; inaccessible domains are rejected.

Start `agentic_search` with `query`, optional `domain_id`, and `mode` (`llm` or explicitly selected `extractive`). It returns a `run_id`. Poll the same tool with `run_id` instead of `query`. Run ownership and current scope are checked on every poll. Evidence contains stable asset IDs and structured row or document offset provenance.

## stdio

From the repository root:

```sh
PYTHONPATH=backend uv run --project backend python -m app.mcp.stdio
```

Configure the client command as the absolute `backend/.venv/bin/python`, arguments `-m app.mcp.stdio`, and environment `PYTHONPATH` as the absolute backend directory. `MCP_STDIO_PERSONA` defaults to `analyst`; `legal` demonstrates restricted scope. Identity is selected by server configuration, never tool arguments. The backend must be configured with the same PostgreSQL, MinIO, Fuseki and OpenSearch endpoints.

The server uses MCP SDK 2 and the FastMCP HTTP app lifespan. Data-reading tools declare read-only annotations; agentic_search persists a bounded search run and is annotated accordingly.

The MCP server cannot execute arbitrary SQL or SPARQL, mutate catalog data, or expose denied source excerpts. A missing provider API key returns a clear configuration-required search state; no silent LLM substitute is used.

## Client verification

With the API running, `make test` includes an actual SDK initialization, tool discovery/calls, resource reads, prompt retrieval, HTTP credential checks, and a restricted stdio client. The catalog/search UI is not required for MCP clients.

## Graph-centered read tools

The server additionally exposes six typed tools sharing the API's server-owned `ToolContext`:

| Tool | Inputs and output |
|---|---|
| `resolve_entities` | Query/domain → bounded business entity candidates, aliases, ambiguity |
| `traverse_graph` | Root IDs, allowed predicates, direction/depth/domain → current scoped nodes/edges/proof paths and source handles |
| `read_document` | Asset ID and optional section → actual source passage with version/locator |
| `query_dataset` | Registered dataset ID, selected fields, typed filters/aggregation/cursor → actual rows or independently computed result |
| `search_evidence` | Query, strategy, kinds and source handles → bounded current content candidates |
| `read_content` | Flat `kind`, `id`, optional cursor → content-first page plus separate context/relationships |

There are fourteen tools including the original eight. Inspect `tools/list` for the exact generated JSON schemas. Tool arguments never include persona, permissions, provider keys, arbitrary SQL or SPARQL. Every domain filter intersects the configured session scope. Hidden intermediate graph nodes and stale source bindings cannot become proof paths.

A minimal Python HTTP client uses `mcp.client.streamable_http.streamable_http_client` and `mcp.ClientSession`: open the URL with bearer headers, initialize, list tools, then call a tool with its typed arguments. `backend/tests/integration/test_mcp.py` is a runnable SDK example covering actual HTTP and stdio negotiation, denied access, resources, prompts, source reads and shared search behavior. Use `make test` with the stores/API available. For external hosting, replace the demo bearer identity with authenticated OAuth and deploy the same private scoped services; public hosting is not configured here.
