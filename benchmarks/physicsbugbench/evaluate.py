"""Evaluator-only scoring CLI. No model, localization or repair scores exist."""

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import random
import platform
from statistics import median
from time import perf_counter

import numpy as np

from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.public import investigator_view
from physicsguard.experiments.scenarios import development_cases
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification
from .variants import ENTRIES


def heldout_cases(seed: int) -> tuple[ExperimentCase, ...]:
    """Evaluator-only parameter holdout; the public seed is NOT a security boundary."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer in [0,2**32)")
    rng = random.Random(seed)
    cases = []
    for i, (profile, mode) in enumerate((("sine", 1), ("sine", 2), ("square", 1))):
        for sign in (1, -1):
            speed = sign * rng.uniform(0.6, 1.5)
            length = rng.uniform(0.8, 1.4)
            cases.append(ExperimentCase(
                f"eval-{i}-{sign:+d}", physics=PhysicsSpecification(speed, -0.4, length-0.4),
                profile=profile, mode=mode, phase=rng.uniform(0.1, 5.9),
                cfl=rng.uniform(0.65, 0.85), final_time=(0.125 if mode == 2 else 0.23) * length / abs(speed),
                offset=rng.uniform(0.7, 1.3), amplitude=rng.uniform(0.15, 0.3)))
    return tuple(cases)


def control_cases(entry, cases):
    if entry.benchmark_id == "PBB-C01":
        return tuple(c for c in cases if c.physics.speed > 0)
    if entry.benchmark_id == "PBB-C02":
        return tuple(c for c in cases if c.physics.speed < 0)
    if entry.benchmark_id == "PBB-C03":
        return tuple(replace(c, physics=replace(c.physics, x_min=2.0,
                            x_max=2 + 3 * (c.physics.x_max-c.physics.x_min), speed=3*c.physics.speed))
                     for c in cases)
    return cases


def score_reports(pairs):
    """Recall denominator is all injected faults, including inconclusive outcomes."""
    faults = [(entry, report) for entry, report in pairs if entry.fault_type is not None]
    controls = [(entry, report) for entry, report in pairs if entry.fault_type is None]
    coverage = {}
    for entry, report in pairs:
        for d in report.diagnostics:
            row = coverage.setdefault(d.diagnostic_id, {"pass": 0, "fail": 0, "inconclusive": 0,
                                                       "applicable": 0, "total": 0})
            row[d.status] += 1
            row["total"] += 1
            row["applicable"] += int(d.applicable)
    counts = Counter(d.status for _, report in pairs for d in report.diagnostics)
    total = sum(counts.values())
    def basic_outcomes(report):
        return [any(d.status == "fail" and d.case_ids == (case.case_id,) for d in report.diagnostics)
                for case in report.cases]
    return {
        "fault_detection": {"detected": sum(r.detected for _, r in faults), "total": len(faults),
                            "rate": sum(r.detected for _, r in faults)/len(faults) if faults else None},
        "detection_by_fault_type": {
            entry.fault_type: {"detected": int(report.detected), "total": 1,
                               "rate": float(report.detected),
                               "basic_case_detected": sum(basic_outcomes(report)),
                               "basic_case_total": len(report.cases),
                               "revealing_diagnostics": sorted({d.diagnostic_id for d in report.diagnostics if d.status == "fail"})}
            for entry, report in faults},
        "false_positives": {"flagged": sum(r.detected for _, r in controls), "total": len(controls),
                            "rate": sum(r.detected for _, r in controls)/len(controls) if controls else None},
        "basic_case_false_positives": {"flagged": sum(sum(basic_outcomes(r)) for _, r in controls),
                                       "total": sum(len(r.cases) for _, r in controls)},
        "diagnostic_coverage": coverage,
        "conclusive_diagnostic_fraction": (counts["pass"] + counts["fail"])/total if total else None,
        "inconclusive_diagnostics": counts["inconclusive"],
        "reports_with_inconclusive_evidence": sum(r.inconclusive_count > 0 for _, r in pairs),
        "fully_inconclusive_reports": sum(all(d.status == "inconclusive" for d in r.diagnostics) for _, r in pairs),
        "execution_errors": sum(run.status == "error" for _, r in pairs for run in r.executions),
        "execution_count": sum(len(r.executions) for _, r in pairs),
        "solver_elapsed_seconds": sum(run.elapsed_seconds for _, r in pairs for run in r.executions),
        "median_execution_seconds": median(run.elapsed_seconds for _, r in pairs for run in r.executions),
        "suite_elapsed_seconds": sum(r.elapsed_seconds for _, r in pairs),
    }


def evaluate(seed: int = 20261027):
    """Private scorer plus separate development-only public evidence.

    Seeded samples are a reproducible parameter split, not unseen fault classes
    or a security guarantee. This callable belongs only in the evaluator.
    """
    started = perf_counter()
    evaluation = heldout_cases(seed)  # Fix samples before inspecting outcomes.
    public = {"schema_version": 1, "reports": []}
    private = {"schema_version": 1, "seed": seed, "evaluation_kind": "deterministic diagnostics only",
               "environment": {"python": platform.python_version(), "numpy": np.__version__},
               "split_kind": "parameter holdout, same fault implementations", "splits": {}}
    # Opaque handles avoid advertising benchmark answers in investigator records.
    handles = {entry.benchmark_id: f"solver-{i:03d}" for i, entry in enumerate(ENTRIES)}
    for split, cases in (("development", development_cases()), ("heldout", evaluation)):
        pairs = []
        reports = []
        for entry in ENTRIES:
            report = diagnose_solver(entry.solver, handles[entry.benchmark_id], control_cases(entry, cases),
                                     audience="investigator" if split == "development" else "evaluator_only")
            pairs.append((entry, report))
            reports.append({"benchmark_id": entry.benchmark_id, "fault_type": entry.fault_type,
                            "detected": report.detected, "report": report.to_dict()})
            if split == "development":
                public["reports"].append(investigator_view(report))
        private["splits"][split] = {"metrics": score_reports(pairs), "outcomes": reports}
    private["elapsed_seconds"] = perf_counter() - started
    return private, public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--output", type=Path, required=True, help="Evaluator-only full JSON with scoring labels")
    parser.add_argument("--public-output", type=Path, help="Development-only investigator JSON")
    args = parser.parse_args()
    if args.public_output and args.public_output.resolve() == args.output.resolve():
        parser.error("private and public outputs must have different paths")
    private, public = evaluate(args.seed)
    args.output.write_text(json.dumps(private, allow_nan=False, sort_keys=True, indent=2) + "\n")
    if args.public_output:
        args.public_output.write_text(json.dumps(public, allow_nan=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({name: split["metrics"] for name, split in private["splits"].items()},
                     allow_nan=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
