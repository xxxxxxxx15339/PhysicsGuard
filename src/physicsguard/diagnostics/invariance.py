"""Metamorphic checks for this linear, periodic, uniform upwind contract only."""

from dataclasses import replace

import numpy as np

from physicsguard.experiments.runner import execute_solver
from physicsguard.schemas.results import DiagnosticResult, ExperimentCase
from ._common import ASSUMPTIONS, amplitude_scale, measure_safely, roundoff_tolerance, unavailable


def metamorphic_checks(solver, solver_id: str, case: ExperimentCase):
    """Return property checks and all supporting executions, with actual inputs."""
    if not case.strategy.supports_upwind_checks:
        return ((replace(unavailable("metamorphic", "Linear upwind metamorphic checks",
                                     "Unsupported strategy", applicable=False), case_ids=(case.case_id,)),), ())
    runs = []
    checks = []

    def run(name, values, config_case=case):
        execution = execute_solver(solver, solver_id, replace(config_case, case_id=f"{case.case_id}-{name}"), values)
        runs.append(execution)
        return execution

    def compare(identifier, description, left, right, expected, support=()):
        evidence = ((left,) if right is None else (left, right)) + support
        if any(r.status != "success" for r in evidence):
            checks.append(replace(unavailable(identifier, description, "; ".join(
                r.error or "missing output" for r in evidence if r.status != "success")),
                case_ids=tuple(r.case.case_id for r in evidence)))
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
                              case_ids=tuple(r.case.case_id for r in evidence)))

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
    if other.status != "success":
        checks.append(replace(unavailable("linearity", "Linear superposition", other.error or "No second run"),
                              case_ids=(combined.case.case_id, base.case.case_id, other.case.case_id)))
    else:
        compare("linearity", "Linear superposition", combined, base,
                lambda: np.asarray(base.final_averages) - 0.4 * np.asarray(other.final_averages), (other,))
    length = case.physics.x_max - case.physics.x_min
    scaled_case = replace(case, physics=replace(case.physics, x_min=2.0,
                                               x_max=2.0 + 3 * length, speed=3 * case.physics.speed))
    scaled = run("space-scale", first, scaled_case)
    compare("space_scaling", "Consistent domain/velocity scaling", scaled, base,
            lambda: np.asarray(base.final_averages))
    time_case = replace(case, physics=replace(case.physics, speed=case.physics.speed / 2),
                        final_time=case.final_time * 2)
    rescaled = run("time-scale", first, time_case)
    compare("time_scaling", "Consistent time/velocity scaling", rescaled, base,
            lambda: np.asarray(base.final_averages))
    if case.physics.speed == 0:
        checks.append(unavailable("periodic_wrap", "One-cell transport across periodic seam",
                                  "Requires nonzero speed", applicable=False))
    else:
        dt = case.config().dx / abs(case.physics.speed)
        seam_case = replace(case, cfl=1.0, final_time=dt)
        seam = run("periodic-wrap", first, seam_case)
        compare("periodic_wrap", "One-cell transport across periodic seam", seam, None,
                lambda: np.roll(first, 1 if case.physics.speed > 0 else -1))
    return tuple(checks), tuple(runs)
