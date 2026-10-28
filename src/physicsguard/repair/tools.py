"""Small host-side tool surface for one future investigator; no model/client here.

Only development evidence is returned. Full verification records stay on the
host; Python objects/import rules are not a security boundary for a hostile agent.
No arbitrary-source/model execution endpoint is exposed.
"""
from physicsguard.experiments.public import investigator_view
from physicsguard.experiments.runner import validate_cases
from copy import deepcopy
from dataclasses import replace
import json
from physicsguard.schemas.repairs import RepairProposal
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification, SolverStrategy
from .executor import run_source_diagnostics
from .proposals import propose_repair
from .sources import source_hash
from .validator import verify_candidate
from .workspace import source_workspace


class RepairTools:
    def __init__(self, store):
        self.store = store
        self._runs = {}
        self._proposals = {}
        self._history = []
        self._run_count = 0

    def inspect_solver_source(self, source_file: str) -> dict:
        snapshot = self.store.inspect(source_file)
        return {"source_file": snapshot.source_file, "sha256": snapshot.sha256, "lines": snapshot.numbered_lines()}

    def run_scientific_experiment(self, source_file: str, case: ExperimentCase) -> dict:
        snapshot = self.store.inspect(source_file)
        validate_cases((case,))
        if self._run_count >= 16:
            raise ValueError("development tool run budget exhausted")
        self._run_count += 1
        run_id = "run-"+source_hash(snapshot.sha256+case.to_json())[:24]
        if run_id in self._runs:
            return self._run_summary(run_id)
        with source_workspace(snapshot) as workspace:
            run = run_source_diagnostics(workspace, source_file, (case,), audience="investigator")
        self._runs[run_id] = (snapshot, run, (case,))
        return self._run_summary(run_id)

    def _run_summary(self, run_id):
        _, run, _ = self._lookup(self._runs, run_id)
        return {"run_id": run_id, "status": run.status, "error": run.error}

    @staticmethod
    def _lookup(records, identifier):
        if not isinstance(identifier, str) or identifier not in records:
            raise ValueError("unknown operation identifier")
        return records[identifier]

    def get_diagnostic_report(self, run_id: str) -> dict:
        _, run, _ = self._lookup(self._runs, run_id)
        return investigator_view(run.report) if run.report else {"status": run.status, "error": run.error}

    def propose_localized_patch(self, source_file: str, run_id: str) -> RepairProposal | None:
        snapshot, run, cases = self._lookup(self._runs, run_id)
        if source_file != snapshot.source_file or not self.store.unchanged(snapshot):
            raise ValueError("diagnostic run does not match current source")
        proposal = propose_repair(snapshot, run.report) if run.report else None
        if proposal:
            proposal = replace(proposal, proposal_id="proposal-"+source_hash(proposal.to_json()+run_id)[:24])
            self._proposals[proposal.proposal_id] = (snapshot, proposal, run, cases)
        return proposal

    def verify_candidate_patch(self, proposal_id: str) -> dict:
        if len(self._history) >= 8:
            raise ValueError("verification tool attempt budget exhausted")
        snapshot, proposal, run, cases = self._lookup(self._proposals, proposal_id)
        attempt = verify_candidate(self.store, snapshot, proposal, development_cases=cases)
        summary = {"proposal_id": proposal_id, "origin": proposal.origin,
                   "decision": attempt.verification.decision,
                   "reasons": {"ACCEPTED": ["Host verification accepted the candidate"],
                               "REJECTED": ["Host verification rejected the candidate"],
                               "INCONCLUSIVE": ["Host verification lacks sufficient evidence"]}[attempt.verification.decision],
                   "stages": attempt.verification.stages, "original_integrity": attempt.original_integrity,
                   "workspaces_cleaned": attempt.workspaces_cleaned}
        self._history.append(deepcopy(summary))
        return summary

    def get_repair_history(self) -> tuple[dict, ...]:
        return tuple(deepcopy(item) for item in self._history)

    def select_localized_edit(self, source_file: str, run_id: str, operation_id: str):
        """Host renders an existing rule; no raw replacement code is accepted.

        Selection is not model-authored source. The resulting proposal truthfully
        retains deterministic origin and passes the same host policy/verifier.
        """
        operations = {"restore_signed_upwind": "transport_direction",
                      "normalize_time_by_cell_width": "spatial_scaling",
                      "wrap_incoming_neighbor": "periodic_neighbor"}
        if operation_id not in operations:
            raise ValueError("unsupported edit operation")
        snapshot, run, _ = self._lookup(self._runs, run_id)
        inferred = propose_repair(snapshot, run.report) if run.report else None
        if inferred is None or inferred.hypothesis.mechanism != operations[operation_id]:
            raise ValueError("edit operation lacks supporting source/evidence")
        return self.propose_localized_patch(source_file, run_id)

    def call(self, operation: str, arguments: dict) -> dict:
        """Allowlisted JSON transport adapter, intended for host dispatch only.

        It does not expose host objects, plans, source edits or Python callables.
        A separately isolated investigator must receive only this serialized data;
        giving it this Python instance would not enforce an access boundary.
        """
        fields = {
            "inspect_solver_source": {"source_file"},
            "run_scientific_experiment": {"source_file", "case"},
            "get_diagnostic_report": {"run_id"},
            "propose_localized_patch": {"source_file", "run_id"},
            "select_localized_edit": {"source_file", "run_id", "operation_id"},
            "verify_candidate_patch": {"proposal_id"}, "get_repair_history": set(),
        }
        try:
            if not isinstance(operation, str) or operation not in fields or type(arguments) is not dict:
                raise ValueError("unsupported operation")
            # Finite JSON round trip rejects host objects, cycles and oversized input.
            payload = json.dumps(arguments, allow_nan=False)
            if len(payload) > 8192 or set(arguments) != fields[operation]:
                raise ValueError("unsupported arguments")
            args = json.loads(payload)
            for name, value in args.items():
                if name != "case" and (not isinstance(value, str) or not value or len(value) > 128):
                    raise ValueError("bounded text arguments required")
            if operation == "run_scientific_experiment":
                values = args["case"]
                if type(values) is not dict:
                    raise ValueError("case object required")
                values["physics"] = PhysicsSpecification(**values.get("physics", {}))
                values["strategy"] = SolverStrategy(**values.get("strategy", {}))
                args["case"] = ExperimentCase(**values)
                if not args["case"].strategy.supports_upwind_checks or len(args["case"].case_id) > 128:
                    raise ValueError("unsupported experiment assumptions")
            value = getattr(self, operation)(**args)
            if isinstance(value, RepairProposal):
                value = value.to_dict()
            return {"ok": True, "result": json.loads(json.dumps(value, allow_nan=False))}
        except (ValueError, TypeError, KeyError, OSError, RecursionError):
            # Detailed host exceptions can include paths or verifier case IDs.
            return {"ok": False, "error": "invalid_or_unavailable_operation"}
