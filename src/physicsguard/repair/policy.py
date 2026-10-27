"""One-line arithmetic edits to reviewed fixtures; this is not a Python sandbox."""
import ast
import difflib
import re

from physicsguard.schemas.repairs import RepairProposal, SourceSnapshot
from .sources import MAX_SOURCE_BYTES, REVIEWED_HASHES, source_hash


def localized_diff(name: str, original: str, proposed: str) -> str:
    return "".join(difflib.unified_diff(original.splitlines(True), proposed.splitlines(True),
                                       fromfile=f"a/{name}", tofile=f"b/{name}", n=0))


def parse_localized_diff(diff: str, name: str) -> tuple[int, str, str]:
    """Only one complete replaced line, one file, one zero-context hunk."""
    lines = diff.splitlines()
    if len(lines) != 5 or lines[:2] != [f"--- a/{name}", f"+++ b/{name}"]:
        raise ValueError("expected one-file one-line unified diff")
    match = re.fullmatch(r"@@ -(\d+) \+(\d+) @@", lines[2])
    if not match or match[1] != match[2] or not lines[3].startswith("-") or not lines[4].startswith("+"):
        raise ValueError("unsupported diff hunk")
    return int(match[1]), lines[3][1:], lines[4][1:]


def editable_assignments(tree: ast.AST):
    for function in getattr(tree, "body", ()):
        if isinstance(function, ast.FunctionDef) and function.name == "advance":
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign) or len(node.targets) != 1 or node.lineno != node.end_lineno:
                    continue
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in ("neighbor_offset", "scale"):
                    yield node
                elif (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                      and target.value.id == "upstream"):
                    yield node


def check_candidate(snapshot: SourceSnapshot, proposed: str) -> int:
    """Check the full AST stays identical except one allowlisted assignment RHS.

    Source hashes authenticate reviewed originals. Arithmetic grammar restricts
    candidate changes; OS filesystem/network isolation is still absent. Only
    reviewed local fixture experiments may use this policy/executor.
    """
    if REVIEWED_HASHES.get(snapshot.source_file) != snapshot.sha256 or source_hash(snapshot.source_text) != snapshot.sha256:
        raise ValueError("unreviewed or corrupt original snapshot")
    if len(proposed.encode()) > MAX_SOURCE_BYTES:
        raise ValueError("candidate source size limit exceeded")
    before_lines, after_lines = snapshot.source_text.splitlines(True), proposed.splitlines(True)
    if len(before_lines) != len(after_lines):
        raise ValueError("patch may replace only one existing line")
    changed = [i+1 for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    if len(changed) != 1 or len(after_lines[changed[0]-1]) > 501:
        raise ValueError("patch must change exactly one bounded line")
    line = changed[0]
    before, after = ast.parse(snapshot.source_text), ast.parse(proposed)
    original = next((n for n in editable_assignments(before) if n.lineno == line), None)
    candidate = next((n for n in editable_assignments(after) if n.lineno == line), None)
    if original is None or candidate is None or ast.dump(original.targets[0]) != ast.dump(candidate.targets[0]):
        raise ValueError("only an allowlisted advance assignment expression may change")
    nodes = list(ast.walk(candidate.value))
    allowed = (ast.Name, ast.Load, ast.Constant, ast.BinOp, ast.UnaryOp, ast.IfExp,
               ast.Compare, ast.BoolOp, ast.Subscript, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Gt, ast.GtE, ast.Lt,
               ast.LtE, ast.Eq, ast.NotEq, ast.And, ast.Or)
    if len(nodes) > 64 or any(not isinstance(n, allowed) for n in nodes):
        raise ValueError("candidate expression exceeds restricted arithmetic grammar")
    if any(isinstance(n, ast.Name) and n.id not in {"state", "speed", "dx", "dt", "neighbor_offset"} for n in nodes):
        raise ValueError("candidate references an unsupported name")
    if any(isinstance(n, ast.Constant) and type(n.value) not in (int, float) for n in nodes):
        raise ValueError("only numeric literal constants are supported")
    if ast.dump(original.value) == ast.dump(candidate.value):
        raise ValueError("proposal has no AST expression change")
    original.value = candidate.value
    if ast.dump(before) != ast.dump(after):
        raise ValueError("patch changes code outside its permitted expression")
    compile(proposed, snapshot.source_file, "exec")  # Compile only; never execute in this process.
    return line


def validate_proposal(snapshot: SourceSnapshot, proposal: RepairProposal) -> str:
    if proposal.source_file != snapshot.source_file or proposal.original_sha256 != snapshot.sha256:
        raise ValueError("unexpected source path or stale original hash")
    if proposal.source_file not in REVIEWED_HASHES:
        raise ValueError("source is not allowlisted")
    parsed = parse_localized_diff(proposal.unified_diff, proposal.source_file)
    if parsed != (proposal.line_number, proposal.old_line, proposal.new_line):
        raise ValueError("diff does not match the structured edit")
    lines = snapshot.source_text.splitlines(True)
    if proposal.line_number > len(lines) or lines[proposal.line_number-1] != proposal.old_line + "\n":
        raise ValueError("conflicting original source line")
    lines[proposal.line_number-1] = proposal.new_line + "\n"
    proposed = "".join(lines)
    check_candidate(snapshot, proposed)
    if source_hash(proposed) != proposal.proposed_sha256 or localized_diff(snapshot.source_file, snapshot.source_text, proposed) != proposal.unified_diff:
        raise ValueError("proposed hash or canonical diff mismatch")
    return proposed
