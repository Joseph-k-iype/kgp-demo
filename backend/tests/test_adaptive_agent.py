import time
import pytest
from app.agent.actions import ActionDecision, PlannedCall, EvidenceAssessment
from app.agent.adaptive import run_research
from app.knowledge.contracts import ToolContext, SearchIntentV2, ToolResult
from app.auth import resolve_scope


def ctx():
    return ToolContext(scope=resolve_scope("admin"), deadline=time.time() + 60)


def test_irrelevant_policy_leaves_coverage_open_and_drives_new_graph_action():
    intent = {
        "query": "Which policies govern treasury liquidity?",
        "facets": [
            {
                "id": "policies",
                "description": "Applicable policy clauses",
                "kinds": ["document"],
            }
        ],
    }
    decisions = [
        ActionDecision(
            intent=intent,
            read_calls=[
                PlannedCall(
                    tool="search_evidence",
                    arguments_json='{"query":"policy","kinds":["document"],"strategy":"keyword"}',
                )
            ],
        ),
        ActionDecision(
            assessments=[
                EvidenceAssessment(evidence_id="people", facet_ids=[], relevant=False)
            ],
            read_calls=[
                PlannedCall(
                    tool="traverse_graph",
                    arguments_json='{"roots":["treasury-liquidity"],"predicates":["governedBy"],"target_kinds":["Policy"]}',
                )
            ],
        ),
        ActionDecision(
            read_calls=[
                PlannedCall(
                    tool="read_document",
                    arguments_json='{"asset_id":"finance-asset-1","section_id":"controls"}',
                )
            ]
        ),
        ActionDecision(
            assessments=[
                EvidenceAssessment(
                    evidence_id="finance", facet_ids=["policies"], relevant=True
                )
            ],
            stop_action="finish",
        ),
    ]
    calls = []

    def read(context, call):
        calls.append(call.tool)
        if call.tool == "resolve_entities":
            return ToolResult(items=[])
        if call.tool == "search_evidence":
            return ToolResult(
                items=[
                    {
                        "id": "people",
                        "asset_id": "people-asset-1",
                        "domain_id": "people",
                        "content_kind": "document",
                        "text": "People access policy",
                        "source_ref": {
                            "asset_id": "people-asset-1",
                            "domain_id": "people",
                            "version": "v1",
                            "locator": "controls",
                        },
                    }
                ]
            )
        if call.tool == "read_document":
            return ToolResult(
                items=[
                    {
                        "id": "finance",
                        "asset_id": "finance-asset-1",
                        "title": "TL-POL-001",
                        "text": "Daily reconciliation",
                        "locator": "controls",
                    }
                ],
                source_refs=[
                    {
                        "asset_id": "finance-asset-1",
                        "domain_id": "finance",
                        "version": "v2",
                        "locator": "controls",
                    }
                ],
            )
        return ToolResult(
            items=[{"id": "TL-POL-001", "name": "Treasury policy"}],
            paths=[{"edges": []}],
        )

    state = run_research(
        ctx(),
        "Which policies govern treasury liquidity?",
        decide=lambda state, deadline: decisions.pop(0),
        reader=read,
    )
    assert state.coverage.uncovered_facet_ids == []
    assert all(e.id != "people" for e in state.evidence)
    assert "traverse_graph" in calls and state.model_calls == 4


def test_unknown_tool_or_identity_argument_is_never_executed():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PlannedCall(tool="shell", arguments_json="{}")
    decision = ActionDecision(
        intent={"query": "Find data", "facets": []},
        read_calls=[
            PlannedCall(
                tool="read_document",
                arguments_json='{"asset_id":"finance-asset-1","person_id":"admin"}',
            )
        ],
    )
    calls = []
    state = run_research(
        ctx(),
        "Find data",
        decide=lambda *a: decision,
        reader=lambda c, call: calls.append(call.tool) or ToolResult(),
    )
    assert calls == ["resolve_entities"]
    assert state.stop_reason in ["invalid_action", "no_progress", "model_budget"]


def test_repeated_read_actions_stop_without_running_forever():
    d = ActionDecision(
        intent={
            "query": "Unmapped source",
            "facets": [
                {"id": "f", "description": "Missing policy", "kinds": ["document"]}
            ],
        },
        read_calls=[
            PlannedCall(tool="search_evidence", arguments_json='{"query":"missing"}')
        ],
    )
    calls = []
    state = run_research(
        ctx(),
        "Unmapped source",
        decide=lambda *a: d,
        reader=lambda c, call: (
            calls.append(call.tool) or ToolResult(outcome="no_match")
        ),
    )
    assert calls.count("search_evidence") == 1
    assert state.model_calls <= 4 and state.stop_reason == "no_progress"


def test_material_ambiguity_returns_clarification():
    state = run_research(
        ctx(),
        "Which policy?",
        decide=lambda *a: ActionDecision(
            intent={"query": "Which policy?", "facets": [], "ambiguous": True},
            stop_action="clarify",
            summary="Which business area do you mean?",
        ),
        reader=lambda *a: ToolResult(),
    )
    assert state.answer_outcome == "needs_clarification"


def test_adapter_selection_requires_verified_native_multiturn():
    from app.agent.adapter import ProviderCapabilities, choose_adapter

    assert (
        choose_adapter(
            ProviderCapabilities(
                structured_outputs=True,
                native_tools_verified=False,
                native_multiturn_verified=False,
            )
        )
        == "json_actions"
    )
    assert (
        choose_adapter(
            ProviderCapabilities(
                structured_outputs=True,
                native_tools_verified=True,
                native_multiturn_verified=True,
            )
        )
        == "native_tools"
    )


def test_native_tool_ids_are_preserved_in_followup_messages():
    from app.agent.adapter import parse_native_decision, native_messages
    from app.agent.actions import ResearchState

    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-plan",
                "type": "function",
                "function": {
                    "name": "update_plan",
                    "arguments": '{"intent_json":"{\\"query\\":\\"Find policy\\",\\"facets\\":[]}","assessments_json":"[]","stop_action":"continue","summary":"Read a policy"}',
                },
            },
            {
                "id": "call-source",
                "type": "function",
                "function": {
                    "name": "read_document",
                    "arguments": '{"asset_id":"finance-asset-1","section_id":"controls"}',
                },
            },
        ],
    }
    decision = parse_native_decision(message)
    assert decision.read_calls[0].call_id == "call-source"
    state = ResearchState(
        query="Find policy",
        native_history=[
            message,
            {"role": "tool", "tool_call_id": "call-plan", "content": "Plan accepted"},
            {
                "role": "tool",
                "tool_call_id": "call-source",
                "content": "Daily reconciliation",
            },
        ],
    )
    messages = native_messages(state, {"query": "Find policy"})
    assert any(m.get("tool_call_id") == "call-source" for m in messages)
    assert any(m.get("tool_calls") == message["tool_calls"] for m in messages)


def test_expired_agent_cannot_call_the_model():
    import pytest

    context = ctx()
    context.deadline = time.time() - 1
    calls = []
    with pytest.raises(TimeoutError):
        run_research(
            context,
            "Find policy",
            decide=lambda *a: calls.append("model"),
            reader=lambda *a: ToolResult(),
        )
    assert not calls


def test_decision_provider_uses_the_strict_openrouter_boundary(monkeypatch):
    import json, httpx
    from openai import OpenAI
    from app.agent import provider
    from app.agent.actions import ResearchState
    from app.agent.provider import make_decider

    from app.config import Settings

    config = Settings(
        _env_file=None,
        llm_provider="openrouter",
        openrouter_model="deepseek/deepseek-v3.2",
        openrouter_structured_mode="json_schema",
        agent_adapter="json_actions",
    )
    monkeypatch.setattr(provider, "settings", lambda: config)

    captured = []

    def respond(request):
        payload = json.loads(request.content)
        captured.append(payload)
        content = {
            "intent": {
                "query": "Find policies",
                "facets": [
                    {
                        "id": "policies",
                        "description": "Governing policies",
                        "kinds": ["document"],
                    }
                ],
                "entity_ids": [],
                "ambiguous": False,
            },
            "read_calls": [],
            "assessments": [],
            "stop_action": "finish",
            "summary": "No supporting evidence",
        }
        return httpx.Response(
            200,
            json={
                "id": "completion-test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek/deepseek-v3.2",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(content),
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    monkeypatch.setattr(
        provider,
        "client",
        lambda: OpenAI(
            api_key="test-only",
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ),
    )
    decision = make_decider(ctx())(
        ResearchState(query="Find policies"), time.time() + 30
    )
    assert decision.stop_action == "finish"
    assert captured[0]["response_format"]["json_schema"]["strict"]
    assert captured[0]["provider"]["require_parameters"] is True
    assert captured[0]["reasoning"]["enabled"] is False


@pytest.mark.parametrize("status_code", [422, 404])
def test_recoverable_tool_argument_error_drives_a_corrected_action(status_code):
    from fastapi import HTTPException

    choices = [
        ActionDecision(
            intent={
                "query": "FIN-100 liquidity",
                "facets": [
                    {
                        "id": "amount",
                        "description": "USD amount",
                        "kinds": ["structured"],
                    }
                ],
            },
            read_calls=[
                PlannedCall(
                    tool="query_dataset",
                    arguments_json='{"query":{"asset_id":"finance-asset-0","select":["wrong_field"]}}',
                )
            ],
        ),
        ActionDecision(
            read_calls=[
                PlannedCall(
                    tool="query_dataset",
                    arguments_json='{"query":{"asset_id":"finance-asset-0","select":["liquidity_usd"]}}',
                )
            ]
        ),
        ActionDecision(
            assessments=[
                EvidenceAssessment(
                    evidence_id="row", facet_ids=["amount"], relevant=True
                )
            ],
            stop_action="finish",
        ),
    ]

    def reader(context, call):
        if call.tool == "resolve_entities":
            return ToolResult()
        if "wrong_field" in call.query.select:
            raise HTTPException(
                status_code,
                "Unknown dataset field"
                if status_code == 422
                else "Record not found in your scope",
            )
        return ToolResult(
            items=[
                {
                    "id": "row",
                    "asset_id": "finance-asset-0",
                    "values": {"liquidity_usd": 12500000},
                    "locator": "r1",
                }
            ],
            source_refs=[
                {
                    "asset_id": "finance-asset-0",
                    "domain_id": "finance",
                    "version": "v1",
                    "locator": "r1",
                }
            ],
        )

    state = run_research(
        ctx(), "FIN-100 liquidity", decide=lambda *a: choices.pop(0), reader=reader
    )
    assert state.answer_outcome == "answered"


def test_independent_document_reads_overlap_with_bounded_source_budget():
    import threading

    gate = threading.Barrier(2)
    reads = []
    choices = [
        ActionDecision(
            intent={
                "query": "Compare two policies",
                "facets": [
                    {
                        "id": "policies",
                        "description": "Two policy clauses",
                        "kinds": ["document"],
                    }
                ],
            },
            read_calls=[
                PlannedCall(
                    tool="read_document",
                    arguments_json='{"asset_id":"finance-asset-1"}',
                ),
                PlannedCall(
                    tool="read_document",
                    arguments_json='{"asset_id":"finance-asset-5"}',
                ),
            ],
        ),
        ActionDecision(stop_action="finish"),
    ]

    def reader(context, call):
        if call.tool == "read_document":
            reads.append(call.asset_id)
            gate.wait(timeout=2)
        return ToolResult()

    state = run_research(
        ctx(), "Compare two policies", lambda *a: choices.pop(0), reader
    )
    assert len(reads) == 2 and state.tool_calls == 3


def test_native_sdk_multiturn_sends_matching_tool_receipts(monkeypatch):
    import json, httpx
    from openai import OpenAI
    from app.agent import provider
    from app.config import settings

    c = settings()
    monkeypatch.setattr(c, "agent_adapter", "native_tools")
    monkeypatch.setattr(c, "openrouter_upstream", "SiliconFlow")
    monkeypatch.setattr(c, "native_tools_verified_upstream", "SiliconFlow")
    monkeypatch.setattr(
        c, "native_tools_verified_model", c.llm_provider + ":" + c.llm_model
    )
    monkeypatch.setattr(c, "native_tools_verified", True)
    monkeypatch.setattr(c, "native_multiturn_verified", True)
    captured = []

    def respond(request):
        payload = json.loads(request.content)
        captured.append(payload)
        first = len(captured) == 1
        intent = {
            "query": "Find treasury policy",
            "facets": [
                {"id": "policy", "description": "Actual clause", "kinds": ["document"]}
            ],
        }
        calls = [
            {
                "id": "plan-" + str(len(captured)),
                "type": "function",
                "function": {
                    "name": "update_plan",
                    "arguments": json.dumps(
                        {
                            "intent_json": json.dumps(intent) if first else "null",
                            "assessments_json": "[]",
                            "stop_action": "continue" if first else "finish",
                            "summary": "Read source" if first else "No evidence",
                        }
                    ),
                },
            }
        ]
        if first:
            calls.append(
                {
                    "id": "source-1",
                    "type": "function",
                    "function": {
                        "name": "read_document",
                        "arguments": '{"asset_id":"finance-asset-1"}',
                    },
                }
            )
        return httpx.Response(
            200,
            json={
                "id": "test-native",
                "object": "chat.completion",
                "created": 0,
                "model": c.llm_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "tool_calls": calls},
                        "finish_reason": "tool_calls",
                    }
                ],
            },
        )

    monkeypatch.setattr(
        provider,
        "client",
        lambda: OpenAI(
            api_key="test-only",
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ),
    )
    context = ctx()
    state = run_research(
        context,
        "Find treasury policy",
        provider.make_decider(context),
        reader=lambda *a: ToolResult(),
    )
    assert len(captured) == 2 and state.answer_outcome == "no_evidence"
    second = captured[1]["messages"]
    assert {m["tool_call_id"] for m in second if m["role"] == "tool"} == {
        "plan-1",
        "source-1",
    }
    assert second[-1]["role"] == "user" and '"coverage"' in second[-1]["content"]
    assert captured[0]["provider"]["require_parameters"]


def test_decision_context_preserves_graph_source_handles_and_registered_fields():
    from app.agent.actions import ResearchState
    from app.agent.prompts import decision_context

    context = ctx()
    ref = {
        "asset_id": "finance-asset-0",
        "domain_id": "finance",
        "locator": "finance-asset-0-row-0",
        "version": "row-version",
    }
    state = ResearchState(
        query="What is FIN-100 liquidity?",
        paths=[
            {
                "edges": [
                    {
                        "source": "FIN-100",
                        "target": "finance-asset-0",
                        "predicate": "recordedIn",
                        "source_ref": ref,
                    }
                ]
            }
        ],
    )
    packed = decision_context(state, context)
    assert packed["paths"][0]["edges"][0]["source_ref"] == ref
    assert packed["source_handles"][0]["source_ref"] == ref
    assert "liquidity_usd" in packed["source_handles"][0]["fields"]


def test_openrouter_structured_prompt_carries_the_actual_output_contract(monkeypatch):
    import json, httpx
    from openai import OpenAI
    from app.agent import provider
    from app.agent.verification import DraftAnswer

    captured = []

    def respond(request):
        body = json.loads(request.content)
        captured.append(body)
        return httpx.Response(
            200,
            json={
                "id": "schema-test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek/deepseek-v3.2",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": '{"claims":[],"gaps":[],"uncertainty":"","sections":[]}',
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    monkeypatch.setattr(
        provider,
        "client",
        lambda: OpenAI(
            api_key="test-only",
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ),
    )
    provider.parse_response(
        DraftAnswer,
        "Answer with supported claims.",
        {"query": "Frequency?"},
        deadline=time.time() + 30,
    )
    prompt = captured[0]["messages"][0]["content"]
    assert '"quote"' in prompt and '"claim_indices"' in prompt
    assert "JSON object" in prompt and "code fence" in prompt


def test_openrouter_pinned_route_disables_fallbacks(monkeypatch):
    from app.agent import provider
    from app.config import Settings

    monkeypatch.setattr(
        provider,
        "settings",
        lambda: Settings(_env_file=None, openrouter_upstream="DeepInfra"),
    )
    assert provider.openrouter_options()["provider"] == {
        "require_parameters": True,
        "order": ["DeepInfra"],
        "allow_fallbacks": False,
    }


def test_native_certification_is_specific_to_the_upstream_route():
    from app.config import Settings
    from app.agent.provider import native_route_certified

    config = Settings(
        _env_file=None,
        openrouter_model="deepseek/deepseek-v3.2",
        openrouter_upstream="SiliconFlow",
        native_tools_verified_model="openrouter:deepseek/deepseek-v3.2",
        native_tools_verified_upstream="DeepInfra",
    )
    assert not native_route_certified(config)
    config.native_tools_verified_upstream = "SiliconFlow"
    assert native_route_certified(config)
    config.openrouter_upstream = ""
    assert not native_route_certified(config)


def test_invalid_native_plan_is_corrected_within_the_same_budget():
    from app.agent.actions import InvalidDecision

    attempts = []

    def decide(state, deadline):
        attempts.append(state.model_calls)
        if len(attempts) == 1:
            raise InvalidDecision(
                "Use only document, structured, definition or metadata evidence kinds."
            )
        assert state.observations[-1]["outcome"] == "invalid_decision"
        return ActionDecision(
            intent={"query": "Find policy", "facets": []}, stop_action="finish"
        )

    result = run_research(
        ctx(), "Find policy", decide, reader=lambda *args: ToolResult()
    )
    assert result.model_calls == 2
    assert len(attempts) == 2
    assert result.stop_reason != "invalid_intent"


def test_native_receipt_compaction_retains_valid_json_and_source_handles():
    import json
    from app.agent.adaptive import compact_tool_receipt

    result = ToolResult(
        items=[
            {
                "id": "clause",
                "text": "policy " * 5000,
                "source_ref": {
                    "asset_id": "finance-asset-1",
                    "locator": "controls",
                    "version": "v1",
                    "domain_id": "finance",
                },
            }
        ]
    )
    packed = compact_tool_receipt(result)
    assert len(packed.encode()) <= 8000
    value = json.loads(packed)
    assert value["truncated"]
    assert value["items"][0]["source_ref"]["locator"] == "controls"


def test_plan_only_round_then_corrective_read_does_not_prematurely_stall():
    from fastapi import HTTPException

    choices = [
        ActionDecision(
            intent={
                "query": "Find policy",
                "facets": [
                    {"id": "policy", "description": "Policy", "kinds": ["document"]}
                ],
            }
        ),
        ActionDecision(
            read_calls=[
                PlannedCall(
                    tool="traverse_graph", arguments_json='{"roots":["missing"]}'
                )
            ]
        ),
        ActionDecision(
            read_calls=[
                PlannedCall(
                    tool="resolve_entities", arguments_json='{"query":"Treasury"}'
                )
            ]
        ),
        ActionDecision(stop_action="finish"),
    ]

    resolutions = []

    def reader(context, call):
        if call.tool == "traverse_graph":
            raise HTTPException(404, "Not found in scope")
        resolutions.append(call.tool)
        return ToolResult(
            items=[{"id": "treasury-liquidity", "name": "Treasury"}]
            if len(resolutions) > 1
            else []
        )

    state = run_research(ctx(), "Find policy", lambda *args: choices.pop(0), reader)
    assert not choices
    assert state.model_calls == 4


def test_bootstrap_graph_exposes_source_handles_before_the_first_model_call():
    calls = []

    def reader(context, call):
        calls.append(call.tool)
        if call.tool == "resolve_entities":
            return ToolResult(
                items=[
                    {
                        "id": "entity",
                        "name": "Resolved business entity",
                        "entity_type": "BusinessEntity",
                        "domain_id": "finance",
                        "score": 10,
                    }
                ]
            )
        assert call.tool == "traverse_graph"
        return ToolResult(
            paths=[
                {
                    "edges": [
                        {
                            "source": "entity",
                            "target": "policy",
                            "predicate": "governedBy",
                            "source_ref": {
                                "asset_id": "finance-asset-1",
                                "domain_id": "finance",
                                "locator": "controls",
                                "version": "v1",
                            },
                        }
                    ]
                }
            ]
        )

    def decide(state, deadline):
        assert state.paths[0]["edges"][0]["source_ref"]["asset_id"] == "finance-asset-1"
        return ActionDecision(
            intent={"query": "Find policy", "facets": []}, stop_action="finish"
        )

    result = run_research(ctx(), "Find policy", decide, reader)
    assert calls == ["resolve_entities", "traverse_graph"]
    assert result.tool_calls == 2


def test_graph_seed_reads_one_real_source_before_model_planning():
    calls = []
    ref = {
        "asset_id": "finance-asset-1",
        "domain_id": "finance",
        "locator": "controls",
        "version": "v1",
    }

    def reader(context, call):
        calls.append(call.tool)
        if call.tool == "resolve_entities":
            return ToolResult(
                items=[
                    {
                        "id": "policy",
                        "entity_type": "Policy",
                        "name": "Named policy",
                        "domain_id": "finance",
                        "score": 10,
                    }
                ]
            )
        if call.tool == "traverse_graph":
            return ToolResult(
                source_refs=[ref],
                paths=[
                    {
                        "edges": [
                            {
                                "source": "policy",
                                "target": "section",
                                "predicate": "supportedBy",
                                "source_ref": ref,
                            }
                        ]
                    }
                ],
            )
        assert (
            call.tool == "read_content"
            and call.kind == "asset"
            and call.id == "finance-asset-1"
        )
        return ToolResult(
            items=[
                {
                    "id": "source-clause",
                    "asset_id": "finance-asset-1",
                    "text": "An actual source clause.",
                    "title": "Named policy",
                    "content_kind": "document",
                    "source_ref": ref,
                }
            ],
            source_refs=[ref],
        )

    def decide(state, deadline):
        assert state.evidence[0].text == "An actual source clause."
        assert state.evidence[0].source_title == "Named policy"
        return ActionDecision(
            intent={"query": "Find policy", "facets": []}, stop_action="finish"
        )

    run_research(ctx(), "Find policy", decide, reader)
    assert calls == ["resolve_entities", "traverse_graph", "read_content"]


def test_json_object_provider_mode_keeps_strict_server_schema(monkeypatch):
    from app.config import Settings
    from app.agent import provider

    monkeypatch.setattr(
        provider,
        "settings",
        lambda: Settings(_env_file=None, openrouter_structured_mode="json_object"),
    )
    from app.agent.verification import DraftAnswer

    assert provider.output_format(DraftAnswer) == {"type": "json_object"}
    assert DraftAnswer.model_config["extra"] == "forbid"


def test_native_plan_uses_typed_objects_instead_of_nested_json_strings():
    from app.agent.adapter import parse_native_decision, native_tools
    import json

    message = {
        "tool_calls": [
            {
                "id": "plan",
                "function": {
                    "name": "update_plan",
                    "arguments": json.dumps(
                        {
                            "intent": {
                                "query": "Name policy",
                                "facets": [
                                    {
                                        "id": "name",
                                        "description": "Policy name",
                                        "kinds": ["document"],
                                    }
                                ],
                                "entity_ids": [],
                                "ambiguous": False,
                            },
                            "assessments": [],
                            "stop_action": "finish",
                            "summary": "Policy found",
                        }
                    ),
                },
            }
        ]
    }
    result = parse_native_decision(message)
    assert result.intent.facets[0].id == "name"
    tool = next(t for t in native_tools() if t["function"]["name"] == "update_plan")
    assert "intent" in tool["function"]["parameters"]["properties"]
    assert "intent_json" not in tool["function"]["parameters"]["properties"]


def test_checkpoint_serializer_explicitly_allows_only_application_state_types():
    from app.agent.service import checkpoint_serializer
    from app.agent.actions import ResearchState

    serializer = checkpoint_serializer()
    state = ResearchState(
        query="Restore search",
        intent={
            "query": "Restore search",
            "facets": [{"id": "name", "description": "Name", "kinds": ["document"]}],
        },
        last_decision=ActionDecision(stop_action="finish"),
    )
    restored = serializer.loads_typed(serializer.dumps_typed(state))
    assert isinstance(restored, ResearchState)
    assert restored.intent.facets[0].id == "name"
    assert serializer.pickle_fallback is False
