"""Evaluator-only correct cases that expose legitimate method limitations.

    These groups supplement the original three controls without changing the
    legacy fault corpus, its experiment parameters or its score denominators.
"""

from math import pi

from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification
from .variants import BenchmarkEntry


CHALLENGING_CONTROLS = (
    (BenchmarkEntry("PBB-C04", None, "Correct, visibly diffusive first-order evolution",
                    "Amplitude loss from valid truncation error; no implementation failure"),
     ExperimentCase("dev-probe-01", n_cells=32, cfl=.3, final_time=1.3)),
    (BenchmarkEntry("PBB-C05", None, "Correct low-resolution transport",
                    "Large coarse-grid truncation error within the declared method bound"),
     ExperimentCase("dev-probe-02", n_cells=8)),
    (BenchmarkEntry("PBB-C06", None, "Correct large phase and multi-period translation",
                    "Periodic analytical cell averages remain valid after several crossings"),
     ExperimentCase("dev-probe-03", phase=11*pi+.7, final_time=3.37,
                    physics=PhysicsSpecification(speed=-1.))),
    (BenchmarkEntry("PBB-C07", None, "Correct discontinuous pulse with numerical smearing",
                    "BV accuracy bound applies; smooth refinement/direction assertions do not"),
     ExperimentCase("dev-probe-04", profile="square", n_cells=24, cfl=.4,
                    final_time=.37, phase=5.2, amplitude=.8, offset=0.,
                    physics=PhysicsSpecification(speed=-1.))),
)
