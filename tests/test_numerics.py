"""Scientific regression tests for source-free periodic finite-volume advection.

References use analytic integrals and measurements computed here, rather than
production diagnostics or production flux/update functions. All random inputs
have explicit seeds. No model, network service, benchmark labels or mocks.
"""

from dataclasses import replace
from math import cos, fsum, pi, remainder

import numpy as np
import pytest

from physicsguard.numerics import (
    AdvectionConfig,
    sine_cell_averages,
    solve_advection,
    step_upwind,
    upwind_flux,
)

EPS = np.finfo(np.float64).eps


def exact_sine(edges, *, speed, time, offset=1.0, amplitude=0.2, mode=1, phase=0.0):
    """Independent primitive-based cell integral (no sinc or production code)."""
    length = edges[-1] - edges[0]
    k = 2 * pi * mode / length
    # Bound the trig arguments before subtracting neighboring primitive values.
    # Otherwise multi-period travel amplifies cancellation in this test oracle.
    travel = remainder(speed * time, length)
    return np.array([
        offset + amplitude * (
            cos(k * (left - edges[0] - travel) + phase)
            - cos(k * (right - edges[0] - travel) + phase)
        ) / (k * (right - left))
        for left, right in zip(edges[:-1], edges[1:])
    ])


def mass(values, dx):
    return dx * fsum(map(float, values))


def periodic_tv(values):
    return fsum(abs(float(values[(i + 1) % len(values)]) - float(value))
                for i, value in enumerate(values))


@pytest.mark.parametrize("speed, expected", [
    (2.0, [2.0, -4.0, 6.0]),
    (-2.0, [-8.0, 10.0, -12.0]),
    (0.0, [0.0, 0.0, 0.0]),
])
def test_flux_selects_the_upstream_state(speed, expected):
    left = np.array([1.0, -2.0, 3.0])
    right = np.array([4.0, -5.0, 6.0])
    flux = upwind_flux(left, right, speed=speed)
    np.testing.assert_array_equal(flux, expected)
    np.testing.assert_array_equal(left, [1.0, -2.0, 3.0])
    np.testing.assert_array_equal(right, [4.0, -5.0, 6.0])
    assert not np.shares_memory(flux, left)
    assert not np.shares_memory(flux, right)


@pytest.mark.parametrize("speed", [-2.3, 0.0, 1.7])
def test_flux_is_consistent_for_equal_face_states(speed):
    values = np.array([-0.5, 0.0, 1.5])
    np.testing.assert_array_equal(upwind_flux(values, values, speed=speed), speed * values)


@pytest.mark.parametrize("speed, expected", [
    (1.0, [0.75, 1.75, 0.5, 0.0]),
    (-1.0, [1.25, 1.5, 0.0, 0.25]),
])
def test_one_step_matches_hand_computed_periodic_flux_balance(speed, expected):
    advanced = step_upwind([1.0, 2.0, 0.0, 0.0], speed=speed, dx=1.0, dt=0.25)
    np.testing.assert_array_equal(advanced, expected)


@pytest.mark.parametrize("speed", [-1.0, 1.0])
@pytest.mark.parametrize("n_cells", [1, 7, 32])
def test_cfl_one_transports_exactly_one_periodic_cell(speed, n_cells):
    # Dyadic values avoid making the expected identity depend on trig rounding.
    initial = np.arange(n_cells, dtype=np.float64) / 8
    config = AdvectionConfig(n_cells=n_cells, speed=speed, cfl=1.0, final_time=1 / n_cells)
    run = solve_advection(initial, config)
    np.testing.assert_array_equal(run.final_averages, np.roll(initial, int(speed)))
    assert run.n_steps == 1


@pytest.mark.parametrize("speed", [-1.7, 0.0, 2.3])
@pytest.mark.parametrize("cfl", [0.2, 0.8, 1.0])
@pytest.mark.parametrize("constant", [-2.0, 0.0, 1.25])
def test_constant_solutions_are_preserved(speed, cfl, constant):
    config = AdvectionConfig(n_cells=31, speed=speed, cfl=cfl, final_time=0.37)
    initial = np.full(config.n_cells, constant)
    np.testing.assert_array_equal(solve_advection(initial, config).final_averages, initial)


@pytest.mark.parametrize("speed", [-1.7, 1.7])
@pytest.mark.parametrize("cfl", [0.2, 0.8, 1.0])
@pytest.mark.parametrize("profile", ["smooth", "discontinuous", "zero_mean"])
def test_mass_conservation_for_multiple_profiles_and_steps(speed, cfl, profile):
    config = AdvectionConfig(
        n_cells=63, speed=speed, cfl=cfl, x_min=-0.75, x_max=1.75, final_time=2.3
    )
    if profile == "smooth":
        initial = exact_sine(config.cell_edges(), speed=speed, time=0.0)
    elif profile == "discontinuous":
        initial = np.zeros(config.n_cells)
        initial[-11:] = 1.0
        initial[:5] = 1.0
    else:
        initial = np.random.default_rng(718).normal(size=config.n_cells)
        initial -= initial.mean()
    run = solve_advection(initial, config)
    scale = max(1.0, config.dx * fsum(abs(float(value)) for value in initial))
    tolerance = 50 * EPS * (run.n_steps + 1) * scale
    assert abs(mass(run.final_averages, config.dx) - mass(initial, config.dx)) <= tolerance
    assert np.all(np.isfinite(run.final_averages))


@pytest.mark.parametrize("speed", [-1.3, 1.3])
@pytest.mark.parametrize("cfl", [0.2, 0.8, 1.0])
def test_each_step_conserves_mass_and_obeys_bounds_and_periodic_tv(speed, cfl):
    values = np.zeros(37)
    values[5:19] = 1.0
    values[-3:] = 0.4
    initial_mass = mass(values, 0.1)
    previous_tv = periodic_tv(values)
    for step in range(1, 81):
        values = step_upwind(values, speed=speed, dx=0.1, dt=cfl * 0.1 / abs(speed))
        tolerance = 50 * EPS * (step + 1)
        assert values.min() >= -tolerance
        assert values.max() <= 1.0 + tolerance
        assert abs(mass(values, 0.1) - initial_mass) <= tolerance * max(1.0, abs(initial_mass))
        variation = periodic_tv(values)
        assert variation <= previous_tv + tolerance
        previous_tv = variation


@pytest.mark.parametrize("speed", [-1.3, 0.0, 1.3])
@pytest.mark.parametrize("time", [0.0, 0.37, 5.125])
def test_sine_reference_matches_independent_analytic_cell_integrals(speed, time):
    edges = np.linspace(-0.75, 1.75, 34)
    kwargs = dict(speed=speed, time=time, offset=-0.3, amplitude=0.7, mode=3, phase=0.4)
    np.testing.assert_allclose(
        sine_cell_averages(edges, **kwargs), exact_sine(edges, **kwargs), rtol=0.0, atol=2e-14
    )


def test_reference_averages_are_not_center_samples():
    # Integral of sin(2*pi*x) on [0, 1/2] is 1/pi; its cell mean is 2/pi.
    values = sine_cell_averages([0.0, 0.5, 1.0], offset=0.0, amplitude=1.0)
    np.testing.assert_allclose(values, [2 / pi, -2 / pi], rtol=0.0, atol=4 * EPS)
    assert abs(values[0] - 1.0) > 0.3


def test_reference_handles_nonuniform_cells_and_full_period_averages():
    edges = np.array([2.0, 2.1, 2.4, 2.9, 3.0])
    kwargs = dict(speed=-0.7, time=0.37, offset=1.2, amplitude=0.6, mode=2, phase=0.3)
    actual = sine_cell_averages(edges, **kwargs)
    np.testing.assert_allclose(actual, exact_sine(edges, **kwargs), rtol=0.0, atol=2e-14)
    assert abs(fsum(actual * np.diff(edges)) - 1.2) <= 5e-15
    np.testing.assert_allclose(sine_cell_averages([2.0, 3.0], **kwargs), [1.2], atol=5e-15)


def test_multiperiod_reference_matches_independent_gauss_quadrature():
    edges = np.linspace(-0.75, 1.75, 34)
    nodes, weights = np.polynomial.legendre.leggauss(32)
    averages = []
    for left, right in zip(edges[:-1], edges[1:]):
        points = left + (nodes + 1) * (right - left) / 2
        field = -0.3 + 0.7 * np.sin(6 * pi * (points + 0.75 + 1.3 * 5.125) / 2.5 + 0.4)
        averages.append(np.dot(weights, field) / 2)
    actual = sine_cell_averages(
        edges, speed=-1.3, time=5.125, offset=-0.3, amplitude=0.7, mode=3, phase=0.4
    )
    np.testing.assert_allclose(actual, averages, rtol=0.0, atol=2e-14)


@pytest.mark.parametrize("speed", [-1.0, 1.0])
def test_smooth_transport_is_first_order_and_accurate(speed):
    errors = []
    for n_cells in (64, 128, 256):
        config = AdvectionConfig(
            n_cells=n_cells, speed=speed, x_min=-0.25, x_max=0.75, cfl=0.8, final_time=0.3
        )
        edges = config.cell_edges()
        initial = exact_sine(edges, speed=speed, time=0.0)
        run = solve_advection(initial, config)
        reference = exact_sine(edges, speed=speed, time=config.final_time)
        difference = run.final_averages - reference
        errors.append([np.mean(abs(difference)), np.sqrt(np.mean(difference**2)), np.max(abs(difference))])
    errors = np.array(errors)
    assert np.all(np.diff(errors, axis=0) < 0.0)
    orders = np.log2(errors[:-1, :2] / errors[1:, :2])
    assert np.all((orders > 0.8) & (orders < 1.2))
    assert errors[-1, 0] < 1e-3


@pytest.mark.parametrize("speed, final_time, n_cells, cfl", [
    (1.0, 1.0, 8, 0.8),  # Repeated floating addition of 0.1 must not add a step.
    (-1.7, 0.37, 17, 0.8),
    (0.4, 0.5, 8, 1.0),
    (1.0, 1e-15, 13, 0.8),  # A tiny duration still requires a real update.
])
def test_time_schedule_reaches_target_without_overshoot(speed, final_time, n_cells, cfl):
    config = AdvectionConfig(n_cells=n_cells, speed=speed, final_time=final_time, cfl=cfl)
    run = solve_advection(np.arange(n_cells, dtype=float), config)
    assert run.final_time == final_time
    assert abs(fsum(map(float, run.time_steps)) - final_time) <= 2 * np.spacing(final_time)
    assert np.all(run.time_steps > 0.0)
    assert run.max_cfl <= cfl + 8 * EPS
    assert np.all(np.cumsum(run.time_steps) <= final_time + 8 * EPS * final_time)
    if (speed, final_time, n_cells, cfl) == (1.0, 1.0, 8, 0.8):
        assert run.n_steps == 10
        solve_advection(np.zeros(n_cells), replace(config, max_steps=10))


def test_last_step_is_shortened():
    config = AdvectionConfig(n_cells=16, final_time=0.37, cfl=0.8)
    run = solve_advection(np.arange(16, dtype=float), config)
    assert run.time_steps[-1] < run.time_steps[0]
    assert abs(fsum(map(float, run.time_steps)) - 0.37) <= EPS


@pytest.mark.parametrize("speed, final_time", [(0.0, 1.0), (1.7, 0.0), (0.0, 0.0)])
def test_stationary_or_zero_duration_run_needs_no_updates(speed, final_time):
    config = AdvectionConfig(n_cells=19, speed=speed, final_time=final_time)
    initial = np.random.default_rng(471).normal(size=19)
    run = solve_advection(initial, config)
    np.testing.assert_array_equal(run.final_averages, initial)
    assert run.n_steps == 0
    assert run.max_cfl == 0.0
    assert run.final_time == final_time


@pytest.mark.parametrize("speed, dt", [(0.0, 1.0), (1.0, 0.0)])
def test_stationary_step_returns_an_independent_array(speed, dt):
    initial = np.arange(4, dtype=np.float32)
    final = step_upwind(initial, speed=speed, dx=1.0, dt=dt)
    np.testing.assert_array_equal(final, initial)
    assert final.dtype == np.float64
    assert not np.shares_memory(initial, final)


def test_run_is_reproducible_and_preserves_owned_inputs():
    initial = np.random.default_rng(417).normal(size=29)
    unchanged = initial.copy()
    initial.setflags(write=False)
    config = AdvectionConfig(n_cells=29, speed=-0.7, final_time=0.37)
    left = solve_advection(initial, config)
    right = solve_advection(initial, config)
    np.testing.assert_array_equal(initial, unchanged)
    for name in ("initial_averages", "final_averages", "cell_edges", "cell_centers", "time_steps"):
        array = getattr(left, name)
        np.testing.assert_array_equal(array, getattr(right, name))
        assert array.dtype == np.float64
        assert not array.flags.writeable
        assert not np.shares_memory(array, initial)
    assert not np.shares_memory(left.initial_averages, left.final_averages)


@pytest.mark.parametrize("speed", [-0.7, 1.3])
def test_linear_superposition_and_periodic_grid_shift(speed):
    rng = np.random.default_rng(719)
    first, second = rng.normal(size=(2, 29))
    config = AdvectionConfig(n_cells=29, speed=speed, cfl=0.73, final_time=0.37)
    left = solve_advection(first, config).final_averages
    right = solve_advection(second, config).final_averages
    combined = solve_advection(first - 0.4 * second, config).final_averages
    shifted = solve_advection(np.roll(first, 7), config).final_averages
    np.testing.assert_allclose(combined, left - 0.4 * right, rtol=0.0, atol=5e-14)
    np.testing.assert_allclose(shifted, np.roll(left, 7), rtol=0.0, atol=5e-14)


def test_domain_and_velocity_rescaling_preserves_transport():
    initial = np.random.default_rng(114).normal(size=29)
    base = AdvectionConfig(n_cells=29, speed=1.3, final_time=0.37)
    scaled = replace(base, x_min=2.0, x_max=5.0, speed=3.9)
    np.testing.assert_allclose(
        solve_advection(initial, base).final_averages,
        solve_advection(initial, scaled).final_averages, rtol=0.0, atol=5e-14,
    )


@pytest.mark.parametrize("field, value", [
    ("n_cells", 0), ("n_cells", -2), ("n_cells", 3.5), ("n_cells", True),
    ("max_steps", 0), ("max_steps", 1.5), ("max_steps", False),
    ("cfl", 0.0), ("cfl", -0.1), ("cfl", np.nextafter(1.0, 2.0)),
    ("cfl", np.nan), ("speed", np.inf), ("speed", 1j), ("speed", "1"),
    ("speed", True), ("x_min", np.nan), ("x_max", np.inf), ("x_max", 0.0),
    ("final_time", -0.1), ("final_time", np.inf), ("final_time", np.nan),
])
def test_invalid_configuration_is_rejected(field, value):
    with pytest.raises(ValueError, match=field if field != "x_max" else "x_max|domain"):
        AdvectionConfig(**{field: value})


@pytest.mark.parametrize("initial", [
    [], 1.0, [[1.0, 2.0]], [np.nan, 1.0], [np.inf, 1.0],
    [1j, 2j], ["1", "2"], [True, False], [[1.0], [1.0, 2.0]],
])
def test_invalid_state_is_rejected(initial):
    with pytest.raises(ValueError, match="initial_averages"):
        solve_advection(initial, AdvectionConfig(n_cells=2))


def test_wrong_state_length_or_config_type_is_rejected():
    with pytest.raises(ValueError, match="n_cells"):
        solve_advection(np.zeros(3), AdvectionConfig(n_cells=4))
    with pytest.raises(ValueError, match="config"):
        solve_advection(np.zeros(3), {})


@pytest.mark.parametrize("kwargs", [
    {"dx": 0.0}, {"dx": -1.0}, {"dx": np.inf}, {"dt": -0.1},
    {"dt": np.nan}, {"speed": np.inf}, {"dt": np.nextafter(1.0, 2.0)},
    {"speed": -2.0, "dt": 0.6},
])
def test_invalid_step_parameters_are_rejected(kwargs):
    controls = dict(speed=1.0, dx=1.0, dt=0.5)
    controls.update(kwargs)
    with pytest.raises(ValueError):
        step_upwind([1.0, 2.0], **controls)


def test_step_budget_is_enforced_before_mutating_input():
    initial = np.arange(16, dtype=float)
    with pytest.raises(ValueError, match="max_steps"):
        solve_advection(initial, AdvectionConfig(n_cells=16, max_steps=2))
    np.testing.assert_array_equal(initial, np.arange(16, dtype=float))


def test_unrepresentable_grid_or_timestep_is_rejected():
    with pytest.raises(ValueError, match="domain|dx"):
        AdvectionConfig(n_cells=8, x_min=-1e308, x_max=1e308)
    with pytest.raises(ValueError, match="dx|representable"):
        AdvectionConfig(n_cells=8, x_max=np.nextafter(0.0, 1.0))
    with pytest.raises(ValueError, match="cell edges"):
        solve_advection(np.zeros(8), AdvectionConfig(n_cells=8, x_min=1e16, x_max=1e16 + 2))
    with pytest.raises(ValueError, match="timestep"):
        solve_advection([1.0], AdvectionConfig(n_cells=1, speed=1e308, x_max=1e-300))


def test_flux_shape_mismatch_and_nonfinite_arithmetic_fail_explicitly():
    with pytest.raises(ValueError, match="matching shapes"):
        upwind_flux([1.0, 2.0], [1.0], speed=1.0)
    with pytest.raises(FloatingPointError):
        upwind_flux([3.0], [4.0], speed=1e308)
    # Even finite input fluxes can have an unrepresentable difference.
    with pytest.raises(FloatingPointError):
        step_upwind([1e308, -1e308], speed=1.0, dx=1.0, dt=0.5)


@pytest.mark.parametrize("edges", [[], [1.0], [1.0, 0.0], [0.0, 0.0, 1.0], [0.0, np.inf]])
def test_invalid_reference_grid_is_rejected(edges):
    with pytest.raises(ValueError, match="edges"):
        sine_cell_averages(edges)


@pytest.mark.parametrize("kwargs", [
    {"mode": 0}, {"mode": 1.5}, {"mode": True}, {"phase": np.nan},
    {"amplitude": np.inf}, {"offset": np.nan}, {"speed": 1j}, {"time": -1.0},
    {"speed": 1e308, "time": 1e308},
])
def test_invalid_reference_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        sine_cell_averages([0.0, 0.5, 1.0], **kwargs)


def test_subnormal_scaling_at_cfl_one():
    for speed in (1e-310, -1e-310):
        result = step_upwind(
            [1.0, 2.0],
            speed=speed,
            dx=1e-310,
            dt=1.0,
        )
        np.testing.assert_array_equal(result, [2.0, 1.0])
