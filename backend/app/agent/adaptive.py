"""A real LangGraph tool-selection loop with bounded state and observable coverage."""

import json, time
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from langgraph.graph import StateGraph, START, END
from app.agent.actions import ResearchState, ActionDecision, InvalidDecision
from app.agent.coverage import assess_coverage
from app.knowledge.contracts import (
    ReadAction,
    ResolveEntitiesAction,
    TraverseGraphAction,
    ReadContentAction,
    EvidenceFragment,
    ToolResult,
)
from app.knowledge.runtime import guard
from app.knowledge.tools import execute_read


def compact_tool_receipt(result):
    data = result.model_dump(mode="json")
    # Full content stays in the checkpoint; native history carries compact, valid JSON.
    if data.get("content"):
        data["content"] = None
        data["truncated"] = True
    for item in data["items"]:
        if isinstance(item.get("text"), str) and len(item["text"]) > 800:
            item["text"] = item["text"][:800]
            data["truncated"] = True

    def encoded():
        return json.dumps(data, ensure_ascii=False, default=str)

    for key in ["items", "paths", "source_refs"]:
        while len(encoded().encode()) > 8000 and len(data[key]) > 1:
            data[key].pop()
            data["truncated"] = True
    if len(encoded().encode()) > 8000:
        first = data["items"][0] if data["items"] else {}
        data = {
            "outcome": data["outcome"],
            "truncated": True,
            "items": [
                {
                    key: first[key]
                    for key in ["id", "asset_id", "locator", "source_ref", "text"]
                    if key in first
                }
            ],
            "detail": "Tool output compacted. Read a specific source handle or cursor for more content.",
        }
    return encoded()


def build_research_graph(
    ctx, decide, reader=execute_read, checkpointer=None, on_event=None
):
    def notice(stage, message):
        if on_event:
            on_event(stage, message)

    def restore(s):
        ctx.tool_calls = max(ctx.tool_calls, s.tool_calls)
        ctx.graph_nodes.update(s.graph_nodes)
        ctx.graph_edges.update(s.graph_edges)

    def read(call):
        guard(ctx)
        if ctx.tool_calls >= ctx.max_tool_calls:
            raise TimeoutError("Source tool budget exhausted")
        before = ctx.tool_calls
        result = reader(ctx, call)
        if ctx.tool_calls == before:
            ctx.tool_calls += 1
        guard(ctx)
        return result

    def initialize(s):
        result = read(ResolveEntitiesAction(query=s.query))
        notice("resolve", "Resolving authorized business entities")
        observations = [
            {
                "tool": "resolve_entities",
                "outcome": result.outcome,
                "items": result.items,
            }
        ]
        paths = []
        seeded = []
        roots = [
            item["id"]
            for item in result.items
            if item.get("entity_type") and item.get("id")
        ][:3]
        if result.outcome == "ok" and roots:
            routed = read(
                TraverseGraphAction(
                    roots=roots,
                    predicates=["governedBy", "supportedBy", "recordedIn", "partOf"],
                    depth=2,
                )
            )
            paths = routed.paths
            observations.append(
                {
                    "tool": "traverse_graph",
                    "outcome": routed.outcome,
                    "items": routed.items,
                    "paths": paths,
                    "detail": routed.detail,
                }
            )
            notice(
                "graph",
                "Following source-backed relationships to scoped source handles",
            )
            if routed.source_refs:
                candidates = [item for item in result.items if item.get("id") in roots]
                if any(word in s.query.lower() for word in ["polic", "govern"]):
                    candidates.sort(
                        key=lambda item: item.get("entity_type") != "Policy"
                    )
                if candidates:
                    # Read the actual source from its beginning, including the
                    # policy identifier/status header, rather than only the
                    # graph assertion's locator. This is still one bounded page.
                    candidate_id = candidates[0]["id"]
                    ref = next(
                        (
                            edge["source_ref"]
                            for path in paths
                            for edge in path.get("edges", [])
                            if edge["source"] == candidate_id
                            and edge["predicate"] == "supportedBy"
                        ),
                        routed.source_refs[0].model_dump(mode="json"),
                    )
                    content = read(ReadContentAction(kind="asset", id=ref["asset_id"]))
                    for entry in content.items[:8]:
                        if entry.get("source_ref") and entry.get("text"):
                            ref = entry["source_ref"]
                            seeded.append(
                                EvidenceFragment(
                                    id=entry["id"],
                                    asset_id=entry["asset_id"],
                                    domain_id=ref["domain_id"],
                                    content_kind=entry["content_kind"],
                                    text=entry["text"],
                                    source_title=entry.get("title"),
                                    source_ref=ref,
                                    values=entry.get("values"),
                                    paths=content.paths,
                                )
                            )
                    observations.append(
                        {
                            "tool": "read_content",
                            "outcome": content.outcome,
                            "items": content.items[:8],
                            "paths": content.paths,
                            "truncated": content.truncated,
                        }
                    )
                    notice(
                        "read",
                        "Reading an initial source through the resolved graph entity",
                    )
        return {
            "entities": result.items,
            "evidence": seeded,
            "tool_calls": ctx.tool_calls,
            "observations": observations,
            "paths": paths,
            "graph_nodes": sorted(ctx.graph_nodes),
            "graph_edges": sorted(ctx.graph_edges),
        }

    def decision(s):
        restore(s)
        guard(ctx)
        if s.model_calls >= 4:
            return {"stop_reason": "model_budget"}
        if ctx.deadline - time.time() < ctx.finalization_reserve_seconds + 25:
            return {"stop_reason": "finalization_reserve"}
        try:
            d = ActionDecision.model_validate(decide(s, ctx.deadline))
        except (InvalidDecision, ValidationError):
            invalid = s.invalid_actions + 1
            notice("decide", "Correcting an invalid tool plan within the search budget")
            return {
                "last_decision": None,
                "model_calls": s.model_calls + 1,
                "invalid_actions": invalid,
                "observations": s.observations
                + [
                    {
                        "outcome": "invalid_decision",
                        "detail": "Return a valid update_plan. Evidence kinds must be document, structured, definition or metadata. Use returned IDs and registered tools only.",
                    }
                ],
                "stop_reason": "invalid_action" if invalid >= 2 else "",
            }

        intent = s.intent or d.intent
        if intent:
            intent = intent.model_copy(update={"query": s.query})
        evidence = []
        assessments = {a.evidence_id: a for a in d.assessments}
        facets = {f.id for f in intent.facets} if intent else set()
        for e in s.evidence:
            a = assessments.get(e.id)
            if a and not a.relevant:
                continue
            evidence.append(
                e.model_copy(
                    update={
                        "matched_facet_ids": [f for f in a.facet_ids if f in facets]
                    }
                )
                if a
                else e
            )
        coverage = assess_coverage(intent, evidence) if intent else s.coverage
        stop = ""
        if d.stop_action == "clarify":
            stop = "ambiguous"
        elif d.stop_action == "finish":
            stop = (
                "covered"
                if intent and intent.facets and not coverage.uncovered_facet_ids
                else "insufficient_evidence"
            )
        history = list(s.native_history)
        if d._native_message:
            history.extend([d._native_message] + d._native_controls)
        notice(
            "decide",
            d.summary or "Selecting evidence reads for unanswered requirements",
        )
        return {
            "native_history": history,
            "intent": intent,
            "last_decision": d,
            "model_calls": s.model_calls + 1,
            "evidence": evidence,
            "coverage": coverage,
            "stop_reason": stop,
            "clarification": d.summary if d.stop_action == "clarify" else "",
        }

    def tools(s):
        restore(s)
        if s.stop_reason:
            return {}
        if not s.intent:
            return {"stop_reason": "invalid_intent"}
        if s.no_progress_rounds >= 2:
            return {"stop_reason": "no_progress"}
        history = list(s.native_history)
        evidence = {e.id: e for e in s.evidence}
        paths = list(s.paths)
        observations = []
        keys = list(s.action_keys)
        invalid = s.invalid_actions
        progress = False
        prepared = {}

        def action_key(call):
            return (
                call.tool
                + ":"
                + json.dumps(call.model_dump(mode="json"), sort_keys=True)
            )

        def independent_read(call):
            local = ctx.model_copy(update={"tool_calls": 0, "max_tool_calls": 1})
            guard(local)
            result = reader(local, call)
            guard(local)
            return result

        # Graph traversal mutates shared graph budgets and stays sequential.
        # Independent source reads get isolated counters and two bounded slots.
        with ThreadPoolExecutor(max_workers=2) as batch:
            futures = {}
            for planned in s.last_decision.read_calls:
                if planned.tool not in [
                    "read_document",
                    "query_dataset",
                    "search_evidence",
                ]:
                    continue
                try:
                    arguments = json.loads(planned.arguments_json)
                    if (
                        not isinstance(arguments, dict)
                        or arguments.get("tool", planned.tool) != planned.tool
                    ):
                        continue
                    call = TypeAdapter(ReadAction).validate_python(
                        {**arguments, "tool": planned.tool}
                    )
                    key = action_key(call)
                    if (
                        key in keys
                        or key in futures
                        or ctx.tool_calls >= ctx.max_tool_calls
                    ):
                        continue
                    guard(ctx)
                    ctx.tool_calls += 1
                    futures[key] = batch.submit(independent_read, call)
                except (ValidationError, ValueError):
                    continue
            for key, future in futures.items():
                try:
                    prepared[key] = future.result()
                except Exception as error:
                    prepared[key] = error
        for planned in s.last_decision.read_calls:
            guard(ctx)
            try:
                arguments = json.loads(planned.arguments_json)
                if not isinstance(arguments, dict):
                    raise ValueError("Arguments must be an object")
                if "tool" in arguments and arguments["tool"] != planned.tool:
                    raise ValueError("Tool name mismatch")
                call = TypeAdapter(ReadAction).validate_python(
                    {**arguments, "tool": planned.tool}
                )
                key = (
                    planned.tool
                    + ":"
                    + json.dumps(call.model_dump(mode="json"), sort_keys=True)
                )
                if key in keys:
                    if planned.call_id:
                        history.append(
                            {
                                "role": "tool",
                                "tool_call_id": planned.call_id,
                                "content": "Already read; choose a new source or refine the action.",
                            }
                        )
                    observations.append(
                        {
                            "tool": planned.tool,
                            "outcome": "already_read",
                            "detail": "Choose a new source or refine the action",
                        }
                    )
                    continue
                keys.append(key)
                if key in prepared:
                    result = prepared[key]
                    if isinstance(result, Exception):
                        raise result
                else:
                    if ctx.tool_calls >= ctx.max_tool_calls:
                        return {
                            "stop_reason": "source_budget",
                            "tool_calls": ctx.tool_calls,
                            "evidence": list(evidence.values())[:20],
                            "paths": paths[:20],
                            "native_history": history,
                        }
                    result = read(call)
                paths.extend(p for p in result.paths if p not in paths)
                notice("read", "Reading " + planned.tool.replace("_", " "))
                entries = []
                for item in result.items:
                    entry = dict(item)
                    if "asset_id" in entry and "text" in entry:
                        ref = entry.get("source_ref") or next(
                            (
                                r.model_dump(mode="json")
                                for r in result.source_refs
                                if r.asset_id == entry["asset_id"]
                            ),
                            None,
                        )
                        if ref:
                            fragment = EvidenceFragment(
                                id=entry["id"],
                                asset_id=entry["asset_id"],
                                domain_id=ref["domain_id"],
                                content_kind=entry.get(
                                    "content_kind",
                                    "document"
                                    if planned.tool == "read_document"
                                    else "structured",
                                ),
                                text=entry["text"],
                                source_title=entry.get("source_title")
                                or entry.get("title")
                                or entry.get("name"),
                                source_ref=ref,
                                values=entry.get("values"),
                                provenance=entry.get("provenance", {}),
                                paths=result.paths,
                            )
                            if fragment.id not in evidence:
                                progress = True
                            evidence[fragment.id] = fragment
                    elif "values" in entry and entry.get("asset_id"):
                        ref = next(
                            (
                                r
                                for r in result.source_refs
                                if r.asset_id == entry["asset_id"]
                                and (
                                    r.locator == entry.get("locator")
                                    or entry.get("operation")
                                )
                            ),
                            None,
                        )
                        if ref:
                            id = entry.get("id") or ref.asset_id + ":" + ref.locator
                            if id not in evidence:
                                progress = True
                            evidence[id] = EvidenceFragment(
                                id=id,
                                asset_id=ref.asset_id,
                                domain_id=ref.domain_id,
                                content_kind="structured",
                                text=json.dumps(entry["values"]),
                                source_title=entry.get("title"),
                                source_ref=ref,
                                values=entry["values"],
                                provenance={
                                    "type": "structured",
                                    "operation": entry.get("operation"),
                                    "row_id": ref.locator,
                                },
                            )
                    entries.append(entry)
                if (
                    result.paths
                    or result.items
                    and not any("text" in e or "values" in e for e in result.items)
                ):
                    progress = True
                if planned.call_id:
                    history.append(
                        {
                            "role": "tool",
                            "tool_call_id": planned.call_id,
                            "content": compact_tool_receipt(result),
                        }
                    )
                observations.append(
                    {
                        "tool": planned.tool,
                        "outcome": result.outcome,
                        "items": entries[:20],
                        "paths": result.paths[:20],
                        "detail": result.detail,
                        "truncated": result.truncated,
                    }
                )
            except (ValidationError, ValueError, HTTPException) as e:
                if isinstance(e, HTTPException) and e.status_code not in (404, 422):
                    raise
                invalid += 1
                detail = (
                    "No accessible source matched this handle. Resolve the entity or search content and use only returned identifiers."
                    if isinstance(e, HTTPException) and e.status_code == 404
                    else str(e.detail)
                    if isinstance(e, HTTPException)
                    else "Arguments do not match the available tool schema"
                )
                if planned.call_id:
                    history.append(
                        {
                            "role": "tool",
                            "tool_call_id": planned.call_id,
                            "content": json.dumps(
                                {"outcome": "invalid_arguments", "detail": detail}
                            ),
                        }
                    )
                observations.append(
                    {
                        "tool": planned.tool,
                        "outcome": "invalid_arguments",
                        "detail": detail,
                    }
                )
                if invalid >= 2:
                    return {
                        "stop_reason": "invalid_action",
                        "invalid_actions": invalid,
                        "observations": observations,
                        "tool_calls": ctx.tool_calls,
                        "native_history": history,
                    }
        chosen = list(evidence.values())[:20]
        coverage = assess_coverage(s.intent, chosen)
        return {
            "native_history": history,
            "evidence": chosen,
            "paths": paths[:20],
            "coverage": coverage,
            "observations": observations,
            "action_keys": keys,
            "invalid_actions": invalid,
            "tool_calls": ctx.tool_calls,
            "graph_nodes": sorted(ctx.graph_nodes),
            "graph_edges": sorted(ctx.graph_edges),
            "no_progress_rounds": 0
            if progress
            else s.no_progress_rounds + (0 if invalid > s.invalid_actions else 1),
        }

    def route_decision(s):
        return (
            "finish"
            if s.stop_reason
            else "decide"
            if s.last_decision is None
            else "tools"
        )

    def route_tools(s):
        return (
            "finish"
            if s.stop_reason or s.no_progress_rounds >= 2 or s.model_calls >= 4
            else "decide"
        )

    def finish(s):
        reason = s.stop_reason or (
            "no_progress" if s.no_progress_rounds >= 2 else "model_budget"
        )
        outcome = (
            "needs_clarification"
            if reason == "ambiguous"
            else "answered"
            if s.intent and s.intent.facets and not s.coverage.uncovered_facet_ids
            else "partial"
            if any(e.matched_facet_ids for e in s.evidence)
            else "no_evidence"
        )
        return {
            "stop_reason": reason,
            "answer_outcome": outcome,
            "tool_calls": ctx.tool_calls,
        }

    graph = StateGraph(ResearchState)
    for name, fn in [
        ("initialize", initialize),
        ("decide", decision),
        ("tools", tools),
        ("finish", finish),
    ]:
        graph.add_node(name, fn)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "decide")
    graph.add_conditional_edges(
        "decide",
        route_decision,
        {"tools": "tools", "finish": "finish", "decide": "decide"},
    )
    graph.add_conditional_edges(
        "tools", route_tools, {"decide": "decide", "finish": "finish"}
    )
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer)


def run_research(ctx, query, decide, reader=execute_read):
    result = build_research_graph(ctx, decide, reader).invoke(
        ResearchState(query=query), config={"recursion_limit": 24}
    )
    return ResearchState.model_validate(result)
