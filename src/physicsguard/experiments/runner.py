"""Bounded orchestration of trusted local callables, not a Python sandbox."""

from math import fsum
from fractions import Fraction
from time import perf_counter
from typing import Protocol

import numpy as np

from physicsguard.numerics import AdvectionConfig, AdvectionResult
from physicsguard.numerics._validation import real_vector
from physicsguard.numerics.advection import _time_steps
from physicsguard.schemas.results import ExperimentCase, SolverExecutionResult
from .scenarios import cell_averages


class Solver(Protocol):
    def __call__(self, initial_averages: np.ndarray, config: AdvectionConfig) -> AdvectionResult: ...


MAX_CELLS = 4096
MAX_STEPS = 20_000
MAX_CELL_UPDATES = 2_000_000


class _NonfiniteOutput(ValueError):
    """Confirmed invalid numerical evidence, distinct from an unavailable run."""


def validate_budget(case: ExperimentCase) -> None:
    if not isinstance(case, ExperimentCase):
        raise ValueError("case must be an ExperimentCase")
    if case.n_cells > MAX_CELLS or case.max_steps > MAX_STEPS:
        raise ValueError("experiment exceeds cell/step computation limits")
    steps = _time_steps(case.config())
    if case.n_cells * len(steps) > MAX_CELL_UPDATES:
        raise ValueError("experiment exceeds cell-update computation limit")
    case.config().cell_edges()


def execute_solver(solver: Solver, solver_id: str, case: ExperimentCase,
                   initial_override=None) -> SolverExecutionResult:
    """Invalid requests raise; candidate failures become explicit execution evidence.

    Work is bounded before invoking our trusted fixtures. No hard wall timeout
    or protection against malicious callables is claimed. Future untrusted
    execution needs a separate resource-limited process/container.
    """
    validate_budget(case)
    if not isinstance(solver_id, str) or not solver_id:
        raise ValueError("solver_id must be nonempty")
    initial = real_vector(cell_averages(case) if initial_override is None else initial_override, "initial")
    if len(initial) != case.n_cells:
        raise ValueError("initial length must match n_cells")
    original = tuple(map(float, initial))
    started = perf_counter()
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            result = solver(initial.copy(), case.config())
        if not isinstance(result, AdvectionResult) or result.config != case.config():
            raise ValueError("candidate returned incompatible result/configuration")
        raw = np.asarray(result.final_averages)
        if raw.dtype.kind in "iuf" and not np.all(np.isfinite(raw)):
            raise _NonfiniteOutput("candidate returned nonfinite final values")
        final = real_vector(raw, "final")
        dt = np.array(result.time_steps, dtype=float, copy=True)
        if not np.all(np.isfinite(dt)):
            raise _NonfiniteOutput("candidate returned nonfinite timesteps")
        if final.size != case.n_cells or dt.ndim != 1:
            raise ValueError("candidate returned incompatible output shape or timesteps")
        if len(dt) > case.max_steps or np.any(dt <= 0):
            raise ValueError("candidate returned invalid timestep count/values")
        if case.physics.speed != 0 and case.final_time > 0:
            if abs(fsum(dt) - case.final_time) > 8 * np.spacing(case.final_time):
                raise ValueError("candidate did not reach requested observation time")
        elif len(dt):
            raise ValueError("stationary case must have no timesteps")
        max_cfl = float(Fraction(abs(case.physics.speed)) * Fraction(float(max(dt, default=0.)))
                        / Fraction(case.config().dx))
        if not np.isfinite(max_cfl):
            raise ValueError("candidate returned nonfinite CFL")
        return SolverExecutionResult(solver_id, case, "success", perf_counter() - started,
                                     original, tuple(map(float, final)), tuple(map(float, dt)), max_cfl)
    except Exception as error:
        # No traceback, source path, or benchmark metadata is returned.
        return SolverExecutionResult(solver_id, case, "error", perf_counter() - started,
                                     original, error=f"{type(error).__name__}: {error}",
                                     error_kind="nonfinite_output" if isinstance(error, _NonfiniteOutput)
                                     else "execution_error")
