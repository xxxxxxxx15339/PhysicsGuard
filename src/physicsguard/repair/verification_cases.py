"""Verifier-owned additional cases. Never supplied to the deterministic proposer.

These public repository definitions are not secret. A future private deployment
must keep verifier assets/parameters outside the investigator's access boundary.
"""
from physicsguard.schemas.repairs import VerificationPlan
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification

REQUIRED_DIAGNOSTICS = ("finite", "conservation", "accuracy", "direction", "cfl", "boundedness",
                        "refinement", "constant", "translation", "linearity", "space_scaling",
                        "time_scaling", "periodic_wrap")


def independent_plan() -> VerificationPlan:
    cases = (
        ExperimentCase("verify-01", n_cells=96, cfl=.67, final_time=.19*1.7/1.3, phase=1.1,
                       physics=PhysicsSpecification(speed=1.3, x_min=-.2, x_max=1.5)),
        ExperimentCase("verify-02", n_cells=80, cfl=.72, final_time=.21*1.1/.9, phase=2.4,
                       physics=PhysicsSpecification(speed=-.9, x_min=.3, x_max=1.4)),
        ExperimentCase("verify-03", n_cells=96, cfl=.75, final_time=.125/.7, mode=2, phase=.9,
                       physics=PhysicsSpecification(speed=.7)),
        ExperimentCase("verify-04", n_cells=72, profile="square", cfl=.8, final_time=.37,
                       phase=5.6, offset=.4, amplitude=.5),
        ExperimentCase("verify-05", n_cells=96, profile="square", cfl=.73, final_time=.19,
                       phase=.3, offset=.1, amplitude=.8, physics=PhysicsSpecification(speed=-1.)),
        ExperimentCase("verify-06", n_cells=37, profile="constant", final_time=.4, offset=-2.,
                       physics=PhysicsSpecification(speed=0.)),
    )
    return VerificationPlan("advection-source-verification-v1", cases, REQUIRED_DIAGNOSTICS)
