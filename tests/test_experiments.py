"""Explicit invalid inputs, resource budgets and candidate contract failures."""

from dataclasses import replace
from fractions import Fraction
import json

import numpy as np
import pytest

from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.diagnostics.stability import stability
from physicsguard.experiments.runner import execute_generated, execute_solver
from physicsguard.numerics import AdvectionConfig, solve_advection
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification


@pytest.mark.parametrize("kwargs", [dict(n_cells=0), dict(n_cells=True), dict(n_cells=3.2),
    dict(cfl=1.1), dict(final_time=-1), dict(mode=0), dict(mode=True), dict(phase=np.nan),
    dict(offset=np.inf), dict(profile="unknown"), dict(case_id=""), dict(physics={})])
def test_invalid_cases_fail_explicitly(kwargs):
    with pytest.raises(ValueError):
        ExperimentCase(**({"case_id": "invalid"} | kwargs))


@pytest.mark.parametrize("kwargs", [dict(boundary="outflow"), dict(source_free=False),
                                    dict(source_free=1), dict(state="point_samples"), dict(speed=np.nan)])
def test_unsupported_physics_fails_explicitly(kwargs):
    with pytest.raises(ValueError):
        PhysicsSpecification(**kwargs)


@pytest.mark.parametrize("kwargs", [dict(n_cells=4097), dict(max_steps=20001), dict(max_steps=1),
                                    dict(n_cells=4096, final_time=1.)])
def test_compute_limits_apply_before_candidate_invocation(kwargs):
    def must_not_run(*args):
        pytest.fail("candidate called before request validation")
    with pytest.raises(ValueError):
        execute_solver(must_not_run, "anonymous", ExperimentCase("limit", **kwargs))


@pytest.mark.parametrize("initial", [[1., 2.], [np.nan]*64, [True]*64])
def test_invalid_override_is_a_request_error(initial):
    with pytest.raises(ValueError):
        execute_solver(solve_advection, "anonymous", ExperimentCase("override"), initial)


@pytest.mark.parametrize("failure", [RuntimeError("controlled failure"), FloatingPointError("overflow")])
def test_execution_errors_become_serializable_inconclusive_evidence(failure):
    def broken(*args):
        raise failure
    result = execute_solver(broken, "anonymous", ExperimentCase("failure"))
    assert result.status == "error"
    assert type(failure).__name__ in result.error
    assert "Traceback" not in result.error
    assert json.loads(result.to_json())["final_averages"] == []
    report = diagnose_solver(broken, "anonymous", (ExperimentCase("failure"),))
    assert not report.detected
    assert report.inconclusive_count == len(report.diagnostics)
    linearity = next(d for d in report.diagnostics if d.diagnostic_id == "linearity")
    assert all(any(case_id in error for error in linearity.evidence_errors) for case_id in linearity.case_ids)


@pytest.mark.parametrize("change", ["shape", "nan", "time", "config", "type", "dt_shape", "negative_dt"])
def test_candidate_output_contract_is_checked(change):
    def malformed(initial, config):
        run = solve_advection(initial, config)
        if change == "shape":
            return replace(run, final_averages=np.zeros(3))
        if change == "nan":
            return replace(run, final_averages=np.full(config.n_cells, np.nan))
        if change == "time":
            return replace(run, time_steps=np.array([.1]))
        if change == "config":
            return replace(run, config=replace(config, speed=2.))
        if change == "dt_shape":
            return replace(run, time_steps=np.array([[.23]]))
        if change == "negative_dt":
            return replace(run, time_steps=np.array([-.23]))
        return None
    result = execute_solver(malformed, "anonymous", ExperimentCase("malformed"))
    assert result.status == "error"
    if change == "nan":
        assert result.error_kind == "nonfinite_output"
        assert stability(result)[0].status == "fail"


def test_suite_requires_nonempty_bounded_unique_cases():
    case = ExperimentCase("same")
    for cases in (None, (), ({},), (case, case), tuple(replace(case, case_id=str(i)) for i in range(17))):
        with pytest.raises(ValueError):
            diagnose_solver(solve_advection, "anonymous", cases)


def test_generated_refinement_budget_preserves_valid_measurements():
    calls = []
    def observed(initial, config):
        calls.append(config)
        return solve_advection(initial, config)
    case = ExperimentCase("budget", n_cells=32, final_time=1., max_steps=100)
    report = diagnose_solver(observed, "anonymous", (case,))
    attempts = {a.case_id: a for a in report.executions}
    assert len(attempts["budget"].time_steps) == 40
    assert attempts["budget-n64"].status == "success"
    for n in (128, 256):
        attempt = attempts[f"budget-n{n}"]
        assert attempt.status == "unavailable"
        assert attempt.error_kind == "generated_validation_error"
        assert "exceeding max_steps=100" in attempt.error
        assert attempt.case.max_steps == 100
        assert not any(config.n_cells == n for config in calls)
    basic = [d for d in report.diagnostics if d.case_ids == (case.case_id,)]
    assert next(d for d in basic if d.diagnostic_id == "conservation").status == "pass"
    refinement = next(d for d in report.diagnostics if d.diagnostic_id == "refinement")
    assert refinement.status == "inconclusive"
    assert {"budget-n128", "budget-n256"}.issubset(refinement.case_ids)
    assert all(any(identifier in error for error in refinement.evidence_errors)
               for identifier in ("budget-n128", "budget-n256"))
    assert next(d for d in report.diagnostics if d.diagnostic_id == "constant").status == "pass"
    assert not report.detected
    json.loads(report.to_json())


def test_generated_metamorphic_step_budget_does_not_abort_other_checks():
    # Moving [0,.1) to [2,2.3) changes the represented length slightly. The
    # scaled nominal dt falls below T; two steps are needed instead of one.
    case = ExperimentCase("meta-budget", n_cells=32, physics=PhysicsSpecification(x_max=.1),
                          final_time=.0025, max_steps=1)
    report = diagnose_solver(solve_advection, "anonymous", (case,))
    attempt = next(a for a in report.executions if a.case_id == "meta-budget-space-scale")
    assert attempt.status == "unavailable"
    assert "2 steps, exceeding max_steps=1" in attempt.error
    checks = {d.diagnostic_id: d for d in report.diagnostics}
    assert checks["space_scaling"].status == "inconclusive"
    assert "meta-budget-space-scale" in checks["space_scaling"].evidence_errors[0]
    assert checks["time_scaling"].status == "pass"
    assert checks["periodic_wrap"].status == "pass"
    assert not report.detected
    json.loads(report.to_json())


@pytest.mark.parametrize("case,unavailable_id", [
    (ExperimentCase("construction", physics=PhysicsSpecification(speed=0.), final_time=1e308),
     "construction-time-scale"),
    (ExperimentCase("grid", n_cells=32, physics=PhysicsSpecification(speed=1e-15, x_max=1e-15)),
     "grid-space-scale"),
])
def test_unrepresentable_generated_controls_are_structured(case, unavailable_id):
    report = diagnose_solver(solve_advection, "anonymous", (case,))
    attempt = next(a for a in report.executions if a.case_id == unavailable_id)
    assert attempt.status == "unavailable"
    assert attempt.error_kind == "generated_validation_error"
    assert attempt.error
    assert any(d.status == "inconclusive" and unavailable_id in d.case_ids for d in report.diagnostics)
    assert next(d for d in report.diagnostics if d.diagnostic_id == "constant").status == "pass"
    assert not report.detected
    json.loads(report.to_json())


def test_all_caller_cases_are_validated_before_any_solver_execution():
    def must_not_run(*args):
        pytest.fail("invalid caller input reached the solver")
    valid = ExperimentCase("valid", n_cells=32)
    invalid = replace(valid, case_id="invalid", final_time=1., max_steps=1)
    with pytest.raises(ValueError, match="max_steps=1"):
        diagnose_solver(must_not_run, "anonymous", (valid, invalid))


def test_generated_execution_errors_are_distinct_from_infeasible_requests():
    def broken(*args):
        raise RuntimeError("solver failed")
    case = ExperimentCase("generated")
    result = execute_generated(broken, "anonymous", "generated-error", lambda: case)
    assert result.status == "error"
    assert result.error_kind == "execution_error"
    assert stability(result)[0].status == "inconclusive"
    json.loads(result.to_json())


def test_generated_nonfinite_output_is_a_scientific_failure():
    def nonfinite(initial, config):
        return replace(solve_advection(initial, config), final_averages=np.full(config.n_cells, np.inf))
    case = ExperimentCase("generated")
    result = execute_generated(nonfinite, "anonymous", "generated-nonfinite", lambda: case)
    assert result.status == "error"
    assert result.error_kind == "nonfinite_output"
    assert stability(result)[0].status == "fail"
    json.loads(result.to_json())


def test_diagnostic_arithmetic_overflow_does_not_abort_a_benchmark_run():
    def extreme_output(initial, config):
        return replace(solve_advection(initial, config), final_averages=np.full(config.n_cells, 1e308))
    report = diagnose_solver(extreme_output, "anonymous", (ExperimentCase("extreme"),))
    assert report.detected  # The endpoint maximum-principle violation is finite.
    assert any("arithmetic unavailable" in error for d in report.diagnostics for error in d.evidence_errors)
    json.loads(report.to_json())  # No NaN/Inf leaks into machine-readable output.


@pytest.mark.parametrize("speed, width, duration", [(1e-310, 1e-310, .5),
    (1e-300, 1e-300, 1e-100), (1e308, 1e308, 10.)])
def test_max_cfl_avoids_intermediate_underflow_and_overflow(speed, width, duration):
    config = AdvectionConfig(n_cells=1, speed=speed, x_max=width, final_time=duration)
    result = solve_advection([1.], config)
    expected = float(Fraction(speed)*Fraction(float(max(result.time_steps)))/Fraction(config.dx))
    assert result.max_cfl == expected
    assert 0 < result.max_cfl <= 1
