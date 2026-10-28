"""Policy, host verifier and IPC regressions. Fake children are test-owned only."""
import ast
import builtins
from dataclasses import replace
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import numpy as np
import pytest

from physicsguard.experiments.scenarios import cell_averages, development_cases
from physicsguard.repair import validator
from physicsguard.repair._worker import load_checked_code
from physicsguard.repair.executor import FixtureWorker, WorkerFailure, run_source_diagnostics
from physicsguard.repair.policy import validate_proposal
from physicsguard.repair.proposals import make_proposal
from physicsguard.repair.protocol import decode_frame, encode_frame, ProtocolError
from physicsguard.repair.sources import default_source_store, source_hash, read_source
from physicsguard.repair.tools import RepairTools
from physicsguard.repair.verification_cases import independent_plan, plan_problem
from physicsguard.repair.workflow import repair_source
from physicsguard.repair.workspace import source_workspace
from physicsguard.schemas.results import ExperimentCase, SolverExecutionResult, SolverStrategy


@pytest.fixture(scope="module")
def repaired():
    report = repair_source(default_source_store(), "solver_02.py")
    assert report.attempts[0].verification.decision == "ACCEPTED"
    return report


@pytest.mark.parametrize("expression", ["9 ** (9 ** 9)", "dt ** 2", "1e309", "-1e309", "float('inf')",
    "state[dt]", "state[0]", "state", "unknown", "speed.real", "[dt for _ in state]",
    "dt // dx", "dt % dx", "dt / 0", "dt / dt", "True", "'dt'", "128 * " + " * ".join(["128"]*30),
    "9"*350])
def test_bounded_expression_rejects_unsafe_arithmetic(repaired, expression):
    old = repaired.attempts[0].proposal
    proposal = make_proposal(repaired.source, old.hypothesis, "    scale = " + expression)
    with pytest.raises(ValueError):
        validate_proposal(repaired.source, proposal)


@pytest.mark.parametrize("field,value", [("proposed_sha256", "f"*64), ("original_sha256", "f"*64),
    ("old_line", "    scale = dx"), ("new_line", "    scale = dt / 2"), ("source_file", "validator.py")])
def test_structured_patch_fields_cannot_disagree(repaired, field, value):
    with pytest.raises(ValueError):
        validate_proposal(repaired.source, replace(repaired.attempts[0].proposal, **{field: value}))


def test_hypothesis_cannot_claim_different_assignment(repaired):
    p = repaired.attempts[0].proposal
    p = replace(p, hypothesis=replace(p.hypothesis, mechanism="transport_direction"))
    with pytest.raises(ValueError, match="hypothesis"):
        validate_proposal(repaired.source, p)


@pytest.mark.parametrize("role", ["original", "candidate"])
@pytest.mark.parametrize("body_exception", [False, True])
def test_workspace_integrity_checked_on_every_exit(repaired, role, body_exception):
    expected = RuntimeError if body_exception else ValueError
    with pytest.raises(expected) as caught:
        with source_workspace(repaired.source) as root:
            path = root / role / repaired.source.source_file
            path.chmod(0o600)
            path.write_text("corrupted\n")
            if body_exception:
                raise RuntimeError("original body error")
    assert not root.exists()
    if body_exception:
        assert str(caught.value) == "original body error"
        assert any(role + " source was modified" in n for n in caught.value.__notes__)
    assert default_source_store().unchanged(repaired.source)


def test_cleanup_failure_preserves_body_exception(repaired, monkeypatch):
    from tempfile import TemporaryDirectory
    cleanup = TemporaryDirectory.cleanup
    def failing_cleanup(self):
        cleanup(self)
        raise OSError("test cleanup failure after release")
    monkeypatch.setattr(TemporaryDirectory, "cleanup", failing_cleanup)
    with pytest.raises(RuntimeError, match="body") as caught:
        with source_workspace(repaired.source) as root:
            raise RuntimeError("body")
    assert not root.exists()
    assert any("cleanup failed" in note for note in caught.value.__notes__)


def test_fifo_and_ancestor_symlink_are_rejected_without_blocking(tmp_path, repaired):
    os.mkfifo(tmp_path / repaired.source.source_file)
    with pytest.raises(ValueError, match="regular"):
        read_source(tmp_path, repaired.source.source_file)
    link = tmp_path / "link"
    link.symlink_to(default_source_store().root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        read_source(link, repaired.source.source_file)


def test_directory_substitution_between_check_and_open_is_rejected(tmp_path, repaired, monkeypatch):
    folder = tmp_path / "swapped"
    folder.mkdir()
    (folder / repaired.source.source_file).write_text(repaired.source.source_text)
    real_open = os.open
    def race(path, flags, *args, **kwargs):
        if path == "swapped":
            folder.rename(tmp_path / "saved")
            folder.symlink_to(default_source_store().root, target_is_directory=True)
        return real_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", race)
    with pytest.raises(ValueError, match="substitution"):
        read_source(folder, repaired.source.source_file)


def test_mutation_during_snapshot_read_is_rejected(tmp_path, repaired, monkeypatch):
    path = tmp_path / repaired.source.source_file
    path.write_text(repaired.source.source_text)
    original_fstat = os.fstat
    calls = []
    def race(fd):
        calls.append(fd)
        if len(calls) == 2:
            path.write_text(repaired.source.source_text+"# independent edit\n")
        return original_fstat(fd)
    monkeypatch.setattr(os, "fstat", race)
    with pytest.raises(ValueError, match="changed during"):
        read_source(tmp_path, repaired.source.source_file)
    assert path.read_text().endswith("# independent edit\n")


def test_worker_compiles_checked_bytes_instead_of_reopening_source(repaired, monkeypatch):
    original_compile = builtins.compile
    seen = []
    with pytest.raises(ValueError, match="modified"):
        with source_workspace(repaired.source) as root:
            target = root / "candidate" / repaired.source.source_file
            def compile_checked(source, filename, *args, **kwargs):
                if filename == str(target):
                    seen.append(source)
                    target.chmod(0o600)
                    target.write_text("raise RuntimeError('different bytes')\n")
                return original_compile(source, filename, *args, **kwargs)
            monkeypatch.setattr(builtins, "compile", compile_checked)
            code = load_checked_code(root, repaired.source.source_file, repaired.source.sha256)
            assert code.co_name == "<module>"  # Never execute it in the parent.
    assert seen == [repaired.source.source_text.encode()]
    assert not root.exists()


def test_public_verifier_does_not_accept_reports_or_plans(repaired):
    args = (default_source_store(), repaired.source, repaired.attempts[0].proposal)
    for extra in ({"plan": independent_plan()}, {"development": repaired.development}):
        with pytest.raises(TypeError):
            validator.verify_candidate(*args, **extra)


@pytest.mark.parametrize("field,value", [("additional_cases", ()),
    ("additional_cases", (independent_plan().additional_cases[0],)*2),
    ("required_diagnostics", ("direction", "direction")), ("required_diagnostics", ())])
def test_verification_plan_rejects_empty_and_duplicate_records(field, value):
    with pytest.raises(ValueError):
        replace(independent_plan(), **{field:value})


@pytest.mark.parametrize("kind", ["families", "duplicate_physics", "strategy", "budget", "development"])
def test_plan_contract_blocks_inadequate_evidence(kind):
    plan = independent_plan()
    cases = plan.additional_cases
    if kind == "families":
        plan = replace(plan, required_diagnostics=("direction",))
    elif kind == "duplicate_physics":
        plan = replace(plan, additional_cases=cases[:-1]+(replace(cases[0], case_id="renamed"),))
    elif kind == "strategy":
        plan = replace(plan, additional_cases=(replace(cases[0], strategy=SolverStrategy(method="other")),)+cases[1:])
    elif kind == "budget":
        plan = replace(plan, additional_cases=(replace(cases[0], max_steps=1),)+cases[1:])
    else:
        plan = replace(plan, additional_cases=development_cases())
    assert plan_problem(plan, development_cases()) is not None


def test_relabeling_units_does_not_make_development_case_independent():
    from physicsguard.repair.verification_cases import case_signature
    case = development_cases()[0]
    renamed = replace(case, case_id="independent-looking", physics=replace(case.physics, length_unit="renamed"))
    assert case_signature(case) == case_signature(renamed)


def replay_runs(monkeypatch, repaired, change):
    """Test-owned evidence fault injection; production accepts no such reports."""
    v = repaired.attempts[0].verification
    originals = iter((v.before_development, v.before_additional, v.after_development, change(v.after_additional)))
    monkeypatch.setattr(validator, "run_source_diagnostics", lambda *a, **kw: next(originals))
    return validator.verify_candidate(default_source_store(), repaired.source, repaired.attempts[0].proposal)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "inapplicable", "inconclusive"])
def test_every_required_moving_case_needs_its_own_direction_evidence(repaired, monkeypatch, kind):
    def change(run):
        ds = list(run.report.diagnostics)
        target = next(d for d in ds if d.diagnostic_id == "direction" and d.case_ids == ("verify-02",))
        if kind == "missing":
            ds.remove(target)
        elif kind == "duplicate":
            ds.append(target)
        else:
            ds[ds.index(target)] = replace(target, status="inconclusive",
                                          applicable=kind != "inapplicable")
        return replace(run, report=replace(run.report, diagnostics=tuple(ds)))
    result = replay_runs(monkeypatch, repaired, change)
    assert result.verification.decision == "INCONCLUSIVE"
    assert any("direction" in reason.lower() for reason in result.verification.reasons)


def test_aggregate_pass_cannot_replace_missing_supporting_execution(repaired, monkeypatch):
    def change(run):
        return replace(run, report=replace(run.report, executions=tuple(
            a for a in run.report.executions if a.case_id != "verify-01-space-scale")))
    result = replay_runs(monkeypatch, repaired, change)
    assert result.verification.decision == "INCONCLUSIVE"
    assert any("verify-01-space-scale" in reason for reason in result.verification.reasons)


@pytest.mark.parametrize("status", ["timeout", "resource_limit", "execution_error", "protocol_error", "source_mismatch"])
def test_worker_failure_never_accepts_patch(repaired, monkeypatch, status):
    result = replay_runs(monkeypatch, repaired, lambda run: replace(run, status=status, report=None, error=status))
    assert result.verification.decision == "INCONCLUSIVE"
    assert status in result.verification.reasons


def test_baseline_execution_failure_is_inconclusive(repaired, monkeypatch):
    run = replace(repaired.development, status="execution_error", report=None, error="original failed")
    monkeypatch.setattr(validator, "run_source_diagnostics", lambda *a, **kw: run)
    result = validator.verify_candidate(default_source_store(), repaired.source, repaired.attempts[0].proposal)
    assert result.verification.decision == "INCONCLUSIVE"


def test_fabricated_evidence_case_ids_cannot_be_accepted(repaired, monkeypatch):
    v = repaired.attempts[0].verification
    runs = iter((v.before_development, v.before_additional, v.after_development, v.after_additional))
    monkeypatch.setattr(validator, "run_source_diagnostics", lambda *a, **kw: next(runs))
    p = repaired.attempts[0].proposal
    proposal = replace(p, hypothesis=replace(p.hypothesis, evidence_case_ids=("invented",)))
    result = validator.verify_candidate(default_source_store(), repaired.source, proposal)
    assert result.verification.decision == "REJECTED"
    assert "freshly measured" in " ".join(result.verification.reasons)


@pytest.mark.parametrize("frame", [b'{"x":NaN}', b'{"x":1e309}', b'{"x":1,"x":2}', b'[]', b'bad', b'\xff'])
def test_protocol_rejects_malformed_nonfinite_duplicate_json(frame):
    with pytest.raises(ProtocolError):
        decode_frame(frame, 1024)


def test_request_and_response_size_limits_are_enforced():
    with pytest.raises(ProtocolError, match="size"):
        encode_frame({"x":"large"}, 3)
    with pytest.raises(ProtocolError, match="size"):
        decode_frame(b'{"x":1}', 3)


def fake_child(monkeypatch, behavior):
    """Replace Popen only in tests; product has no configurable command argument."""
    popen = subprocess.Popen
    def spawn(command, **kwargs):
        digest = command[-1]
        program = "import sys,json,time,os,signal\n" + \
                  "print(json.dumps({'ready':True,'sha256':"+repr(digest)+"}),flush=True)\n" + \
                  "request=json.loads(sys.stdin.readline())\n" + behavior
        return popen([sys.executable, "-I", "-u", "-c", program], **kwargs)
    monkeypatch.setattr(subprocess, "Popen", spawn)


@pytest.mark.parametrize("behavior,status", [
    ("time.sleep(5)\n", "timeout"),
    ("sys.exit(7)\n", "execution_error"),
    ("os.kill(os.getpid(),signal.SIGKILL)\n", "resource_limit"),
    ("print('not-json',flush=True)\n", "protocol_error"),
    ("print('{\"x\":1e309}',flush=True)\n", "protocol_error"),
    ("print(json.dumps({'request_id':999,'sha256':request['sha256'],'result':{}}),flush=True)\n", "protocol_error"),
    ("print('x'*(2*1024**2+1),flush=True)\n", "protocol_error"),
    ("print('{',end='',flush=True)\ntime.sleep(5)\n", "timeout"),
])
def test_child_failures_are_classified_reaped_and_cleanup(repaired, monkeypatch, behavior, status):
    fake_child(monkeypatch, behavior)
    case = ExperimentCase("ipc-control")
    with source_workspace(repaired.source) as root:
        with FixtureWorker(root, repaired.source.source_file, timeout_seconds=.15) as worker:
            with pytest.raises(WorkerFailure) as caught:
                worker(cell_averages(case), case.config())
            assert caught.value.status == status
            assert worker.process.poll() is not None
            assert worker.process.stdin.closed and worker.process.stdout.closed
            with pytest.raises(WorkerFailure):
                worker(cell_averages(case), case.config())
    assert not root.exists()


def test_parent_rejects_unapproved_candidate_hash(repaired):
    proposed = validate_proposal(repaired.source, repaired.attempts[0].proposal)
    with source_workspace(repaired.source, proposed) as root:
        with pytest.raises(WorkerFailure) as caught:
            with FixtureWorker(root, repaired.source.source_file):
                pytest.fail("stale hash executed")
        assert caught.value.status == "source_mismatch"


def test_startup_failure_reaps_child(repaired, monkeypatch):
    processes = []
    popen = subprocess.Popen
    def capture(*args, **kwargs):
        child = popen(*args, **kwargs)
        processes.append(child)
        return child
    monkeypatch.setattr(subprocess, "Popen", capture)
    def fail(*args):
        raise OSError("controlled descriptor setup failure")
    monkeypatch.setattr(os, "set_blocking", fail)
    with source_workspace(repaired.source) as root:
        with pytest.raises(OSError, match="descriptor"):
            with FixtureWorker(root, repaired.source.source_file):
                pytest.fail("startup failure ignored")
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdin.closed and processes[0].stdout.closed


def test_cpu_limit_exit_is_unavailable_evidence(repaired, monkeypatch):
    fake_child(monkeypatch, "import resource\nresource.setrlimit(resource.RLIMIT_CPU,(1,1))\nwhile True: pass\n")
    case = ExperimentCase("cpu-limit")
    with source_workspace(repaired.source) as root:
        with FixtureWorker(root, repaired.source.source_file, timeout_seconds=4) as worker:
            with pytest.raises(WorkerFailure) as caught:
                worker(cell_averages(case), case.config())
            assert caught.value.status == "resource_limit"
            assert worker.process.poll() is not None


@pytest.mark.parametrize("kind,status", [("nonfinite_output","completed"), ("execution_error","completed"), ("memory","resource_limit")])
def test_numeric_errors_are_distinct_from_protocol_and_resource_failures(repaired, monkeypatch, kind, status):
    error = "MemoryError: constrained allocation" if kind == "memory" else "controlled numeric error"
    template = SolverExecutionResult("worker", ExperimentCase("worker-request"), "error", 0.,
        error=error, error_kind="nonfinite_output" if kind == "nonfinite_output" else "execution_error").to_dict()
    behavior = "result="+repr(template)+"\n" + "while True:\n" + \
        " cfg=request['config']\n" + \
        " for k in ('n_cells','cfl','final_time','max_steps'): result['case'][k]=cfg[k]\n" + \
        " for k in ('speed','x_min','x_max'): result['case']['physics'][k]=cfg[k]\n" + \
        " print(json.dumps({'request_id':request['request_id'],'sha256':request['sha256'],'result':result}),flush=True)\n" + \
        " line=sys.stdin.readline()\n" + \
        " if not line: break\n" + \
        " request=json.loads(line)\n"
    fake_child(monkeypatch, behavior)
    with source_workspace(repaired.source) as root:
        run = run_source_diagnostics(root, repaired.source.source_file, (ExperimentCase("classification"),))
    assert run.status == status
    if status == "completed":
        assert all(a.status == "error" for a in run.report.executions)
        finite = next(d for d in run.report.diagnostics if d.diagnostic_id == "finite")
        assert finite.status == ("fail" if kind == "nonfinite_output" else "inconclusive")


def test_cleanup_terminates_descendants_after_leader_exit(repaired, monkeypatch):
    behavior = "child=os.fork()\n" + \
        "if child==0:\n time.sleep(10)\n os._exit(0)\n" + \
        "open('descendant.pid','w').write(str(child))\n" + \
        "os._exit(7)\n"
    fake_child(monkeypatch, behavior)
    case = ExperimentCase("descendant")
    with source_workspace(repaired.source) as root:
        with FixtureWorker(root, repaired.source.source_file, timeout_seconds=.1) as worker:
            with pytest.raises(WorkerFailure):
                worker(cell_averages(case), case.config())
            pid = int((root / "descendant.pid").read_text())
            # A killed grandchild may remain a zombie until the OS reaps it.
            import time
            for _ in range(50):
                stat = Path(f"/proc/{pid}/stat")
                if not stat.exists() or stat.read_text().split()[2] == "Z":
                    break
                time.sleep(.01)
            else:
                pytest.fail("worker descendant remained running")
            assert worker.process.poll() is not None


def test_tool_json_dispatch_rejects_privileged_arguments():
    tools = RepairTools(default_source_store())
    for op, args in [("verify_candidate_patch", {"proposal_id":"x", "plan":{}}),
                     ("verify_candidate", {}), ("select_localized_edit", {"source_file":"solver_02.py", "run_id":"x", "operation_id":"raw_python"}),
                     ("run_scientific_experiment", {"source_file":"solver_02.py", "case":{"case_id":"x", "max_steps":1}}),
                     ("inspect_solver_source", {"source_file":"../validator.py"})]:
        assert tools.call(op, args) == {"ok":False,"error":"invalid_or_unavailable_operation"}


def test_tool_stable_ids_duplicate_cache_and_bounded_selection():
    tools = RepairTools(default_source_store())
    case = ExperimentCase("same-id")
    run1 = tools.run_scientific_experiment("solver_01.py", case)
    run2 = tools.run_scientific_experiment("solver_02.py", case)
    p1 = tools.propose_localized_patch("solver_01.py", run1["run_id"])
    p2 = tools.propose_localized_patch("solver_02.py", run2["run_id"])
    assert p1.proposal_id != p2.proposal_id
    cached = tools._runs[run2["run_id"]]
    assert tools.run_scientific_experiment("solver_02.py", case) == run2
    assert tools._runs[run2["run_id"]] is cached and tools._run_count == 3
    selection = tools.call("select_localized_edit", {"source_file":"solver_02.py", "run_id":run2["run_id"],
                                                    "operation_id":"normalize_time_by_cell_width"})
    assert selection["ok"] and selection["result"]["origin"] == "deterministic"
    selection["result"]["new_line"] = "mutated"
    assert tools._proposals[p2.proposal_id][1].new_line == "    scale = dt / dx"
    assert tools.call("verify_candidate_patch", {"proposal_id":p2.proposal_id})["result"]["decision"] == "ACCEPTED"
    payload = json.dumps(tools.call("get_repair_history", {}), allow_nan=False)
    assert all(token not in payload for token in ("verify-", "plan_id", "before_additional", "after_additional"))
