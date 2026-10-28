"""New correct control: convex cell mixing with explicit periodic concatenation."""
import numpy as np
from physicsguard.numerics import AdvectionResult
from physicsguard.numerics._validation import real_vector
from physicsguard.numerics.advection import _time_steps


def solve_advection(initial_averages, config):
    initial = real_vector(initial_averages, "initial").copy()
    if initial.shape != (config.n_cells,):
        raise ValueError("cell count mismatch")
    values = initial.copy()
    times = _time_steps(config)
    for dt in times:
        fraction = abs(config.speed) * (float(dt) / config.dx)
        if config.speed >= 0:
            adjacent = np.concatenate((values[-1:], values[:-1]))
        else:
            adjacent = np.concatenate((values[1:], values[:1]))
        values = (1.0 - fraction) * values + fraction * adjacent
    edges = config.cell_edges()
    centers = edges[:-1] + np.diff(edges) / 2
    for array in (initial, values, times, edges, centers):
        array.setflags(write=False)
    return AdvectionResult(config, edges, centers, initial, values, times)
