"""Empirical first-order behavior on compatible resolved smooth experiments."""

from math import log

from physicsguard.experiments.scenarios import cell_averages
from physicsguard.schemas.results import DiagnosticResult, SolverExecutionResult
from ._common import ASSUMPTIONS, amplitude_scale, norm_errors, roundoff_tolerance, unavailable
from .accuracy import matches_reference_initial


def grid_refinement(runs: tuple[SolverExecutionResult, ...]) -> DiagnosticResult:
    if len(runs) < 3 or any(r.status != "success" for r in runs):
        return unavailable("refinement", "Observed smooth-grid convergence",
                           "Need three successful compatible resolutions")
    if any(not matches_reference_initial(run) for run in runs):
        return unavailable("refinement", "Observed smooth-grid convergence",
                           "Initial data do not match the declared analytical profile", applicable=False)
    first = runs[0].case
    signature = lambda c: (c.physics, c.strategy, c.cfl, c.final_time, c.profile,
                            c.offset, c.amplitude, c.mode, c.phase)
    widths = [r.case.config().dx for r in runs]
    compatible = (all(signature(r.case) == signature(first) for r in runs)
                  and all(widths[i] > widths[i+1] for i in range(len(widths)-1)))
    resolved = all(r.case.n_cells >= 32 * r.case.mode for r in runs)
    travel = abs(first.physics.speed) * first.final_time / (first.physics.x_max - first.physics.x_min)
    if (not compatible or not resolved or first.profile != "sine" or first.amplitude == 0
            or not first.strategy.supports_upwind_checks or not 0.1 <= first.cfl <= 0.9
            or not 0.05 <= travel <= 0.5):
        return unavailable("refinement", "Observed smooth-grid convergence",
                           "Requires resolved nonconstant sine, fixed CFL in [.1,.9], travel in [.05,.5], "
                           "same physics/profile/time and decreasing dx", applicable=False)
    errors = [norm_errors(r.final_averages, cell_averages(r.case, r.case.final_time),
                          r.case.config().dx)["L1"] for r in runs]
    if any(e <= 100 * roundoff_tolerance(r, amplitude_scale(r)) *
           (r.case.physics.x_max - r.case.physics.x_min) for e, r in zip(errors, runs)):
        return unavailable("refinement", "Observed smooth-grid convergence",
                           "Errors are too close to rounding floor to estimate order")
    orders = [log(errors[i] / errors[i+1]) / log(widths[i] / widths[i+1])
              for i in range(len(errors)-1)]
    passed = all(0.7 <= order <= 1.3 for order in orders)
    return DiagnosticResult("refinement", "Observed smooth-grid convergence", ASSUMPTIONS + (
        "resolved smooth sine, fixed CFL away from 1, same physical time",), True,
        "pass" if passed else "fail", {"L1_errors": errors, "observed_orders": orders, "dx": widths},
        {"L1_errors": f"{first.physics.field_unit}*{first.physics.length_unit}",
         "observed_orders": "1", "dx": first.physics.length_unit},
        "Each log(error_coarse/error_fine)/log(dx_coarse/dx_fine) lies in [0.7,1.3]", 0.3,
        "Qualitative first-order envelope 1 +/- 0.3 for resolved sine data; empirical, not a theorem "
        "for arbitrary grids/times/profiles")
