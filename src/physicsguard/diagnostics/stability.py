"""Finite outputs, measured CFL, and conditional endpoint maximum principle."""

from physicsguard.schemas.results import DiagnosticResult, SolverExecutionResult
from ._common import (ASSUMPTIONS, EPS, amplitude_scale, roundoff_tolerance, unavailable)


def stability(run: SolverExecutionResult) -> tuple[DiagnosticResult, ...]:
    finite = DiagnosticResult("finite", "Finite numerical execution", ASSUMPTIONS, True,
                              "pass" if run.status == "success" else (
                                  "fail" if run.error_kind == "nonfinite_output" else "inconclusive"),
                              {"completed": float(run.status == "success")}, {"completed": "1"},
                              "All output values and reported time controls are finite", 0.0,
                              "Finite representable float64 values are required",
                              (run.error,) if run.error else ())
    if run.status != "success":
        return (finite, unavailable("cfl", "Upwind CFL admissibility", run.error or "No execution"),
                unavailable("boundedness", "Endpoint discrete maximum principle", run.error or "No execution"))
    if not run.case.strategy.supports_upwind_checks:
        return (finite, unavailable("cfl", "Upwind CFL admissibility", "Unsupported strategy", applicable=False),
                unavailable("boundedness", "Endpoint discrete maximum principle", "Unsupported strategy", applicable=False))
    cfl = DiagnosticResult("cfl", "Upwind CFL admissibility", ASSUMPTIONS + ("upwind + forward Euler",),
                           True, "pass" if run.max_cfl <= 1 + 16 * EPS else "fail",
                           {"max_cfl": run.max_cfl}, {"max_cfl": "1"}, "max |a|*dt/dx <= 1 + tolerance",
                           16 * EPS, "16 eps64 permits rounded timestep ratios")
    if cfl.status != "pass":
        bounds = unavailable("boundedness", "Endpoint discrete maximum principle",
                             "CFL condition required for the maximum principle is violated", applicable=False)
    else:
        low, high = min(run.initial_averages), max(run.initial_averages)
        end_low, end_high = min(run.final_averages), max(run.final_averages)
        violation = max(0.0, low - end_low, end_high - high)
        tolerance = roundoff_tolerance(run, amplitude_scale(run))
        measurements = {"initial_min": low, "initial_max": high, "final_min": end_low,
                        "final_max": end_high, "bound_violation": violation}
        bounds = DiagnosticResult("boundedness", "Endpoint discrete maximum principle",
                                  ASSUMPTIONS + ("declared monotone upwind/Euler at CFL<=1",), True,
                                  "pass" if violation <= tolerance else "fail", measurements,
                                  {k: run.case.physics.field_unit for k in measurements},
                                  "Final extrema lie within initial extrema plus rounding tolerance", tolerance,
                                  "gamma_k*max absolute field value; only initial/final states are observed")
    return finite, cfl, bounds
