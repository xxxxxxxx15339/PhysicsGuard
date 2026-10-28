"""Separate source-presentation probes and trusted independent correct controls.

Unreviewed source variations are inspected/compiled only, never executed by the
repair worker. Equivalent-AST probes reuse evidence from their unchanged program.
Recognition is not a new repaired bug or unseen-mechanism generalization.
"""
import ast
from dataclasses import replace
from pathlib import Path

from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.scenarios import development_cases
from physicsguard.repair.policy import validate_proposal
from physicsguard.repair.proposals import propose_repair
from physicsguard.repair.sources import source_hash, SourceStore
from physicsguard.schemas.repairs import SourceSnapshot
from benchmarks.source_variations import correct_flux, correct_convex


def evaluate_variations(reports):
    observations = []
    for name, report in reports.items():
        if not report.attempts:
            continue
        snapshot = report.source
        p = report.attempts[0].proposal
        old = p.old_line
        prefix, value = old.split(" = ", 1)
        equivalent = {"transport_direction": "-1 if speed > 0 else 1",
                      "spatial_scaling": "dt + 0", "periodic_neighbor": "state[+0]"}[p.hypothesis.mechanism]
        for kind, line in (("spacing", prefix+"  =  "+value), ("parentheses", prefix+" = ("+value+")"),
                           ("comment", old+"  # presentation probe"), ("equivalent_expression", prefix+" = "+equivalent)):
            lines = snapshot.source_text.splitlines(True)
            lines[p.line_number-1] = line+"\n"
            text = "".join(lines)
            varied = replace(snapshot, sha256=source_hash(text), source_text=text)
            identical = ast.dump(ast.parse(text)) == ast.dump(ast.parse(snapshot.source_text))
            proposed = propose_repair(varied, report.development.report)
            syntax_valid = False
            if proposed:
                lines[p.line_number-1] = proposed.new_line+"\n"
                compile("".join(lines), name, "exec")  # Syntax only, no execution.
                syntax_valid = True
                try:
                    validate_proposal(varied, proposed)
                except ValueError:
                    pass
                else:
                    raise AssertionError("unreviewed variation escaped source policy")
            observations.append({"source_file": name, "variation": kind, "ast_identical": identical,
                "proposal_generated": proposed is not None, "proposal_syntax_valid": syntax_valid,
                "execution": "unsupported_unreviewed_source", "repair_verified": False})
    return {"samples": len(observations), "recognized": sum(o["proposal_generated"] for o in observations),
            "unsupported_recognition": sum(not o["proposal_generated"] for o in observations),
            "scope": "static pattern recognition and syntax only; no additional repaired bugs", "observations": observations}


def evaluate_correct_sources():
    records = []
    for module in (correct_flux, correct_convex):
        path = Path(module.__file__)
        text = path.read_text()
        snapshot = SourceSnapshot(path.name, source_hash(text), text)
        report = diagnose_solver(module.solve_advection, path.stem, development_cases())
        proposal = propose_repair(snapshot, report)
        try:
            SourceStore(path.parent).inspect(path.name)
        except ValueError:
            refused = True
        else:
            refused = False
        records.append({"source_file": path.name, "report": report.to_dict(), "detected": report.detected,
                        "proposal_generated": proposal is not None, "repair_policy_refused": refused})
    return {"samples": len(records), "scientifically_flagged": sum(r["detected"] for r in records),
            "unnecessary_proposals": sum(r["proposal_generated"] for r in records),
            "repair_policy_refusals": sum(r["repair_policy_refused"] for r in records),
            "scope": "trusted local correct callables; no expansion of source-execution allowlist", "observations": records}
