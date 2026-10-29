"""SDK contract fakes: all tests here are offline, never Llama measurements."""
import builtins
import json
import sys
from types import SimpleNamespace

import pytest

from physicsguard.agent.model_client import BackendError, OllamaClient
from physicsguard.agent.planner import investigate
from physicsguard.agent.protocol import dumps, parse_message
from physicsguard.repair.sources import default_source_store


class Context:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def sdk_fake(monkeypatch, value=None, error=None):
    recorded = {}
    class HTTPError(Exception): pass
    class HTTPTimeout(HTTPError): pass
    class APIError(Exception): pass
    class APITimeout(APIError): pass
    class Transport(Context):
        def __init__(self, **kwargs):
            recorded["transport"] = kwargs
    class Response(Context):
        def iter_bytes(self, chunk_size):
            data = value if isinstance(value, bytes) else json.dumps(value).encode()
            for i in range(0, len(data), chunk_size):
                yield data[i:i+chunk_size]
    def create(**kwargs):
        recorded["request"] = kwargs
        if error:
            raise {"timeout": APITimeout, "http": APIError}[error]("private credential /path verify-01")
        return Response()
    class OpenAI(Context):
        def __init__(self, **kwargs):
            recorded["client"] = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(
                with_streaming_response=SimpleNamespace(create=create)))
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(Client=Transport, Timeout=lambda t: t,
        HTTPError=HTTPError, TimeoutException=HTTPTimeout))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=OpenAI,
        APITimeoutError=APITimeout, APIError=APIError))
    return recorded


def response(*, calls=None, content=None, model="llama3.1:8b", tokens=25):
    return {"model": model, "usage": {"completion_tokens": tokens}, "choices": [{
        "finish_reason": "tool_calls" if calls else "stop",
        "message": {"content": content, "tool_calls": calls}}]}


def request(client):
    return client.complete(dumps({"messages": [{"role": "user", "content": "test"}]}),
                           dumps({"tools": []}), max_tokens=128)


def test_sdk_tool_call_continuation_and_transport_options(monkeypatch):
    value = response(calls=[{"id": "sdk-1", "function": {
        "name": "get_repair_history", "arguments": "{}"}}])
    recorded = sdk_fake(monkeypatch, value)
    client = OllamaClient()
    completion = request(client)
    action = parse_message(completion.message_json)
    assert action.call_id == "sdk-1" and action.operation == "get_repair_history"
    assert completion.output_tokens == 25
    assert recorded["client"]["base_url"] == "http://127.0.0.1:11434/v1"
    assert recorded["client"]["api_key"] == "ollama-local-placeholder"
    assert recorded["client"]["organization"] == recorded["client"]["project"] == ""
    assert recorded["client"]["max_retries"] == 0
    assert recorded["transport"]["trust_env"] is False
    assert recorded["transport"]["follow_redirects"] is False
    assert recorded["request"]["stream"] is False
    assert recorded["request"]["max_tokens"] == 128
    assert client.provenance.model_inference and client.provenance.successful_requests == 1
    # This is synthetic protocol evidence; it is never persisted as a live run.
    messages = [action.assistant_message(), {"role": "tool", "tool_call_id": "sdk-1", "content": '{"ok":true,"result":[]}'}]
    client.complete(dumps({"messages": messages}), dumps({"tools": []}), max_tokens=128)
    assert recorded["request"]["messages"] == messages


def test_sdk_structured_final_explanation(monkeypatch):
    sdk_fake(monkeypatch, response(content=dumps({"summary": "No evidence yet", "evidence_ids": [],
        "hypothesis": None, "abstain": True})))
    explanation = parse_message(request(OllamaClient()).message_json)
    assert explanation.abstain and explanation.hypothesis is None


@pytest.mark.parametrize("error,code", [("timeout", "model_timeout"), ("http", "model_unavailable")])
def test_failed_real_backend_never_becomes_mock(monkeypatch, error, code):
    sdk_fake(monkeypatch, error=error)
    result = investigate(OllamaClient(), default_source_store(), "solver_01.py")
    assert result.provenance.backend == "ollama" and not result.provenance.model_inference
    assert result.verifier_decision is None and result.termination == code
    assert result.actions == 0 and "private credential" not in result.to_json()


@pytest.mark.parametrize("value,code", [
    (response(model="other", content="{}"), "model_identity_mismatch"),
    (response(content="{invalid"), "invalid_model_response"),
    (response(content="{}", tokens=129), "invalid_model_response"),
    (response(content="{}", tokens=True), "invalid_model_response"),
    (b'{"model":"llama3.1:8b","model":"other"}', "invalid_model_response"),
    (b'{"number":NaN}', "invalid_model_response"),
    (b'x' * 40000, "invalid_model_response"),
])
def test_sdk_malformed_oversize_identity_and_token_validation(monkeypatch, value, code):
    sdk_fake(monkeypatch, value)
    with pytest.raises(BackendError) as raised:
        request(OllamaClient())
    assert raised.value.code == code


def test_optional_dependency_absence_is_explicit(monkeypatch):
    original = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    with pytest.raises(BackendError, match="optional_dependency_missing"):
        request(OllamaClient())
