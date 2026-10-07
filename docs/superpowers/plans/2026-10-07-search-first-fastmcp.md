# Search-first Knowledge Product Manager and FastMCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native implementation, or superpowers:subagent-driven-development if the user selects it. Steps use checkbox syntax for tracking.

**Goal:** Make Knowledge Product Manager a simple search-plus-catalog application with automatic cited AI answers and a standalone FastMCP server.

**Architecture:** A shared scoped discovery service powers immediate UI results and an MCP tool. LangGraph handles the parallel AI run using the same query/domain context. Replace the dashboard shell with home/results/catalog flows, retaining governance/edit destinations through a workspace menu.

**Tech Stack:** Existing Next.js/React, FastAPI/Python 3.12, PostgreSQL, MinIO, Fuseki, OpenSearch, OpenRouter/DeepSeek and LangGraph; standalone FastMCP 4.0.11; GSAP/@gsap/react and Framer Motion.

**Spec:** `docs/superpowers/specs/2026-10-07-search-first-fastmcp-design.md`

**Status:** Proposed plan for review. Planning files only; implementation has not started. Native execution is recommended and matches the previous session's execution preference.

## Global Constraints

- Name: Knowledge Product Manager; light-only; red primary; subtle rose-tinted glass.
- User confirmed: AI answer and results together on each submitted query; no provider calls on keystrokes or passive reload/back.
- Preserve all 11 domains, real data services, demo scope, citations, source previews and editable metadata.
- Scope query/domain consistently across discovery and AI; derive identity on the server.
- Keep 90-second AI deadline, 12 tool calls and at most two retrieval passes.
- MCP stays loopback `/mcp` and stdio, curated and read-only with respect to business data.
- Read `frontend/AGENTS.md` and relevant bundled Next.js guides before changing routes/state.
- Use required 12ui-design workflow at UI implementation time; adapt references to these confirmed requirements.

## Review Focus

1. Query changes during slow results or synthesis: stale data/answers never replace the active search.
2. Domain filter outside current access: no widening, denied excerpts or leaking result counts.
3. Reload/back/double-submit: preserve URL state and existing run without hidden paid replay.
4. AI or search dependency failure: independent states, usable surviving channel, honest errors.
5. Reduced motion, keyboard navigation and mobile dialogs: all actions remain available without animations.

## File map

Backend: retain business services; add `app/discovery/contracts.py` and `service.py`; adapt `app/mcp/server.py` and `stdio.py`; modify `main.py`, `contracts.py`, `agent/state.py`, `agent/service.py`, `agent/graph.py`; extend actual client/integration tests. Update lockfiles, API schema and generated frontend types.

Frontend: replace `components/Shell.tsx`; add `components/discovery/{SearchBox,SearchHeader,ResultList,AnswerPanel,DiscoveryDetail}.tsx`, `api/discovery.ts`, `hooks/useDiscovery.ts`, `hooks/useKnowledgeRun.ts`, and `components/motion/MotionProvider.tsx`; rebuild home/search/catalog routes; simplify `theme.css`/`globals.css`; retain and restyle secondary routes/components.

## Task 1: Migrate the curated MCP adapter

**Files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/app/mcp/server.py`, `backend/app/mcp/stdio.py`, `backend/app/main.py`, `backend/tests/integration/test_mcp.py`, `docs/mcp.md`.

**Interfaces:** Preserve existing seven tools, three resource URI patterns, `search_knowledge` prompt, `/mcp` endpoint and stdio command. Produce standalone FastMCP `mcp`, its HTTP ASGI app and a combined application lifespan.

- [ ] Add failing migration checks: actual FastMCP client initializes/list/calls/reads/prompts; official MCP client still passes; HTTP missing/wrong token and invalid origin are denied; Legal stdio cannot read risk assets; source data is unchanged after tools.
- [ ] Run the focused MCP tests and confirm the new client/import checks fail against the SDK adapter.
- [ ] Pin `fastmcp==4.0.11`, align its SDK dependency with the lock resolver, migrate decorators/HTTP app/lifespan and preserve server-derived identity. Inspect installed package APIs rather than assuming older FastMCP constructor options remain valid.
- [ ] Run `PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_mcp.py -q` against the restarted API. Confirm both real transports and all preserved contracts pass.
- [ ] Update client configuration/docs and commit `feat: migrate governed tools to standalone FastMCP`.

## Task 2: Shared ranked discovery and scoped AI context

**Files:** create `backend/app/discovery/contracts.py`, `service.py`, `backend/tests/integration/test_discovery.py`; modify `main.py`, `contracts.py`, `agent/state.py`, `agent/service.py`, `agent/graph.py`, `mcp/server.py`, `tests/integration/test_agent_runs.py`, `tests/integration/test_mcp.py`, `backend/openapi.json`, `frontend/src/api/generated.ts`.

**Interfaces:** `search_discovery(scope: ScopeContext, query: DiscoveryQuery) -> DiscoveryPage`; `GET /discovery/search`; DTO fields/limits exactly as spec. `SearchRequest.domain_id: str | None = None` is persisted to run/state and intersected with current scope by every graph guard. New MCP tool `search_knowledge` delegates to the shared service (existing prompt of the same name remains in its separate MCP namespace).

- [ ] Add failing tests: counterparty queries return actual product/data/document links; stable IDs/order and bounded pagination; source pointers remain valid; Legal sees only Legal; denied domain returns 404; empty/oversized query and invalid paging reject; chunk dedup yields one asset; current scope changes invalidate run evidence; filtered AI evidence belongs only to requested domain.
- [ ] Run `PYTHONPATH=backend uv run --project backend pytest backend/tests/integration/test_discovery.py backend/tests/integration/test_agent_runs.py -q` and confirm the added contracts fail.
- [ ] Implement scoped metadata/evidence ranking with RRF, stable ID tie-break and 100-candidate cap; pagination follows filtering/dedup. Use actual indexed matches, not synthetic relevance labels/counts.
- [ ] Persist and enforce domain context in run creation/resume/graph guard. Polling cannot modify query/domain. Add the MCP discovery tool and optional start-only agent domain filter.
- [ ] Re-run focused discovery/AI/MCP tests sequentially against real services; regenerate OpenAPI/client types; commit `feat: share scoped discovery across UI AI and MCP`.

## Task 3: Search-first shell and home

**Files:** `frontend/src/components/Shell.tsx`, `components/discovery/SearchBox.tsx`, `SearchHeader.tsx`, `frontend/src/app/page.tsx`, `layout.tsx`, `theme.css`, `globals.css`, `frontend/tests/e2e/discovery-home.spec.ts`.

**Interfaces:** `SearchBox({query, domainId, onSubmit}: SearchBoxProps)` emits `{query: string, domainId: string | null}` on explicit submit; shared across home/results/catalog. Top navigation exposes home, Catalog and Workspace menu; session provider remains available to existing pages.

- [ ] Before code, read required 12ui-design and relevant local Next.js guides. Generate/review home/results/catalog references as one coherent light search product; save selected references under `design/search-first/`.
- [ ] Add failing browser checks: home has one primary search and no dashboard KPI/sidebar; keyboard/IME behavior; example submits exactly once; all 11 domains are available to Administrator; Workspace links preserve direct destinations; persona menu remains reachable on mobile.
- [ ] Run focused browser checks and confirm they fail against the current overview shell.
- [ ] Replace dashboard home/sidebar with the proposed top navigation, search home and clearable per-persona local recent queries (last 5). Limit technical service information to Workspace.
- [ ] Verify home/menu at 1440/768/390px and keyboard use; commit `feat: introduce search-first knowledge home`.

## Task 4: Combined results and automatic cited AI

**Files:** `frontend/src/app/search/page.tsx`, `api/discovery.ts`, `hooks/useDiscovery.ts`, `hooks/useKnowledgeRun.ts`, `components/discovery/ResultList.tsx`, `AnswerPanel.tsx`, `DiscoveryDetail.tsx`, `SearchHeader.tsx`, `frontend/tests/e2e/discovery-search.spec.ts`.

**Interfaces:** `useDiscovery({query, domainId, type, sort, page}, token)` returns independent ranked result state; `useKnowledgeRun({query, domainId}, token)` returns scoped stored run/status, explicit `submit`, `cancel` and `reconnect`. Route query key is `q`; preserve legacy `/search` by displaying its search entry state. Result selection is encoded in URL.

- [ ] Add failing checks with intercepted result/run boundaries: results appear while AI is delayed; one explicit submit creates one AI run; provider failure leaves results; result failure leaves valid answer; rapid query/persona changes cannot show stale data; domain Apply changes both requests; tabs/sort/page never create runs; reload/back reconnect rather than POST; citations open real evidence; cancel is terminal.
- [ ] Run the focused browser spec and confirm the current separate search/catalog flow fails.
- [ ] Start deterministic search and LangGraph concurrently on explicit submit; separate their loading/error state. Disconnect/cancel prior active run; persist query/domain/persona run associations. Use generation keys and request cancellation to reject stale callbacks. Passive URL restoration cannot create a paid run without an existing association.
- [ ] Implement compact header/tabs, AI answer above readable result rows, expandable tool steps and source details. Keep unknown/truncated counts honest. Expose explicit retry/Generate answer only when necessary.
- [ ] Run the mocked timing/race cases and actual extractive search; then perform one real DeepSeek query and open its citations. Commit `feat: combine discovery results and cited AI answers`.

## Task 5: Catalog and contextual governance

**Files:** `frontend/src/app/catalog/page.tsx`, `components/discovery/DiscoveryDetail.tsx`, existing `AssetDetail.tsx`, secondary domain/source/ontology/project/role routes and shared styles; `frontend/tests/e2e/catalog.spec.ts`, `accessibility.spec.ts`.

**Interfaces:** Preserve existing catalog filters and detail APIs. URL selects list/grid mode, domain/filter state and optional selected item; dialogs restore focus to their originating result/card.

- [ ] Add/adjust checks: default catalog is an unselected library; list/grid and filters persist on reload/back; source previews still show PostgreSQL rows and MinIO text; product detail shows stewardship/gaps/ontology; Project edits persist; Analyst stays read-only; Escape and focus restoration work on mobile.
- [ ] Run these tests and confirm changed library expectations fail against the current preselected side pane/KPI strip.
- [ ] Build simple catalog cards/list, progressive item details, domain browsing and filter controls. Restyle retained secondary pages under the new shell without changing their business behavior.
- [ ] Run catalog/accessibility specs and manually inspect all secondary routes; commit `feat: simplify catalog and contextual governance`.

## Task 6: Purposeful motion and delivery verification

**Files:** `frontend/package.json`, `package-lock.json`, `components/motion/MotionProvider.tsx`, home/SearchBox/result/detail components, `ShaderSurface.tsx`, `frontend/tests/e2e/motion.spec.ts`, README, MCP/verification docs, final screenshots.

**Interfaces:** Shared motion preference provider; Framer Motion owns layout/presence/interactions; GSAP owns only home intro/dot motif. Timings/limits follow spec; no two libraries animate the same property/element.

- [ ] Add failing behavioral checks: reduced-motion skips transforms but permits full interaction; route unmount cleans up GSAP; detail focus survives animation; busy/results states remain keyboard usable. Do not write tests merely asserting CSS duration constants.
- [ ] Verify and lock React-compatible GSAP/@gsap/react and Framer Motion releases from official package documentation; implement 160–240ms interactions, 320ms search layout and <=600ms home sequence. First 6 results only, 24ms stagger. Add reduced-motion/static/offscreen handling.
- [ ] Run backend suite, frontend typecheck/build and all browser tests **sequentially** where shared index/run fixtures can collide. Verify package audits and real HTTP/stdio clients. Take home/results/catalog/detail screenshots at 1440px and 390px and inspect them.
- [ ] Confirm live DeepSeek answer/citations, service readiness and no browser/git credential exposure. Record counts, latency and any bounded-result limitations in `docs/verification.md`.
- [ ] Use the final review/verification skills, fix material issues, commit `feat: polish discovery motion and verify FastMCP delivery` and open the local preview. Preserve the worktree and source; no public deployment is part of this plan.

## Self-review

The user-confirmed simultaneous AI/results behavior is covered by Task 4; domain consistency by Task 2. MCP transport migration precedes shared discovery registration. Tasks 3–5 preserve all existing destinations and data capabilities. Task 6 assigns separate animation ownership and checks reduced motion. Review-focus failures map respectively to Tasks 4, 2, 4–5, 4 and 3/5/6. No implementation, dependency installation or service changes occurred while writing this plan.
