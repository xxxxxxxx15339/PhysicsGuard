"""Deterministic finite-volume advection and analytical cell-average references."""

from .advection import AdvectionConfig, AdvectionResult, solve_advection, step_upwind
from .fluxes import upwind_flux
from .references import sine_cell_averages

__all__ = [
    "AdvectionConfig",
    "AdvectionResult",
    "sine_cell_averages",
    "solve_advection",
    "step_upwind",
    "upwind_flux",
]
