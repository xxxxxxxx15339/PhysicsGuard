"""Source repair hypotheses and measured verification, independent of any model."""
from dataclasses import dataclass
import json
import re
from typing import Literal

from .results import DiagnosticReport, ExperimentCase, JsonRecord


@dataclass(frozen=True)
class SourceSnapshot(JsonRecord):
    source_file: str
    sha256: str
    source_text: str

    def __post_init__(self):
        if not isinstance(self.source_file, str) or not isinstance(self.source_text, str) or len(self.source_text.encode()) > 20_000:
            raise ValueError("bounded source text and file identifier required")
        if not isinstance(self.sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("valid source SHA256 required")

    def numbered_lines(self) -> list[dict]:
        return [{"line": i, "text": line} for i, line in enumerate(self.source_text.splitlines(), 1)]


@dataclass(frozen=True)
class FaultHypothesis(JsonRecord):
    mechanism: Literal["transport_direction", "spatial_scaling", "periodic_neighbor"]
    function: str
    start_line: int
    end_line: int
    explanation: str
    evidence_ids: tuple[str, ...]
    evidence_case_ids: tuple[str, ...]

    def __post_init__(self):
        if self.mechanism not in ("transport_direction", "spatial_scaling", "periodic_neighbor") or not isinstance(self.explanation, str) or not self.explanation:
            raise ValueError("supported mechanism and scientific explanation required")
        if (self.function != "advance" or type(self.start_line) is not int or type(self.end_line) is not int
                or self.start_line < 1 or not self.start_line <= self.end_line <= self.start_line + 20):
            raise ValueError("bounded advance source range required")
        for field in ("evidence_ids", "evidence_case_ids"):
            entries = getattr(self, field)
            if not isinstance(entries, (tuple, list)) or not entries or not all(isinstance(x, str) and x for x in entries):
                raise ValueError("diagnostic identifiers and supporting cases are required")
            object.__setattr__(self, field, tuple(entries))


@dataclass(frozen=True)
class RepairProposal(JsonRecord):
    proposal_id: str
    source_file: str
    original_sha256: str
    proposed_sha256: str
    hypothesis: FaultHypothesis
    line_number: int
    old_line: str
    new_line: str
    unified_diff: str
    expected_effect: str
    verification_experiments: tuple[str, ...]
    origin: Literal["deterministic", "human", "meta"]

    def __post_init__(self):
        if not isinstance(self.hypothesis, FaultHypothesis):
            raise ValueError("typed fault hypothesis required")
        if not all(isinstance(value, str) for value in (self.proposal_id, self.source_file, self.original_sha256,
                self.proposed_sha256, self.old_line, self.new_line, self.unified_diff, self.expected_effect)):
            raise ValueError("proposal text fields must be strings")
        if self.origin not in ("deterministic", "human", "meta"):
            raise ValueError("unsupported proposal origin")
        if not self.proposal_id or not self.expected_effect or not self.hypothesis.explanation:
            raise ValueError("proposal identity, hypothesis and expected effect are required")
        if self.hypothesis.mechanism not in ("transport_direction", "spatial_scaling", "periodic_neighbor"):
            raise ValueError("unsupported hypothesis")
        if self.hypothesis.function != "advance" or not self.hypothesis.evidence_ids:
            raise ValueError("supported function and diagnostic evidence are required")
        if (type(self.line_number) is not int or self.line_number < 1
                or not self.hypothesis.start_line <= self.line_number <= self.hypothesis.end_line):
            raise ValueError("invalid source line range")
        for digest in (self.original_sha256, self.proposed_sha256):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("SHA256 must be 64 lowercase hexadecimal digits")
        for line in (self.old_line, self.new_line):
            if not line or "\n" in line or "\r" in line or len(line) > 500:
                raise ValueError("repair replaces exactly one bounded source line")
        if self.old_line == self.new_line or not self.verification_experiments:
            raise ValueError("a changed line and requested verification are required")
        if (len(self.unified_diff) > 4096 or not isinstance(self.verification_experiments, (tuple, list))
                or not all(isinstance(x, str) and x for x in self.verification_experiments)):
            raise ValueError("bounded diff and named verification requests required")
        object.__setattr__(self, "verification_experiments", tuple(self.verification_experiments))


def parse_proposal(payload: str) -> RepairProposal:
    """Parse a bounded structured record; this never executes or authorizes code."""
    if not isinstance(payload, str) or len(payload) > 8192:
        raise ValueError("proposal payload exceeds size/type limit")
    try:
        # Local import avoids coupling record definitions to the repair executor.
        from physicsguard.repair.protocol import decode_frame
        values = decode_frame(payload, 8192)
        values["hypothesis"] = FaultHypothesis(**values["hypothesis"])
        return RepairProposal(**values)
    except (TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError("malformed repair proposal") from error


@dataclass(frozen=True)
class PatchApplicationResult(JsonRecord):
    applied: bool
    original_sha256: str
    proposed_sha256: str | None
    unified_diff: str
    changed_lines: int
    error: str | None = None


@dataclass(frozen=True)
class VerificationPlan(JsonRecord):
    plan_id: str
    additional_cases: tuple[ExperimentCase, ...]
    required_diagnostics: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.plan_id, str) or not self.plan_id or len(self.plan_id) > 128:
            raise ValueError("bounded verification plan identifier required")
        if (not isinstance(self.additional_cases, (tuple, list)) or not self.additional_cases
                or not all(isinstance(c, ExperimentCase) for c in self.additional_cases)):
            raise ValueError("nonempty typed verification cases required")
        if len({c.case_id for c in self.additional_cases}) != len(self.additional_cases):
            raise ValueError("duplicate verification case identifiers")
        if (not isinstance(self.required_diagnostics, (tuple, list)) or not self.required_diagnostics
                or not all(isinstance(d, str) and d for d in self.required_diagnostics)
                or len(set(self.required_diagnostics)) != len(self.required_diagnostics)):
            raise ValueError("nonempty unique diagnostic identifiers required")
        object.__setattr__(self, "additional_cases", tuple(self.additional_cases))
        object.__setattr__(self, "required_diagnostics", tuple(self.required_diagnostics))


@dataclass(frozen=True)
class ProcessRun(JsonRecord):
    status: Literal["completed", "timeout", "execution_error", "unsupported", "resource_limit", "protocol_error", "source_mismatch"]
    report: DiagnosticReport | None
    elapsed_seconds: float
    requests: int
    error: str | None = None


@dataclass(frozen=True)
class VerificationResult(JsonRecord):
    decision: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"]
    plan_id: str
    reasons: tuple[str, ...]
    stages: dict[str, str]
    before_additional: ProcessRun | None
    after_development: ProcessRun | None
    after_additional: ProcessRun | None
    regression_ids: tuple[str, ...]
    lost_evidence_ids: tuple[str, ...]
    elapsed_seconds: float
    before_development: ProcessRun | None = None

    def __post_init__(self):
        if self.decision not in ("ACCEPTED", "REJECTED", "INCONCLUSIVE"):
            raise ValueError("unsupported final verification outcome")


@dataclass(frozen=True)
class RepairAttempt(JsonRecord):
    proposal: RepairProposal
    application: PatchApplicationResult
    verification: VerificationResult
    original_integrity: bool
    workspaces_cleaned: bool


@dataclass(frozen=True)
class RepairReport(JsonRecord):
    source: SourceSnapshot
    development: ProcessRun
    attempts: tuple[RepairAttempt, ...]
    abstained: bool
    reason: str
    original_integrity: bool
    workspaces_cleaned: bool
    elapsed_seconds: float
