import pytest
from app.agent.provider import validate_answer
from app.contracts import AnswerOutput, Statement
from app.agent.graph import build_graph


def test_citation_validation_rejects_unknown_ids():
    answer = AnswerOutput(
        statements=[Statement(text="Claim", evidence_ids=["invented"])],
        gaps=[],
        uncertainty="",
    )
    with pytest.raises(ValueError):
        validate_answer(answer, [{"id": "real"}])


def test_uncited_claim_rejected():
    answer = AnswerOutput(
        statements=[Statement(text="Claim", evidence_ids=[])], gaps=[], uncertainty=""
    )
    with pytest.raises(ValueError):
        validate_answer(answer, [{"id": "real"}])


def test_responses_uses_strict_schema_and_server_model(monkeypatch):
    import json, httpx
    from openai import OpenAI
    from app.agent import provider
    from app.config import settings

    monkeypatch.setattr(settings(), "llm_provider", "openai")
    captured = []

    def respond(request):
        body = json.loads(request.content)
        captured.append(body)
        text = json.dumps(
            {
                "concept_labels": ["Counterparty"],
                "query_variants": ["exposure"],
                "strategies": ["keyword", "vector", "graph"],
            }
        )
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "model": settings().openai_model,
                "status": "completed",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": text, "annotations": []}
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(
        provider,
        "client",
        lambda: OpenAI(
            api_key="test-only-key",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ),
    )
    result = provider.plan_query("counterparty exposure")
    assert result.concept_labels == ["Counterparty"]
    assert captured[0]["model"] == settings().openai_model
    assert captured[0]["store"] is False
    assert captured[0]["text"]["format"]["strict"] is True


def test_expired_graph_cannot_call_model():
    import time

    graph = build_graph()
    with pytest.raises(TimeoutError):
        graph.invoke(
            {
                "run_id": "expired",
                "person_id": "admin",
                "scope_version": 1,
                "query": "counterparty",
                "mode": "extractive",
                "started": time.time() - 91,
            }
        )


def test_openrouter_uses_deepseek_and_openai_compatible_schema(monkeypatch):
    import json, httpx
    from openai import OpenAI
    from app.agent import provider
    from app.config import settings

    captured = []

    def respond(request):
        captured.append((str(request.url), json.loads(request.content)))
        content = json.dumps(
            {
                "concept_labels": ["Counterparty"],
                "query_variants": ["exposure"],
                "strategies": ["keyword", "vector", "graph"],
            }
        )
        return httpx.Response(
            200,
            json={
                "id": "chat_test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek/deepseek-v3.2",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
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
    result = provider.plan_query("counterparty exposure")
    assert result.concept_labels == ["Counterparty"]
    assert captured[0][0].endswith("/chat/completions")
    assert captured[0][1]["model"] == "deepseek/deepseek-v3.2"
    assert captured[0][1]["response_format"]["json_schema"]["strict"] is True
    assert captured[0][1]["plugins"] == [{"id": "response-healing"}]


def test_openrouter_rejects_malformed_output_without_leaking_content(monkeypatch):
    import httpx
    from openai import OpenAI
    from app.agent import provider

    def respond(request):
        return httpx.Response(200, json={
            "id": "chat_bad", "object": "chat.completion", "created": 0,
            "model": "deepseek/deepseek-v3.2", "choices": [{
                "index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": '{ĊĠĠ"private_provider_content": []}'
                }
            }]
        })

    monkeypatch.setattr(provider, "client", lambda: OpenAI(
        api_key="test-only", base_url="https://openrouter.ai/api/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    ))
    with pytest.raises(ValueError, match="invalid structured result") as failure:
        provider.plan_query("counterparty exposure")
    assert "private_provider_content" not in str(failure.value)


def test_tokenizer_whitespace_is_decoded_only_outside_json_strings():
    from app.agent.provider import decode_structured_content
    from app.contracts import PlanOutput

    result = decode_structured_content(PlanOutput,
        '{ĊĠĠ"concept_labels": ["literal Ġ and Ċ"],ĊĠĠ"query_variants": [],ĊĠĠ"strategies": ["vector"]Ċ}')
    assert result.concept_labels == ["literal Ġ and Ċ"]
    assert result.strategies == ["vector"]
    with pytest.raises(ValueError):
        decode_structured_content(PlanOutput, '{"concept_labels": [], "query_variants": [], "strategies": ["write"]}')
