"""One-line arithmetic edits to reviewed fixtures; this is not a Python sandbox."""
import ast
import difflib
import math
import re

from physicsguard.schemas.repairs import RepairProposal, SourceSnapshot
from .sources import MAX_SOURCE_BYTES, REVIEWED_HASHES, source_hash

MAX_EXPRESSION_NODES = 48
MAX_EXPRESSION_DEPTH = 10
MAX_LITERAL_MAGNITUDE = 128


def _numeric_literal(node):
    if not isinstance(node, ast.Constant) or type(node.value) not in (int, float):
        return False
    return abs(node.value) <= MAX_LITERAL_MAGNITUDE and math.isfinite(node.value)


def _index(node):
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value == 0:
        return True
    return (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int
            and node.operand.value == 1)


def validate_expression(value, target):
    """Bounded scalar FV edits: no power, vector arithmetic or dynamic indexing."""
    nodes = list(ast.walk(value))
    def depth(node):
        return 1 + max((depth(child) for child in ast.iter_child_nodes(node)), default=0)
    if len(nodes) > MAX_EXPRESSION_NODES or depth(value) > MAX_EXPRESSION_DEPTH:
        raise ValueError("candidate expression size/depth budget exceeded")
    boundary = isinstance(target, ast.Subscript)

    def scalar(node):
        if _numeric_literal(node):
            return
        if isinstance(node, ast.Name) and node.id in {"speed", "dx", "dt"}:
            return
        if (boundary and isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id == "state" and _index(node.slice)):
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            scalar(node.operand)
            return
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            if isinstance(node.op, ast.Div) and not (
                    isinstance(node.right, ast.Name) and node.right.id == "dx"
                    or _numeric_literal(node.right) and abs(node.right.value) >= 1e-12):
                raise ValueError("division requires dx or a bounded nonzero literal denominator")
            scalar(node.left)
            scalar(node.right)
            return
        if isinstance(node, ast.IfExp):
            condition(node.test)
            scalar(node.body)
            scalar(node.orelse)
            return
        raise ValueError("unsupported FV scalar expression, name, literal or subscript")

    def condition(node):
        if isinstance(node, ast.Compare) and all(isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq)) for op in node.ops):
            scalar(node.left)
            for item in node.comparators:
                scalar(item)
            return
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            for item in node.values:
                condition(item)
            return
        raise ValueError("unsupported scalar condition")

    def neighbor(node):
        if (isinstance(node, ast.Constant) and type(node.value) is int and node.value == 1
                or isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
                and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int and node.operand.value == 1):
            return
        if isinstance(node, ast.IfExp):
            condition(node.test)
            neighbor(node.body)
            neighbor(node.orelse)
            return
        raise ValueError("neighbor selector must choose adjacent offsets +1/-1")

    if isinstance(target, ast.Name) and target.id == "neighbor_offset":
        neighbor(value)
    else:
        scalar(value)


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
    validate_expression(candidate.value, candidate.targets[0])
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
    line = check_candidate(snapshot, proposed)
    target = next(n.targets[0] for n in editable_assignments(ast.parse(proposed)) if n.lineno == line)
    mechanism = ("periodic_neighbor" if isinstance(target, ast.Subscript) else
                 "transport_direction" if target.id == "neighbor_offset" else "spatial_scaling")
    if proposal.hypothesis.mechanism != mechanism:
        raise ValueError("hypothesis does not match the edited assignment")
    if source_hash(proposed) != proposal.proposed_sha256 or localized_diff(snapshot.source_file, snapshot.source_text, proposed) != proposal.unified_diff:
        raise ValueError("proposed hash or canonical diff mismatch")
    return proposed
