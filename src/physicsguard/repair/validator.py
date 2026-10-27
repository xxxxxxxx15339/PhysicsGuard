"""Independent measured gate. Proposer assertions never decide acceptance."""
from dataclasses import asdict
import json
from time import perf_counter

from physicsguard.schemas.repairs import (PatchApplicationResult, RepairAttempt, VerificationResult)
from physicsguard.experiments.runner import validate_cases
from .executor import run_source_diagnostics
from .policy import validate_proposal
from .sources import source_hash
from .verification_cases import independent_plan, REQUIRED_DIAGNOSTICS
from .workspace import source_workspace


def case_signature(case):
    values = asdict(case)
    values.pop("case_id")
    values.pop("max_steps")
    return json.dumps(values, sort_keys=True, allow_nan=False)


def compare_regressions(before, after, label):
    keys = lambda d: (d.diagnostic_id, d.case_ids)
    old = {keys(d): d for d in before.diagnostics}
    new = {keys(d): d for d in after.diagnostics}
    regressions, lost = [], []
    for key, previous in old.items():
        if previous.status == "pass":
            current = new.get(key)
            identifier = f"{label}:{key[0]}:{','.join(key[1])}"
            if current is None or current.status == "inconclusive":
                lost.append(identifier)
            elif current.status == "fail":
                regressions.append(identifier)
    return tuple(regressions), tuple(lost)


def verify_candidate(store, snapshot, proposal, development, development_cases, *, plan=None, timeout_seconds=2.0):
    """Host-only gate for reviewed one-line deterministic/human fixture edits.

    No benchmark labels/patches are read. Additional cases are owned here, not
    selected or weakened by a proposal. Arbitrary Meta-origin execution remains
    disabled until a genuine untrusted-execution boundary is available.
    """
    started = perf_counter()
    plan = independent_plan() if plan is None else plan
    stages = {"source": "pending", "execution": "pending", "science": "pending",
              "additional_cases": "pending", "regressions": "pending"}
    application = PatchApplicationResult(False, snapshot.sha256, None, proposal.unified_diff, 0)
    before_additional = after_development = after_additional = None
    regressions, lost = (), ()
    paths = []
    decision, reasons = "INCONCLUSIVE", ("Required evidence is unavailable",)
    try:
        if proposal.origin == "meta":
            stages["source"] = "unsupported"
            reasons = ("Arbitrary model-origin source execution is disabled in this trusted-fixture milestone",)
        else:
            proposed = validate_proposal(snapshot, proposal)
            if not store.unchanged(snapshot):
                raise ValueError("original source changed since inspection")
            stages["source"] = "pass"
            application = PatchApplicationResult(True, snapshot.sha256, source_hash(proposed), proposal.unified_diff, 1)
            known = {case_signature(c) for c in development_cases}
            if development.report:
                known.update(case_signature(r.case) for r in development.report.executions if r.case is not None)
            try:
                validate_cases(plan.additional_cases)
                feasible_plan = True
            except ValueError:
                feasible_plan = False
            if (not feasible_plan or not set(REQUIRED_DIAGNOSTICS).issubset(plan.required_diagnostics)
                    or any(case_signature(c) in known for c in plan.additional_cases)):
                reasons = ("Verification plan lacks independent cases or mandatory diagnostic coverage",)
                stages["additional_cases"] = "inconclusive"
            else:
                with source_workspace(snapshot) as baseline_workspace:
                    paths.append(baseline_workspace)
                    before_additional = run_source_diagnostics(baseline_workspace, snapshot.source_file,
                        plan.additional_cases, timeout_seconds=timeout_seconds)
                with source_workspace(snapshot, proposed) as workspace:
                    paths.append(workspace)
                    after_development = run_source_diagnostics(workspace, snapshot.source_file,
                        development_cases, timeout_seconds=timeout_seconds, audience="investigator")
                    after_additional = run_source_diagnostics(workspace, snapshot.source_file,
                        plan.additional_cases, timeout_seconds=timeout_seconds)
                runs = (before_additional, after_development, after_additional)
                if any(r.status in ("timeout", "resource_limit", "unsupported") or r.report is None for r in runs):
                    reasons = tuple(r.error or r.status for r in runs if r.status != "completed" or r.report is None)
                    stages["execution"] = "inconclusive"
                elif not development.report or development.status != "completed":
                    reasons = ("Development baseline evidence unavailable",)
                    stages["execution"] = "inconclusive"
                else:
                    patched = (after_development.report, after_additional.report)
                    reg_dev, lost_dev = compare_regressions(development.report, patched[0], "development")
                    reg_add, lost_add = compare_regressions(before_additional.report, patched[1], "additional")
                    regressions, lost = reg_dev + reg_add, lost_dev + lost_add
                    execution_errors = any(a.status == "error" for r in patched for a in r.executions)
                    failures = any(d.status == "fail" for r in patched for d in r.diagnostics)
                    stages["execution"] = "fail" if execution_errors else "pass"
                    stages["regressions"] = "fail" if regressions else ("inconclusive" if lost else "pass")
                    missing = [name for name in plan.required_diagnostics if not any(
                        d.diagnostic_id == name and d.status == "pass" for d in patched[1].diagnostics)]
                    unavailable = any(a.status == "unavailable" for r in patched for a in r.executions)
                    uncertain = any(d.applicable and d.status == "inconclusive" and d.diagnostic_id in plan.required_diagnostics
                                    for r in patched for d in r.diagnostics)
                    stages["science"] = "fail" if failures else (
                        "inconclusive" if execution_errors or missing or unavailable or uncertain else "pass")
                    stages["additional_cases"] = "fail" if patched[1].detected else (
                        "inconclusive" if missing or any(a.status != "success" for a in patched[1].executions)
                        or any(d.applicable and d.status == "inconclusive" for d in patched[1].diagnostics) else "pass")
                    if execution_errors or failures or regressions:
                        decision = "REJECTED"
                        reasons = ("Candidate fails execution, a scientific acceptance criterion, or a previously passing property",)
                    elif missing or unavailable or uncertain or lost:
                        reasons = ("Mandatory evidence unavailable or inconclusive: "+", ".join(missing),)
                        stages["science"] = "inconclusive"
                    elif any(a.status != "success" for a in before_additional.report.executions):
                        reasons = ("Independent baseline execution evidence is unavailable",)
                        stages["additional_cases"] = "inconclusive"
                    elif not before_additional.report.detected:
                        decision = "REJECTED"
                        reasons = ("No independently observed baseline defect justifies accepting a repair",)
                    else:
                        decision = "ACCEPTED"
                        reasons = ("Independent additional cases fix observed failures and show no tested regression",)
    except (ValueError, SyntaxError, OSError) as error:
        decision, reasons = "REJECTED", (f"Source/policy validation failed: {error}",)
        stages["source"] = "fail"
        application = PatchApplicationResult(False, snapshot.sha256, None, proposal.unified_diff, 0, str(error))
    intact = store.unchanged(snapshot)
    cleaned = all(not p.exists() for p in paths)
    if not intact or not cleaned:
        decision, reasons = "REJECTED", ("Source integrity or workspace cleanup failed",)
    result = VerificationResult(decision, plan.plan_id, reasons, stages, before_additional,
        after_development, after_additional, regressions, lost, perf_counter()-started)
    return RepairAttempt(proposal, application, result, intact, cleaned)
