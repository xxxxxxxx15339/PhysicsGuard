"""Independent checks of measured values, assumptions and numerical tolerances."""

from dataclasses import replace
from math import cos, fsum, pi, sqrt
import json

import numpy as np
import pytest

from physicsguard.diagnostics.accuracy import analytical_accuracy, transport_direction
from physicsguard.diagnostics.conservation import conservation
from physicsguard.diagnostics.refinement import grid_refinement
from physicsguard.diagnostics.stability import stability
from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.runner import execute_solver
from physicsguard.experiments.scenarios import cell_averages, development_cases, refinement_cases
from physicsguard.numerics import solve_advection
from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification, SolverStrategy


@pytest.fixture
def run():
    return execute_solver(solve_advection, "anonymous", ExperimentCase("values"))


def test_conservation_measurements_and_cancellation_safe_tolerance(run):
    u = (1.0, -1.0, 2.0, -2.0)
    v = (1.0, -1.0, 2.0, -1.99)
    run = replace(run, case=ExperimentCase("manual", n_cells=4), initial_averages=u, final_averages=v)
    result = conservation(run)
    assert result.status == "fail"
    assert result.measurements["initial_mass"] == 0.0
    expected = abs(fsum(v)) / 4
    assert result.measurements["final_mass"] == expected
    assert result.measurements["absolute_drift"] == expected
    assert result.measurements["normalization_scale"] == 1.5
    assert result.measurements["normalized_drift"] == expected / 1.5
    k = 32 * (len(run.time_steps) + 1) + 8
    eps = np.finfo(float).eps
    assert result.tolerance == k * eps / (1-k*eps) * 1.5
    assert result.units["absolute_drift"] == "u*length"


def test_conservation_does_not_demand_exact_zero(run):
    values = list(run.final_averages)
    values[0] += np.finfo(float).eps
    assert conservation(replace(run, final_averages=tuple(values))).status == "pass"
    zeros = tuple(0.0 for _ in values)
    result = conservation(replace(run, initial_averages=zeros, final_averages=zeros))
    assert result.status == "pass"
    assert result.measurements["normalized_drift"] == 0


def test_accuracy_reports_domain_integrated_norms_on_nonunit_domain(run):
    case = ExperimentCase("norms", n_cells=4, profile="constant", offset=2.0,
                          physics=PhysicsSpecification(x_min=-1.0, x_max=3.0))
    result = analytical_accuracy(replace(run, case=case, initial_averages=(2.,)*4,
                                         final_averages=(3., 0., 5., -2.)))
    assert result.measurements == {"L1": 10., "L2": sqrt(30.), "Linf": 4.}
    assert result.status == "fail"


@pytest.mark.parametrize("profile", ["sine", "square"])
@pytest.mark.parametrize("speed", [-1.3, 1.7])
def test_cell_averages_use_analytic_integrals_across_periodic_seam(profile, speed):
    case = ExperimentCase("reference", profile=profile, n_cells=32,
                          physics=PhysicsSpecification(speed=speed), phase=0.)
    if profile == "sine":
        edges = case.config().cell_edges()
        expected = [case.offset + case.amplitude * (
            cos(2*pi*(left-speed*case.final_time)) - cos(2*pi*(right-speed*case.final_time)))
            / (2*pi*(right-left)) for left, right in zip(edges[:-1], edges[1:])]
        np.testing.assert_allclose(cell_averages(case, case.final_time), expected, atol=2e-15, rtol=0)
    else:
        # Independent interval-overlap geometry; avoids the primitive used by scenarios.
        edges = case.config().cell_edges()
        shift = (speed*case.final_time) % 1
        expected = []
        for left, right in zip(edges[:-1], edges[1:]):
            overlap = fsum(max(0., min(right, shift+.3+k) - max(left, shift+k)) for k in (-1, 0, 1))
            expected.append(case.offset + case.amplitude*overlap/(right-left))
        np.testing.assert_allclose(cell_averages(case, case.final_time), expected, atol=4e-15, rtol=0)


@pytest.mark.parametrize("duration", [0.0, 0.5, 1.0])
def test_direction_does_not_claim_identification_at_ambiguous_times(duration):
    case = ExperimentCase("ambiguous", final_time=duration)
    result = transport_direction(execute_solver(solve_advection, "anonymous", case))
    assert result.status == "inconclusive"
    assert not result.applicable


def test_boundedness_and_accuracy_require_supported_method(run):
    case = replace(run.case, strategy=SolverStrategy(method="future_high_order"))
    changed = replace(run, case=case)
    assert analytical_accuracy(changed).status == "inconclusive"
    assert analytical_accuracy(changed).measurements["Linf"] >= 0
    checks = stability(changed)
    assert checks[0].status == "pass"
    assert all(not c.applicable and c.status == "inconclusive" for c in checks[1:])


def test_arbitrary_initial_data_cannot_be_compared_to_the_declared_sine_reference():
    run = execute_solver(solve_advection, "anonymous", ExperimentCase("arbitrary"), np.arange(64.))
    assert analytical_accuracy(run).status == "inconclusive"
    assert transport_direction(run).status == "inconclusive"


def test_discontinuous_accuracy_has_an_independent_bv_translation_bound():
    case = ExperimentCase("square", profile="square", phase=5.2)
    run = execute_solver(solve_advection, "anonymous", case)
    check = analytical_accuracy(run)
    a, dx = abs(case.physics.speed), case.config().dx
    variance = fsum(a*dt*dx - (a*dt)**2 for dt in run.time_steps)
    assert check.tolerance > 2*abs(case.amplitude)*sqrt(variance)
    assert check.tolerance < 2*abs(case.amplitude)*sqrt(variance) + 1e-11
    assert check.status == "pass"
    assert check.acceptance_criteria.startswith("L1")


def test_cfl_violation_is_measured_and_invalidates_maximum_principle(run):
    _, cfl, bounded = stability(replace(run, max_cfl=1.2))
    assert cfl.status == "fail"
    assert cfl.measurements["max_cfl"] == 1.2
    assert not bounded.applicable


@pytest.mark.parametrize("change", [dict(cfl=1.), dict(profile="square"), dict(amplitude=0.),
                                    dict(final_time=0.), dict(mode=4)])
def test_refinement_is_inconclusive_outside_assumptions(change):
    case = replace(ExperimentCase("refine"), **change)
    runs = tuple(execute_solver(solve_advection, "anonymous", c) for c in refinement_cases(case))
    assert grid_refinement(runs).status == "inconclusive"


def test_refinement_checks_compatibility_and_reports_actual_orders():
    runs = tuple(execute_solver(solve_advection, "anonymous", c)
                 for c in refinement_cases(ExperimentCase("refine", final_time=.3, phase=0.)))
    result = grid_refinement(runs)
    assert result.status == "pass"
    np.testing.assert_allclose(result.measurements["observed_orders"], [.993585, .996709], atol=1e-5)
    incompatible = (runs[0], replace(runs[1], case=replace(runs[1].case, cfl=.6)), runs[2])
    assert grid_refinement(incompatible).status == "inconclusive"


@pytest.mark.parametrize("speed", [-1.4, 0., 1.7])
@pytest.mark.parametrize("offset,amplitude", [(1., .2), (0., .8), (-2., .5)])
def test_correct_solver_has_no_false_failures_under_varied_data(speed, offset, amplitude):
    cases = tuple(replace(c, physics=PhysicsSpecification(speed=speed),
                          offset=offset, amplitude=amplitude) for c in development_cases())
    report = diagnose_solver(solve_advection, "anonymous", cases)
    assert not report.detected
    assert all(d.status != "fail" for d in report.diagnostics)
    parsed = json.loads(report.to_json())
    assert parsed["solver_id"] == "anonymous"
    for diagnostic in parsed["diagnostics"]:
        assert diagnostic["description"]
        assert diagnostic["assumptions"]
        assert diagnostic["acceptance_criteria"]
        assert diagnostic["tolerance_justification"]
        assert diagnostic["measurements"].keys() == diagnostic["units"].keys()
