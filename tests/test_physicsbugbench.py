"""Evaluator tests: fault presence is checked independently of detection claims."""

from dataclasses import replace
import json

import numpy as np
import pytest

from benchmarks.physicsbugbench.evaluate import evaluate, heldout_cases, score_reports
from benchmarks.physicsbugbench.controls import CHALLENGING_CONTROLS
from benchmarks.physicsbugbench.variants import ENTRIES, faulty_solver
from physicsguard.diagnostics.accuracy import transport_direction
from physicsguard.diagnostics.conservation import conservation
from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.runner import execute_solver
from physicsguard.experiments.public import investigator_view
from physicsguard.experiments.scenarios import development_cases
from physicsguard.numerics import AdvectionConfig, solve_advection
from physicsguard.schemas.results import ExperimentCase


FAULTS = ENTRIES[:6]


@pytest.mark.parametrize("entry,expected", list(zip(FAULTS, [
        [1.25, 2.5, 3.75, 2.5],     # Stable update using right neighbor.
        [.5, 2.25, 4.5, 2.75],      # Opposite update sign, upstream difference.
        [1., 1.75, 3.5, 3.25],      # Periodic incoming face clamped to self.
        np.array([1.5, 1.75, 3.5, 3.25])*np.exp(-.4*.0625),
        [1.125, 1.9375, 3.875, 3.0625],  # Coefficient loses a factor 1/dx.
        [.75, 1.5, 4.25, 3.5],      # Downstream state, original update sign.
])))
def test_fault_is_present_in_hand_computed_one_step(entry, expected):
    config = AdvectionConfig(n_cells=4, cfl=.25, final_time=.0625)
    result = entry.solver(np.array([1., 2., 4., 3.]), config)
    # Expected values follow directly from each specified mutation, independently
    # of the diagnostics and trusted solver. Similar anti-diffusive faults differ.
    np.testing.assert_allclose(result.final_averages, expected, rtol=0, atol=1e-15)


@pytest.mark.parametrize("entry", FAULTS)
@pytest.mark.parametrize("profile,mode", [("sine", 1), ("sine", 2), ("square", 1)])
def test_each_fault_is_detectable_across_multiple_initial_conditions(entry, profile, mode):
    case = ExperimentCase("multiple", profile=profile, mode=mode,
                          final_time=.125 if mode == 2 else .23,
                          phase=5.2 if profile == "square" else .37)
    report = diagnose_solver(entry.solver, "anonymous", (case,))
    # Basic checks alone must reveal the fault on this IC; do not credit the
    # separate one-cell exact-shift or refinement/metamorphic experiments here.
    basic = [d for d in report.diagnostics if d.case_ids == (case.case_id,)]
    assert any(d.status == "fail" for d in basic)


def test_wrong_direction_preserves_mass_and_bounds_but_is_detected():
    result = execute_solver(FAULTS[0].solver, "anonymous", ExperimentCase("direction"))
    assert conservation(result).status == "pass"
    assert transport_direction(result).status == "fail"
    assert min(result.final_averages) >= min(result.initial_averages)
    assert max(result.final_averages) <= max(result.initial_averages)


def test_basic_suite_can_miss_wrong_direction_near_half_wavelength():
    # Preserve the observed coarse-grid blind spot instead of lowering thresholds.
    case = ExperimentCase("blind-spot", mode=2, final_time=.23)
    report = diagnose_solver(FAULTS[0].solver, "anonymous", (case,))
    basic = [d for d in report.diagnostics if d.case_ids == (case.case_id,)]
    assert not any(d.status == "fail" for d in basic)
    assert any(d.status == "inconclusive" for d in basic)
    assert report.detected  # Follow-up exact-shift experiments still expose it.


def test_variants_are_not_duplicate_operators():
    config = AdvectionConfig(n_cells=7, final_time=.04, cfl=.8)
    initial = np.array([1., -.2, .3, 4., 2., .1, -.8])
    outputs = [entry.solver(initial, config).final_averages for entry in FAULTS]
    for i in range(len(outputs)):
        for j in range(i):
            assert not np.allclose(outputs[i], outputs[j], atol=1e-12, rtol=0)


@pytest.fixture(scope="module")
def evaluation():
    return evaluate()


def without_timing(value):
    if isinstance(value, dict):
        return {k: without_timing(v) for k, v in value.items() if "seconds" not in k}
    if isinstance(value, (tuple, list)):
        return [without_timing(v) for v in value]
    return value


def test_measured_detection_and_false_positive_rates(evaluation):
    private, _ = evaluation
    for split in private["splits"].values():
        metrics = split["metrics"]
        assert metrics["fault_detection"] == {"detected": 6, "total": 6, "rate": 1.}
        assert metrics["false_positives"] == {"flagged": 0, "total": 3, "rate": 0.}
        assert metrics["execution_errors"] == 0
        assert metrics["inconclusive_diagnostics"] > 0
        assert len(metrics["diagnostic_coverage"]) >= 12
        for outcome in split["outcomes"]:
            statuses = [d["status"] for d in outcome["report"]["diagnostics"]]
            assert outcome["detected"] == ("fail" in statuses)
        for outcome in split["outcomes"][6:]:
            assert all(d["status"] != "fail" for d in outcome["report"]["diagnostics"])


def test_evaluation_categories_do_not_claim_unseen_fault_generalization(evaluation):
    private, _ = evaluation
    categories = private["evaluation_categories"]
    assert categories["known_injected_faults"]["detection"] == private["splits"]["development"]["metrics"]["fault_detection"]
    assert categories["unseen_parameter_configurations"]["detection"] == private["splits"]["heldout"]["metrics"]["fault_detection"]
    assert categories["unseen_fault_mechanisms"]["status"] == "unevaluated"
    assert categories["unseen_fault_mechanisms"]["rate"] is None
    assert categories["unseen_fault_mechanisms"]["total"] == 0
    assert categories["correct_implementation_false_positives"]["challenging_controls"] == {
        "flagged": 0, "total": 4, "rate": 0.}


@pytest.mark.parametrize("index", range(4))
def test_challenging_correct_controls_keep_legitimate_truncation_error(index, evaluation):
    private, _ = evaluation
    outcome = private["challenging_controls"]["outcomes"][index]
    assert not outcome["detected"]
    diagnostics = outcome["report"]["diagnostics"]
    assert all(d["status"] != "fail" for d in diagnostics)
    accuracy = next(d for d in diagnostics if d["diagnostic_id"] == "accuracy")
    assert accuracy["status"] == "pass"
    run = outcome["report"]["executions"][0]
    case = run["case"]
    if index == 0:
        assert np.ptp(run["final_averages"]) < .7 * np.ptp(run["initial_averages"])
        assert accuracy["measurements"]["Linf"] > .05
    elif index == 1:
        assert case["n_cells"] == 8
        assert accuracy["measurements"]["Linf"] > .01
    elif index == 2:
        assert abs(case["phase"]) > 2*np.pi
        assert abs(case["physics"]["speed"] * case["final_time"]) > 3
    else:
        assert case["profile"] == "square"
        assert accuracy["acceptance_criteria"].startswith("L1")
        assert next(d for d in diagnostics if d["diagnostic_id"] == "refinement")["status"] == "inconclusive"


def test_unavailable_generated_attempts_are_neither_executions_nor_passing_diagnostics():
    case = ExperimentCase("unavailable-score", n_cells=32, final_time=1., max_steps=100)
    report = diagnose_solver(solve_advection, "anonymous", (case,))
    metrics = score_reports([(ENTRIES[-1], report)])
    assert metrics["generated_unavailable_attempts"] == 2
    assert metrics["execution_count"] == sum(a.status != "unavailable" for a in report.executions)
    refinement = metrics["diagnostic_coverage"]["refinement"]
    assert refinement["inconclusive"] == 1
    assert refinement["pass"] == 0
    assert metrics["execution_errors"] == 0
    assert metrics["false_positives"]["flagged"] == 0


@pytest.mark.parametrize("seed", [20261027, 20261028])
def test_benchmark_replays_deterministically_apart_from_timing(evaluation, seed):
    private, public = evaluation if seed == 20261027 else evaluate(seed)
    replay_private, replay_public = evaluate(seed)
    assert without_timing(private) == without_timing(replay_private)
    assert without_timing(public) == without_timing(replay_public)
    assert heldout_cases(7) == heldout_cases(7)
    assert heldout_cases(7) != heldout_cases(8)
    assert set(heldout_cases(7)).isdisjoint(development_cases())


def test_public_interface_has_no_ground_truth_or_heldout_evidence(evaluation):
    private, public = evaluation
    payload = json.dumps(public, allow_nan=False)
    assert "PBB-" not in payload
    assert "eval-" not in payload
    for forbidden in ("fault_type", "injected_fault", "expected_behavior", "seed", "heldout", "reference_patch"):
        assert forbidden not in payload
    for entry, _ in CHALLENGING_CONTROLS:
        assert entry.injected_fault not in payload
        assert entry.expected_behavior not in payload
    assert "fault_type" in json.dumps(private)
    from physicsguard.experiments import public as interface
    assert not hasattr(interface, "ENTRIES")
    assert not hasattr(interface, "heldout_cases")
    # Distinct artifacts: only development evidence is exported by evaluate().
    assert all(c["case_id"].startswith("dev-") for r in public["reports"] for c in r["cases"])
    assert all("control" not in c["case_id"] for r in public["reports"] for c in r["cases"])


def test_public_export_serializes_unavailable_generated_requests_without_labels():
    case = ExperimentCase("dev-budget", n_cells=32, final_time=1., max_steps=100)
    report = diagnose_solver(solve_advection, "anonymous", (case,), audience="investigator")
    exported = json.loads(json.dumps(investigator_view(report), allow_nan=False))
    skipped = [a for a in exported["executions"] if a["status"] == "unavailable"]
    assert len(skipped) == 2
    assert all(a["error_kind"] == "generated_validation_error" for a in skipped)
    assert "fault_type" not in json.dumps(exported)


def test_private_reports_are_rejected_by_investigator_projection():
    report = diagnose_solver(ENTRIES[-1].solver, "anonymous", heldout_cases(77))
    with pytest.raises(ValueError, match="evaluator-only"):
        investigator_view(report)


@pytest.mark.parametrize("seed", [-1, True, 2**32, 1.5])
def test_invalid_holdout_seed_fails(seed):
    with pytest.raises(ValueError):
        heldout_cases(seed)
