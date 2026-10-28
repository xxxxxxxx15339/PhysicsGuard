"""New correct control: explicit face fluxes rather than an upstream difference."""
import numpy as np
from physicsguard.numerics import AdvectionResult
from physicsguard.numerics._validation import real_vector
from physicsguard.numerics.advection import _time_steps


def solve_advection(initial_averages, config):
    initial = real_vector(initial_averages, "initial").copy()
    if len(initial) != config.n_cells:
        raise ValueError("cell count mismatch")
    state = initial.copy()
    schedule = _time_steps(config)
    for dt in schedule:
        # Face j is the right face of cell j; adjacent fluxes telescope.
        right = config.speed * (state if config.speed >= 0 else np.roll(state, -1))
        left = np.concatenate((right[-1:], right[:-1]))
        state = state - (float(dt) / config.dx) * (right - left)
    edges = config.cell_edges()
    centers = edges[:-1] + np.diff(edges) / 2
    for array in (initial, state, schedule, edges, centers):
        array.setflags(write=False)
    return AdvectionResult(config, edges, centers, initial, state, schedule)
