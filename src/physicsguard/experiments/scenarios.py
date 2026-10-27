"""Deterministic scenarios and analytic integrals, independent of candidate code."""

from dataclasses import replace

import numpy as np

from physicsguard.numerics import sine_cell_averages
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification

REFINEMENT_CELLS = (64, 128, 256)


def cell_averages(case: ExperimentCase, time: float = 0.0, *, reverse: bool = False) -> np.ndarray:
    edges = case.config().cell_edges()
    velocity = case.physics.speed * (-1 if reverse else 1)
    if case.profile == "constant":
        return np.full(case.n_cells, case.offset)
    if case.profile == "sine":
        return sine_cell_averages(edges, time=time, speed=velocity, offset=case.offset,
                                  amplitude=case.amplitude, mode=case.mode, phase=case.phase)
    # Analytic integral of a periodic indicator on fractional coordinates [0,.3).
    # floor(z)*.3 + min(frac(z),.3) is its continuous primitive across wraps.
    length = case.physics.x_max - case.physics.x_min
    z = (edges - case.physics.x_min - velocity * time) / length - case.phase / (2 * np.pi)
    primitive = np.floor(z) * 0.3 + np.minimum(z - np.floor(z), 0.3)
    return case.offset + case.amplitude * np.diff(primitive) * case.n_cells


def development_cases() -> tuple[ExperimentCase, ...]:
    """Off-period observation times and multiple profiles/signs; no fault labels."""
    return tuple(ExperimentCase(
        case_id=f"dev-{profile}-m{mode}-{sign:+d}", profile=profile, mode=mode,
        physics=PhysicsSpecification(speed=float(sign)),
        final_time=0.125 if mode == 2 else 0.23,
        phase=5.2 if profile == "square" else 0.37,
    ) for profile, mode in (("sine", 1), ("sine", 2), ("square", 1))
        for sign in (1, -1))


def refinement_cases(case: ExperimentCase) -> tuple[ExperimentCase, ...]:
    return tuple(replace(case, case_id=f"{case.case_id}-n{n}", n_cells=n)
                 for n in REFINEMENT_CELLS)
