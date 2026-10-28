"""Verifier-owned additional cases. Never supplied to the deterministic proposer.

These public repository definitions are not secret. A future private deployment
must keep verifier assets/parameters outside the investigator's access boundary.
"""
from physicsguard.schemas.repairs import VerificationPlan
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification
from physicsguard.experiments.runner import validate_cases
from dataclasses import asdict
import json

REQUIRED_DIAGNOSTICS = ("finite", "conservation", "accuracy", "direction", "cfl", "boundedness",
                        "refinement", "constant", "translation", "linearity", "space_scaling",
                        "time_scaling", "periodic_wrap")


def case_signature(case):
    values = asdict(case)
    values.pop("case_id")
    values.pop("max_steps")
    # Unit labels are descriptive metadata, not a new numerical experiment.
    for name in ("length_unit", "time_unit", "field_unit"):
        values["physics"].pop(name)
    return json.dumps(values, sort_keys=True, allow_nan=False)


def plan_problem(plan, development_cases, development_report=None):
    """Host contract validation; missing/unsupported evidence is not a pass."""
    if not isinstance(plan, VerificationPlan):
        return "Verification plan must be a typed host-owned record"
    try:
        validate_cases(plan.additional_cases)
    except ValueError as error:
        return f"Verification plan inputs/budget unavailable: {error}"
    if len(set(plan.required_diagnostics)) != len(plan.required_diagnostics) or set(plan.required_diagnostics) != set(REQUIRED_DIAGNOSTICS):
        return "Verification plan must contain exactly the mandatory diagnostic families"
    signatures = [case_signature(c) for c in plan.additional_cases]
    if len(set(signatures)) != len(signatures):
        return "Verification plan repeats a physical experiment under another identifier"
    known = {case_signature(c) for c in development_cases}
    if development_report:
        known.update(case_signature(a.case) for a in development_report.executions if a.case is not None)
    if any(signature in known for signature in signatures):
        return "Verification plan duplicates development experiments"
    cases = plan.additional_cases
    if any(not c.strategy.supports_upwind_checks for c in cases):
        return "Verification plan uses an unsupported numerical strategy"
    moving = [c for c in cases if c.profile == "sine" and c.amplitude != 0 and c.final_time > 0]
    if (len(cases) < 6 or not {"sine", "square", "constant"}.issubset({c.profile for c in cases})
            or not any(c.physics.speed > 0 for c in moving) or not any(c.physics.speed < 0 for c in moving)
            or len({c.n_cells for c in cases}) < 2
            or len({c.physics.x_max-c.physics.x_min for c in cases}) < 2):
        return "Verification plan lacks signed smooth transport, profiles, grids or domain coverage"
    return None


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
