"""Input checks shared by numerical routines; no PDE calculations live here."""

from math import isfinite
from numbers import Integral, Real

import numpy as np
from numpy.typing import ArrayLike, NDArray


def finite_real(value: object, name: str) -> float:
    """Accept a finite real scalar, excluding booleans and implicit strings."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be representable as a finite float64") from error
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def positive_integer(value: object, name: str) -> int:
    """Accept a positive integer without silently truncating floats."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be a positive integer")
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def real_vector(
    values: ArrayLike, name: str, *, minimum_size: int = 1
) -> NDArray[np.float64]:
    """Return an owned float64 vector; reject nonfinite or non-real input."""
    try:
        raw = np.asarray(values)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a one-dimensional real numeric array") from error
    if raw.ndim != 1 or raw.size < minimum_size:
        raise ValueError(f"{name} must be one-dimensional with at least {minimum_size} entries")
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} must contain real numeric values")
    try:
        with np.errstate(over="raise", invalid="raise"):
            result = np.array(raw, dtype=np.float64, copy=True)
    except (FloatingPointError, OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be representable as finite float64 values") from error
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result
