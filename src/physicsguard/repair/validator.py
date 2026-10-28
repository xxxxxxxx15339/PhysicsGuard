"""Host-owned measured verification. Caller reports/plans never authorize repair."""
from time import perf_counter

from physicsguard.experiments.scenarios import development_cases as default_development_cases
from physicsguard.experiments.runner import validate_cases
from physicsguard.schemas.repairs import PatchApplicationResult, RepairAttempt, VerificationResult
from .coverage import coverage_gaps
from .executor import run_source_diagnostics
from .policy import validate_proposal
from .sources import source_hash
from .verification_cases import independent_plan, plan_problem, case_signature
from .workspace import source_workspace


def compare_regressions(before, after, label):
    old = {(d.diagnostic_id, d.case_ids): d for d in before.diagnostics}
    new = {(d.diagnostic_id, d.case_ids): d for d in after.diagnostics}
    regressions, lost = [], []
    for key, previous in old.items():
        if previous.applicable and previous.status == "pass":
            current = new.get(key)
            identifier = f"{label}:{key[0]}:{','.join(key[1])}"
            if current is None or current.status == "inconclusive" or not current.applicable:
                lost.append(identifier)
            elif current.status == "fail":
                regressions.append(identifier)
    return tuple(regressions), tuple(lost)


def verify_candidate(store, snapshot, proposal, *, development_cases=None, timeout_seconds=2.0):
    """Production host entry: no caller report, custom plan or tolerance argument.

    Development inputs may describe investigator-requested experiments. The host
    reruns their original source and always owns the full independent plan.
    Raw Meta-origin execution remains disabled; provenance is not authorization.
    """
    cases = default_development_cases() if development_cases is None else validate_cases(development_cases)
    return _verify(store, snapshot, proposal, cases, independent_plan(), timeout_seconds)


def _verify_candidate_for_testing(store, snapshot, proposal, development_cases, *, plan, timeout_seconds=2.0):
    """Explicit evaluator/test hook, never dispatched by investigator tools.

    Python privacy is not a security boundary. The host must expose only the
    allowlisted JSON tool dispatcher to a separate future investigator process.
    """
    return _verify(store, snapshot, proposal, validate_cases(development_cases), plan, timeout_seconds)


def _verify(store, snapshot, proposal, cases, plan, timeout_seconds):
    started = perf_counter()
    stages = {name: "pending" for name in ("source", "execution", "science", "additional_cases", "regressions")}
    application = PatchApplicationResult(False, snapshot.sha256, None, proposal.unified_diff, 0)
    before_development = before_additional = after_development = after_additional = None
    regressions, lost, paths = (), (), []
    decision, reasons = "INCONCLUSIVE", ("Required evidence is unavailable",)
    try:
        if proposal.origin == "meta":
            stages["source"] = "unsupported"
            reasons = ("Raw model-origin source execution is disabled",)
        else:
            proposed = validate_proposal(snapshot, proposal)
            if not store.unchanged(snapshot):
                raise ValueError("original source changed since inspection")
            stages["source"] = "pass"
            application = PatchApplicationResult(False, snapshot.sha256, source_hash(proposed), proposal.unified_diff, 1)
            problem = plan_problem(plan, cases)
            if problem:
                stages["additional_cases"] = "inconclusive"
                reasons = (problem,)
            else:
                with source_workspace(snapshot) as root:
                    paths.append(root)
                    before_development = run_source_diagnostics(root, snapshot.source_file, cases,
                        expected_sha256=snapshot.sha256, timeout_seconds=timeout_seconds, audience="investigator")
                    before_additional = run_source_diagnostics(root, snapshot.source_file, plan.additional_cases,
                        expected_sha256=snapshot.sha256, timeout_seconds=timeout_seconds)
                problem = plan_problem(plan, cases, before_development.report)
                if problem:
                    reasons = (problem,)
                    stages["additional_cases"] = "inconclusive"
                else:
                    with source_workspace(snapshot, proposed) as root:
                        paths.append(root)
                        application = PatchApplicationResult(True, snapshot.sha256, proposal.proposed_sha256, proposal.unified_diff, 1)
                        after_development = run_source_diagnostics(root, snapshot.source_file, cases,
                            expected_sha256=proposal.proposed_sha256, timeout_seconds=timeout_seconds, audience="investigator")
                        after_additional = run_source_diagnostics(root, snapshot.source_file, plan.additional_cases,
                            expected_sha256=proposal.proposed_sha256, timeout_seconds=timeout_seconds)
                    runs = (before_development, before_additional, after_development, after_additional)
                    if any(r.status != "completed" or r.report is None for r in runs):
                        reasons = tuple(r.error or r.status for r in runs if r.status != "completed" or r.report is None)
                        stages["execution"] = "inconclusive"
                    else:
                        original = (before_development.report, before_additional.report)
                        patched = (after_development.report, after_additional.report)
                        reg_dev, lost_dev = compare_regressions(original[0], patched[0], "development")
                        reg_add, lost_add = compare_regressions(original[1], patched[1], "additional")
                        regressions, lost = reg_dev + reg_add, lost_dev + lost_add
                        baseline_unavailable = any(a.status != "success" for r in original for a in r.executions)
                        baseline_gaps = coverage_gaps(original[0], cases, require_pass=False) + coverage_gaps(
                            original[1], plan.additional_cases, require_pass=False)
                        candidate_errors = any(a.status == "error" for r in patched for a in r.executions)
                        unavailable = any(a.status == "unavailable" for r in patched for a in r.executions)
                        failed = sorted({d.diagnostic_id for r in patched for d in r.diagnostics
                                         if d.applicable and d.status == "fail"})
                        gaps = coverage_gaps(patched[0], cases, require_pass=True) + coverage_gaps(
                            patched[1], plan.additional_cases, require_pass=True, require_families=True)
                        stages["execution"] = "fail" if candidate_errors else "pass"
                        stages["science"] = "fail" if failed else ("inconclusive" if gaps or unavailable or candidate_errors else "pass")
                        stages["additional_cases"] = "fail" if patched[1].detected else ("inconclusive" if gaps or unavailable or candidate_errors else "pass")
                        stages["regressions"] = "fail" if regressions else ("inconclusive" if lost else "pass")
                        if baseline_unavailable or baseline_gaps:
                            reasons = ("Independent original-source evidence unavailable",) + baseline_gaps + tuple(
                                f"{a.case_id}: {a.error}" for r in original for a in r.executions if a.status != "success")
                            stages["execution"] = "inconclusive"
                        elif candidate_errors or failed or regressions:
                            decision = "REJECTED"
                            reasons = (("Candidate execution contract failed",) if candidate_errors else ()) + (
                                ("Scientific failures: " + ", ".join(failed),) if failed else ()) + (
                                ("Previously passing properties regressed",) if regressions else ())
                        elif gaps or unavailable or lost:
                            reasons = ("Mandatory verification evidence unavailable",) + gaps
                        elif not original[1].detected:
                            decision, reasons = "REJECTED", ("No independently observed baseline defect justifies repair",)
                        else:
                            measured_failures = {d.diagnostic_id for d in original[0].diagnostics if d.applicable and d.status == "fail"}
                            supporting_cases = {c for d in original[0].diagnostics
                                if d.applicable and d.status == "fail" and d.diagnostic_id in proposal.hypothesis.evidence_ids
                                for c in d.case_ids}
                            if (not set(proposal.hypothesis.evidence_ids).issubset(measured_failures)
                                    or not set(proposal.hypothesis.evidence_case_ids).issubset(supporting_cases)):
                                decision, reasons = "REJECTED", ("Proposal evidence is not supported by freshly measured development failures",)
                            else:
                                decision, reasons = "ACCEPTED", ("Per-case independent evidence resolves failures with no observed regression",)
    except (ValueError, SyntaxError, OSError) as error:
        decision, reasons = "REJECTED", (f"Source/policy/integrity validation failed: {error}",)
        stages["source"] = "fail"
        application = PatchApplicationResult(False, snapshot.sha256, None, proposal.unified_diff, 0, str(error))
    intact = store.unchanged(snapshot)
    cleaned = all(not path.exists() for path in paths)
    if not intact or not cleaned:
        decision, reasons = "REJECTED", ("Source integrity or workspace cleanup failed",)
    plan_id = getattr(plan, "plan_id", "invalid-plan")
    result = VerificationResult(decision, plan_id, reasons, stages, before_additional,
        after_development, after_additional, regressions, lost, perf_counter()-started, before_development)
    return RepairAttempt(proposal, application, result, intact, cleaned)
