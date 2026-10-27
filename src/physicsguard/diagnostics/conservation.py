"""Discrete mass balance for the supported source-free periodic PDE."""

from math import fsum

from physicsguard.schemas.results import DiagnosticResult, SolverExecutionResult
from ._common import ASSUMPTIONS, execution_issue, roundoff_tolerance


def conservation(run: SolverExecutionResult) -> DiagnosticResult:
    if issue := execution_issue(run, "conservation", "Discrete mass conservation"):
        return issue
    dx = run.case.config().dx
    initial = dx * fsum(run.initial_averages)
    final = dx * fsum(run.final_averages)
    drift = abs(final - initial)
    scale = dx * max(fsum(abs(x) for x in run.initial_averages),
                     fsum(abs(x) for x in run.final_averages))
    tolerance = roundoff_tolerance(run, scale)
    unit = f"{run.case.physics.field_unit}*{run.case.physics.length_unit}"
    return DiagnosticResult("conservation", "Discrete mass conservation", ASSUMPTIONS, True,
                            "pass" if drift <= tolerance else "fail",
                            {"initial_mass": initial, "final_mass": final, "absolute_drift": drift,
                             "normalization_scale": scale,
                             "normalized_drift": drift / scale if scale else 0.0},
                            {"initial_mass": unit, "final_mass": unit, "absolute_drift": unit,
                             "normalization_scale": unit, "normalized_drift": "1"},
                            "abs(M_final-M_initial) <= tolerance; M=dx*fsum(cell averages)", tolerance,
                            "gamma_k times max initial/final absolute mass; k=32*(steps+1)+2*N; "
                            "allows accumulated update and reduction rounding without net-mass cancellation")
