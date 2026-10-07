# Knowledge Product Manager — Search-first redesign and FastMCP

Status: proposed design for the user's /plan request; no product implementation in this planning pass.

## Intent and confirmed constraints

Make finding and understanding knowledge the primary activity. The user wants a Google-like search-first product with a useful catalog, simple interactions, GSAP and Framer Motion, and standalone FastMCP. The user confirmed: **AI answer and results together** on every submitted search.

Keep the app name Knowledge Product Manager, light-only surfaces, red primary color, subtle rose-tinted glass, restrained Swiss typography and dot patterns. Keep all 11 existing business domains and their data. PostgreSQL, MinIO, Fuseki/RDF, OpenSearch vectors, LangGraph, OpenRouter/DeepSeek, scoped access, citations and source previews remain real integrations.

This is an architectural change to navigation, discovery interfaces and the MCP adapter. Native implementation in the existing attached worktree is the recommended execution method, consistent with the prior delivery.

## Approaches considered

1. **Search-first discovery with a catalog and secondary workspace — recommended.** Minimal home, persistent search header on results, catalog as an equal destination. Governance appears when relevant to an item; administrative work remains discoverable through a workspace menu.
2. Search-first skin around the current sidebar/dashboard. Less work, but the information architecture still makes users navigate an administrative application to discover knowledge.
3. Conversational chat as the entire product. Convenient for synthesis, but weak for scanning, filtering, comparing products and inspecting provenance.

## Screen and navigation model

### Home `/`

A compact top bar with brand, Catalog, and Workspace menu plus persona/access control. Centered title “Find knowledge. Understand it.” and one prominent search field. Three useful example questions below it. A quiet “Browse all domains” link and recent queries stored locally per persona (last 5, clearable, no server history feature). No KPI tiles, activity feed, portfolio charts or persistent sidebar.

Search submission navigates to `/search?q=...&domain_id=...` and starts both deterministic search and one LangGraph AI run. Search is explicit Enter/button submission, never an LLM request on each keystroke. IME composition must not accidentally submit. A domain scope selector is optional and defaults to all authorized domains.

### Results `/search`

Compact persistent search bar and tabs: All, Products, Data, Documents. Domain filter with an Apply action, sort, and active filter chips. The AI answer appears first in a restrained surface with citations; ranked results appear below immediately when available, without waiting for synthesis. AI progress and failure are independently visible, and a failed AI run must leave useful results intact.

List rows carry title, readable excerpt, domain, source type, steward and a concise quality indicator. Relevance and snippets reflect actual indexed content. Do not invent web-style result counts: label bounded retrieval “Top matches” and use `returned_count`/`has_more` honestly. Clicking a product or asset opens an accessible detail panel with a shareable URL state. Citations open the authorized evidence and its SQL row or MinIO document pointer.

“Search steps” and ontology context are expandable details. Show tool progress and outcomes, never private reasoning. Answer scope is visible. Tabs, sort and pagination change the displayed results only; domain Apply starts a new scoped search and AI run. Reload/back restores the existing run; it never silently replays a paid provider request.

### Catalog `/catalog`

A clean library browser with All products, domain chips/menu, optional source/quality filters, and list/grid toggle. Default cards contain title, one-line purpose, steward and source formats. Details progressively reveal assets, storage, ontology relationships, issues, gaps and projects. No global KPI strip or preselected detail sidebar. On mobile, details use a full-height dialog with a close/back action.

### Secondary destinations

Workspace menu retains Domains, Sources, Ontology, Projects & gaps, Roles & access and connection information. Preserve existing edits and permissions. Simplify their shared shell to the new top navigation, with contextual page tools. Existing direct links remain valid. The former home overview is replaced; service readiness is available in Workspace rather than occupying every page.

## Discovery and AI contracts

Add `GET /discovery/search` with `q` (3–2000 trimmed characters), optional `domain_id`, `type` (all/product/data/document), `sort` (relevance/name), `page` (>=1), `page_size` (1–30, default 20). Return `DiscoveryPage`: `items`, `returned_count`, `has_more`, `page`, `page_size`, `query`, `domain_id`. A `DiscoveryItem` carries stable `id`, `kind`, `title`, `excerpt`, `domain_id`, `source_type`, `asset_id`/`product_id`, optional `evidence_id`, `steward`, `quality`, and `score`.

Use the existing scoped OpenSearch keyword/vector fusion and bounded RDF concept resolution, plus scoped catalog metadata matching and product-to-asset associations. Collapse multiple evidence chunks into one asset result and link products from matching assets. Merge name/metadata matches with evidence-derived matches by reciprocal rank fusion; ties resolve by stable ID. Keep at most 100 ranked candidates. `has_more` only concerns this bounded set, not an invented estate-wide total. Filters and authorization apply before ranking/pagination; unavailable dependencies show an explicit recoverable error.

Extend `SearchRequest` with optional `domain_id`, carry it in stored runs and LangGraph state, and intersect it with current authorized domains at every guard. An inaccessible requested domain is rejected (404) rather than widening to all domains. Both deterministic results and AI retrieval use the same query/domain context. Tabs and sorting are presentation filters, so the answer can still cite mixed source types within the displayed domain scope. OpenSearch evidence, SQL pointers, documents, RDF relationships, current scope checks, citation validation and the 90-second deadline remain authoritative.

The client keeps separate results and AI status/error state keyed by query/domain/persona. A new search disconnects and cancels the previous in-progress run. Stale responses never overwrite the active search. Store run associations in session storage per persona and query/domain. Reload/back reconnects to the stored run; if none exists, show results and an explicit Generate answer action instead of starting a paid replay. No key appears in URLs, browser code or MCP metadata.

## Standalone FastMCP adapter

Current code uses `mcp.server.fastmcp.FastMCP`, embedded in the MCP SDK. Migrate to the standalone `fastmcp` package, initially pinning **4.0.11**, the release verified on PyPI during planning. Resolve/lock compatible transitive MCP SDK versions; preserve Python 3.12 and test real protocol clients.

Keep curated service-backed tools rather than auto-exposing every REST endpoint. Preserve the seven existing tool names, resource URIs and prompt. Add `search_knowledge(query, domain_id=None, type="all", page=1, page_size=20)` using the same deterministic discovery service as the UI. Add `domain_id=None` to `agentic_search` when starting a query; reject context changes when polling an existing run.

Keep Streamable HTTP at `/mcp` and stdio. Use FastMCP's HTTP ASGI app with its lifespan combined with the existing embedding warm-up. HTTP bearer verification maps the configured token to the Analyst demo identity; stdio derives identity from server configuration. Never accept persona, credentials or arbitrary query languages as tool arguments. Retain loopback/origin restrictions and current service-level access checks. Tools that start a run are annotated as starting work rather than being misleadingly described as side-effect-free; data access tools are read-only. Tools/resources/prompts return structured, bounded results with source pointers.

No new public hosting or production OAuth is implied. The adapter must work with both the FastMCP client and the official MCP SDK client over real HTTP/stdio.

## Visual and motion direction

Google-inspired interaction clarity, whitespace, readable results and progressive disclosure; retain the application's own red identity. Warm near-white background, neutral dark text, red action/selection emphasis. Tint/blur only navigation, floating filter controls and detail surfaces; do not layer glass behind every result. Paper shader restricted to a quiet home accent, with static/reduced-motion fallback.

Use **Framer Motion** for shared search-field layout, result presence, tab indicator, filter expansion and detail-panel transitions. Use **GSAP + @gsap/react** for the single home introduction/dot motif sequence. Do not let both libraries own the same element/property. No scroll hijacking, pinned sections or delayed access to results. Transitions 160–240ms, main search layout 320ms, home introduction <=600ms. Limit result stagger to the first 6 rows, 24ms apart. Respect prefers-reduced-motion, hidden-page/offscreen pause, keyboard focus and animation cleanup on unmount. Animate opacity/transforms; avoid continuously animated layout or heavy blur.

## Acceptance

- From home, one submitted question opens results and automatically starts one scoped cited AI answer.
- Deterministic results remain usable while AI is pending, unavailable, cancelled or failed.
- Query/domain, result selection and browser back/reload are consistent, with no unintentional paid replay.
- All 11 domains and all existing product/source/edit/ontology capabilities remain reachable.
- SQL and MinIO previews, RDF context and citations retain real provenance and permissions.
- HTTP and stdio FastMCP discovery/tools/resources/prompts work, reject unauthorized calls, and expose no mutations or credentials.
- Desktop 1440px, tablet 768px, mobile 390px have no horizontal overflow; dialogs trap/restore focus and close with Escape.
- Reduced-motion mode remains complete and readable; motion does not block inputs or search results.

## Primary references

- [FastMCP package release](https://pypi.org/project/fastmcp/)
- [FastMCP FastAPI mounting and lifespans](https://gofastmcp.com/integrations/fastapi)
- [FastMCP token verification](https://gofastmcp.com/servers/auth/token-verification)
- [Google Material search](https://m3.material.io/components/search/overview)
- [GSAP in React](https://gsap.com/resources/React/)
- [Motion layout animations](https://motion.dev/docs/react-layout-animations)
- [Motion reduced-motion controls](https://motion.dev/docs/react-motion-config)
