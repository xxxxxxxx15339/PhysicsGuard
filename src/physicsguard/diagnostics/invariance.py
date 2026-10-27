"""Metamorphic checks for this linear, periodic, uniform upwind contract only."""

from dataclasses import replace

import numpy as np

from physicsguard.experiments.runner import execute_generated
from physicsguard.schemas.results import DiagnosticResult, ExperimentCase
from ._common import ASSUMPTIONS, amplitude_scale, attempt_errors, measure_safely, roundoff_tolerance, unavailable


def metamorphic_checks(solver, solver_id: str, case: ExperimentCase):
    """Return property checks and all supporting executions, with actual inputs."""
    if not case.strategy.supports_upwind_checks:
        return ((replace(unavailable("metamorphic", "Linear upwind metamorphic checks",
                                     "Unsupported strategy", applicable=False), case_ids=(case.case_id,)),), ())
    runs = []
    checks = []

    def run(name, values, case_factory=lambda: case):
        execution = execute_generated(solver, solver_id, f"{case.case_id}-{name}", case_factory, values)
        runs.append(execution)
        return execution

    def compare(identifier, description, left, right, expected, support=()):
        evidence = ((left,) if right is None else (left, right)) + support
        if any(r.status != "success" for r in evidence):
            checks.append(replace(unavailable(identifier, description, "; ".join(attempt_errors(evidence))),
                case_ids=tuple(r.case_id for r in evidence)))
            return
        def measurement():
            target = expected()
            difference = float(np.max(np.abs(np.asarray(left.final_averages) - target)))
            scale = max(*(amplitude_scale(r) for r in evidence), float(np.max(np.abs(target))))
            tolerance = 4 * sum(roundoff_tolerance(r, scale) for r in evidence)
            return DiagnosticResult(identifier, description, ASSUMPTIONS + (
                "linear homogeneous PDE and declared upwind method",), True,
                "pass" if difference <= tolerance else "fail", {"max_difference": difference},
                {"max_difference": case.physics.field_unit}, "Maximum absolute difference <= tolerance",
                tolerance, "4*sum(gamma_k*field_scale) across compared runs allows combined rounding")
        checks.append(replace(measure_safely(identifier, description, measurement),
                              case_ids=tuple(r.case_id for r in evidence)))

    # Fixed algebraic, non-symmetric data exercises the seam and high frequencies.
    x = np.arange(case.n_cells, dtype=float)
    first = np.sin(0.73 * x) + 0.2 * np.cos(1.17 * x)
    second = np.cos(0.43 * x + 0.2)
    base = run("base", first)
    constant = run("constant", np.full(case.n_cells, 1.25))
    compare("constant", "Constant-state preservation", constant, None,
            lambda: np.full(case.n_cells, 1.25))
    shifted = run("shift", np.roll(first, 7))
    compare("translation", "Cyclic translation equivariance", shifted, base,
            lambda: np.roll(base.final_averages, 7))
    other = run("other", second)
    combined = run("linear", first - 0.4 * second)
    compare("linearity", "Linear superposition", combined, base,
            lambda: np.asarray(base.final_averages) - 0.4 * np.asarray(other.final_averages), (other,))
    length = case.physics.x_max - case.physics.x_min
    scaled = run("space-scale", first, lambda: replace(case, physics=replace(case.physics, x_min=2.0,
                            x_max=2.0 + 3 * length, speed=3 * case.physics.speed)))
    compare("space_scaling", "Consistent domain/velocity scaling", scaled, base,
            lambda: np.asarray(base.final_averages))
    rescaled = run("time-scale", first, lambda: replace(case,
                  physics=replace(case.physics, speed=case.physics.speed / 2), final_time=case.final_time * 2))
    compare("time_scaling", "Consistent time/velocity scaling", rescaled, base,
            lambda: np.asarray(base.final_averages))
    if case.physics.speed == 0:
        checks.append(unavailable("periodic_wrap", "One-cell transport across periodic seam",
                                  "Requires nonzero speed", applicable=False))
    else:
        seam = run("periodic-wrap", first, lambda: replace(case, cfl=1.0,
                    final_time=case.config().dx / abs(case.physics.speed)))
        compare("periodic_wrap", "One-cell transport across periodic seam", seam, None,
                lambda: np.roll(first, 1 if case.physics.speed > 0 else -1))
    return tuple(checks), tuple(runs)
