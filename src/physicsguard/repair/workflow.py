"""Deterministic end-to-end source investigation and measured repair history."""
from time import perf_counter

from physicsguard.experiments.scenarios import development_cases
from physicsguard.schemas.repairs import RepairReport
from .executor import run_source_diagnostics
from .proposals import propose_repair
from .validator import verify_candidate
from .workspace import source_workspace


def repair_source(store, source_file: str, *, cases=None, timeout_seconds=2.0) -> RepairReport:
    started = perf_counter()
    snapshot = store.inspect(source_file)
    cases = development_cases() if cases is None else tuple(cases)
    with source_workspace(snapshot) as workspace:
        development = run_source_diagnostics(workspace, source_file, cases,
            timeout_seconds=timeout_seconds, audience="investigator")
    attempts = ()
    abstained = False
    if development.status != "completed" or development.report is None:
        reason = "Source execution evidence unavailable; no localization asserted"
    else:
        proposal = propose_repair(snapshot, development.report)
        if proposal is None:
            abstained = (not development.report.detected
                and all(a.status == "success" for a in development.report.executions)
                and not any(d.applicable and d.status == "inconclusive" for d in development.report.diagnostics))
            reason = ("No failed scientific properties observed; no source modification proposed" if abstained
                      else "Evidence is inconclusive or no supported source pattern is sufficiently evidenced")
        else:
            attempt = verify_candidate(store, snapshot, proposal, development, cases, timeout_seconds=timeout_seconds)
            attempts = (attempt,)
            reason = "; ".join(attempt.verification.reasons)
    return RepairReport(snapshot, development, attempts, abstained, reason,
        store.unchanged(snapshot) and all(a.original_integrity for a in attempts),
        not workspace.exists() and all(a.workspaces_cleaned for a in attempts), perf_counter()-started)
