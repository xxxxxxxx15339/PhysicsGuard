"""Numerical tolerances and unavailable-evidence records; no solver oracle."""

from math import fsum

import numpy as np

from physicsguard.schemas.results import DiagnosticResult, SolverExecutionResult

EPS = float(np.finfo(float).eps)
ASSUMPTIONS = ("source-free constant-speed scalar advection", "periodic uniform finite-volume cell averages")


def roundoff_tolerance(run: SolverExecutionResult, scale: float) -> float:
    """Conservative operation-count envelope, not a statistical confidence bound.

    32 operations per step plus 2N reduction terms; gamma_k=k*eps/(1-k*eps).
    Scale uses absolute data rather than net mass, so cancellation is safe.
    Runner limits keep k*eps far below one. Zero data has exact zero tolerance.
    """
    k = 32 * (len(run.time_steps) + 1) + 2 * run.case.n_cells
    return k * EPS / (1 - k * EPS) * scale


def amplitude_scale(run: SolverExecutionResult) -> float:
    return max((abs(v) for v in (*run.initial_averages, *run.final_averages)), default=0.0)


def norm_errors(values, reference, dx: float) -> dict[str, float]:
    """Absolute domain-integrated L1/L2 and unscaled Linf; robust L2 scaling."""
    error = np.abs(np.asarray(values) - np.asarray(reference))
    maximum = float(max(error, default=0.0))
    return {"L1": dx * fsum(map(float, error)),
            "L2": maximum * float(np.sqrt(dx * np.sum((error / maximum)**2))) if maximum else 0.0,
            "Linf": maximum}


def unavailable(identifier: str, description: str, reason: str, *, applicable: bool = True) -> DiagnosticResult:
    return DiagnosticResult(identifier, description, ASSUMPTIONS, applicable, "inconclusive", {}, {},
                            "Sufficient valid numerical evidence is required", None,
                            "No acceptance tolerance can be applied without the required evidence", (reason,))


def execution_issue(run: SolverExecutionResult, identifier: str, description: str):
    if run.status != "success":
        return unavailable(identifier, description, run.error or "execution evidence unavailable")
    return None


def measure_safely(identifier: str, description: str, computation) -> DiagnosticResult:
    """Retain unavailable arithmetic as evidence rather than aborting a suite."""
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            result = computation()
        result.to_json()  # Also rejects Python arithmetic that produced Inf.
        return result
    except (ArithmeticError, ValueError) as error:
        return unavailable(identifier, description, f"Diagnostic arithmetic unavailable: {error}")
