"""Controlled, trusted fault fixtures. Ground truth stays in the evaluator package.

    These are independently written mutations, not copied external solvers.
    Reuse only the trusted timestep scheduler/data contract, never alter the
    Milestone 1 production implementation to manufacture a benchmark failure.
"""

from dataclasses import dataclass
from math import exp

import numpy as np

from physicsguard.numerics import AdvectionResult, solve_advection
from physicsguard.numerics.advection import _time_steps


def faulty_solver(initial, config, fault):
    values = np.array(initial, dtype=float, copy=True)
    steps = _time_steps(config)
    for dt in steps:
        s = 1 if config.speed > 0 else -1
        c = abs(config.speed) * float(dt) / config.dx
        neighbor = np.roll(values, s)
        if fault == "direction":
            advanced = values - c * (values - np.roll(values, -s))
        elif fault == "update_sign":
            advanced = values + c * (values - neighbor)
        elif fault == "periodic_index":
            neighbor[0 if s > 0 else -1] = values[0 if s > 0 else -1]
            advanced = values - c * (values - neighbor)
        elif fault == "mass_loss":
            advanced = (values - c * (values - neighbor)) * exp(-0.4 * float(dt))
        elif fault == "dt_scaling":
            # Missing division by dx: effective velocity becomes a*dx.
            advanced = values - c * config.dx * (values - neighbor)
        elif fault == "downwind_state":
            advanced = values - c * (np.roll(values, -s) - values)
        else:
            raise ValueError("unknown fixture")
        values = advanced
        if not np.all(np.isfinite(values)):
            raise FloatingPointError("nonfinite candidate output")
    edges = config.cell_edges()
    arrays = (edges, edges[:-1] + np.diff(edges)/2, np.array(initial, dtype=float), values, steps)
    for array in arrays:
        array.setflags(write=False)
    return AdvectionResult(config, *arrays)


@dataclass(frozen=True)
class BenchmarkEntry:
    benchmark_id: str
    fault_type: str | None
    injected_fault: str
    expected_behavior: str

    def solver(self, initial, config):
        if self.fault_type is None:
            return solve_advection(initial, config)
        return faulty_solver(initial, config, self.fault_type)


ENTRIES = (
    BenchmarkEntry("PBB-F01", "direction", "Reverse velocity while retaining stable upwinding",
                   "Mass-conserving bounded transport against physical velocity"),
    BenchmarkEntry("PBB-F02", "update_sign", "Add the upstream flux difference instead of subtracting",
                   "Conservative anti-diffusion, reversed phase and growth"),
    BenchmarkEntry("PBB-F03", "periodic_index", "Clamp upstream seam index to self",
                   "Seam-dependent mass error; broken cyclic equivariance"),
    BenchmarkEntry("PBB-F04", "mass_loss", "Apply exp(-0.4*dt) damping in a source-free equation",
                   "Mass and constants decay; introduces an unphysical source"),
    BenchmarkEntry("PBB-F05", "dt_scaling", "Omit division by cell width in the update",
                   "Conservative but wrong speed a*dx; inconsistent scaling/refinement"),
    BenchmarkEntry("PBB-F06", "downwind_state", "Choose the downstream face state",
                   "Conservative anti-diffusion with physical phase direction"),
    BenchmarkEntry("PBB-C01", None, "No fault; positive-velocity control", "Correct first-order transport"),
    BenchmarkEntry("PBB-C02", None, "No fault; negative-velocity control", "Correct signed transport"),
    BenchmarkEntry("PBB-C03", None, "No fault; rescaled-domain control", "Correct physical scaling"),
)
