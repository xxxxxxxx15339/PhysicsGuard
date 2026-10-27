"""Limited deterministic AST rules driven by observed development failures.

No fixture IDs, benchmark labels, reference patches or verifier cases are inputs.
These rules recognize explicit source patterns; they are not model reasoning or
general-purpose numerical fault localization.
"""
import ast

from physicsguard.schemas.repairs import FaultHypothesis, RepairProposal, SourceSnapshot
from physicsguard.schemas.results import DiagnosticReport
from .policy import editable_assignments, localized_diff
from .sources import source_hash


def make_proposal(snapshot: SourceSnapshot, hypothesis: FaultHypothesis, new_line: str,
                  *, origin="human", expected_effect="Restore the declared physical transport") -> RepairProposal:
    lines = snapshot.source_text.splitlines(True)
    old_line = lines[hypothesis.start_line-1].rstrip("\n")
    lines[hypothesis.start_line-1] = new_line + "\n"
    proposed = "".join(lines)
    digest = source_hash(proposed)
    return RepairProposal("proposal-"+digest[:16], snapshot.source_file, snapshot.sha256, digest,
                          hypothesis, hypothesis.start_line, old_line, new_line,
                          localized_diff(snapshot.source_file, snapshot.source_text, proposed),
                          expected_effect, ("independent_physics_suite", "development_regressions"), origin)


def propose_repair(snapshot: SourceSnapshot, report: DiagnosticReport) -> RepairProposal | None:
    if not report.detected:
        return None
    failures = {d.diagnostic_id for d in report.diagnostics if d.status == "fail"}
    # Pattern predicates inspect AST shape, not filenames or a ground-truth registry.
    for node in editable_assignments(ast.parse(snapshot.source_text)):
        target, value = node.targets[0], node.value
        segment = ast.get_source_segment(snapshot.source_text, value)
        mechanism = replacement = description = None
        required = set()
        if (isinstance(target, ast.Name) and target.id == "neighbor_offset"
                and isinstance(value, ast.IfExp) and segment == "-1 if speed > 0.0 else 1"):
            mechanism, replacement = "transport_direction", "1 if speed > 0.0 else -1"
            required = {"accuracy", "direction"}
            description = "The signed neighbor selection opposes physical velocity; conservation alone cannot detect reversed transport."
        elif (isinstance(target, ast.Name) and target.id == "scale"
              and isinstance(value, ast.Name) and value.id == "dt"):
            mechanism, replacement = "spatial_scaling", "dt / dx"
            required = {"accuracy", "space_scaling", "refinement"}
            description = "The update coefficient has time units without division by cell width; physical scaling and refinement fail."
        elif (isinstance(target, ast.Subscript) and ast.unparse(target) == "upstream[0]"
              and segment == "state[0]"):
            mechanism, replacement = "periodic_neighbor", "state[-1]"
            required = {"conservation", "translation", "periodic_wrap"}
            description = "The incoming seam value uses the first cell itself rather than the periodic upstream neighbor; cyclic symmetry and mass fail."
        if mechanism and required.issubset(failures):
            supports = [d for d in report.diagnostics if d.status == "fail" and d.diagnostic_id in required]
            hypothesis = FaultHypothesis(mechanism, "advance", node.lineno, node.end_lineno, description,
                tuple(sorted(required)), tuple(sorted({c for d in supports for c in d.case_ids})))
            old_line = snapshot.source_text.splitlines()[node.lineno-1]
            # Replace just the RHS in the original physical line; retain the rest of the module.
            prefix = old_line[:value.col_offset]
            return make_proposal(snapshot, hypothesis, prefix+replacement, origin="deterministic",
                                 expected_effect=description)
    return None
