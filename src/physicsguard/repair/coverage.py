"""Required per-experiment evidence, separate from numerical tolerance formulas."""
from collections import Counter

from physicsguard.diagnostics.accuracy import transport_direction
from physicsguard.diagnostics._common import measure_safely
from .verification_cases import REQUIRED_DIAGNOSTICS

BASE_FAMILIES = ("conservation", "accuracy", "direction", "finite", "cfl", "boundedness")


def coverage_gaps(report, cases, *, require_pass, require_families=False):
    """Require each expected record, not one unrelated pass per family.

    Inapplicable directions on stationary/ambiguous/discontinuous cases are valid
    but cannot replace an identifying check for each signed moving smooth group.
    """
    if report is None or report.cases != tuple(cases):
        return ("Report does not match the requested case configurations",)
    smooth = next((c for c in cases if c.profile == "sine" and c.mode == 1), cases[0])
    base = smooth.case_id
    expected = {(name, (case.case_id,)) for case in cases for name in BASE_FAMILIES}
    expected.add(("refinement", tuple(f"{base}-n{n}" for n in (64, 128, 256))))
    expected.update({
        ("constant", (f"{base}-constant",)),
        ("translation", (f"{base}-shift", f"{base}-base")),
        ("linearity", (f"{base}-linear", f"{base}-base", f"{base}-other")),
        ("space_scaling", (f"{base}-space-scale", f"{base}-base")),
        ("time_scaling", (f"{base}-time-scale", f"{base}-base")),
        ("periodic_wrap", (f"{base}-periodic-wrap",)),
    })
    counts = Counter((d.diagnostic_id, d.case_ids) for d in report.diagnostics)
    gaps = [f"Missing/duplicate {name}:{','.join(ids)}" for (name, ids) in expected if counts[(name, ids)] != 1]
    if set(counts) - expected:
        gaps.append("Unexpected diagnostic identifiers or supporting cases")
    attempts = {a.case_id: a for a in report.executions}
    if len(attempts) != len(report.executions):
        gaps.append("Duplicate execution identifiers")
    for record in report.diagnostics:
        if record.applicable:
            for identifier in record.case_ids:
                if identifier not in attempts:
                    gaps.append(f"Missing supporting execution:{identifier}")
    by_key = {(d.diagnostic_id, d.case_ids): d for d in report.diagnostics}
    eligible_direction = set()
    for case in cases:
        run = attempts.get(case.case_id)
        if run is None or run.case != case:
            gaps.append(f"Missing execution for {case.case_id}")
            continue
        if run.status != "success":
            continue  # Classified by the gate as execution/unavailable evidence.
        for name in BASE_FAMILIES:
            record = by_key.get((name, (case.case_id,)))
            if record is None:
                continue
            if name == "direction":
                canonical = measure_safely("direction", "Direction applicability", lambda: transport_direction(run))
                if record.applicable != canonical.applicable:
                    gaps.append(f"Direction applicability mismatch:{case.case_id}")
                if canonical.applicable:
                    eligible_direction.add(1 if case.physics.speed > 0 else -1)
            elif not record.applicable:
                gaps.append(f"Required {name} is unavailable:{case.case_id}")
    if require_pass:
        for record in report.diagnostics:
            if record.status == "fail" and not record.applicable:
                gaps.append(f"Inapplicable failure:{record.diagnostic_id}")
            if record.applicable and record.status == "inconclusive":
                gaps.append(f"Inconclusive {record.diagnostic_id}:{','.join(record.case_ids)}")
    if require_families:
        for name in REQUIRED_DIAGNOSTICS:
            if not any(d.diagnostic_id == name and d.applicable and d.status == "pass" for d in report.diagnostics):
                gaps.append(f"No applicable pass for mandatory family:{name}")
        requested_signs = {1 if c.physics.speed > 0 else -1 for c in cases
                           if c.profile == "sine" and c.amplitude != 0 and c.physics.speed != 0 and c.final_time > 0}
        if not requested_signs.issubset(eligible_direction):
            gaps.append("Missing identifying direction evidence for a signed moving group")
    return tuple(sorted(set(gaps)))
