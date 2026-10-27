"""Measure actual deterministic source localization/proposals/verification."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from physicsguard.experiments.scenarios import development_cases
from physicsguard.repair.executor import run_source_diagnostics
from physicsguard.repair.proposals import make_proposal
from physicsguard.repair.sources import default_source_store
from physicsguard.repair.validator import verify_candidate, case_signature
from physicsguard.repair.verification_cases import independent_plan
from physicsguard.repair.workflow import repair_source
from physicsguard.repair.workspace import source_workspace

# Ground truth is used ONLY after investigation, to score measured hypotheses.
GROUND_TRUTH = {
    "solver_01.py": ("transport_direction", 8),
    "solver_02.py": ("spatial_scaling", 9),
    "solver_03.py": ("periodic_neighbor", 12),
    "solver_04.py": None,
}


def negative_proposals(store, reports):
    """Requested gate controls; scored separately from successful repair recall."""
    outcomes = []
    source_report = reports["solver_01.py"]
    snapshot = source_report.source
    original_proposal = source_report.attempts[0].proposal
    positive_cases = tuple(c for c in development_cases() if c.physics.speed > 0)
    with source_workspace(snapshot) as workspace:
        positive_run = run_source_diagnostics(workspace, snapshot.source_file, positive_cases, audience="investigator")
    proposal = make_proposal(snapshot, original_proposal.hypothesis, "    neighbor_offset = 1", origin="human")
    outcomes.append(("positive_only", verify_candidate(store, snapshot, proposal, positive_run, positive_cases)))
    for label, source, replacement in (
        ("mass_damaging", "solver_02.py", "    scale = dt / dx + 0.1 * state"),
        ("nonfinite", "solver_02.py", "    scale = dt / dx if dt > 0.5 * dx else 1e309"),
        ("execution_failure", "solver_02.py", "    scale = dt / 0"),
        ("timeout", "solver_02.py", "    scale = 9 ** (9 ** 9)"),
        ("syntax", "solver_02.py", "    scale = ("),
    ):
        report = reports[source]
        proposal = make_proposal(report.source, report.attempts[0].proposal.hypothesis, replacement, origin="human")
        attempt = verify_candidate(store, report.source, proposal, report.development, development_cases(),
                                   timeout_seconds=.2 if label == "timeout" else 2.)
        outcomes.append((label, attempt))
    for label, proposal in (
        ("stale_hash", replace(original_proposal, original_sha256="f"*64, origin="human")),
        ("test_modification", replace(original_proposal, source_file="tests/test_numerics.py", origin="human")),
        ("unrelated_file", replace(original_proposal, source_file="README.md", origin="human")),
    ):
        outcomes.append((label, verify_candidate(store, snapshot, proposal, source_report.development, development_cases())))
    plan = independent_plan()
    limited = replace(plan, additional_cases=tuple(replace(c, max_steps=50) for c in plan.additional_cases))
    outcomes.append(("verification_unavailable", verify_candidate(store, snapshot,
        replace(original_proposal, origin="human"), source_report.development, development_cases(), plan=limited)))
    return [{"case": label, "attempt": attempt.to_dict()} for label, attempt in outcomes]


def evaluate_repairs(*, include_negative=True):
    started = perf_counter()
    store = default_source_store()
    reports = {name: repair_source(store, name) for name in GROUND_TRUTH}
    defective = [r for name, r in reports.items() if GROUND_TRUTH[name] is not None]
    attempts = [a for r in defective for a in r.attempts]
    controls = [r for name, r in reports.items() if GROUND_TRUTH[name] is None]
    useful = sum(bool(r.attempts) and r.attempts[0].proposal.hypothesis.mechanism == GROUND_TRUTH[name][0]
                 and r.attempts[0].proposal.hypothesis.start_line <= GROUND_TRUTH[name][1] <= r.attempts[0].proposal.hypothesis.end_line
                 for name, r in reports.items() if GROUND_TRUTH[name] is not None)
    runs = [r.development for r in reports.values()]
    runs += [run for a in attempts for run in (a.verification.before_additional,
             a.verification.after_development, a.verification.after_additional) if run is not None]
    metrics = {"defective_fixtures": len(defective),
        "detected": sum(bool(r.development.report and r.development.report.detected) for r in defective),
        "useful_localization": useful, "proposals": len(attempts),
        "valid_proposals": sum(a.application.applied for a in attempts),
        **{decision.lower(): sum(a.verification.decision == decision for a in attempts)
           for decision in ("ACCEPTED", "REJECTED", "INCONCLUSIVE")},
        "correct_controls": len(controls), "correct_abstentions": sum(r.abstained for r in controls),
        "false_repairs": sum(a.verification.decision == "ACCEPTED" for r in controls for a in r.attempts),
        "regression_rate": sum(bool(a.verification.regression_ids) for a in attempts)/len(attempts) if attempts else None,
        "average_changed_lines": mean(a.application.changed_lines for a in attempts) if attempts else None,
        "solver_requests": sum(r.requests for r in runs), "worker_sessions": len(runs),
        "verification_elapsed_seconds": sum(a.verification.elapsed_seconds for a in attempts),
    }
    negative = negative_proposals(store, reports) if include_negative else []
    return {"schema_version": 1, "origin": "deterministic", "baseline": "46b6e78c19b0bf37aa15e2c14d91fce2a1d971ef",
        "categories": {"known_source_fixtures": metrics,
          "additional_parameter_cases": {"unique_configurations": len({case_signature(c) for a in attempts
              if a.verification.after_additional and a.verification.after_additional.report
              for c in a.verification.after_additional.report.cases}), "candidate_base_case_evaluations": sum(
              len(a.verification.after_additional.report.cases) for a in attempts
              if a.verification.after_additional and a.verification.after_additional.report),
              "scope": "same known source fixtures; additional cases withheld from proposal generation"},
          "unseen_source_mutation_patterns": {"status": "unevaluated", "samples": 0, "rate": None},
          "negative_proposals": {"attempted": len(negative), **{d.lower(): sum(
              o["attempt"]["verification"]["decision"] == d for o in negative)
              for d in ("ACCEPTED", "REJECTED", "INCONCLUSIVE")}}},
        "reports": {name: report.to_dict() for name, report in reports.items()}, "negative_proposals": negative,
        "elapsed_seconds": perf_counter()-started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Evaluator-owned full repair evidence JSON")
    args = parser.parse_args()
    if args.output.suffix != ".json" or args.output.is_symlink():
        parser.error("repair reports require a .json output file without a symlink")
    result = evaluate_repairs()
    args.output.write_text(json.dumps(result, allow_nan=False, sort_keys=True, indent=2)+"\n")
    print(json.dumps(result["categories"], allow_nan=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
