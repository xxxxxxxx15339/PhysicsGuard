"""Investigator-facing JSON view; imports no benchmark registry or ground truth.

    Only this explicit projection should cross a future process boundary. Never
    give an investigator a Python callable/object reference to an evaluator.
"""

from physicsguard.schemas.results import DiagnosticReport


def investigator_view(report: DiagnosticReport) -> dict:
    """Allowlisted experiment evidence, without reference arrays/labels/paths.

    Only reports explicitly marked for the investigator may be projected.
    Audience tagging prevents accidental export, not a hostile Python caller.
    The evaluator and its artifacts still require an OS-enforced boundary.
    """
    if report.audience != "investigator":
        raise ValueError("evaluator-only evidence cannot be exported to the investigator")
    return {"solver_id": report.solver_id,
            "cases": [case.to_dict() for case in report.cases],
            "executions": [run.to_dict() for run in report.executions],
            "diagnostics": [diagnostic.to_dict() for diagnostic in report.diagnostics],
            "elapsed_seconds": report.elapsed_seconds}
