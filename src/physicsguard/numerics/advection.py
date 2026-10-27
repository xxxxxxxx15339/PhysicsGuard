"""Uniform finite-volume advection with periodic boundaries and forward Euler.

The state contains cell averages, not samples at cell centers. There are no
sources. A shared face flux makes the update conservative; upwind + Euler is
monotone/TVD when |a|*dt/dx <= 1. These claims are specific to this scheme.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import finite_real, positive_integer, real_vector
from .fluxes import upwind_flux


@dataclass(frozen=True, slots=True)
class AdvectionConfig:
    """Numerical controls in consistent length/time units.

    ``speed`` has units length/time, ``final_time`` has units time, and ``cfl``
    is dimensionless. A single periodic cell is allowed. Both spatial and time
    quantities must be representable in float64. ``max_steps`` bounds work
    before integration starts; it is not a scientific acceptance criterion.
    """

    n_cells: int = 128
    speed: float = 1.0
    x_min: float = 0.0
    x_max: float = 1.0
    cfl: float = 0.8
    final_time: float = 1.0
    max_steps: int = 1_000_000

    def __post_init__(self) -> None:
        for name in ("n_cells", "max_steps"):
            object.__setattr__(self, name, positive_integer(getattr(self, name), name))
        for name in ("speed", "x_min", "x_max", "cfl", "final_time"):
            object.__setattr__(self, name, finite_real(getattr(self, name), name))
        if self.x_max <= self.x_min:
            raise ValueError("x_max must exceed x_min")
        if not isfinite(self.x_max - self.x_min) or self.dx <= 0.0:
            raise ValueError("domain length and dx must be finite and representable")
        if not 0.0 < self.cfl <= 1.0:
            raise ValueError("cfl must satisfy 0 < cfl <= 1 for upwind + forward Euler")
        if self.final_time < 0.0:
            raise ValueError("final_time must be nonnegative")

    @property
    def dx(self) -> float:
        """Uniform cell width."""
        return (self.x_max - self.x_min) / self.n_cells

    def cell_edges(self) -> NDArray[np.float64]:
        """Return N+1 edges, rejecting an unresolvable spatial grid."""
        edges = np.linspace(self.x_min, self.x_max, self.n_cells + 1, dtype=np.float64)
        if not np.all(np.isfinite(edges)) or not np.all(np.diff(edges) > 0.0):
            raise ValueError("cell edges are not distinct finite float64 coordinates")
        return edges


@dataclass(frozen=True, slots=True)
class AdvectionResult:
    """Completed run with owned arrays marked read-only by the solver.

    Only the initial/final fields and actual timesteps are stored, not a full
    space-time history. Read-only array flags prevent accidental edits; this
    record is not an execution/security boundary.
    """

    config: AdvectionConfig
    cell_edges: NDArray[np.float64]
    cell_centers: NDArray[np.float64]
    initial_averages: NDArray[np.float64]
    final_averages: NDArray[np.float64]
    time_steps: NDArray[np.float64]

    @property
    def final_time(self) -> float:
        """Requested time reached by this completed run."""
        return self.config.final_time

    @property
    def n_steps(self) -> int:
        return int(self.time_steps.size)

    @property
    def max_cfl(self) -> float:
        """Largest measured |a|*dt/dx; zero for stationary/no-step runs."""
        return float(np.max(abs(self.config.speed) * self.time_steps / self.config.dx, initial=0.0))


def step_upwind(
    averages: ArrayLike, *, speed: float, dx: float, dt: float
) -> NDArray[np.float64]:
    """Advance periodic cell averages once using the conservative flux difference.

    No ghost cells or duplicated periodic endpoint belong in ``averages``.
    ``dt=0`` and ``speed=0`` return independent unchanged arrays. Positive dt
    must satisfy the upwind/Euler CFL limit. No clipping or filtering is used.
    Nonrepresentable flux/update arithmetic raises ``FloatingPointError``.
    """
    values = real_vector(averages, "averages")
    velocity = finite_real(speed, "speed")
    width = finite_real(dx, "dx")
    timestep = finite_real(dt, "dt")
    if width <= 0.0:
        raise ValueError("dx must be positive")
    if timestep < 0.0:
        raise ValueError("dt must be nonnegative")
    if velocity == 0.0 or timestep == 0.0:
        return values
    # Compare timesteps directly so an inadmissible dt is not hidden by a
    # rounded product |a|*dt/dx. The final ratio may differ by an ulp from 1.
    if timestep > width / abs(velocity):
        raise ValueError("dt violates the CFL limit |speed|*dt/dx <= 1")
    faces = upwind_flux(values, np.roll(values, -1), speed=velocity)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        advanced = values - (timestep / width) * (faces - np.roll(faces, 1))
    if not np.all(np.isfinite(advanced)):
        raise FloatingPointError("advection update produced nonfinite values")
    return advanced


def _time_steps(config: AdvectionConfig) -> NDArray[np.float64]:
    if config.speed == 0.0 or config.final_time == 0.0:
        return np.empty(0, dtype=np.float64)
    nominal = (config.cfl * config.dx) / abs(config.speed)
    if nominal == 0.0:
        raise ValueError("CFL timestep is not representable; rescale the problem")
    if not isfinite(nominal):
        # The admissible timestep exceeds finite float64 time. The requested
        # finite duration can therefore be taken as a single step.
        return np.array([config.final_time], dtype=np.float64)
    # Exact arithmetic on the supplied binary floats avoids accumulated clock
    # drift, a spurious tiny last step, and inaccurate preflight step budgets.
    full_steps, remainder = divmod(Fraction(config.final_time), Fraction(nominal))
    count = int(full_steps) + bool(remainder)
    if count > config.max_steps:
        raise ValueError(f"run requires {count} steps, exceeding max_steps={config.max_steps}")
    steps = np.full(count, nominal, dtype=np.float64)
    if remainder:
        steps[-1] = float(remainder)
    return steps


def solve_advection(
    initial_averages: ArrayLike, config: AdvectionConfig
) -> AdvectionResult:
    """Solve source-free periodic advection through ``config.final_time``.

    Uses float64 and fixed nominal CFL steps plus a shortened last step when
    required. Inputs are copied. No random state, I/O, LLM or diagnostic engine
    participates in this calculation. Invalid configurations raise ValueError;
    nonrepresentable arithmetic raises FloatingPointError, never fake success.
    """
    if not isinstance(config, AdvectionConfig):
        raise ValueError("config must be an AdvectionConfig")
    initial = real_vector(initial_averages, "initial_averages")
    if initial.size != config.n_cells:
        raise ValueError("initial_averages length must match n_cells")
    steps = _time_steps(config)
    edges = config.cell_edges()
    centers = edges[:-1] + 0.5 * np.diff(edges)
    final = initial.copy()
    for dt in steps:
        final = step_upwind(final, speed=config.speed, dx=config.dx, dt=float(dt))
    for array in (edges, centers, initial, final, steps):
        array.setflags(write=False)
    return AdvectionResult(config, edges, centers, initial, final, steps)
