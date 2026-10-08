import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client
from app.mcp.server import mcp


@pytest.mark.asyncio
async def test_http_mcp_discovery_and_scoped_tools():
    async with (
        create_mcp_http_client(
            headers={"Authorization": "Bearer atlas-local-analyst-token"}
        ) as http_client,
        streamable_http_client(
            "http://127.0.0.1:58123/mcp",
            http_client=http_client,
        ) as (read, write),
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert names == {
                "search_knowledge",
                "list_domains",
                "search_catalog",
                "get_knowledge_product",
                "get_asset",
                "explore_ontology",
                "get_evidence",
                "agentic_search",
                "resolve_entities",
                "traverse_graph",
                "read_document",
                "query_dataset",
                "search_evidence",
                "read_content",
            }
            result = await session.call_tool("list_domains", {})
            assert not result.is_error
            assert "Risk and Compliance" in str(result)
            assert (await session.list_resources()).resources
            assert (
                await session.get_prompt(
                    "search_knowledge", {"query": "counterparty exposure"}
                )
            ).messages


@pytest.mark.asyncio
async def test_stdio_mcp_and_resource_reads():
    import sys, os
    from pathlib import Path
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.stdio"],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            "MCP_STDIO_PERSONA": "legal",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            domains = await session.read_resource("knowledge://domains")
            assert "Legal" in str(domains)
            assert "Risk and Compliance" not in str(domains)
            result = await session.call_tool("get_asset", {"asset_id": "risk-asset-0"})
            assert result.is_error
            denied = await session.call_tool(
                "search_knowledge", {"query": "counterparty", "domain_id": "risk"}
            )
            assert denied.is_error
            result = await session.call_tool(
                "explore_ontology", {"concept_id": "Counterparty", "limit": 8}
            )
            assert not result.is_error
            assert "risk-asset" not in str(result)


@pytest.mark.asyncio
async def test_http_transport_rejects_missing_auth():
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://127.0.0.1:58123/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert r.status_code == 401
        wrong = await client.post(
            "http://127.0.0.1:58123/mcp",
            headers={"Authorization": "Bearer invalid-token"},
            json={},
        )
        assert wrong.status_code == 401
        r = await client.post(
            "http://127.0.0.1:58123/mcp",
            headers={
                "Authorization": "Bearer atlas-local-analyst-token",
                "Origin": "https://untrusted.example",
            },
            json={},
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_standalone_fastmcp_client_uses_governed_services():
    from fastmcp import Client
    from app.db import query

    before = query("SELECT count(*) AS n FROM business_rows")[0]["n"]
    async with Client(
        "http://127.0.0.1:58123/mcp", auth="atlas-local-analyst-token"
    ) as client:
        tools = await client.list_tools()
        assert "get_asset" in {tool.name for tool in tools}
        result = await client.call_tool(
            "search_knowledge", {"query": "counterparty", "domain_id": "risk"}
        )
        assert "risk-product-0" in str(result)
        domains = await client.call_tool("list_domains", {})
        assert "Risk and Compliance" in str(domains)
        assert await client.list_resources()
        assert (
            await client.get_prompt(
                "search_knowledge", {"query": "counterparty exposure"}
            )
        ).messages
        asset = await client.call_tool("get_asset", {"asset_id": "risk-asset-0"})
        assert "PostgreSQL" in str(asset) or "postgres" in str(asset).lower()
    assert query("SELECT count(*) AS n FROM business_rows")[0]["n"] == before


@pytest.mark.asyncio
async def test_stdio_shared_read_kernel_tools_and_actual_content():
    import sys, os
    from pathlib import Path
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.stdio"],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            "MCP_STDIO_PERSONA": "legal",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert {
                "resolve_entities",
                "traverse_graph",
                "read_document",
                "query_dataset",
                "search_evidence",
                "read_content",
            } <= names
            calls = [
                ("resolve_entities", {"query": "CT-2000"}),
                (
                    "traverse_graph",
                    {"roots": ["CT-2000"], "predicates": ["supportedBy"], "depth": 1},
                ),
                (
                    "read_document",
                    {"asset_id": "legal-asset-1", "section_id": "controls"},
                ),
                (
                    "query_dataset",
                    {
                        "query": {
                            "asset_id": "legal-asset-0",
                            "select": ["contract_id"],
                            "limit": 1,
                        }
                    },
                ),
                (
                    "search_evidence",
                    {
                        "query": "annual disclosure",
                        "asset_ids": ["legal-asset-1"],
                        "kinds": ["document"],
                        "strategy": "keyword",
                    },
                ),
                ("read_content", {"kind": "asset", "id": "legal-asset-1"}),
            ]
            for name, args in calls:
                result = await session.call_tool(name, args)
                assert not result.is_error, (name, str(result))
                assert "finance-asset" not in str(result) and "risk-asset" not in str(
                    result
                )
            denied = await session.call_tool(
                "read_document", {"asset_id": "finance-asset-1"}
            )
            assert denied.is_error
            injection = await session.call_tool(
                "query_dataset",
                {
                    "query": {
                        "asset_id": "legal-asset-0",
                        "select": ["contract_id; DROP TABLE business_rows"],
                    }
                },
            )
            assert injection.is_error
            override = await session.call_tool(
                "read_document", {"asset_id": "finance-asset-1", "person_id": "admin"}
            )
            assert override.is_error


@pytest.mark.asyncio
async def test_http_shared_kernel_content_and_tool_calls():
    from fastmcp import Client

    async with Client(
        "http://127.0.0.1:58123/mcp", auth="atlas-local-analyst-token"
    ) as client:
        calls = [
            ("resolve_entities", {"query": "treasury liquidity"}),
            (
                "traverse_graph",
                {
                    "roots": ["treasury-liquidity"],
                    "predicates": ["governedBy"],
                    "depth": 1,
                },
            ),
            (
                "read_document",
                {"asset_id": "finance-asset-1", "section_id": "controls"},
            ),
            (
                "query_dataset",
                {
                    "query": {
                        "asset_id": "finance-asset-0",
                        "select": ["position_id", "liquidity_usd"],
                        "limit": 1,
                    }
                },
            ),
            (
                "search_evidence",
                {
                    "query": "daily liquidity",
                    "asset_ids": ["finance-asset-1"],
                    "kinds": ["document"],
                    "strategy": "keyword",
                },
            ),
            ("read_content", {"kind": "definition", "id": "Policy"}),
        ]
        for name, args in calls:
            result = await client.call_tool(name, args)
            assert result.data is not None, (name, result)
        assert "reconcile liquidity positions daily" in str(
            await client.call_tool(
                "read_content", {"kind": "asset", "id": "finance-asset-1"}
            )
        )
