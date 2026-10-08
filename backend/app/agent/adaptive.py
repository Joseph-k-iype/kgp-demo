"""A real LangGraph tool-selection loop with bounded state and observable coverage."""

import json, time
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from langgraph.graph import StateGraph, START, END
from app.agent.actions import ResearchState, ActionDecision
from app.agent.coverage import assess_coverage
from app.knowledge.contracts import (
    ReadAction,
    ResolveEntitiesAction,
    EvidenceFragment,
    ToolResult,
)
from app.knowledge.runtime import guard
from app.knowledge.tools import execute_read


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
        return {
            "entities": result.items,
            "tool_calls": ctx.tool_calls,
            "observations": [
                {
                    "tool": "resolve_entities",
                    "outcome": result.outcome,
                    "items": result.items,
                }
            ],
        }

    def decision(s):
        restore(s)
        guard(ctx)
        if s.model_calls >= 4:
            return {"stop_reason": "model_budget"}
        if ctx.deadline - time.time() < 20:
            return {"stop_reason": "finalization_reserve"}
        d = ActionDecision.model_validate(decide(s, ctx.deadline))
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
                            "content": json.dumps(
                                result.model_dump(mode="json"), default=str
                            )[:8000],
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
                if isinstance(e, HTTPException) and e.status_code != 422:
                    raise
                invalid += 1
                detail = (
                    str(e.detail)
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
            "no_progress_rounds": 0 if progress else s.no_progress_rounds + 1,
        }

    def route_decision(s):
        return "finish" if s.stop_reason else "tools"

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
        "decide", route_decision, {"tools": "tools", "finish": "finish"}
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
