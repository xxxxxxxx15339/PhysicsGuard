"""Measured source repairs and independent rejection controls; no model traces."""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import re

import pytest

from benchmarks.source_repair.evaluate import evaluate_repairs
from physicsguard.experiments.scenarios import development_cases
from physicsguard.repair.executor import FixtureWorker, WorkerTimeout, run_source_diagnostics
from physicsguard.repair.policy import check_candidate, localized_diff, parse_localized_diff, validate_proposal
from physicsguard.repair.proposals import make_proposal, propose_repair
from physicsguard.repair.sources import REVIEWED_HASHES, SourceStore, default_source_store, source_hash
from physicsguard.repair.tools import RepairTools
from physicsguard.repair.validator import case_signature, compare_regressions, verify_candidate, _verify_candidate_for_testing
from physicsguard.repair.verification_cases import independent_plan
from physicsguard.repair.workflow import repair_source
from physicsguard.repair.workspace import source_workspace
from physicsguard.schemas.repairs import FaultHypothesis, SourceSnapshot, parse_proposal
from physicsguard.schemas.results import ExperimentCase


@pytest.fixture(scope="module")
def measured():
    return evaluate_repairs()


@pytest.fixture
def store():
    return default_source_store()


@pytest.mark.parametrize("source_file", tuple(REVIEWED_HASHES))
def test_reviewed_source_hashes_and_numbered_inspection(store, source_file):
    source = store.inspect(source_file)
    assert source.sha256 == source_hash(source.source_text)
    assert source.numbered_lines()[0]["line"] == 1
    assert store.unchanged(source)
    assert json.loads(source.to_json())["source_file"] == source_file


@pytest.mark.parametrize("name", ["../solver_01.py", "/tmp/solver_01.py", "tests/test_numerics.py",
                                  "validator.py", "README.md", "nested/solver_01.py"])
def test_source_paths_are_allowlisted_basenames(store, name):
    with pytest.raises(ValueError):
        store.inspect(name)


def test_source_symlinks_hardlinks_and_unreviewed_originals_are_rejected(store, tmp_path):
    target = store.root/"solver_01.py"
    link = tmp_path/target.name
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        SourceStore(tmp_path).inspect(target.name)
    link.unlink()
    copy = tmp_path/"original-copy.py"
    shutil.copyfile(target, copy)
    os.link(copy, link)
    try:
        with pytest.raises(ValueError, match="hard links"):
            SourceStore(tmp_path).inspect(target.name)
    finally:
        link.unlink()
    shutil.copyfile(target, link)
    link.write_text(link.read_text()+"\n")
    with pytest.raises(ValueError, match="hash"):
        SourceStore(tmp_path).inspect(target.name)
    root_link = tmp_path/"directory-link"
    root_link.symlink_to(store.root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        SourceStore(root_link).inspect(target.name)


@pytest.mark.parametrize("name,line,mechanism", [("solver_01.py",8,"transport_direction"),
    ("solver_02.py",9,"spatial_scaling"),("solver_03.py",12,"periodic_neighbor")])
def test_actual_source_repairs_are_independently_accepted(measured, store, name, line, mechanism):
    report = measured["reports"][name]
    assert report["development"]["report"]["diagnostics"]
    assert not report["abstained"]
    attempt = report["attempts"][0]
    proposal, verification = attempt["proposal"], attempt["verification"]
    assert proposal["origin"] == "deterministic"
    assert proposal["line_number"] == line
    assert proposal["hypothesis"]["mechanism"] == mechanism
    assert verification["decision"] == "ACCEPTED"
    assert all(status == "pass" for status in verification["stages"].values())
    assert attempt["application"]["changed_lines"] == 1
    assert not verification["regression_ids"] and not verification["lost_evidence_ids"]
    for phase in ("after_development", "after_additional"):
        assert all(d["status"] != "fail" for d in verification[phase]["report"]["diagnostics"])
        assert all(a["status"] == "success" for a in verification[phase]["report"]["executions"])
    assert report["original_integrity"] and report["workspaces_cleaned"]
    assert store.inspect(name).sha256 == report["source"]["sha256"]


def test_correct_solver_abstains_without_source_modification(measured):
    correct = measured["reports"]["solver_04.py"]
    assert correct["abstained"]
    assert not correct["attempts"]
    assert correct["original_integrity"] and correct["workspaces_cleaned"]


def test_proposal_roundtrip_and_diff_parsing(measured, store):
    data = measured["reports"]["solver_02.py"]["attempts"][0]["proposal"]
    proposal = parse_proposal(json.dumps(data))
    assert json.loads(proposal.to_json()) == json.loads(json.dumps(data))
    assert parse_localized_diff(proposal.unified_diff, proposal.source_file) == (
        proposal.line_number, proposal.old_line, proposal.new_line)
    source = store.inspect(proposal.source_file)
    candidate = validate_proposal(source, proposal)
    assert source_hash(candidate) == proposal.proposed_sha256
    assert check_candidate(source, candidate) == proposal.line_number
    # Rename only the snapshot's public identifier: pattern analysis is not an ID lookup.
    from physicsguard.repair.executor import run_source_diagnostics
    with source_workspace(source) as root:
        evidence = run_source_diagnostics(root, source.source_file, development_cases())
    renamed = replace(source, source_file="unlisted_solver.py")
    inferred = propose_repair(renamed, evidence.report)
    assert inferred.hypothesis.mechanism == "spatial_scaling"
    assert "verify-" not in inferred.to_json()


@pytest.mark.parametrize("field,value", [("origin","model_made_up"),("original_sha256","bad"),
    ("line_number",True),("new_line","x\ny"),("verification_experiments",[]),("hypothesis",{})])
def test_malformed_proposal_schema_is_rejected(measured, field, value):
    data = dict(measured["reports"]["solver_02.py"]["attempts"][0]["proposal"])
    data[field] = value
    with pytest.raises(ValueError):
        parse_proposal(json.dumps(data))


@pytest.mark.parametrize("diff", ["", "not a diff", "--- a/x\n+++ b/x\n@@ -1,3 +1,3 @@\n-a\n+b\n",
                                 "--- a/x\n+++ b/y\n@@ -1 +1 @@\n-a\n+b\n"])
def test_invalid_patch_format_is_rejected(diff):
    with pytest.raises(ValueError):
        parse_localized_diff(diff,"solver_01.py")


@pytest.mark.parametrize("replacement", ["    scale = __import__('os').system('true')", "    scale = speed.__class__",
                                       "    scale = [dt] * 100", "    scale = dt; speed = 0"])
def test_calls_attributes_and_scope_expansion_cannot_be_patched(store, measured, replacement):
    source = store.inspect("solver_02.py")
    old = parse_proposal(json.dumps(measured["reports"][source.source_file]["attempts"][0]["proposal"]))
    proposal = make_proposal(source, old.hypothesis, replacement)
    with pytest.raises(ValueError):
        validate_proposal(source, proposal)


def test_wholesale_replacement_multifile_and_tampered_hashes_are_rejected(store, measured):
    source = store.inspect("solver_02.py")
    old = parse_proposal(json.dumps(measured["reports"][source.source_file]["attempts"][0]["proposal"]))
    with pytest.raises(ValueError):
        check_candidate(source,"from physicsguard.numerics import solve_advection\n")
    for bad in (replace(old,proposed_sha256="f"*64),replace(old,unified_diff=old.unified_diff+old.unified_diff),
                replace(old,source_file="../solver_02.py")):
        with pytest.raises(ValueError):
            validate_proposal(source,bad)


def test_disposable_copies_cleanup_and_original_integrity_even_on_failure(store):
    source = store.inspect("solver_01.py")
    before = (store.root/source.source_file).read_bytes()
    with pytest.raises(RuntimeError):
        with source_workspace(source) as root:
            assert root != store.root
            assert (root/"original"/source.source_file).read_bytes() == before
            raise RuntimeError("controlled failure")
    assert not root.exists()
    assert (store.root/source.source_file).read_bytes() == before


def test_symlinked_disposable_candidate_is_not_executed(store):
    source = store.inspect("solver_01.py")
    with pytest.raises(ValueError,match="symlink"):
        with source_workspace(source) as root:
            target=root/"candidate"/source.source_file
            target.unlink()
            target.symlink_to(store.root/source.source_file)
            with FixtureWorker(root,source.source_file):
                pytest.fail("symlinked candidate was executed")
    assert not root.exists()


@pytest.mark.parametrize("case,expected", [("positive_only","REJECTED"),("mass_damaging","REJECTED"),
    ("nonfinite","REJECTED"),("execution_failure","REJECTED"),("syntax","REJECTED"),
    ("stale_hash","REJECTED"),("test_modification","REJECTED"),("unrelated_file","REJECTED"),
    ("timeout","REJECTED"),("verification_unavailable","INCONCLUSIVE"),
    ("domain_overfit","REJECTED"),("grid_overfit","REJECTED"),
    ("profile_seam","REJECTED"),("conservative_wrong_speed","REJECTED")])
def test_bad_proposals_and_unsupported_execution_are_not_accepted(measured, case, expected):
    attempt = next(o["attempt"] for o in measured["negative_proposals"] if o["case"] == case)
    assert attempt["verification"]["decision"] == expected
    assert attempt["original_integrity"] and attempt["workspaces_cleaned"]
    if case == "positive_only":
        # Source change passes its development examples; independent negative speed reveals it.
        assert all(d["status"] != "fail" for d in attempt["verification"]["after_development"]["report"]["diagnostics"])
        assert any(d["status"] == "fail" for d in attempt["verification"]["after_additional"]["report"]["diagnostics"])
    elif case in {"mass_damaging", "nonfinite", "execution_failure", "timeout"}:
        assert attempt["verification"]["stages"]["source"] == "fail"
        assert attempt["verification"]["after_development"] is None
    elif case == "verification_unavailable":
        assert any(a["status"] == "unavailable" for a in attempt["verification"]["before_additional"]["report"]["executions"])
    elif case in {"domain_overfit", "grid_overfit"}:
        v = attempt["verification"]
        assert not any(d["status"] == "fail" for d in v["after_development"]["report"]["diagnostics"])
        assert any(d["status"] == "fail" for d in v["after_additional"]["report"]["diagnostics"])
        assert any("Scientific failures" in reason for reason in v["reasons"])
    elif case == "conservative_wrong_speed":
        ds = attempt["verification"]["after_additional"]["report"]["diagnostics"]
        assert all(d["status"] == "pass" for d in ds if d["diagnostic_id"] == "conservation")
        assert any(d["status"] == "fail" for d in ds if d["diagnostic_id"] == "accuracy")
    elif case == "profile_seam":
        assert attempt["verification"]["regression_ids"]
        assert any(d["diagnostic_id"] == "conservation" and d["status"] == "fail"
                   for d in attempt["verification"]["after_additional"]["report"]["diagnostics"])


def test_verifier_withheld_case_separation_and_missing_evidence(store, measured):
    report = repair_source(store,"solver_01.py")
    proposal = report.attempts[0].proposal
    known = {case_signature(a.case) for a in report.development.report.executions if a.case}
    plan = independent_plan()
    assert all(case_signature(c) not in known for c in plan.additional_cases)
    assert all(c.case_id not in proposal.to_json() for c in plan.additional_cases)
    duplicated = replace(plan,additional_cases=development_cases())
    result = _verify_candidate_for_testing(store,report.source,proposal,development_cases(),plan=duplicated)
    assert result.verification.decision == "INCONCLUSIVE"
    missing = next(o["attempt"] for o in measured["negative_proposals"] if o["case"] == "verification_unavailable")
    assert missing["verification"]["decision"] == "INCONCLUSIVE"
    assert missing["original_integrity"] and missing["workspaces_cleaned"]


def test_future_model_origin_is_disabled_without_executing_source(store, measured):
    # Synthetic reserved-origin tag exercises the refusal path, not an actual model proposal.
    source=store.inspect("solver_01.py")
    proposal=parse_proposal(json.dumps(measured["reports"][source.source_file]["attempts"][0]["proposal"]))
    from physicsguard.schemas.repairs import ProcessRun
    result=verify_candidate(store,source,replace(proposal,origin="meta"),development_cases=development_cases())
    assert result.verification.decision == "INCONCLUSIVE"
    assert result.verification.after_development is None
    assert result.verification.after_additional is None


def test_worker_is_separate_and_invalid_caller_cases_raise_before_startup(store):
    source=store.inspect("solver_04.py")
    with source_workspace(source) as root:
        with FixtureWorker(root,source.source_file) as worker:
            assert worker.process.pid != os.getpid()
            limits=Path(f"/proc/{worker.process.pid}/limits").read_text()
            assert re.search(r"Max cpu time\s+10\s+10\s+seconds", limits)
            assert re.search(r"Max address space\s+2147483648\s+2147483648", limits)
        assert worker.process.poll() is not None
        with pytest.raises(ValueError):
            run_source_diagnostics(root,source.source_file,(ExperimentCase("invalid",max_steps=1),))


def test_expensive_timeout_payload_is_rejected_before_execution(store, measured):
    source=store.inspect("solver_02.py")
    supported=parse_proposal(json.dumps(measured["reports"][source.source_file]["attempts"][0]["proposal"]))
    proposal=make_proposal(source,supported.hypothesis,"    scale = 9 ** (9 ** 9)")
    with pytest.raises(ValueError, match="unsupported"):
        validate_proposal(source,proposal)
    assert store.unchanged(source)


def test_external_source_changes_are_rejected_without_overwriting_them(store, measured, tmp_path):
    for name in REVIEWED_HASHES:
        shutil.copyfile(store.root/name,tmp_path/name)
    local=SourceStore(tmp_path)
    source=local.inspect("solver_02.py")
    proposal=parse_proposal(json.dumps(measured["reports"][source.source_file]["attempts"][0]["proposal"]))
    altered=source.source_text+"# concurrent owner edit\n"
    (tmp_path/source.source_file).write_text(altered)
    from physicsguard.schemas.repairs import ProcessRun
    attempt=verify_candidate(local,source,proposal,development_cases=development_cases())
    assert attempt.verification.decision == "REJECTED"
    assert not attempt.original_integrity
    assert (tmp_path/source.source_file).read_text() == altered


def test_bounded_tools_do_not_export_verifier_cases_or_answers(store):
    tools = RepairTools(store)
    source = tools.inspect_solver_source("solver_02.py")
    assert source["lines"][8]["line"] == 9
    run = tools.run_scientific_experiment("solver_02.py",ExperimentCase("dev-tool"))
    evidence = tools.get_diagnostic_report(run["run_id"])
    proposal = tools.propose_localized_patch("solver_02.py",run["run_id"])
    assert proposal.origin == "deterministic"
    verified=tools.verify_candidate_patch(proposal.proposal_id)
    assert verified["decision"] == "ACCEPTED"
    payload=json.dumps([source,evidence,proposal.to_dict(),verified,tools.get_repair_history()],allow_nan=False)
    for private in ("GROUND_TRUTH","before_additional","after_additional","verify-01","reference_patch"):
        assert private not in payload
    verified["stages"]["science"]="tampered"
    assert tools.get_repair_history()[0]["stages"]["science"] == "pass"
    # Duplicate run IDs must not bypass the bounded operation count.
    tools._run_count=16
    with pytest.raises(ValueError,match="budget"):
        tools.run_scientific_experiment("solver_02.py",ExperimentCase("dev-tool"))


def without_runtime(value):
    if isinstance(value,dict):
        return {k:without_runtime(v) for k,v in value.items() if "seconds" not in k}
    if isinstance(value,(tuple,list)):
        return [without_runtime(v) for v in value]
    return value


def test_repair_metrics_json_and_reproducibility(measured):
    metrics=measured["categories"]["known_source_fixtures"]
    assert {k:metrics[k] for k in ("defective_fixtures","detected","useful_localization","valid_proposals","accepted")} == {
        "defective_fixtures":3,"detected":3,"useful_localization":3,"valid_proposals":3,"accepted":3}
    assert metrics["false_repairs"] == 0 and metrics["regression_rate"] == 0
    assert measured["categories"]["unseen_source_mutation_patterns"]["status"] == "unevaluated"
    assert measured["categories"]["negative_proposals"] == {"attempted":14,"accepted":0,"rejected":13,"inconclusive":1}
    assert all(o["attempt"]["proposal"]["origin"] == "human" for o in measured["negative_proposals"])
    replay=evaluate_repairs()
    assert without_runtime(measured) == without_runtime(replay)
    json.loads(json.dumps(measured,allow_nan=False))


def test_source_presentation_robustness_is_static_not_a_repair_score(measured):
    result = measured["categories"]["source_format_robustness"]
    assert (result["samples"], result["recognized"], result["unsupported_recognition"]) == (12, 9, 3)
    for record in result["observations"]:
        assert not record["repair_verified"]
        assert record["execution"] == "unsupported_unreviewed_source"
        assert record["proposal_generated"] == record["proposal_syntax_valid"]
        assert record["ast_identical"] == (record["variation"] != "equivalent_expression")


def test_independently_structured_correct_sources_are_not_false_repairs(measured):
    result = measured["categories"]["independent_correct_sources"]
    assert result["samples"] == 2
    assert result["scientifically_flagged"] == result["unnecessary_proposals"] == 0
    assert result["repair_policy_refusals"] == 2
    for row in result["observations"]:
        assert all(a["status"] == "success" for a in row["report"]["executions"])
        assert not any(d["applicable"] and d["status"] == "inconclusive" for d in row["report"]["diagnostics"])


def test_repair_cli_cannot_overwrite_a_solver_source(store, monkeypatch):
    from benchmarks.source_repair.evaluate import main
    source=store.inspect("solver_01.py")
    monkeypatch.setattr("sys.argv",["evaluate","--output",str(store.root/source.source_file)])
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 2 and store.unchanged(source)
