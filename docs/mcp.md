# Knowledge Product Manager MCP

The server exposes read-only application capabilities through Streamable HTTP and stdio. Both use the same catalog permissions and evidence retrieval as the web app.

## HTTP

Endpoint: `http://127.0.0.1:58123/mcp`

Send `Authorization: Bearer atlas-local-analyst-token` (or the configured `MCP_TOKEN`). The token maps to the Analyst demo persona. The server is bound to loopback. This is a local demonstration identity, not production OAuth.

Tools: `list_domains`, `search_catalog`, `get_knowledge_product`, `get_asset`, `explore_ontology`, `get_evidence`, `agentic_search`.

Resources: `knowledge://domains`, `knowledge://products/{id}`, `knowledge://ontology`.

Prompt: `search_knowledge(query)`.

Start `agentic_search` with `query` and `mode` (`llm` or explicitly selected `extractive`). It returns a `run_id`. Poll the same tool with `run_id` instead of `query`. Run ownership and current scope are checked on every poll. Evidence contains stable asset IDs and structured row or document offset provenance.

## stdio

From the repository root:

```sh
PYTHONPATH=backend uv run --project backend python -m app.mcp.stdio
```

Configure the client command as the absolute `backend/.venv/bin/python`, arguments `-m app.mcp.stdio`, and environment `PYTHONPATH` as the absolute backend directory. `MCP_STDIO_PERSONA` defaults to `analyst`; `legal` demonstrates restricted scope. Identity is selected by server configuration, never tool arguments. The backend must be configured with the same PostgreSQL, MinIO, Fuseki and OpenSearch endpoints.

The MCP server cannot execute arbitrary SQL or SPARQL, mutate catalog data, or expose denied source excerpts. A missing provider API key returns a clear configuration-required search state; no silent LLM substitute is used.

## Client verification

With the API running, `make test` includes an actual SDK initialization, tool discovery/calls, resource reads, prompt retrieval, HTTP credential checks, and a restricted stdio client. The catalog/search UI is not required for MCP clients.
