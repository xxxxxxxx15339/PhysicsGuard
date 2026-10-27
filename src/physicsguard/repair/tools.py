"""Small host-side tool surface for one future investigator; no model/client here.

Only development evidence is returned. Full verification records stay on the
host; Python objects/import rules are not a security boundary for a hostile agent.
No arbitrary-source/model execution endpoint is exposed.
"""
from physicsguard.experiments.public import investigator_view
from physicsguard.experiments.runner import validate_cases
from copy import deepcopy
from physicsguard.schemas.repairs import RepairProposal
from physicsguard.schemas.results import ExperimentCase
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
        with source_workspace(snapshot) as workspace:
            run = run_source_diagnostics(workspace, source_file, (case,), audience="investigator")
        run_id = "run-"+source_hash(snapshot.sha256+case.to_json())[:16]
        self._runs[run_id] = (snapshot, run, (case,))
        return {"run_id": run_id, "status": run.status, "error": run.error}

    def get_diagnostic_report(self, run_id: str) -> dict:
        _, run, _ = self._runs[run_id]
        return investigator_view(run.report) if run.report else {"status": run.status, "error": run.error}

    def propose_localized_patch(self, source_file: str, run_id: str) -> RepairProposal | None:
        snapshot, run, cases = self._runs[run_id]
        if source_file != snapshot.source_file or not self.store.unchanged(snapshot):
            raise ValueError("diagnostic run does not match current source")
        proposal = propose_repair(snapshot, run.report) if run.report else None
        if proposal:
            self._proposals[proposal.proposal_id] = (snapshot, proposal, run, cases)
        return proposal

    def verify_candidate_patch(self, proposal_id: str) -> dict:
        if len(self._history) >= 8:
            raise ValueError("verification tool attempt budget exhausted")
        snapshot, proposal, run, cases = self._proposals[proposal_id]
        attempt = verify_candidate(self.store, snapshot, proposal, run, cases)
        summary = {"proposal_id": proposal_id, "origin": proposal.origin,
                   "decision": attempt.verification.decision, "reasons": attempt.verification.reasons,
                   "stages": attempt.verification.stages, "original_integrity": attempt.original_integrity,
                   "workspaces_cleaned": attempt.workspaces_cleaned}
        self._history.append(deepcopy(summary))
        return summary

    def get_repair_history(self) -> tuple[dict, ...]:
        return tuple(deepcopy(item) for item in self._history)
