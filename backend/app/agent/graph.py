import time
from langgraph.graph import StateGraph, START, END
from app.agent.state import SearchState
from app.agent.provider import (
    plan_query,
    synthesize,
    validate_answer,
    ConfigurationRequired,
)
from app.auth import resolve_scope, narrow_scope
from app.ontology.service import resolve_concepts, explore_ontology
from app.retrieval.service import retrieve, expand_evidence
from app.contracts import AnswerOutput
from app.config import settings


class RunCancelled(Exception):
    pass


class ScopeChanged(Exception):
    pass


def build_graph(checkpointer=None, event_callback=None, run_reader=None):
    def guard(s, stage):
        scope = resolve_scope(s["person_id"])
        if scope.scope_version != s["scope_version"]:
            raise ScopeChanged("Access scope changed; start a new search.")
        if time.time() - s["started"] > 90:
            raise TimeoutError("Search exceeded its 90 second limit")
        if s.get("tool_calls", 0) >= 12:
            raise TimeoutError("Search exceeded its tool limit")
        if run_reader and run_reader(s["run_id"])["status"] == "cancelled":
            raise RunCancelled()
        if event_callback:
            event_callback(
                s["run_id"],
                stage,
                "running",
                {
                    "authorize": "Checking domain access",
                    "plan": "Planning retrieval",
                    "resolve": "Resolving RDF concepts",
                    "retrieve": "Searching keyword and vector indexes",
                    "expand": "Checking evidence provenance",
                    "assess": "Assessing source coverage",
                    "synthesize": "Composing an evidence-backed answer",
                    "validate": "Validating source citations",
                    "finish": "Finalizing verified evidence",
                }[stage],
            )
        return narrow_scope(scope, s.get("domain_id"))

    def authorize(s):
        guard(s, "authorize")
        if s["mode"] != "extractive" and not settings().llm_key:
            raise ConfigurationRequired(
                "LLM provider key is not configured. Select Extractive demo or configure the server."
            )
        return {"tool_calls": 0, "retrieval_passes": 0}

    def plan(s):
        guard(s, "plan")
        if s["mode"] != "extractive":
            p = plan_query(s["query"], deadline=s["started"] + 90)
            labels = p.concept_labels
            variants = p.query_variants[:2]
        else:
            labels = [s["query"]]
            variants = [s["query"]]
        return {
            "concept_labels": labels,
            "variants": variants or [s["query"]],
            "tool_calls": s["tool_calls"] + 1,
        }

    def resolve(s):
        scope = guard(s, "resolve")
        concepts = resolve_concepts(scope, s["concept_labels"])
        graph = (
            explore_ontology(scope, concepts[0], depth=1, limit=20)
            if concepts
            else {"nodes": [], "edges": []}
        )
        return {"concepts": concepts, "graph": graph, "tool_calls": s["tool_calls"] + 1}

    def retrieval(s):
        scope = guard(s, "retrieve")
        items = retrieve(
            scope,
            s["variants"][min(s["retrieval_passes"], len(s["variants"]) - 1)],
            s["concepts"],
            limit=10,
            deadline=s["started"] + 90,
        )
        merged = {e["id"]: e for e in s.get("evidence", [])}
        merged.update({e["id"]: e for e in items})
        return {
            "evidence": list(merged.values())[:16],
            "retrieval_passes": s["retrieval_passes"] + 1,
            "tool_calls": s["tool_calls"] + 1,
        }

    def expand(s):
        scope = guard(s, "expand")
        return {
            "evidence": expand_evidence(
                scope, s["evidence"], deadline=s["started"] + 90
            ),
            "tool_calls": s["tool_calls"] + 1,
        }

    def assess(s):
        guard(s, "assess")
        types = {e["provenance"]["type"] for e in s["evidence"]}
        gaps = []
        if "document" not in types:
            gaps.append("No matching document evidence was retrieved.")
        if "structured" not in types:
            gaps.append("No matching structured rows were retrieved.")
        return {"gaps": gaps, "tool_calls": s["tool_calls"] + 1}

    def routing(s):
        if not s["evidence"]:
            return "finish"
        if s["gaps"] and s["retrieval_passes"] < 2 and len(s["variants"]) > 1:
            return "retrieve"
        return "synthesize"

    def synthesis(s):
        guard(s, "synthesize")
        if s["mode"] != "extractive":
            answer = synthesize(
                s["query"], s["evidence"], deadline=s["started"] + 90
            ).model_dump()
        else:
            chosen = []
            types = set()
            for e in s["evidence"]:
                if e["provenance"]["type"] not in types:
                    chosen.append(e)
                    types.add(e["provenance"]["type"])
            answer = {
                "statements": [
                    {"text": e["text"][:650], "evidence_ids": [e["id"]]}
                    for e in chosen[:4]
                ],
                "gaps": s["gaps"],
                "uncertainty": "Extractive demo: these are source excerpts, not LLM-generated conclusions.",
            }
        return {**answer, "tool_calls": s["tool_calls"] + 1}

    def validation(s):
        scope = guard(s, "validate")
        current = expand_evidence(scope, s["evidence"], deadline=s["started"] + 90)
        validate_answer(
            AnswerOutput(
                statements=s["statements"], gaps=s["gaps"], uncertainty=s["uncertainty"]
            ),
            current,
        )
        return {"evidence": current, "tool_calls": s["tool_calls"] + 1}

    def finish(s):
        guard(s, "finish")
        if not s.get("evidence"):
            return {
                "statements": [],
                "gaps": ["No supporting evidence found within your authorized scope."],
                "uncertainty": "No evidence",
            }
        return {}

    builder = StateGraph(SearchState)
    for name, fn in [
        ("authorize", authorize),
        ("plan", plan),
        ("resolve", resolve),
        ("retrieve", retrieval),
        ("expand", expand),
        ("assess", assess),
        ("synthesize", synthesis),
        ("validate", validation),
        ("finish", finish),
    ]:
        builder.add_node(name, fn)
    builder.add_edge(START, "authorize")
    for a, b in [
        ("authorize", "plan"),
        ("plan", "resolve"),
        ("resolve", "retrieve"),
        ("retrieve", "expand"),
        ("expand", "assess"),
        ("synthesize", "validate"),
        ("validate", "finish"),
        ("finish", END),
    ]:
        builder.add_edge(a, b)
    builder.add_conditional_edges(
        "assess",
        routing,
        {"retrieve": "retrieve", "synthesize": "synthesize", "finish": "finish"},
    )
    return builder.compile(checkpointer=checkpointer)
