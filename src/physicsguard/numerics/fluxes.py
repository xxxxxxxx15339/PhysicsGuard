"""Consistent upwind flux for scalar advection with constant real velocity."""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import finite_real, real_vector


def upwind_flux(
    left: ArrayLike, right: ArrayLike, *, speed: float
) -> NDArray[np.float64]:
    """Return one shared flux per face: ``a*left`` if a>0, ``a*right`` if a<0.

    Inputs are matching finite one-dimensional interface-state arrays. Flux has
    units of state times length/time. The result owns its memory; inputs are
    unchanged. A nonrepresentable physical flux raises ``FloatingPointError``.
    """
    velocity = finite_real(speed, "speed")
    left_values = real_vector(left, "left")
    right_values = real_vector(right, "right")
    if left_values.shape != right_values.shape:
        raise ValueError("left and right must have matching shapes")
    if velocity == 0.0:
        return np.zeros_like(left_values)
    upstream = left_values if velocity > 0.0 else right_values
    with np.errstate(over="raise", invalid="raise"):
        return velocity * upstream
