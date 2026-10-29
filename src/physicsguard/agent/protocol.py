"""Finite JSON contracts for an investigator, independent of any provider.

Only serialized messages cross the provider boundary. Source text is evidence,
never an executable model output. No evaluator module is imported here.
"""
from dataclasses import dataclass, field
import json
import re
from typing import Literal

from physicsguard.repair.protocol import decode_frame, encode_frame, ProtocolError
from physicsguard.schemas.results import (
    ExperimentCase, JsonRecord, PhysicsSpecification, SolverStrategy,
)
from physicsguard.experiments.runner import validate_cases

MAX_ARGUMENT_BYTES = 8192
MAX_MODEL_BYTES = 16384
MAX_TOOL_BYTES = 65536
OPERATIONS = (
    "restore_signed_upwind", "normalize_time_by_cell_width", "wrap_incoming_neighbor",
)
FIELDS = {
    "inspect_solver_source": {"source_file"},
    "run_scientific_experiment": {"source_file", "case"},
    "get_diagnostic_report": {"run_id"},
    "propose_localized_patch": {"source_file", "run_id"},
    "select_localized_edit": {"source_file", "run_id", "operation_id"},
    "verify_candidate_patch": {"proposal_id"},
    "get_repair_history": set(),
}


def dumps(value, limit=MAX_TOOL_BYTES):
    return encode_frame(value, limit).decode().strip()


def loads(value, limit=MAX_TOOL_BYTES):
    if isinstance(value, str) and len(value.encode("utf-8")) > limit:
        raise ProtocolError("JSON byte budget exceeded")
    return decode_frame(value, limit)


def bounded_text(value, limit=128):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > limit:
        raise ProtocolError("bounded nonempty text required")
    return value


@dataclass(frozen=True)
class ToolRequest(JsonRecord):
    call_id: str
    operation: str
    arguments: dict

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", bounded_text(self.call_id)):
            raise ProtocolError("invalid tool call ID")
        if not isinstance(self.operation, str) or self.operation not in FIELDS or type(self.arguments) is not dict:
            raise ProtocolError("unknown tool or arguments")
        args = loads(dumps(self.arguments, MAX_ARGUMENT_BYTES), MAX_ARGUMENT_BYTES)
        if set(args) != FIELDS[self.operation]:
            raise ProtocolError("unexpected tool arguments")
        for name, value in args.items():
            if name != "case":
                bounded_text(value)
        if "source_file" in args and not re.fullmatch(r"[A-Za-z0-9_]+\.py", args["source_file"]):
            raise ProtocolError("source basename required")
        if "operation_id" in args and args["operation_id"] not in OPERATIONS:
            raise ProtocolError("unknown localized operation")
        if "case" in args:
            case = args["case"]
            allowed = set(ExperimentCase.__dataclass_fields__) - {"strategy"}
            if type(case) is not dict or set(case) - allowed:
                raise ProtocolError("unexpected experiment arguments")
            physics = case.get("physics", {})
            if type(physics) is not dict or set(physics) - {"speed", "x_min", "x_max"}:
                raise ProtocolError("physical contract cannot be overridden")
            try:
                experiment = ExperimentCase(**{**case, "physics": PhysicsSpecification(**physics),
                                               "strategy": SolverStrategy()})
                bounded_text(experiment.case_id)
                validate_cases((experiment,))
            except (ValueError, TypeError, OverflowError) as error:
                raise ProtocolError("invalid or excessive experiment") from error
        object.__setattr__(self, "arguments", args)

    @classmethod
    def from_function(cls, call_id, operation, arguments_json):
        return cls(call_id, operation, loads(arguments_json, MAX_ARGUMENT_BYTES))

    def assistant_message(self):
        return {"role": "assistant", "content": None, "tool_calls": [{
            "id": self.call_id, "type": "function", "function": {
                "name": self.operation, "arguments": dumps(self.arguments, MAX_ARGUMENT_BYTES),
            }}]}


@dataclass(frozen=True)
class ToolResponse(JsonRecord):
    call_id: str
    operation: str
    ok: bool
    result: dict | list | None = None
    error: str | None = None

    def __post_init__(self):
        bounded_text(self.call_id)
        if self.operation not in FIELDS or type(self.ok) is not bool:
            raise ProtocolError("invalid tool response")
        if self.ok:
            if self.error is not None or not isinstance(self.result, (dict, list, type(None))):
                raise ProtocolError("invalid success result")
        elif self.result is not None or self.error != "invalid_or_unavailable_operation":
            raise ProtocolError("only sanitized errors may cross the boundary")
        dumps(self.to_dict(), MAX_TOOL_BYTES)

    def tool_message(self):
        return {"role": "tool", "tool_call_id": self.call_id,
                "content": dumps({"ok": self.ok, "result": self.result, "error": self.error})}


@dataclass(frozen=True)
class AgentExplanation(JsonRecord):
    summary: str
    evidence_ids: tuple[str, ...]
    hypothesis: str | None
    abstain: bool
    stage: Literal["hypothesis", "final"] = "final"

    def __post_init__(self):
        bounded_text(self.summary, 2000)
        if self.hypothesis is not None:
            bounded_text(self.hypothesis, 1000)
        if type(self.abstain) is not bool or not isinstance(self.evidence_ids, (tuple, list)):
            raise ProtocolError("invalid explanation")
        if self.stage not in ("hypothesis", "final") or self.stage == "hypothesis" and (
            self.abstain or self.hypothesis is None or not self.evidence_ids
        ):
            raise ProtocolError("hypotheses require cited evidence and a mechanism")
        if len(self.evidence_ids) > 32:
            raise ProtocolError("excessive evidence references")
        for identifier in self.evidence_ids:
            bounded_text(identifier)
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))


def parse_message(payload):
    """One function call or a structured final explanation; no arbitrary fields."""
    value = loads(payload, MAX_MODEL_BYTES)
    if set(value) == {"tool_calls"}:
        calls = value["tool_calls"]
        if not isinstance(calls, list) or len(calls) != 1:
            raise ProtocolError("exactly one sequential tool call required")
        call = calls[0]
        if type(call) is not dict or set(call) != {"id", "name", "arguments"}:
            raise ProtocolError("invalid function call record")
        return ToolRequest.from_function(call["id"], call["name"], call["arguments"])
    if set(value) == {"explanation"} and type(value["explanation"]) is dict:
        try:
            return AgentExplanation(**value["explanation"])
        except TypeError as error:
            raise ProtocolError("invalid explanation fields") from error
    raise ProtocolError("tool call or explanation required")


@dataclass(frozen=True)
class BackendProvenance(JsonRecord):
    backend: Literal["mock", "ollama"]
    model: str | None
    model_inference: bool
    successful_requests: int = 0

    def __post_init__(self):
        if type(self.successful_requests) is not int or self.successful_requests < 0:
            raise ProtocolError("invalid inference count")
        if type(self.model_inference) is not bool or self.backend not in ("mock", "ollama"):
            raise ProtocolError("invalid backend provenance")
        if self.backend == "mock":
            if self.model is not None or self.model_inference or self.successful_requests:
                raise ProtocolError("mock cannot claim model inference")
        elif self.model != "llama3.1:8b" or self.model_inference != (self.successful_requests > 0):
            raise ProtocolError("invalid local model provenance")


@dataclass(frozen=True)
class TraceEvent(JsonRecord):
    index: int
    kind: Literal["tool_request", "tool_response", "invalid_response", "backend_error", "explanation", "termination"]
    data: dict

    def __post_init__(self):
        if type(self.index) is not int or self.index < 0 or self.kind not in (
            "tool_request", "tool_response", "invalid_response", "backend_error", "explanation", "termination",
        ) or type(self.data) is not dict:
            raise ProtocolError("invalid trace event")
        dumps(self.data)


@dataclass(frozen=True)
class InvestigationResult(JsonRecord):
    provenance: BackendProvenance
    source_file: str
    termination: str
    explanation: AgentExplanation | None
    proposal: dict | None
    verifier_decision: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"] | None
    verification: dict | None
    original_integrity: bool
    workspaces_cleaned: bool | None
    final_explanation: str
    actions: int
    verifications: int
    output_tokens: int
    events: tuple[TraceEvent, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not isinstance(self.provenance, BackendProvenance):
            raise ProtocolError("backend provenance required")
        bounded_text(self.source_file)
        bounded_text(self.termination)
        if type(self.original_integrity) is not bool or self.workspaces_cleaned is not None and type(self.workspaces_cleaned) is not bool:
            raise ProtocolError("invalid integrity/cleanup flags")
        if any(type(count) is not int or count < 0 for count in (self.actions, self.verifications, self.output_tokens)):
            raise ProtocolError("invalid investigation counters")
        if self.explanation is not None and not isinstance(self.explanation, AgentExplanation):
            raise ProtocolError("typed explanation required")
        if not all(isinstance(event, TraceEvent) for event in self.events):
            raise ProtocolError("typed trace events required")
        if self.verifier_decision not in (None, "ACCEPTED", "REJECTED", "INCONCLUSIVE"):
            raise ProtocolError("invalid verification decision")
        if self.verifier_decision is not None and (
            not self.verification or self.verification.get("decision") != self.verifier_decision
            or not self.proposal or self.verifications < 1
            or self.verification.get("proposal_id") != self.proposal.get("proposal_id")
        ):
            raise ProtocolError("a decision requires independent verification")
        bounded_text(self.final_explanation, 2000)


def tool_descriptions():
    text = {"type": "string", "minLength": 1, "maxLength": 128}
    number = {"type": "number"}
    case = {"type": "object", "additionalProperties": False, "required": ["case_id"], "properties": {
        "case_id": text,
        "physics": {"type": "object", "additionalProperties": False, "properties": {
            "speed": number, "x_min": number, "x_max": number}},
        "n_cells": {"type": "integer", "minimum": 4, "maximum": 4096},
        "cfl": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
        "final_time": {"type": "number", "minimum": 0},
        "profile": {"type": "string", "enum": ["sine", "square", "constant"]},
        "offset": number, "amplitude": number, "phase": number,
        "mode": {"type": "integer", "minimum": 1},
        "max_steps": {"type": "integer", "minimum": 1, "maximum": 20000},
    }}
    descriptions = {
        "inspect_solver_source": "Inspect numbered reviewed source lines and content hash.",
        "run_scientific_experiment": "Run a chosen development case plus host refinement and metamorphic diagnostics. Defaults: 64 cells, CFL .8, sine mode 1, time .23, phase .37, unit periodic domain.",
        "get_diagnostic_report": "Read measured development diagnostics, assumptions, criteria and execution status for a run ID.",
        "propose_localized_patch": "Ask deterministic host rules for an evidence-supported patch, or null. This is host rule selection, not model-authored code.",
        "select_localized_edit": "Choose restore_signed_upwind, normalize_time_by_cell_width or wrap_incoming_neighbor. Host requires supporting source and diagnostic evidence; renders a restricted patch or refuses.",
        "verify_candidate_patch": "Request independent host verification. Only its returned decision establishes ACCEPTED, REJECTED or INCONCLUSIVE; private tests are withheld.",
        "get_repair_history": "Read sanitized verifier summaries for this investigation.",
    }
    tools = []
    for operation, fields in FIELDS.items():
        properties = {key: text for key in sorted(fields)}
        if "case" in properties:
            properties["case"] = case
        if "operation_id" in properties:
            properties["operation_id"] = {"type": "string", "enum": list(OPERATIONS)}
        tools.append({"type": "function", "function": {"name": operation,
            "description": descriptions[operation], "parameters": {"type": "object",
            "additionalProperties": False, "properties": properties, "required": sorted(fields)}}})
    return tools
