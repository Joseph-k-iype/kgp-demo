"""OpenAI-compatible adapter boundaries with explicit capability selection."""

import json
from pydantic import BaseModel, ConfigDict
from typing import Literal
from app.agent.actions import ActionDecision, PlannedCall, EvidenceAssessment
from app.knowledge.contracts import (
    SearchIntentV2,
    ResolveEntitiesAction,
    TraverseGraphAction,
    ReadDocumentAction,
    QueryDatasetAction,
    SearchEvidenceAction,
    ReadContentAction,
)
from app.knowledge.tools import available_tools


class ProviderCapabilities(BaseModel):
    structured_outputs: bool = True
    native_tools_verified: bool = False
    native_multiturn_verified: bool = False


def choose_adapter(capabilities: ProviderCapabilities):
    if capabilities.native_tools_verified and capabilities.native_multiturn_verified:
        return "native_tools"
    if capabilities.structured_outputs:
        return "json_actions"
    raise ValueError("The provider does not support validated search decisions")


def native_messages(state, context):
    from app.agent.prompts import DECISION_SYSTEM

    blocks = []
    for message in state.native_history:
        if message.get("role") == "assistant":
            blocks.append([])
        if blocks:
            blocks[-1].append(message)
    return (
        [{"role": "system", "content": DECISION_SYSTEM}]
        + [message for block in blocks[-2:] for message in block]
        + [{"role": "user", "content": json.dumps(context, default=str)}]
    )


class PlanControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent_json: str
    assessments_json: str
    stop_action: Literal["continue", "finish", "clarify"]
    summary: str


def native_tools():
    models = {
        "resolve_entities": ResolveEntitiesAction,
        "traverse_graph": TraverseGraphAction,
        "read_document": ReadDocumentAction,
        "query_dataset": QueryDatasetAction,
        "search_evidence": SearchEvidenceAction,
        "read_content": ReadContentAction,
    }
    tools = []
    for name in available_tools():
        if name not in models:
            continue
        schema = models[name].model_json_schema()
        schema["properties"].pop("tool", None)
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": {
                        "resolve_entities": "Resolve scoped business mentions and ambiguity.",
                        "traverse_graph": "Find source-backed governing relationships and source handles.",
                        "read_document": "Read a specific original document passage.",
                        "query_dataset": "Read or aggregate approved dataset fields with typed filters.",
                        "search_evidence": "Find content candidates within authorized source handles.",
                        "read_content": "Open actual document, rows, RDF facts or product content with separate catalog context.",
                    }[name],
                    "parameters": schema,
                },
            }
        )
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "update_plan",
                "description": "Set the first question-specific intent, assess relevant evidence facets, or finish/clarify. Always establish the intent before reading.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent_json": {
                            "type": "string",
                            "description": "SearchIntentV2 JSON or null; query, facets:[{id,description,kinds}],entity_ids,ambiguous.",
                        },
                        "assessments_json": {
                            "type": "string",
                            "description": "JSON array [{evidence_id,facet_ids,relevant}]",
                        },
                        "stop_action": {
                            "type": "string",
                            "enum": ["continue", "finish", "clarify"],
                        },
                        "summary": {"type": "string"},
                    },
                    "required": [
                        "intent_json",
                        "assessments_json",
                        "stop_action",
                        "summary",
                    ],
                    "additionalProperties": False,
                },
            },
        }
    )
    return tools


def parse_native_decision(message):
    intent = None
    assessments = []
    reads = []
    stop = "continue"
    summary = ""
    controls = []
    ids = [c["id"] for c in message.get("tool_calls", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate native tool call identifiers")
    for call in message.get("tool_calls", []):
        name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])
        if name == "update_plan":
            if controls:
                raise ValueError("Only one plan update is permitted per decision")
            args = PlanControl.model_validate(args).model_dump()
            value = json.loads(args.get("intent_json", "null"))
            if value:
                intent = SearchIntentV2.model_validate(value)
            assessments = [
                EvidenceAssessment.model_validate(a)
                for a in json.loads(args.get("assessments_json", "[]"))
            ]
            stop = args.get("stop_action", "continue")
            summary = args.get("summary", "")
            controls.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": "Plan update accepted",
                }
            )
        else:
            reads.append(
                PlannedCall(
                    tool=name, arguments_json=json.dumps(args), call_id=call["id"]
                )
            )
    if not message.get("tool_calls"):
        raise ValueError("The model returned no validated action")
    decision = ActionDecision(
        intent=intent,
        read_calls=reads,
        assessments=assessments,
        stop_action=stop,
        summary=summary,
    )
    decision._native_message = message
    decision._native_controls = controls
    return decision
