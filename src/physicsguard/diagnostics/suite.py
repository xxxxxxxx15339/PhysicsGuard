"""Coarse evidence followed by refinement and metamorphic diagnostics."""

from time import perf_counter
from dataclasses import replace

from physicsguard.experiments.runner import execute_generated, execute_solver, validate_budget
from physicsguard.experiments.scenarios import REFINEMENT_CELLS
from physicsguard.schemas.results import DiagnosticReport, ExperimentCase
from ._common import measure_safely
from .accuracy import analytical_accuracy, transport_direction
from .conservation import conservation
from .invariance import metamorphic_checks
from .refinement import grid_refinement
from .stability import stability


def diagnose_solver(solver, solver_id, cases, *, audience="evaluator_only") -> DiagnosticReport:
    """All outcomes are measured; a failed property does not localize source code.

    Each supplied development case gets the basic families. The first suitable
    smooth case also gets three refinement levels and metamorphic checks.
    """
    try:
        cases = tuple(cases)
    except TypeError as error:
        raise ValueError("cases must be an iterable of ExperimentCase records") from error
    if audience not in ("investigator", "evaluator_only"):
        raise ValueError("unsupported report audience")
    if (not cases or len(cases) > 16 or not all(isinstance(c, ExperimentCase) for c in cases)
            or len({c.case_id for c in cases}) != len(cases)):
        raise ValueError("provide 1..16 cases with distinct case IDs")
    for case in cases:
        validate_budget(case)
    started = perf_counter()
    runs = []
    checks = []
    for case in cases:
        run = execute_solver(solver, solver_id, case)
        runs.append(run)
        for diagnostic, identifier in ((conservation, "conservation"), (analytical_accuracy, "accuracy"),
                                       (transport_direction, "direction")):
            check = measure_safely(identifier, "Numerical diagnostic", lambda: diagnostic(run))
            checks.append(replace(check, case_ids=(case.case_id,)))
        checks.extend(replace(measure_safely(d.diagnostic_id, d.description, lambda: d),
                              case_ids=(case.case_id,)) for d in stability(run))
    smooth = next((c for c in cases if c.profile == "sine" and c.mode == 1), cases[0])
    refined = tuple(execute_generated(solver, solver_id, f"{smooth.case_id}-n{n}",
                                      lambda n=n: replace(smooth, n_cells=n)) for n in REFINEMENT_CELLS)
    runs.extend(refined)
    checks.append(replace(measure_safely("refinement", "Observed smooth-grid convergence",
                                        lambda: grid_refinement(refined)),
                          case_ids=tuple(r.case_id for r in refined)))
    invariants, extra = metamorphic_checks(solver, solver_id, smooth)
    runs.extend(extra)
    checks.extend(invariants)
    return DiagnosticReport(solver_id, cases, tuple(runs), tuple(checks), perf_counter() - started, audience)
