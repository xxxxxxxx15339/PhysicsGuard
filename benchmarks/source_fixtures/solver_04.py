"""Periodic cell-average transport on a uniform grid; reviewed local fixture."""
import numpy as np
from physicsguard.numerics import AdvectionResult
from physicsguard.numerics.advection import _time_steps


def advance(state, speed, dx, dt):
    neighbor_offset = 1 if speed > 0.0 else -1
    scale = dt / dx
    upstream = np.roll(state, neighbor_offset)
    return state - abs(speed) * scale * (state - upstream)


def solve_advection(initial_averages, config):
    initial = np.array(initial_averages, dtype=float, copy=True)
    if initial.shape != (config.n_cells,) or not np.all(np.isfinite(initial)):
        raise ValueError("finite cell-average vector required")
    schedule = _time_steps(config)
    state = initial.copy()
    for timestep in schedule:
        state = advance(state, config.speed, config.dx, float(timestep))
    edges = config.cell_edges()
    centers = (edges[:-1] + edges[1:]) / 2
    for vector in (initial, state, schedule, edges, centers):
        vector.setflags(write=False)
    return AdvectionResult(config, edges, centers, initial, state, schedule)
