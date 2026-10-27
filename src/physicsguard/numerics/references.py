"""Analytical finite-volume references, independent of numerical fluxes/updates.

These are exact source-free travelling waves, not a general forced manufactured
solution interface. Only elementary input validation is shared with the solver.
"""

from math import isfinite, tau

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import finite_real, positive_integer, real_vector


def sine_cell_averages(
    edges: ArrayLike,
    *,
    time: float = 0.0,
    speed: float = 1.0,
    offset: float = 1.0,
    amplitude: float = 0.2,
    mode: int = 1,
    phase: float = 0.0,
) -> NDArray[np.float64]:
    """Average ``offset + amplitude*sin(k*(x-x_min-speed*time)+phase)``.

    ``k=2*pi*mode/L`` with positive integer mode and ``L=edges[-1]-edges[0]``.
    Phase is in radians, x/speed/time use consistent length/time units. Edges
    may be nonuniform but must be finite and strictly increasing. Analytic
    integration introduces the factor sin(k*dx/2)/(k*dx/2), implemented with
    NumPy's normalized sinc. No quadrature or solver-derived reference is used.
    """
    coordinates = real_vector(edges, "edges", minimum_size=2)
    duration = finite_real(time, "time")
    velocity = finite_real(speed, "speed")
    background = finite_real(offset, "offset")
    height = finite_real(amplitude, "amplitude")
    angle = finite_real(phase, "phase")
    wave_mode = positive_integer(mode, "mode")
    if duration < 0.0:
        raise ValueError("time must be nonnegative")
    length = float(coordinates[-1]) - float(coordinates[0])
    if not isfinite(length) or length <= 0.0:
        raise ValueError("edges must span a finite positive domain")
    widths = np.diff(coordinates)
    if not np.all(widths > 0.0):
        raise ValueError("edges must be strictly increasing")
    travel = velocity * duration
    if not isfinite(travel):
        raise ValueError("speed*time must be representable for the reference phase")
    frequency = finite_real(wave_mode, "mode")
    centers = coordinates[:-1] + 0.5 * widths
    shift = travel % length
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        cell_phase = tau * frequency * ((centers - coordinates[0] - shift) / length) + angle
        result = background + height * np.sinc(frequency * (widths / length)) * np.sin(cell_phase)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("analytical reference produced nonfinite values")
    return result
