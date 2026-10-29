"""Offline agent orchestration and boundary regressions. No model downloads."""
from dataclasses import replace
import json
import os
from pathlib import Path
import socket

import pytest

from physicsguard.agent.boundary import public_response
from physicsguard.agent.demo import main, save_trace
from physicsguard.agent.model_client import BackendError, Completion, MockClient, OllamaClient, local_endpoint
from physicsguard.agent.planner import AgentBudgets, investigate
from physicsguard.agent.protocol import (
    AgentExplanation, BackendProvenance, ProtocolError, ToolRequest, ToolResponse,
    TraceEvent, dumps, loads, parse_message, tool_descriptions,
)
from physicsguard.repair.sources import default_source_store


def call(name="inspect_solver_source", arguments=None, identifier="test-1"):
    return Completion(dumps({"tool_calls": [{"id": identifier, "name": name,
        "arguments": dumps({"source_file": "solver_01.py"} if arguments is None else arguments)}]}))


class ScriptedClient:
    provenance = BackendProvenance("mock", None, False)

    def __init__(self, replies):
        self.replies, self.conversations = iter(replies), []

    def complete(self, messages_json, tools_json, *, max_tokens):
        assert type(messages_json) is str and type(tools_json) is str
        self.conversations.append(loads(messages_json, 131072))
        value = next(self.replies)
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture(scope="module")
def measured():
    return {name: investigate(MockClient(), default_source_store(), name)
            for name in ("solver_01.py", "solver_02.py", "solver_03.py", "solver_04.py")}


@pytest.mark.parametrize("name,operation", [
    ("solver_01.py", "restore_signed_upwind"),
    ("solver_02.py", "normalize_time_by_cell_width"),
    ("solver_03.py", "wrap_incoming_neighbor"),
])
def test_mock_actual_repairs_require_independent_verification(measured, name, operation):
    result = measured[name]
    assert result.termination == "completed"
    assert result.verifier_decision == "ACCEPTED"
    assert result.verifications == 1
    assert result.proposal["origin"] == "deterministic"
    assert all(v == "pass" for v in result.verification["stages"].values())
    assert any(e.kind == "tool_request" and e.data["arguments"].get("operation_id") == operation
               for e in result.events)
    assert result.provenance == BackendProvenance("mock", None, False)
    assert result.original_integrity and result.workspaces_cleaned


def test_correct_control_abstains(measured):
    result = measured["solver_04.py"]
    assert result.termination == "abstained" and result.explanation.abstain
    assert result.verifier_decision is None and result.verifications == 0
    assert result.proposal is None and result.explanation.hypothesis is None
    assert result.original_integrity and result.workspaces_cleaned


def test_mock_no_credentials_network_ollama_or_optional_sdk(monkeypatch):
    import builtins
    original_import = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        if name in ("openai", "httpx"):
            raise ImportError("optional SDK deliberately unavailable")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network in mock"))
    for name in ("OPENAI_API_KEY", "META_API_KEY", "OLLAMA_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    result = investigate(MockClient(), default_source_store(), "solver_04.py")
    assert result.termination == "abstained" and not result.provenance.model_inference


def test_mock_trace_exact_determinism_and_original_bytes(measured):
    store = default_source_store()
    before = {p.name: p.read_bytes() for p in store.root.glob("solver_*.py")}
    for name, first in measured.items():
        second = investigate(MockClient(), store, name)
        assert second.to_json() == first.to_json()
        payload = loads(second.to_json(), 2 * 1024**2)
        assert payload["provenance"]["model_inference"] is False
    assert before == {p.name: p.read_bytes() for p in store.root.glob("solver_*.py")}


@pytest.mark.parametrize("payload", ["", "{", "[]", '{"tool_calls":NaN}',
    '{"tool_calls":1e999}', '{"explanation":{},"explanation":{}}',
    '{"tool_calls":[]}', '{"tool_calls":[{},{}]}', '{"decision":"ACCEPTED"}',
    '{"tool_calls":[{"id":"x","name":"get_repair_history","arguments":"{\\"a\\":1,\\"a\\":2}"}]}',
    '{"explanation":{"summary":"x","evidence_ids":[],"hypothesis":null,"abstain":true,"decision":"ACCEPTED"}}',
])
def test_malformed_protocol_rejected(payload):
    with pytest.raises(ValueError):
        parse_message(payload)


@pytest.mark.parametrize("operation,arguments", [
    ("__dict__", {}), ("_verify_candidate_for_testing", {}),
    ("store", {}), ("get_repair_history", {"plan": {}}),
    ("inspect_solver_source", {"source_file": "../solver_01.py"}),
    ("inspect_solver_source", {"source_file": "solver_01.py", "report": {}}),
    ("verify_candidate_patch", {"proposal_id": "x", "tolerance": 1}),
    ("select_localized_edit", {"source_file": "solver_01.py", "run_id": "x", "operation_id": "execute_code"}),
    ("select_localized_edit", {"source_file": "solver_01.py", "run_id": "x", "operation_id": "restore_signed_upwind", "source": "print(1)"}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "strategy": {}}}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "physics": {"source_free": False}}}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "n_cells": 5000}}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "cfl": float("inf")}}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "n_cells": True}}),
    ("run_scientific_experiment", {"source_file": "solver_01.py", "case": {"case_id": "a", "final_time": 1e9}}),
    ("inspect_solver_source", {"source_file": "x" * 10000}),
])
def test_tool_argument_privileges_and_budgets_rejected(operation, arguments):
    with pytest.raises(ValueError):
        ToolRequest("test", operation, arguments)


def test_typed_request_and_result_continuation():
    request = parse_message(call().message_json)
    assert isinstance(request, ToolRequest)
    response = ToolResponse(request.call_id, request.operation, True, {"source_file": "solver_01.py"})
    assert response.tool_message()["tool_call_id"] == request.assistant_message()["tool_calls"][0]["id"]
    assert loads(response.tool_message()["content"])["result"]["source_file"] == "solver_01.py"
    assert {t["function"]["name"] for t in tool_descriptions()} == {
        "inspect_solver_source", "run_scientific_experiment", "get_diagnostic_report",
        "propose_localized_patch", "select_localized_edit", "verify_candidate_patch", "get_repair_history"}


def test_conversation_contains_paired_actual_results_only():
    class Spy(MockClient):
        def complete(self, messages_json, tools_json, *, max_tokens):
            messages = loads(messages_json, 131072)["messages"]
            for index, message in enumerate(messages):
                if message["role"] == "tool":
                    previous = messages[index-1]["tool_calls"][0]
                    assert previous["id"] == message["tool_call_id"]
                    assert loads(message["content"])["ok"] is True
            for private in ("GROUND_TRUTH", "before_additional", "after_additional", "verify-01", "reference_patch"):
                assert private not in messages_json and private not in tools_json
            return super().complete(messages_json, tools_json, max_tokens=max_tokens)
    result = investigate(Spy(), default_source_store(), "solver_01.py")
    assert result.verifier_decision == "ACCEPTED"


@pytest.mark.parametrize("settings,reason", [
    ({"max_turns": 1}, "turn_budget"), ({"max_actions": 1}, "action_budget"),
    ({"max_experiments": 1}, "experiment_budget"),
    ({"max_conversation_bytes": 1}, "conversation_budget"),
    ({"max_cumulative_input_bytes": 1}, "input_budget"),
])
def test_agent_budgets(settings, reason):
    result = investigate(MockClient(), default_source_store(), "solver_01.py", budgets=AgentBudgets(**settings))
    assert result.termination == reason and result.verifier_decision is None


def test_output_tokens_stop_before_tool_dispatch():
    client = ScriptedClient([Completion(call().message_json, 2)])
    result = investigate(client, default_source_store(), "solver_01.py", budgets=AgentBudgets(max_output_tokens=1))
    assert result.termination == "output_token_budget" and result.actions == 0


def test_per_turn_token_allowance_cannot_be_exceeded():
    result = investigate(ScriptedClient([Completion(call().message_json, 2)]),
        default_source_store(), "solver_01.py", budgets=AgentBudgets(max_tokens_per_turn=1))
    assert result.termination == "output_token_budget" and result.actions == 0


def test_oversized_model_response_is_rejected():
    with pytest.raises(ValueError):
        Completion("x" * 16385)
    with pytest.raises(ValueError):
        ToolResponse("x", "get_repair_history", True, {"value": "x" * 65536})


@pytest.mark.parametrize("field,value", [("max_turns", 0), ("max_actions", True),
    ("max_verifications", 9), ("max_conversation_bytes", 10000000), ("max_output_tokens", -1)])
def test_invalid_budget_configuration(field, value):
    with pytest.raises(ValueError):
        AgentBudgets(**{field: value})


def test_duplicate_calls_and_call_ids_stop():
    for second in (call(identifier="test-2"), call("get_repair_history", {})):
        result = investigate(ScriptedClient([call(), second]), default_source_store(), "solver_01.py")
        assert result.termination == "duplicate_call" and result.verifier_decision is None


@pytest.mark.parametrize("reply", [Completion("{"), call("eval", {}), call("get_repair_history", {"plan": {}})])
def test_repeated_invalid_responses_terminate_without_dispatch(reply):
    result = investigate(ScriptedClient([reply, reply]), default_source_store(), "solver_01.py")
    assert result.termination == "invalid_response_limit" and result.actions == 0
    assert sum(e.kind == "invalid_response" for e in result.events) == 2


@pytest.mark.parametrize("reply,reason", [(BackendError("model_timeout"), "model_timeout"),
    (TimeoutError("private path /home/key"), "model_timeout"),
    (BackendError("model_unavailable"), "model_unavailable")])
def test_model_failures_are_sanitized(reply, reason):
    result = investigate(ScriptedClient([reply]), default_source_store(), "solver_01.py")
    assert result.termination == reason and result.verifier_decision is None
    assert "/home/key" not in result.to_json() and not result.provenance.model_inference


def test_tool_error_terminates_safely(monkeypatch):
    from physicsguard.repair.tools import RepairTools
    monkeypatch.setattr(RepairTools, "call", lambda *args: {"ok": False, "error": "private token and verify-01"})
    result = investigate(MockClient(), default_source_store(), "solver_01.py")
    assert result.termination == "tool_error"
    assert "private token" not in result.to_json() and "verify-01" not in result.to_json()


def test_execution_tool_exception_does_not_claim_cleanup(monkeypatch):
    from physicsguard.repair.tools import RepairTools
    original = RepairTools.call
    def broken(self, operation, arguments):
        if operation == "run_scientific_experiment":
            raise RuntimeError("private host failure")
        return original(self, operation, arguments)
    monkeypatch.setattr(RepairTools, "call", broken)
    result = investigate(MockClient(), default_source_store(), "solver_01.py")
    assert result.termination == "tool_error" and result.workspaces_cleaned is None
    assert result.verifier_decision is None and "private host failure" not in result.to_json()


@pytest.mark.parametrize("decision", ["REJECTED", "INCONCLUSIVE"])
def test_agent_preserves_host_decisions_without_self_acceptance(monkeypatch, decision):
    from physicsguard.repair.tools import RepairTools
    original = RepairTools.call
    def synthetic_gate(self, operation, arguments):
        if operation == "verify_candidate_patch":
            return {"ok": True, "result": {"proposal_id": arguments["proposal_id"],
                "origin": "deterministic", "decision": decision, "original_integrity": True,
                "workspaces_cleaned": True, "stages": {name: "inconclusive" for name in
                    ("source", "execution", "science", "additional_cases", "regressions")}}}
        return original(self, operation, arguments)
    monkeypatch.setattr(RepairTools, "call", synthetic_gate)
    result = investigate(MockClient(), default_source_store(), "solver_01.py")
    assert result.verifier_decision == decision
    assert decision in result.final_explanation and "ACCEPTED" not in result.final_explanation


def test_hypothesis_is_recorded_before_patch_selection(measured):
    events = measured["solver_01.py"].events
    hypothesis = next(e for e in events if e.kind == "explanation" and e.data["stage"] == "hypothesis")
    patch = next(e for e in events if e.kind == "tool_request" and e.data["operation"] == "select_localized_edit")
    assert hypothesis.index < patch.index and {"accuracy", "direction"} <= set(hypothesis.data["evidence_ids"])


@pytest.mark.parametrize("tool_reply,reason", [
    (call(arguments={"source_file": "solver_02.py"}), "source_scope_violation"),
    (call("get_diagnostic_report", {"run_id": "made-up"}), "unsupported_evidence_reference"),
    (call("verify_candidate_patch", {"proposal_id": "made-up"}), "unsupported_evidence_reference"),
])
def test_scoped_source_and_evidence_ids(tool_reply, reason):
    result = investigate(ScriptedClient([tool_reply]), default_source_store(), "solver_01.py")
    assert result.termination == reason and result.verifier_decision is None


def test_model_cannot_self_accept_or_cite_private_evidence():
    for explanation in (
        {"summary": "ACCEPTED", "evidence_ids": [], "hypothesis": None, "abstain": False},
        {"summary": "done", "evidence_ids": ["verify-01"], "hypothesis": None, "abstain": True},
    ):
        reply = Completion(dumps({"explanation": explanation}))
        result = investigate(ScriptedClient([reply, reply]), default_source_store(), "solver_01.py")
        assert result.verifier_decision is None and result.termination == "invalid_response_limit"


def test_final_record_refuses_unverified_acceptance(measured):
    with pytest.raises(ValueError, match="independent verification"):
        replace(measured["solver_04.py"], verifier_decision="ACCEPTED")


def test_sanitized_projection_drops_private_fields(measured):
    verification = dict(measured["solver_01.py"].verification)
    verification.update({"before_additional": {"secret": "private"}, "reasons": ["verify-01 and private answer"]})
    request = ToolRequest("x", "verify_candidate_patch", {"proposal_id": verification["proposal_id"]})
    response = public_response(request, {"ok": True, "result": verification})
    assert "private" not in response.to_json() and "verify-01" not in response.to_json()
    request = ToolRequest("x", "get_diagnostic_report", {"run_id": "x"})
    with pytest.raises(ValueError, match="evaluator"):
        public_response(request, {"ok": True, "result": {"audience": "evaluator_only"}})


def test_mock_uses_observed_evidence_not_fixture_id(measured):
    original = measured["solver_02.py"]
    requests = [e for e in original.events if e.kind == "tool_request"][:5]
    responses = [e for e in original.events if e.kind == "tool_response"][:5]
    messages = [{"role": "user", "content": dumps({"source_file": "unknown_name.py"})}]
    for request, response in zip(requests, responses):
        req = ToolRequest(**request.data)
        messages.append(req.assistant_message())
        messages.append(ToolResponse(**response.data).tool_message())
    hypothesis = parse_message(MockClient().complete(dumps({"messages": messages}, 131072), "{}", max_tokens=100).message_json)
    assert hypothesis.stage == "hypothesis"
    messages.append({"role": "assistant", "content": dumps(hypothesis.to_dict())})
    selection = parse_message(MockClient().complete(dumps({"messages": messages}, 131072), "{}", max_tokens=100).message_json)
    assert selection.arguments["source_file"] == "unknown_name.py"
    assert selection.arguments["operation_id"] == "normalize_time_by_cell_width"


def test_actual_workspace_directories_are_removed(monkeypatch):
    from physicsguard.repair import workspace
    original = workspace.TemporaryDirectory
    roots = []
    def track(*args, **kwargs):
        directory = original(*args, **kwargs)
        roots.append(Path(directory.name))
        return directory
    monkeypatch.setattr(workspace, "TemporaryDirectory", track)
    result = investigate(MockClient(), default_source_store(), "solver_03.py")
    assert result.workspaces_cleaned and len(roots) >= 3
    assert all(not root.exists() for root in roots)


def test_verification_budget_blocks_second_independent_attempt():
    class Twice(MockClient):
        def complete(self, messages_json, tools_json, *, max_tokens):
            messages = loads(messages_json, 131072)["messages"]
            verified = [m for m in messages if m["role"] == "tool" and
                        isinstance(loads(m["content"]).get("result"), dict) and
                        "decision" in loads(m["content"])["result"]]
            # After the first verified candidate, use another already-observed
            # experiment to obtain a different proposal ID for the same source.
            if verified:
                after = messages[messages.index(verified[0])+1:]
                if not after:
                    reports = [m for m in messages if m["role"] == "assistant" and m.get("tool_calls") and
                               m["tool_calls"][0]["function"]["name"] == "get_diagnostic_report"]
                    run = loads(reports[-1]["tool_calls"][0]["function"]["arguments"])["run_id"]
                    return call("propose_localized_patch", {"source_file": "solver_01.py", "run_id": run}, "again-propose")
                proposal = loads(after[-1]["content"])["result"]
                return call("verify_candidate_patch", {"proposal_id": proposal["proposal_id"]}, "again-verify")
            return super().complete(messages_json, tools_json, max_tokens=max_tokens)
    result = investigate(Twice(), default_source_store(), "solver_01.py", budgets=AgentBudgets(max_verifications=1))
    assert result.termination == "verification_budget" and result.verifications == 1


def test_trace_file_is_strict_private_and_cannot_overwrite_sources(measured, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = measured["solver_01.py"]
    path = save_trace(result, "test.json")
    assert loads(path.read_text(), 2 * 1024**2)["provenance"]["backend"] == "mock"
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        save_trace(result, "test.json")
    with pytest.raises(ValueError):
        save_trace(result, "../solver_01.py")


def test_trace_directory_symlink_is_refused(measured, tmp_path, monkeypatch):
    destination = tmp_path / "destination"
    destination.mkdir()
    (tmp_path / "artifacts").symlink_to(destination, target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        save_trace(measured["solver_01.py"], "test.json")


def test_cli_mock(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--backend", "mock", "--source", "solver_04.py", "--trace", "control.json"]) == 0
    output = capsys.readouterr().out
    assert "backend: mock" in output and "model_inference: false" in output
    assert "Mock-selected" in output and "Termination: abstained" in output


@pytest.mark.parametrize("endpoint", ["https://example.com/v1", "http://192.168.1.1:11434/v1",
    "http://127.0.0.1.evil/v1", "http://localhost.evil/v1", "http://user:secret@127.0.0.1/v1",
    "http://127.0.0.1/v1?key=secret", "http://127.0.0.1/v1#bad", "http://127.0.0.1/other",
    "file:///v1", "http://[::ffff:192.168.1.1]/v1"])
def test_nonloopback_endpoints_rejected(endpoint):
    with pytest.raises(ValueError):
        OllamaClient(endpoint=endpoint)


@pytest.mark.parametrize("endpoint", ["http://localhost:11434/v1/", "http://127.0.0.1:11434/v1", "http://[::1]:11434/v1"])
def test_loopback_endpoints(endpoint):
    assert "localhost" not in local_endpoint(endpoint)


@pytest.mark.parametrize("model", ["muse-spark", "llama3.1:8b-cloud", "other", ""])
def test_only_requested_local_model_allowed(model):
    with pytest.raises(ValueError):
        OllamaClient(model=model)


def test_provenance_cannot_label_mock_as_model():
    for args in (("mock", None, True), ("mock", "llama3.1:8b", False), ("ollama", "muse-spark", True, 1)):
        with pytest.raises(ValueError):
            BackendProvenance(*args)


@pytest.mark.skipif(os.environ.get("PHYSICSGUARD_LIVE_OLLAMA") != "1", reason="explicit local inference opt-in required")
def test_live_ollama_investigation():
    result = investigate(OllamaClient(), default_source_store(), "solver_01.py")
    assert result.provenance.backend == "ollama" and result.provenance.model == "llama3.1:8b"
    assert result.provenance.model_inference
    assert result.original_integrity and result.workspaces_cleaned is not False
    # Real scientific outcomes are recorded, never forced to mirror the mock.
    if result.verifier_decision == "ACCEPTED":
        assert result.verifications > 0 and result.verification["decision"] == "ACCEPTED"
