"""Analytical cell-average accuracy and direction, independent of flux/update code."""

from math import fsum, tau

import numpy as np

from physicsguard.experiments.scenarios import cell_averages
from physicsguard.schemas.results import DiagnosticResult, SolverExecutionResult
from ._common import (ASSUMPTIONS, amplitude_scale, execution_issue, norm_errors,
                      roundoff_tolerance, unavailable)


def matches_reference_initial(run: SolverExecutionResult) -> bool:
    """A profile label is not evidence that arbitrary supplied data match it."""
    expected = cell_averages(run.case)
    return (len(run.initial_averages) == len(expected) and
            bool(np.array_equal(np.asarray(run.initial_averages), expected)))


def smooth_error_budget(run: SolverExecutionResult) -> float | None:
    """A priori Linf bound from space/time truncation and monotone stability.

    Upwind derivative consistency <= dx/2 * ||u_xx||inf. Taylor's Euler
    residual <= a^2*dt^2/2 * ||u_xx||inf. A convex upwind step is Linf
    nonexpansive, so sum the local bounds. Cell averaging only lowers this
    derivative bound. No call to a candidate or trusted discrete solver.
    This intentionally conservative bound does not establish optimal accuracy.
    """
    case = run.case
    if not case.strategy.supports_upwind_checks or case.profile == "square":
        return None
    if run.max_cfl is None or run.max_cfl > 1 + 16 * np.finfo(float).eps:
        return None
    length = case.physics.x_max - case.physics.x_min
    curvature = abs(case.amplitude) * (tau * case.mode / length)**2 if case.profile == "sine" else 0.0
    speed = abs(case.physics.speed)
    return (0.5 * curvature * (speed * case.final_time * case.config().dx
                              + speed**2 * fsum(dt**2 for dt in run.time_steps))
            + roundoff_tolerance(run, amplitude_scale(run)))


def analytical_accuracy(run: SolverExecutionResult) -> DiagnosticResult:
    if issue := execution_issue(run, "accuracy", "Analytical cell-average error"):
        return issue
    if not matches_reference_initial(run):
        return unavailable("accuracy", "Analytical cell-average error",
                           "Actual initial data do not match the declared analytical profile", applicable=False)
    errors = norm_errors(run.final_averages, cell_averages(run.case, run.case.final_time), run.case.config().dx)
    budget = smooth_error_budget(run)
    norm = "Linf"
    justification = ("0.5*||u_xx||inf*(|a|*T*dx+a^2*sum(dt^2)) + gamma_k*field_scale; "
                     "not calibrated against benchmark outcomes")
    if (run.case.profile == "square" and run.case.strategy.supports_upwind_checks
            and run.max_cfl is not None and run.max_cfl <= 1 + 16 * np.finfo(float).eps):
        # A monotone step is a Bernoulli translation by one cell. For a BV
        # profile, ||f(. - X)-f(. - aT)||L1 <= TV(f)*|X-aT|. Jensen then
        # bounds expected displacement by sqrt(variance). Cell averaging is
        # L1 contractive; this is valid for discontinuities and across the seam.
        dx = run.case.config().dx
        a = abs(run.case.physics.speed)
        variance = max(0., fsum(a*dt*dx - (a*dt)**2 for dt in run.time_steps))
        length = run.case.physics.x_max - run.case.physics.x_min
        budget = 2 * abs(run.case.amplitude) * variance**0.5 + length * roundoff_tolerance(run, amplitude_scale(run))
        norm = "L1"
        justification = ("TV(square)=2*abs(amplitude); L1 <= TV*sqrt(sum(|a|*dt*dx-(a*dt)^2)) "
                         "+ length*gamma_k*field_scale by Bernoulli-shift variance and BV translation bound")
    unit = run.case.physics.field_unit
    length = run.case.physics.length_unit
    return DiagnosticResult("accuracy", "Analytical cell-average error", ASSUMPTIONS + (
        "declared upwind/Euler at CFL<=1; smooth Linf or BV-square L1 error bound",),
        budget is not None, "inconclusive" if budget is None else (
            "pass" if errors[norm] <= budget else "fail"), errors,
        {"L1": f"{unit}*{length}", "L2": f"{unit}*sqrt({length})", "Linf": unit},
        f"{norm} <= a priori upwind discretization bound plus roundoff", budget, justification,
        ("No supported acceptance bound for this profile/strategy/CFL",) if budget is None else ())


def transport_direction(run: SolverExecutionResult) -> DiagnosticResult:
    if issue := execution_issue(run, "direction", "Physical transport direction"):
        return issue
    if not matches_reference_initial(run):
        return unavailable("direction", "Physical transport direction",
                           "Actual initial data do not match the declared analytical profile", applicable=False)
    case = run.case
    budget = smooth_error_budget(run)
    if case.physics.speed == 0 or case.final_time == 0 or budget is None:
        return unavailable("direction", "Physical transport direction",
                           "Requires nonzero travel and a smooth-method error budget", applicable=False)
    correct = cell_averages(case, case.final_time)
    opposite = cell_averages(case, case.final_time, reverse=True)
    separation = norm_errors(correct, opposite, case.config().dx)["Linf"]
    forward = norm_errors(run.final_averages, correct, case.config().dx)["Linf"]
    backward = norm_errors(run.final_averages, opposite, case.config().dx)["Linf"]
    identifiable = separation > 4 * budget
    status = "inconclusive"
    if identifiable:
        if forward <= budget:
            status = "pass"
        elif backward + budget < forward:
            status = "fail"
    return DiagnosticResult("direction", "Physical transport direction", ASSUMPTIONS + (
        "correct and opposite analytical translations must be distinguishable above discretization error",),
        identifiable, status,
        {"correct_Linf": forward, "opposite_Linf": backward, "reference_separation_Linf": separation},
        {k: case.physics.field_unit for k in ("correct_Linf", "opposite_Linf", "reference_separation_Linf")},
        "Require separation>4*budget; pass if correct error<=budget; fail if opposite error+budget<correct error",
        budget, "Independent smooth truncation bound; excludes complete/half-period ambiguities",
        ("Direction is ambiguous at this resolution/time or solution matches neither direction",)
        if status == "inconclusive" else ())
